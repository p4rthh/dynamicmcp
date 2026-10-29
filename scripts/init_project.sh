#!/usr/bin/env bash
set -euo pipefail

echo "============================================================"
echo "Initializing DynamicMCP Environment..."
echo "============================================================"

# Create venv if not exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -e ".[dev]"

# Ensure directories
python3 -c "from dynamicmcp.config import settings; settings.ensure_directories(); print('Directories initialized.')"

echo "Running smoke tests..."
pytest tests/ -q

echo "============================================================"
echo "DynamicMCP initialization complete!"
echo "Run: dynamicmcp --help"
echo "============================================================"
