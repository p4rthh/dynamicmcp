"""Unit tests for the Spec Ingestor module."""

import pytest
from dynamicmcp.ingestor import CurlParser, OpenAPIParser, CLIHelpParser, SpecIngestor
from dynamicmcp.models.spec import IngestType, ParameterLocation


def test_curl_parser_open_meteo():
    curl_cmd = (
        'curl -X GET "https://api.open-meteo.com/v1/forecast?latitude=52.52&longitude=13.41&current_weather=true" '
        '-H "Accept: application/json"'
    )
    spec = CurlParser.parse(curl_cmd)

    assert spec.target_domain == "api.open-meteo.com"
    assert spec.base_url == "https://api.open-meteo.com"
    assert len(spec.endpoints) == 1

    ep = spec.endpoints[0]
    assert ep.path == "/v1/forecast"
    assert ep.method == "GET"
    assert len(ep.parameters) == 3

    # Check parameter types
    params_by_name = {p.name: p for p in ep.parameters}
    assert params_by_name["latitude"].type == "float"
    assert params_by_name["latitude"].location == ParameterLocation.QUERY
    assert params_by_name["longitude"].type == "float"
    assert params_by_name["current_weather"].type == "boolean"


def test_curl_parser_post_with_body():
    curl_cmd = (
        'curl -X POST "https://api.github.com/repos/octocat/Hello-World/issues" '
        '-H "Authorization: Bearer my_github_token" '
        '-H "Content-Type: application/json" '
        '-d \'{"title": "Bug found", "body": "Details here"}\''
    )
    spec = CurlParser.parse(curl_cmd)

    assert spec.target_domain == "api.github.com"
    assert spec.endpoints[0].method == "POST"
    assert spec.auth.auth_type.value == "bearer"

    body_params = {p.name: p for p in spec.endpoints[0].parameters if p.location == ParameterLocation.BODY}
    assert "title" in body_params
    assert "body" in body_params


def test_openapi_parser():
    openapi_yaml = """
openapi: 3.0.0
info:
  title: PetStoreAPI
  version: 1.0.0
servers:
  - url: https://petstore.swagger.io/v2
paths:
  /pet/{petId}:
    get:
      summary: Find pet by ID
      parameters:
        - name: petId
          in: path
          required: true
          schema:
            type: integer
      responses:
        '200':
          description: successful operation
"""
    spec = OpenAPIParser.parse(openapi_yaml)

    assert spec.target_domain == "petstore.swagger.io"
    assert spec.base_url == "https://petstore.swagger.io"
    assert len(spec.endpoints) == 1
    assert spec.endpoints[0].path == "/pet/{petId}"
    assert spec.endpoints[0].parameters[0].name == "petId"
    assert spec.endpoints[0].parameters[0].location == ParameterLocation.PATH
    assert spec.endpoints[0].parameters[0].type == "integer"


def test_cli_parser():
    help_text = """
Usage: weather-cli [OPTIONS] COMMAND [ARGS]...

Options:
  -c, --city TEXT       Target city name
  -d, --days INTEGER    Forecast days
  --hourly              Include hourly breakdown
  --help                Show this message and exit.
"""
    spec = CLIHelpParser.parse(help_text, command_name="weather_cli")

    assert spec.name == "cli_weather_cli"
    params = {p.name: p for p in spec.endpoints[0].parameters}
    assert "city" in params
    assert params["city"].type == "string"
    assert "days" in params
    assert params["days"].type == "integer"
    assert "hourly" in params
    assert params["hourly"].type == "boolean"


@pytest.mark.asyncio
async def test_spec_ingestor_auto_detect():
    ingestor = SpecIngestor(offline_mode=True)

    curl_cmd = 'curl -X GET "https://api.open-meteo.com/v1/forecast?latitude=52.52"'
    spec = await ingestor.ingest(curl_cmd)
    assert spec.source_type == IngestType.CURL
    assert spec.target_domain == "api.open-meteo.com"
