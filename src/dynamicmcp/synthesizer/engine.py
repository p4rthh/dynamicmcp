"""Code Synthesizer Engine using NVIDIA Nemotron 3 Ultra via Nebius Token Factory."""

import re
import logging
import httpx
from typing import Optional
from pydantic import BaseModel, Field
from dynamicmcp.models.spec import ToolSpec, ParameterLocation
from dynamicmcp.synthesizer.prompts import (
    SYNTHESIZER_SYSTEM_PROMPT,
    SYNTHESIZER_USER_PROMPT,
)
from dynamicmcp.synthesizer.validator import ASTValidator, ValidationResult
from dynamicmcp.config import settings

logger = logging.getLogger(__name__)


class SynthesisResult(BaseModel):
    """Result of code synthesis."""
    code: str
    validation: ValidationResult
    version_hash: str
    model_used: str


class SynthesizerEngine:
    """Synthesizes FastMCP server code from a ToolSpec."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        token_factory_url: Optional[str] = None,
        model_name: Optional[str] = None,
        offline_mode: Optional[bool] = None,
    ):
        self.api_key = api_key or settings.nebius_api_key
        self.token_factory_url = token_factory_url or settings.nebius_token_factory_url
        self.model_name = model_name or settings.ultra_model
        self.offline_mode = offline_mode if offline_mode is not None else settings.offline_mode

    async def synthesize(self, spec: ToolSpec) -> SynthesisResult:
        """Synthesize a complete FastMCP server script from a ToolSpec."""
        if self.offline_mode or not self.api_key or self.api_key == "mock-key":
            logger.info("Operating in offline or mock mode for code synthesis.")
            code = self._generate_template_code(spec)
            model_used = "template_synthesizer"
        else:
            try:
                code = await self._synthesize_with_ultra(spec)
                model_used = self.model_name
            except Exception as e:
                logger.warning(f"Nemotron Ultra API call failed: {e}. Falling back to template synthesizer.")
                code = self._generate_template_code(spec)
                model_used = "template_fallback"

        # Validate AST & Security
        validation = ASTValidator.validate(code)
        version_hash = spec.compute_version_hash(code)

        return SynthesisResult(
            code=code,
            validation=validation,
            version_hash=version_hash,
            model_used=model_used,
        )

    async def _synthesize_with_ultra(self, spec: ToolSpec) -> str:
        """Call NVIDIA Nemotron 3 Ultra via Nebius Token Factory."""
        system_prompt = SYNTHESIZER_SYSTEM_PROMPT.format(
            tool_name=spec.name,
            target_domain=spec.target_domain,
        )
        user_prompt = SYNTHESIZER_USER_PROMPT.format(
            spec_json=spec.model_dump_json(indent=2)
        )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 4096,
            "extra_body": {
                "enable_thinking": True
            }
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.token_factory_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            message = data["choices"][0]["message"]
            raw_text = message.get("content") or ""
            if not raw_text and message.get("reasoning_content"):
                raw_text = message.get("reasoning_content", "")
            raw_text = raw_text.strip()

            # Clean markdown code markers if model outputs them
            if "```python" in raw_text:
                match = re.search(r"```python\s*(.*?)\s*```", raw_text, re.DOTALL)
                if match:
                    return match.group(1).strip()
            elif "```" in raw_text:
                match = re.search(r"```\s*(.*?)\s*```", raw_text, re.DOTALL)
                if match:
                    return match.group(1).strip()

            return raw_text

    def _generate_template_code(self, spec: ToolSpec) -> str:
        """Generate a production-ready FastMCP server script deterministically."""
        endpoints_code: list[str] = []

        for ep in spec.endpoints:
            # Generate parameter signatures and docstrings
            fn_name = re.sub(r"[^a-zA-Z0-9_]", "_", f"{spec.name}_{ep.path}").strip("_").lower()
            params_sig: list[str] = []
            doc_args: list[str] = []
            query_params: list[str] = []
            body_params: list[str] = []

            for p in ep.parameters:
                py_type = "str"
                if p.type == "integer":
                    py_type = "int"
                elif p.type == "float":
                    py_type = "float"
                elif p.type == "boolean":
                    py_type = "bool"
                elif p.type == "array":
                    py_type = "list"
                elif p.type == "object":
                    py_type = "dict"

                if p.required:
                    params_sig.append(f"{p.name}: {py_type}")
                else:
                    default_repr = repr(p.default) if p.default is not None else "None"
                    params_sig.append(f"{p.name}: Optional[{py_type}] = {default_repr}")

                doc_args.append(f"        {p.name}: {p.description or 'Parameter'}")

                if p.location == ParameterLocation.QUERY:
                    query_params.append(f'"{p.name}": {p.name}')
                elif p.location == ParameterLocation.BODY:
                    body_params.append(f'"{p.name}": {p.name}')

            sig_str = ", ".join(params_sig)
            doc_args_str = "\n".join(doc_args) if doc_args else "        None"

            query_dict_str = "{" + ", ".join(query_params) + "}" if query_params else "{}"
            body_dict_str = "{" + ", ".join(body_params) + "}" if body_params else "None"

            ep_code = f'''
@mcp.tool()
async def {fn_name}({sig_str}) -> dict[str, Any]:
    """{ep.description or f"Execute {ep.method} on {ep.path}"}

    Args:
{doc_args_str}

    Returns:
        JSON response dictionary from the target API endpoint.
    """
    url = f"{spec.base_url.rstrip('/')}{ep.path}"
    raw_params = {query_dict_str}
    params = {{k: v for k, v in raw_params.items() if v is not None}}
    json_body = {body_dict_str}
    if json_body:
        json_body = {{k: v for k, v in json_body.items() if v is not None}}

    headers = {{"Accept": "application/json"}}
    # Zero-trust secret injection is handled at the network boundary

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.request(
                method="{ep.method}",
                url=url,
                params=params if params else None,
                json=json_body if json_body else None,
                headers=headers,
            )
            response.raise_for_status()
            try:
                return response.json()
            except Exception:
                return {{"status_code": response.status_code, "text": response.text}}
        except httpx.HTTPStatusError as e:
            return {{
                "error": "HTTPStatusError",
                "status_code": e.response.status_code,
                "message": str(e),
                "details": e.response.text,
            }}
        except httpx.RequestError as e:
            return {{
                "error": "RequestError",
                "message": f"Network request failed: {{str(e)}}",
            }}
'''
            endpoints_code.append(ep_code)

        full_script = f'''"""FastMCP Server auto-generated by DynamicMCP for {spec.name}.
Target Domain: {spec.target_domain}
Base URL: {spec.base_url}
"""

from typing import Optional, Any
import httpx
from pydantic import BaseModel, Field
from fastmcp import FastMCP

# Initialize FastMCP Server
mcp = FastMCP(
    name="{spec.name}",
    instructions="{spec.description}",
)

{"".join(endpoints_code)}

if __name__ == "__main__":
    mcp.run()
'''
        return full_script
