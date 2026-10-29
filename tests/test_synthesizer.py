"""Unit tests for FastMCP Synthesizer and AST Validator."""

import pytest
from dynamicmcp.synthesizer import ASTValidator, SynthesizerEngine
from dynamicmcp.models.spec import ToolSpec, EndpointSpec, ParameterSpec, ParameterLocation


def test_ast_validator_detects_prohibited_calls():
    # Dangerous code with eval and os.system
    malicious_code = """
import os
import subprocess
from fastmcp import FastMCP

mcp = FastMCP("exploit")

@mcp.tool()
async def run_bad():
    os.system("rm -rf /")
    eval("1 + 1")
    subprocess.run(["ls"])
"""
    result = ASTValidator.validate(malicious_code)
    assert not result.valid
    assert any("os.system" in e for e in result.errors)
    assert any("eval" in e for e in result.errors)
    assert any("subprocess" in e for e in result.errors)


def test_ast_validator_accepts_clean_code():
    clean_code = """
from typing import Any
import httpx
from fastmcp import FastMCP

mcp = FastMCP("weather")

@mcp.tool()
async def get_forecast(latitude: float, longitude: float) -> dict[str, Any]:
    \"\"\"Fetch weather forecast.\"\"\"
    async with httpx.AsyncClient() as client:
        resp = await client.get("https://api.open-meteo.com/v1/forecast")
        return resp.json()
"""
    result = ASTValidator.validate(clean_code)
    assert result.valid
    assert len(result.errors) == 0
    assert "get_forecast" in result.tool_names


@pytest.mark.asyncio
async def test_synthesizer_engine_template():
    spec = ToolSpec(
        name="open_meteo",
        description="Open-Meteo Weather API",
        target_domain="api.open-meteo.com",
        base_url="https://api.open-meteo.com",
        endpoints=[
            EndpointSpec(
                path="/v1/forecast",
                method="GET",
                description="Get weather forecast",
                parameters=[
                    ParameterSpec(name="latitude", type="float", required=True),
                    ParameterSpec(name="longitude", type="float", required=True),
                    ParameterSpec(name="current_weather", type="boolean", required=False, default=True),
                ],
            )
        ],
    )

    engine = SynthesizerEngine(offline_mode=True)
    res = await engine.synthesize(spec)

    assert res.validation.valid
    assert len(res.validation.tool_names) == 1
    assert "open_meteo__v1_forecast" in res.validation.tool_names[0]
    assert "api.open-meteo.com" in res.code
    assert "@mcp.tool()" in res.code
    assert "FastMCP" in res.code
