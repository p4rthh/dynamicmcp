"""End-to-End Pipeline Integration Test."""

import pytest
from pathlib import Path
from dynamicmcp.orchestrator.pipeline import DynamicMCPPipeline
from dynamicmcp.models.tool import ToolLifecycleState
from dynamicmcp.registry.store import SkillStore


@pytest.mark.asyncio
async def test_end_to_end_weather_pipeline(tmp_path: Path):
    db_file = tmp_path / "e2e_skills.db"
    store = SkillStore(db_file)
    pipeline = DynamicMCPPipeline(store=store, offline_mode=True)

    # Raw curl input from user intent
    curl_input = (
        'curl -X GET "https://api.open-meteo.com/v1/forecast?latitude=52.52&longitude=13.41&current_weather=true" '
        '-H "Accept: application/json"'
    )

    # Run the complete autonomous pipeline
    result = await pipeline.create_tool_from_spec(
        raw_input=curl_input,
        suggested_name="open_meteo_berlin",
    )

    # Assert pipeline success and state transitions
    assert result.success, f"Pipeline failed: {result.error_message}"
    assert result.state == ToolLifecycleState.REGISTERED
    assert len(result.registered_tools) >= 1
    assert Path(result.code_path).exists()
    assert Path(result.policy_path).exists()

    # Verify tool is recorded in database
    tool_rec = store.get_tool_by_name("open_meteo_berlin")
    assert tool_rec is not None
    assert tool_rec.state == ToolLifecycleState.REGISTERED
    assert tool_rec.registered_at is not None

    # Execute the synthesized tool live!
    active_tool_name = result.registered_tools[0]
    exec_result = await pipeline.execute_tool(
        active_tool_name,
        latitude=52.52,
        longitude=13.41,
        current_weather=True,
    )

    assert exec_result is not None
    assert isinstance(exec_result, dict)
    # Open-Meteo returns latitude and elevation or error dictionary
    assert "latitude" in exec_result or "status_code" in exec_result or "current_weather" in str(exec_result)
