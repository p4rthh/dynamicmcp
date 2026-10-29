# DynamicMCP

> **Self-Assembling Model Context Protocol (MCP) Server Factory & Personal Agent Runtime**  
> Built for the **Nebius × NVIDIA Global AI Hackathon** — *Personal AI Track*.

[![Tests](https://img.shields.io/badge/pytest-17%20passed-brightgreen.svg)](tests/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12-blue.svg)](pyproject.toml)
[![MCP](https://img.shields.io/badge/MCP-JSON--RPC_2.0-orange.svg)](https://modelcontextprotocol.io)

---

## 🚀 Overview

**DynamicMCP** observes unfamiliar CLI commands, raw `curl` snippets, and REST/OpenAPI specs, and autonomously writes, tests, sandboxes, and hot-registers typed **FastMCP** servers on the fly into live agent sessions (such as Hermes Agent).

When an agent needs to perform an action for which it lacks a pre-existing tool:
1. **Spec Extraction**: NVIDIA Nemotron Nano extracts typed parameters, HTTP methods, endpoints, and authentication schemes via the Nebius Token Factory.
2. **Code Synthesis**: NVIDIA Nemotron 3 Ultra synthesizes a self-contained Python FastMCP server with Pydantic validation, error handling, and tool docstrings.
3. **AST Validation**: Rejects dangerous calls (`eval`, `exec`, `os.system`, raw `subprocess`) before any execution occurs.
4. **Isolated Verification**: Runs headless dry-run unit tests using Nebius Serverless Jobs.
5. **Automated Self-Healing**: Catches runtime errors and stack traces, prompting Nemotron 3 Ultra to repair the code (up to 3 iterations).
6. **OpenShell Sandboxing**: Automatically generates a NemoClaw YAML security policy restricting egress strictly to the target API host and mounting the tool inside an isolated OpenShell sandbox.
7. **Hot-Registration**: Loads the verified tool into FastMCP and notifies the active Hermes Agent session without restarting the daemon.

---

## 🛠️ Quick Start

### 1. Installation

```bash
git clone https://github.com/your-username/dynamicmcp.git
cd dynamicmcp

# Run automated initialization
./scripts/init_project.sh
```

### 2. Configuration

Copy `.env.example` to `.env` and set your credentials:
```bash
cp .env.example .env
```

```ini
NEBIUS_API_KEY=your_nebius_api_key
NEBIUS_PROJECT_ID=your_nebius_project_id
NEBIUS_TOKEN_FACTORY_URL=https://api.studio.nebius.ai/v1
NEBIUS_JOBS_API_URL=https://api.nebius.ai/v1/jobs
```

### 3. Ingesting an API on the Fly

Pass any raw `curl` command or OpenAPI specification:

```bash
dynamicmcp ingest 'curl -X GET "https://api.open-meteo.com/v1/forecast?latitude=52.52&longitude=13.41&current_weather=true"' --name weather_tool
```

### 4. Inspecting Registered Tools

```bash
dynamicmcp list
```

### 5. Running the Synthesized Tool

```bash
dynamicmcp run dynamic__weather_tool__v1_forecast --args '{"latitude": 52.52, "longitude": 13.41, "current_weather": true}'
```

### 6. Starting FastMCP Server for Hermes Agent

```bash
dynamicmcp serve --port 8000
```

---

## 🧪 Running the Test Suite

Run all unit and integration tests:

```bash
pytest tests/ -v
```

Run the end-to-end integration test:

```bash
./scripts/run_e2e_test.sh
```

---

## 🏛️ Architecture & Documentation

- For deep system design, security threat models, and state diagrams, see [ARCHITECTURE.md](ARCHITECTURE.md).
- For the complete developer handbook and agent execution instructions, see [PROJECT_MANUAL.md](PROJECT_MANUAL.md).

---

## 📄 License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for details.
