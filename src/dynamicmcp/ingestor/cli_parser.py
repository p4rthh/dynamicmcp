"""Parser for CLI help outputs and command invocations into ToolSpec."""

import re
from typing import Optional
from dynamicmcp.models.spec import (
    ToolSpec,
    EndpointSpec,
    ParameterSpec,
    ParameterLocation,
    IngestType,
)


class CLIHelpParser:
    """Parses CLI help text or CLI command signatures into a ToolSpec."""

    @staticmethod
    def parse(help_text: str, command_name: Optional[str] = None) -> ToolSpec:
        """Parse CLI help output (e.g. from `tool --help`)."""
        lines = help_text.strip().splitlines()
        first_line = lines[0].strip() if lines else "cli_tool"

        # Guess tool name if not provided
        if not command_name:
            match = re.search(r"(?:Usage:\s+|command:\s+)?([a-zA-Z0-9_\-]+)", first_line, re.IGNORECASE)
            if match:
                command_name = match.group(1).replace("-", "_").lower()
            else:
                command_name = "cli_tool"

        # Extract options and arguments
        parameters: list[ParameterSpec] = []
        # Match short/long options, type hints (e.g. TEXT, INTEGER, <arg>), and description
        option_pattern = re.compile(
            r"^\s*(?:(-\w),\s+)?(--[a-zA-Z0-9\-]+)(?:\s+(TEXT|INT|INTEGER|FLOAT|BOOL|BOOLEAN|PATH|FILE|STRING|<[^>]+>))?\s{2,}(.*?)$",
            re.IGNORECASE
        )

        for line in lines:
            m = option_pattern.match(line)
            if m:
                short_flag = m.group(1)
                long_flag = m.group(2)
                type_hint = m.group(3)
                desc = m.group(4) or ""

                param_name = long_flag.lstrip("-").replace("-", "_")
                # Infer type
                if not type_hint:
                    p_type = "boolean"
                elif type_hint.lower() in ("int", "integer", "num", "number", "count", "port"):
                    p_type = "integer"
                elif type_hint.lower() in ("float", "rate"):
                    p_type = "float"
                else:
                    p_type = "string"

                parameters.append(
                    ParameterSpec(
                        name=param_name,
                        type=p_type,
                        location=ParameterLocation.QUERY,
                        required=False,
                        default=False if p_type == "boolean" else None,
                        description=desc.strip(),
                    )
                )

        endpoint = EndpointSpec(
            path=f"/cli/{command_name}",
            method="POST",
            description=f"CLI execution endpoint for {command_name}",
            parameters=parameters,
        )

        return ToolSpec(
            name=f"cli_{command_name}",
            description=f"CLI tool generated from help text for {command_name}",
            target_domain="localhost",
            base_url="http://localhost",
            endpoints=[endpoint],
            source_type=IngestType.CLI,
            raw_input=help_text,
        )
