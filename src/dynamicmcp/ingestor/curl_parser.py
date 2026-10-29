"""Parser for raw curl commands into typed ToolSpec."""

import shlex
import re
from urllib.parse import urlparse, parse_qs, unquote
from typing import Optional, Any
from dynamicmcp.models.spec import (
    ToolSpec,
    EndpointSpec,
    ParameterSpec,
    ParameterLocation,
    AuthSpec,
    AuthType,
    IngestType,
)


def infer_type_from_value(val: str) -> str:
    """Infer primitive type from a string representation."""
    if val.lower() in ("true", "false"):
        return "boolean"
    try:
        int(val)
        return "integer"
    except ValueError:
        pass
    try:
        float(val)
        return "float"
    except ValueError:
        pass
    return "string"


class CurlParser:
    """Parses curl commands into a structured ToolSpec."""

    @staticmethod
    def parse(curl_cmd: str, tool_name: Optional[str] = None) -> ToolSpec:
        """Parse a raw curl command line string into a ToolSpec."""
        # Normalize newlines and continuation slashes
        clean_cmd = curl_cmd.replace("\\\n", " ").replace("\\\r\n", " ").strip()

        try:
            tokens = shlex.split(clean_cmd)
        except Exception:
            # Fallback simple split if shlex fails on unbalanced quotes
            tokens = clean_cmd.split()

        if not tokens:
            raise ValueError("Empty curl command provided")

        if tokens[0].lower() == "curl":
            tokens = tokens[1:]

        method = "GET"
        url = ""
        headers: dict[str, str] = {}
        data_body: Optional[str] = None
        auth_spec = AuthSpec()

        i = 0
        while i < len(tokens):
            token = tokens[i]

            if token in ("-X", "--request") and i + 1 < len(tokens):
                method = tokens[i + 1].upper()
                i += 2
            elif token in ("-H", "--header") and i + 1 < len(tokens):
                header_line = tokens[i + 1]
                if ":" in header_line:
                    k, v = header_line.split(":", 1)
                    headers[k.strip()] = v.strip()
                i += 2
            elif token in ("-d", "--data", "--data-raw", "--data-binary", "--json") and i + 1 < len(tokens):
                data_body = tokens[i + 1]
                if method == "GET":
                    method = "POST"
                i += 2
            elif token in ("-u", "--user") and i + 1 < len(tokens):
                auth_spec.auth_type = AuthType.BASIC
                auth_spec.key_name = tokens[i + 1]
                i += 2
            elif not token.startswith("-") and not url:
                url = token
                i += 1
            else:
                i += 1

        if not url:
            raise ValueError("No valid URL found in curl command")

        # Parse URL
        parsed_url = urlparse(url)
        target_domain = parsed_url.netloc
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        path = parsed_url.path or "/"

        # Extract Query Parameters
        parameters: list[ParameterSpec] = []
        if parsed_url.query:
            query_dict = parse_qs(parsed_url.query, keep_blank_values=True)
            for param_name, param_values in query_dict.items():
                val = param_values[0] if param_values else ""
                val_type = infer_type_from_value(val)
                parameters.append(
                    ParameterSpec(
                        name=param_name,
                        type=val_type,
                        location=ParameterLocation.QUERY,
                        required=True,
                        default=val if val else None,
                        description=f"Query parameter: {param_name}",
                    )
                )

        # Check Authorization Header
        for h_name, h_val in headers.items():
            if h_name.lower() == "authorization":
                if h_val.lower().startswith("bearer "):
                    auth_spec.auth_type = AuthType.BEARER
                    auth_spec.header_name = "Authorization"
                elif h_val.lower().startswith("basic "):
                    auth_spec.auth_type = AuthType.BASIC
                    auth_spec.header_name = "Authorization"
            elif "api-key" in h_name.lower() or "apikey" in h_name.lower() or "token" in h_name.lower():
                auth_spec.auth_type = AuthType.API_KEY
                auth_spec.header_name = h_name

        # Parse Request Body
        body_schema: Optional[dict[str, Any]] = None
        if data_body:
            import json
            try:
                parsed_json = json.loads(data_body)
                body_schema = {"type": "object", "properties": {}}
                if isinstance(parsed_json, dict):
                    for k, v in parsed_json.items():
                        v_type = infer_type_from_value(str(v))
                        parameters.append(
                            ParameterSpec(
                                name=k,
                                type=v_type,
                                location=ParameterLocation.BODY,
                                required=True,
                                default=v,
                                description=f"Body field: {k}",
                            )
                        )
            except Exception:
                body_schema = {"type": "string", "raw": data_body}

        # Determine Tool Name
        if not tool_name:
            domain_slug = target_domain.replace(".", "_").replace("-", "_").lower()
            path_slug = re.sub(r"[^a-zA-Z0-9_]", "_", path).strip("_").lower()
            tool_name = f"{domain_slug}_{path_slug}" if path_slug else domain_slug

        endpoint = EndpointSpec(
            path=path,
            method=method,
            description=f"{method} request to {path}",
            parameters=parameters,
            request_body_schema=body_schema,
        )

        return ToolSpec(
            name=tool_name,
            description=f"Auto-generated tool from curl for {target_domain}{path}",
            target_domain=target_domain,
            base_url=base_url,
            endpoints=[endpoint],
            auth=auth_spec,
            source_type=IngestType.CURL,
            raw_input=curl_cmd,
        )
