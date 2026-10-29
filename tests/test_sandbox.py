"""Unit tests for NVIDIA OpenShell & NemoClaw sandbox policies."""

import pytest
import yaml
from pathlib import Path
from dynamicmcp.models.spec import ToolSpec, EndpointSpec, ParameterSpec, AuthSpec, AuthType
from dynamicmcp.sandbox.openshell import PolicyGenerator
from dynamicmcp.sandbox.container import OpenShellRunner


def test_nemoclaw_policy_generation(tmp_path: Path):
    spec = ToolSpec(
        name="weather_tool",
        description="Open-Meteo forecast",
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
        auth=AuthSpec(auth_type=AuthType.BEARER, header_name="Authorization", secret_ref="vault://weather/token"),
    )

    policy_file = tmp_path / "weather_policy.yaml"
    yaml_str = PolicyGenerator.generate_policy(spec, output_path=policy_file)

    assert policy_file.exists()
    policy = yaml.safe_load(yaml_str)

    assert policy["version"] == "1.0"
    assert policy["sandbox"]["name"] == "sandbox-weather-tool"
    assert policy["security_policy"]["default_action"] == "deny"

    # Verify filesystem rules
    fs = policy["security_policy"]["filesystem"]
    assert "/tmp/workspace" in fs["writable_paths"]
    assert "/home/*/.ssh" in fs["blocked_paths"]
    assert "/home/*/.env" in fs["blocked_paths"]

    # Verify network egress rules
    net = policy["security_policy"]["network"]
    assert "api.open-meteo.com" in net["allowed_domains"]
    assert 443 in net["allowed_ports"]
    assert "169.254.169.254" in net["blocked_domains"]

    # Verify zero-trust credentials
    creds = policy["security_policy"]["credentials"]
    assert creds["injection_mode"] == "header"
    assert creds["inject_only_for"][0]["domain"] == "api.open-meteo.com"
    assert creds["inject_only_for"][0]["secret_ref"] == "vault://weather/token"


@pytest.mark.asyncio
async def test_openshell_runner_mount_and_destroy(tmp_path: Path):
    spec = ToolSpec(
        name="test_tool",
        description="Test",
        target_domain="api.example.com",
        base_url="https://api.example.com",
        endpoints=[],
    )

    dummy_code = tmp_path / "tool.py"
    dummy_code.write_text("print('hello')", encoding="utf-8")

    runner = OpenShellRunner(policy_dir=tmp_path / "policies")
    sandbox_id = await runner.mount_sandbox(spec, dummy_code)

    assert sandbox_id == "sandbox-test-tool"
    info = runner.get_sandbox_info(sandbox_id)
    assert info is not None
    assert info["status"] == "ACTIVE"

    destroyed = await runner.destroy_sandbox(sandbox_id)
    assert destroyed
    assert runner.get_sandbox_info(sandbox_id) is None
