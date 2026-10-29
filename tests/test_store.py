"""Tests for SQLite SkillStore."""

import pytest
from pathlib import Path
from dynamicmcp.registry.store import SkillStore
from dynamicmcp.models.tool import ToolRecord, ToolLifecycleState
from dynamicmcp.models.spec import ToolSpec, EndpointSpec, ParameterSpec


def test_skill_store_lifecycle(tmp_path: Path):
    db_file = tmp_path / "test_skills.db"
    store = SkillStore(db_file)

    spec = ToolSpec(
        name="test_weather",
        description="Fetch weather",
        target_domain="api.open-meteo.com",
        base_url="https://api.open-meteo.com",
        endpoints=[
            EndpointSpec(
                path="/v1/forecast",
                method="GET",
                description="Get weather forecast",
                parameters=[ParameterSpec(name="latitude", type="float", required=True)],
            )
        ],
    )

    record = ToolRecord(
        id=spec.id,
        name=spec.name,
        version=spec.version,
        state=ToolLifecycleState.UNRECOGNIZED_TOOL,
        tool_spec_json=spec.model_dump_json(),
        source_type="curl",
        target_domain=spec.target_domain,
    )

    store.save_tool(record)

    # Fetch tool
    retrieved = store.get_tool(spec.id)
    assert retrieved is not None
    assert retrieved.name == "test_weather"
    assert retrieved.state == ToolLifecycleState.UNRECOGNIZED_TOOL

    # Update state
    store.update_tool_state(
        spec.id,
        ToolLifecycleState.SPEC_PARSING,
        trigger="Ingest started",
        metadata={"step": 1},
    )
    retrieved = store.get_tool(spec.id)
    assert retrieved.state == ToolLifecycleState.SPEC_PARSING

    # Transition to REGISTERED
    store.update_tool_state(
        spec.id,
        ToolLifecycleState.REGISTERED,
        trigger="Verification passed and sandbox mounted",
    )
    retrieved = store.get_tool(spec.id)
    assert retrieved.state == ToolLifecycleState.REGISTERED
    assert retrieved.registered_at is not None

    # Test execution log
    store.record_execution(
        tool_id=spec.id,
        execution_id="exec_1",
        input_hash="hash123",
        output_summary="200 OK - sunny",
        duration_ms=120,
        success=True,
    )

    # Test healing log
    store.record_healing_attempt(
        tool_id=spec.id,
        attempt_number=1,
        error_trace="SyntaxError on line 10",
        fix_prompt="Fix syntax error",
        patched_code="print('fixed')",
        verification_result="PASS",
    )
    assert store.get_healing_attempt_count(spec.id) == 1

    # List tools
    all_tools = store.list_tools()
    assert len(all_tools) == 1
    assert all_tools[0].name == "test_weather"
