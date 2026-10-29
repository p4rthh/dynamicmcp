"""Unified Spec Ingestor & Parameter Extractor with Nemotron Nano assistance."""

import re
import json
import logging
import httpx
from typing import Optional, Any
from dynamicmcp.models.spec import ToolSpec, IngestType, EndpointSpec, ParameterSpec
from dynamicmcp.ingestor.curl_parser import CurlParser
from dynamicmcp.ingestor.openapi_parser import OpenAPIParser
from dynamicmcp.ingestor.cli_parser import CLIHelpParser
from dynamicmcp.config import settings

logger = logging.getLogger(__name__)

NANO_SPEC_SYSTEM_PROMPT = """You are an expert API and CLI schema extraction engine powered by NVIDIA Nemotron Nano.
Given user input (raw curl command, OpenAPI fragment, CLI help text, or API description), extract a structured ToolSpec JSON.
Your output must be strictly valid JSON matching this schema:
{
  "name": "string (snake_case tool identifier, e.g. open_meteo_forecast)",
  "description": "string (clear tool description)",
  "target_domain": "string (e.g. api.open-meteo.com)",
  "base_url": "string (e.g. https://api.open-meteo.com)",
  "endpoints": [
    {
      "path": "string (e.g. /v1/forecast)",
      "method": "string (GET, POST, etc.)",
      "description": "string",
      "parameters": [
        {
          "name": "string",
          "type": "string (string|integer|float|boolean|array|object)",
          "location": "string (query|path|header|body)",
          "required": true,
          "default": null,
          "description": "string"
        }
      ]
    }
  ]
}
Do not include markdown code block markers or any commentary outside the JSON."""


class SpecIngestor:
    """Unified spec ingestor that combines rule-based parsers with Nemotron Nano AI extraction."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        token_factory_url: Optional[str] = None,
        model_name: Optional[str] = None,
        offline_mode: Optional[bool] = None,
    ):
        self.api_key = api_key or settings.nebius_api_key
        self.token_factory_url = token_factory_url or settings.nebius_token_factory_url
        self.model_name = model_name or settings.nano_model
        self.offline_mode = offline_mode if offline_mode is not None else settings.offline_mode

    @staticmethod
    def detect_type(raw_input: str) -> IngestType:
        """Heuristically detect the type of input."""
        stripped = raw_input.strip()
        if stripped.startswith("curl ") or "\ncurl " in stripped or "curl -" in stripped:
            return IngestType.CURL
        if (
            '"openapi"' in stripped
            or "openapi:" in stripped
            or '"swagger"' in stripped
            or "swagger:" in stripped
            or '"paths"' in stripped
            or "paths:" in stripped
        ):
            return IngestType.OPENAPI
        if (
            "usage:" in stripped.lower()
            or "options:" in stripped.lower()
            or "flags:" in stripped.lower()
            or "--help" in stripped
        ):
            return IngestType.CLI
        return IngestType.TEXT

    async def ingest(self, raw_input: str, tool_name: Optional[str] = None) -> ToolSpec:
        """Extract a structured ToolSpec from raw input, local file, or remote URL."""
        actual_input = raw_input
        stripped = raw_input.strip()

        # If input is a remote HTTP(S) URL to a spec file, fetch it
        if (stripped.startswith("http://") or stripped.startswith("https://")) and not stripped.startswith("curl"):
            try:
                async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                    resp = await client.get(stripped)
                    if resp.status_code == 200:
                        actual_input = resp.text
                        logger.info(f"Successfully downloaded remote spec from {stripped}")
            except Exception as e:
                logger.warning(f"Failed to fetch remote spec URL: {e}")

        detected = self.detect_type(actual_input)
        logger.info(f"Detected input format: {detected.value}")

        try:
            if detected == IngestType.CURL:
                return CurlParser.parse(actual_input, tool_name=tool_name)
            elif detected == IngestType.OPENAPI:
                return OpenAPIParser.parse(actual_input, tool_name=tool_name)
            elif detected == IngestType.CLI:
                return CLIHelpParser.parse(actual_input, command_name=tool_name)
        except Exception as e:
            logger.warning(f"Deterministic parser failed for {detected.value}: {e}. Falling back to Nemotron Nano.")

        # Fallback to Nemotron Nano via Nebius Token Factory
        return await self._extract_with_nano(actual_input, tool_name)

    async def _extract_with_nano(self, raw_input: str, tool_name: Optional[str] = None) -> ToolSpec:
        """Call NVIDIA Nemotron Nano to extract ToolSpec from unstructured text."""
        if self.offline_mode or not self.api_key or self.api_key == "mock-key":
            logger.info("Operating in offline or mock mode for spec extraction.")
            return self._mock_extraction(raw_input, tool_name)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": NANO_SPEC_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Extract ToolSpec from this input (suggested name: {tool_name or 'auto'}):\n\n{raw_input}",
                },
            ],
            "temperature": 0.1,
            "max_tokens": 1024,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.token_factory_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            message = data["choices"][0]["message"]
            content = message.get("content") or message.get("reasoning_content") or message.get("reasoning") or ""
            content = content.strip()

            # Clean JSON if wrapped in backticks or embedded in text
            if "```" in content:
                match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
                if match:
                    content = match.group(1).strip()
                else:
                    content = re.sub(r"^```(?:json)?\n?", "", content)
                    content = re.sub(r"\n?```$", "", content).strip()
            elif "{" in content and "}" in content:
                start = content.find("{")
                end = content.rfind("}") + 1
                content = content[start:end]

            spec_dict = json.loads(content)
            spec_dict["source_type"] = IngestType.TEXT
            spec_dict["raw_input"] = raw_input
            return ToolSpec(**spec_dict)

    def _mock_extraction(self, raw_input: str, tool_name: Optional[str] = None) -> ToolSpec:
        """Deterministic fallback when running without cloud credentials."""
        # Simple extraction from raw text (e.g. searching for URLs)
        url_match = re.search(r"https?://[^\s\"']+", raw_input)
        if url_match:
            from urllib.parse import urlparse
            url = url_match.group(0)
            parsed = urlparse(url)
            name = tool_name or parsed.netloc.replace(".", "_").replace("-", "_")
            return ToolSpec(
                name=name,
                description=f"Generated tool for {parsed.netloc}",
                target_domain=parsed.netloc,
                base_url=f"{parsed.scheme}://{parsed.netloc}",
                endpoints=[
                    EndpointSpec(
                        path=parsed.path or "/",
                        method="GET",
                        description=f"GET {parsed.path}",
                    )
                ],
                source_type=IngestType.TEXT,
                raw_input=raw_input,
            )

        name = tool_name or "custom_api_tool"
        return ToolSpec(
            name=name,
            description="Auto-generated tool from raw text input",
            target_domain="api.example.com",
            base_url="https://api.example.com",
            endpoints=[
                EndpointSpec(
                    path="/api/action",
                    method="GET",
                    description="Default endpoint",
                )
            ],
            source_type=IngestType.TEXT,
            raw_input=raw_input,
        )
