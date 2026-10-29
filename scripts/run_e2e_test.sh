#!/usr/bin/env bash
set -euo pipefail

echo "============================================================"
echo "Running DynamicMCP End-to-End Test Suite..."
echo "============================================================"

source .venv/bin/activate
pytest tests/test_pipeline.py -v --tb=short

echo "Testing CLI direct ingestion..."
python3 -m dynamicmcp.cli ingest "curl -X GET 'https://api.open-meteo.com/v1/forecast?latitude=52.52&longitude=13.41'" --name "cli_weather_test" --offline

echo "Listing registered tools..."
python3 -m dynamicmcp.cli list

echo "============================================================"
echo "All E2E tests verified successfully!"
echo "============================================================"
