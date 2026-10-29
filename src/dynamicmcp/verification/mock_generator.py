"""Synthetic mock input and test harness generator for ToolSpec verification."""

import json
from typing import Any
from dynamicmcp.models.spec import ToolSpec, ParameterSpec


class MockGenerator:
    """Generates synthetic test inputs and pytest harnesses for synthesized FastMCP servers."""

    @staticmethod
    def generate_mock_value(param: ParameterSpec) -> Any:
        """Generate a realistic test value based on parameter metadata."""
        if param.enum_values:
            return param.enum_values[0]

        if param.default is not None:
            return param.default

        p_name = param.name.lower()
        p_type = param.type.lower()

        if p_type in ("float", "number"):
            if "lat" in p_name:
                return 52.52
            elif "lon" in p_name:
                return 13.41
            return 1.0

        elif p_type in ("integer", "int"):
            if "port" in p_name:
                return 8080
            elif "limit" in p_name or "count" in p_name:
                return 10
            return 1

        elif p_type in ("boolean", "bool"):
            return True

        elif p_type in ("array", "list"):
            return ["test_item"]

        elif p_type in ("object", "dict"):
            return {"test_key": "test_value"}

        # Default string heuristics
        if "city" in p_name:
            return "Berlin"
        elif "date" in p_name:
            return "2026-10-24"
        elif "email" in p_name:
            return "test@example.com"
        elif "id" in p_name:
            return "12345"
        return f"mock_{param.name}"

    @classmethod
    def generate_test_inputs(cls, spec: ToolSpec) -> dict[str, dict[str, Any]]:
        """Generate synthetic inputs for each endpoint in the ToolSpec."""
        inputs_per_endpoint: dict[str, dict[str, Any]] = {}
        for ep in spec.endpoints:
            fn_name = f"{spec.name}_{ep.path}".replace("/", "_").replace("-", "_").strip("_").lower()
            inputs_per_endpoint[fn_name] = {
                p.name: cls.generate_mock_value(p)
                for p in ep.parameters
            }
        return inputs_per_endpoint

    @classmethod
    def generate_pytest_script(cls, spec: ToolSpec, tool_module_name: str = "tool") -> str:
        """Generate a complete pytest script to verify the generated tool."""
        test_cases: list[str] = []
        for ep in spec.endpoints:
            fn_name = f"{spec.name}_{ep.path}".replace("/", "_").replace("-", "_").strip("_").lower()
            mock_kwargs = {
                p.name: cls.generate_mock_value(p)
                for p in ep.parameters
            }
            kwargs_json = json.dumps(mock_kwargs)

            test_case = f"""
@pytest.mark.asyncio
async def test_invoke_{fn_name}():
    import inspect
    
    # Locate tool function (by exact name or first exported tool function)
    fn = None
    if hasattr({tool_module_name}, "{fn_name}"):
        fn = getattr({tool_module_name}, "{fn_name}")
    else:
        for attr_name in dir({tool_module_name}):
            val = getattr({tool_module_name}, attr_name)
            if (inspect.iscoroutinefunction(val) or inspect.isfunction(val)) and not attr_name.startswith("_") and attr_name != "main":
                fn = val
                break
                
    assert fn is not None, "No executable tool function found in {tool_module_name}"
    
    # Filter arguments to match function signature
    mock_args = {kwargs_json}
    sig = inspect.signature(fn)
    call_kwargs = {{k: v for k, v in mock_args.items() if k in sig.parameters}}
    
    # Execute tool with synthetic mock inputs
    if inspect.iscoroutinefunction(fn):
        result = await fn(**call_kwargs)
    else:
        result = fn(**call_kwargs)
        
    assert result is not None
    assert "Traceback" not in str(result)
"""
            test_cases.append(test_case)

        script = f"""import pytest
import asyncio
import inspect
import {tool_module_name}

{"".join(test_cases)}
"""
        return script
