---
name: dynamicmcp-orchestrator
description: >
  Automatically detects when an external API or CLI tool is missing, synthesizes a new
  FastMCP server from raw specifications (curl, OpenAPI, CLI help), verifies it in an
  isolated sandbox, and hot-registers it into the active Hermes Agent session.
version: 1.0.0
author: DynamicMCP Team
platforms: [linux, macos]
metadata:
  hermes:
    tags: [Infrastructure, MCP, Automation, Security, PersonalAI]
    requires_toolsets: [web, terminal]
    requires_tools: [terminal]
---

# DynamicMCP Orchestrator Skill

## Overview
DynamicMCP provides autonomous personal AI tool creation. When your workflow requires an action for which no built-in tool exists (e.g. querying a new weather service, interacting with an internal REST API, or calling an unfamiliar CLI tool), DynamicMCP will:
1. Parse the API or CLI contract using NVIDIA Nemotron Nano.
2. Synthesize a fully typed, secure FastMCP server using NVIDIA Nemotron 3 Ultra.
3. Verify the generated code via isolated dry-run unit tests.
4. Mount the tool inside an NVIDIA OpenShell container governed by NemoClaw egress policies.
5. Hot-register the tool into your Hermes session without restarting.

## When to Activate
Activate this skill when:
- The user requests an API or CLI command that is missing from `tools/list`.
- The user supplies a raw `curl` snippet, OpenAPI/Swagger fragment, or CLI `--help` text.
- A runtime error occurs due to third-party API drift and automated self-repair is required.

## Available DynamicMCP Tools
- `mcp__dynamicmcp__ingest_spec`: Submit a raw curl, OpenAPI, or CLI help snippet to synthesize a new tool.
- `mcp__dynamicmcp__list_tools`: Inspect all dynamically synthesized tools and their lifecycle states.
- `mcp__dynamicmcp__execute_tool`: Execute a dynamically registered tool directly.
- `mcp__dynamicmcp__deregister_tool`: Remove a tool from the session and persistent store.
