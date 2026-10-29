"""Unit tests for the FastMCP Registry Manager and Hot Reload Orchestrator."""

import pytest
from pathlib import Path
from fastmcp import FastMCP
from dynamicmcp.registry.manager import RegistryManager
from dynamicmcp.registry.store import SkillStore
from dynamicmcp.models.tool import ToolRecord, ToolLifecycleState
from dynamicmcp.models.spec import ToolSpec


@pytest.mark.asyncio
async def test_registry_manager_direct_registration():
    mcp = FastMCP("test_mcp")
    reg = RegistryManager(mcp)

    async def sample_calc(a: int, b: int) -> dict[str, int]:
        """Add two numbers."""
        return {"result": a + b}

    reg_name = reg.register_tool_function(
        tool_name="add_numbers",
        tool_function=sample_calc,
        description="Addition tool",
    )

    assert reg_name == "dynamic__add_numbers"
    tools = reg.list_registered_tools()
    assert len(tools) == 1
    assert tools[0]["name"] == "dynamic__add_numbers"

    # Execute tool
    res = await reg.execute_tool("dynamic__add_numbers", a=5, b=10)
    assert res == {"result": 15}

    # Deregister
    dereg = reg.deregister_tool("add_numbers")
    assert dereg
    assert len(reg.list_registered_tools()) == 0


@pytest.mark.asyncio
async def test_registry_manager_load_from_file(tmp_path: Path):
    mcp = FastMCP("file_mcp")
    reg = RegistryManager(mcp)

    code = """
from fastmcp import FastMCP

mcp = FastMCP("demo")

@mcp.tool()
async def get_status(service_name: str) -> dict[str, str]:
    \"\"\"Check service status.\"\"\"
    return {"service": service_name, "status": "UP"}
"""
    script_path = tmp_path / "demo_tool.py"
    script_path.write_text(code, encoding="utf-8")

    registered = reg.load_and_register_from_file(
        source_path=script_path,
        tool_name="demo",
    )

    assert len(registered) >= 1
    assert any("get_status" in name for name in registered)

    # Execute
    res = await reg.execute_tool(registered[0], service_name="auth-service")
    assert res == {"service": "auth-service", "status": "UP"}
