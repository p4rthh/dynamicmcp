"""Parser for OpenAPI 3.0 / 3.1 and Swagger specs into ToolSpec."""

import yaml
import json
import re
from urllib.parse import urlparse
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


class OpenAPIParser:
    """Parses OpenAPI and Swagger specifications into ToolSpec."""

    @staticmethod
    def parse(spec_text: str, tool_name: Optional[str] = None) -> ToolSpec:
        """Parse raw JSON or YAML OpenAPI specification."""
        try:
            data = yaml.safe_load(spec_text)
        except Exception:
            try:
                data = json.loads(spec_text)
            except Exception as e:
                raise ValueError(f"Failed to parse OpenAPI document: {e}")

        if not isinstance(data, dict):
            raise ValueError("Invalid OpenAPI format: root element must be a dictionary")

        info = data.get("info", {})
        title = info.get("title", "api_tool")
        description = info.get("description", f"API tool generated from OpenAPI spec {title}")

        # Extract Base URL & Target Domain
        base_url = "https://api.example.com"
        target_domain = "api.example.com"

        if "servers" in data and isinstance(data["servers"], list) and data["servers"]:
            server_url = data["servers"][0].get("url", "")
            if server_url.startswith("http"):
                parsed = urlparse(server_url)
                base_url = f"{parsed.scheme}://{parsed.netloc}"
                target_domain = parsed.netloc
        elif "host" in data:
            schemes = data.get("schemes", ["https"])
            scheme = schemes[0] if schemes else "https"
            host = data["host"]
            base_url = f"{scheme}://{host}"
            target_domain = host

        # Extract Endpoints
        endpoints: list[EndpointSpec] = []
        paths = data.get("paths", {})

        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue

            for method_name, op in path_item.items():
                if method_name.lower() not in ("get", "post", "put", "delete", "patch"):
                    continue

                op_desc = op.get("summary") or op.get("description") or f"{method_name.upper()} {path}"
                parameters: list[ParameterSpec] = []

                # Path-level parameters
                raw_params = list(path_item.get("parameters", []))
                # Operation-level parameters
                raw_params.extend(op.get("parameters", []))

                for p in raw_params:
                    if not isinstance(p, dict):
                        continue
                    p_name = p.get("name", "")
                    p_in = p.get("in", "query").lower()
                    p_req = p.get("required", False)
                    p_desc = p.get("description", "")
                    p_schema = p.get("schema", {})
                    p_type = p_schema.get("type", "string") if isinstance(p_schema, dict) else "string"

                    loc = ParameterLocation.QUERY
                    if p_in == "path":
                        loc = ParameterLocation.PATH
                    elif p_in == "header":
                        loc = ParameterLocation.HEADER
                    elif p_in == "body":
                        loc = ParameterLocation.BODY

                    parameters.append(
                        ParameterSpec(
                            name=p_name,
                            type=p_type,
                            location=loc,
                            required=p_req,
                            default=p_schema.get("default") if isinstance(p_schema, dict) else None,
                            description=p_desc,
                            enum_values=p_schema.get("enum") if isinstance(p_schema, dict) else None,
                        )
                    )

                # Request body parameters (OpenAPI 3)
                request_body = op.get("requestBody", {})
                body_schema = None
                if isinstance(request_body, dict):
                    content = request_body.get("content", {})
                    json_media = content.get("application/json", {})
                    if "schema" in json_media:
                        body_schema = json_media["schema"]
                        # Extract top-level properties as parameters
                        if isinstance(body_schema, dict) and body_schema.get("type") == "object":
                            props = body_schema.get("properties", {})
                            req_list = body_schema.get("required", [])
                            for prop_name, prop_spec in props.items():
                                parameters.append(
                                    ParameterSpec(
                                        name=prop_name,
                                        type=prop_spec.get("type", "string"),
                                        location=ParameterLocation.BODY,
                                        required=prop_name in req_list,
                                        description=prop_spec.get("description", ""),
                                    )
                                )

                endpoints.append(
                    EndpointSpec(
                        path=path,
                        method=method_name.upper(),
                        description=op_desc,
                        parameters=parameters,
                        request_body_schema=body_schema,
                    )
                )

        # Name sanitization
        if not tool_name:
            clean_name = re.sub(r"[^a-zA-Z0-9_]", "_", title).strip("_").lower()
            tool_name = clean_name or "openapi_tool"

        return ToolSpec(
            name=tool_name,
            description=description,
            target_domain=target_domain,
            base_url=base_url,
            endpoints=endpoints,
            source_type=IngestType.OPENAPI,
            raw_input=spec_text,
        )
