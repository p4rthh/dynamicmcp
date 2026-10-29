"""Tests for FastAPI backend server and REST endpoints."""

import pytest
from fastapi.testclient import TestClient
from dynamicmcp.server import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_system_status_endpoint(client):
    """Verify /api/system returns diagnostic and model information."""
    resp = client.get("/api/system")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "HEALTHY"
    assert "nebius_token_factory" in data
    assert "sandbox" in data
    assert "metrics" in data


def test_presets_endpoint(client):
    """Verify /api/presets returns the demonstration templates."""
    resp = client.get("/api/presets")
    assert resp.status_code == 200
    presets = resp.json()
    assert len(presets) >= 4
    preset_ids = [p["id"] for p in presets]
    assert "open-meteo-weather" in preset_ids
    assert "nasa-mars-weather" in preset_ids


def test_assemble_and_list_tools(client):
    """Verify assembling a tool via /api/pipeline/assemble and querying /api/tools."""
    payload = {
        "input": "curl -X GET 'https://api.test-exchange.org/v1/rates?base=EUR'",
        "name": "test_exchange_api",
        "offline": True,
    }
    resp = client.post("/api/pipeline/assemble", json=payload)
    assert resp.status_code == 200
    result = resp.json()
    assert result["success"] is True
    assert result["tool_name"] == "test_exchange_api"
    assert result["state"] == "REGISTERED"

    # List tools
    list_resp = client.get("/api/tools")
    assert list_resp.status_code == 200
    tools = list_resp.json()
    assert any(t["name"] == "test_exchange_api" for t in tools)

    # Get details
    detail_resp = client.get(f"/api/tools/{result['tool_id']}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["record"]["name"] == "test_exchange_api"
    assert detail["generated_code"] is not None
    assert detail["policy_yaml"] is not None


def test_frontend_html_served(client):
    """Verify that frontend root / serves index.html."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert "DynamicMCP" in resp.text
    assert "<div id=\"root\">" in resp.text

