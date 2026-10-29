"""Unit tests for the Verification Runner module."""

import pytest
from dynamicmcp.models.spec import ToolSpec, EndpointSpec, ParameterSpec
from dynamicmcp.synthesizer.engine import SynthesizerEngine
from dynamicmcp.verification.runner import VerificationRunner


@pytest.mark.asyncio
async def test_verification_runner_passes_clean_tool():
    spec = ToolSpec(
        name="test_weather_verifier",
        description="Fetch weather",
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
                ],
            )
        ],
    )

    # Synthesize clean tool
    synthesizer = SynthesizerEngine(offline_mode=True)
    synth_res = await synthesizer.synthesize(spec)

    # Run verification
    runner = VerificationRunner(offline_mode=True)
    result = await runner.verify(spec, synth_res.code)

    assert result.passed
    assert result.exit_code == 0
    assert result.tests_run >= 1


@pytest.mark.asyncio
async def test_verification_runner_catches_failing_tool():
    spec = ToolSpec(
        name="broken_tool",
        description="Intentionally broken tool",
        target_domain="api.example.com",
        base_url="https://api.example.com",
        endpoints=[
            EndpointSpec(
                path="/broken",
                method="GET",
                description="Broken",
            )
        ],
    )

    # Synthesize intentionally broken code (syntax error or exception)
    broken_code = """
import pytest
from fastmcp import FastMCP

mcp = FastMCP("broken")

@mcp.tool()
async def broken_tool__broken():
    raise RuntimeError("Simulated internal crash")
"""

    runner = VerificationRunner(offline_mode=True)
    result = await runner.verify(spec, broken_code)

    assert not result.passed
    assert result.exit_code != 0
    assert "Simulated internal crash" in result.error_trace or "RuntimeError" in result.error_trace
