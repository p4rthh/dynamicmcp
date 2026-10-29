"""Unit tests for the Self-Healing Loop."""

import pytest
from pathlib import Path
from dynamicmcp.models.spec import ToolSpec, EndpointSpec, ParameterSpec
from dynamicmcp.models.tool import ToolLifecycleState, ToolRecord
from dynamicmcp.verification.result_parser import VerificationResult
from dynamicmcp.healing.loop import HealingLoop
from dynamicmcp.registry.store import SkillStore


@pytest.mark.asyncio
async def test_healing_loop_repairs_broken_code(tmp_path: Path):
    db_file = tmp_path / "test_healing.db"
    store = SkillStore(db_file)

    spec = ToolSpec(
        name="healed_tool",
        description="Tool that needs healing",
        target_domain="api.open-meteo.com",
        base_url="https://api.open-meteo.com",
        endpoints=[
            EndpointSpec(
                path="/v1/forecast",
                method="GET",
                description="Weather",
                parameters=[ParameterSpec(name="latitude", type="float", required=True)],
            )
        ],
    )

    record = ToolRecord(
        id=spec.id,
        name=spec.name,
        version=spec.version,
        state=ToolLifecycleState.DRY_RUN_VERIFICATION,
        tool_spec_json=spec.model_dump_json(),
        source_type="curl",
    )
    store.save_tool(record)

    broken_code = """
from fastmcp import FastMCP
mcp = FastMCP("healed_tool")
# Syntax error intentionally introduced
def broken_syntax(
"""

    initial_verification = VerificationResult(
        passed=False,
        exit_code=1,
        error_trace="SyntaxError: unexpected EOF while parsing",
    )

    healing_loop = HealingLoop(store=store, offline_mode=True)
    res = await healing_loop.heal(spec, broken_code, initial_verification)

    assert res.success
    assert not res.quarantined
    assert res.attempts_used == 1
    assert res.patched_code is not None

    # Check that store recorded the healing attempt
    count = store.get_healing_attempt_count(spec.id)
    assert count == 1
