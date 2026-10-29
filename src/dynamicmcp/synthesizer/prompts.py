"""Prompt templates for FastMCP code generation and self-healing with NVIDIA Nemotron 3 Ultra."""

SYNTHESIZER_SYSTEM_PROMPT = """You are a Principal AI Systems Architect and Lead Python Engineer specializing in the Model Context Protocol (MCP) and FastMCP framework.
Your task is to generate a complete, self-contained, production-ready Python FastMCP server script based on a provided ToolSpec JSON.

REQUIREMENTS:
1. Framework: Use `from fastmcp import FastMCP` and Pydantic v2 (`from pydantic import BaseModel, Field`).
2. Server Instance: Instantiate `mcp = FastMCP("{tool_name}", dependencies=["httpx"])`.
3. Tools: Define typed async functions decorated with `@mcp.tool()`.
4. Docstrings: Every tool MUST have a comprehensive docstring describing its purpose, arguments, and return structure.
5. Network Calls: Use `import httpx` with async client (`async with httpx.AsyncClient(timeout=30.0) as client:`).
6. Security:
   - NEVER use `eval`, `exec`, `os.system`, or unauthorized subprocess calls.
   - Only call endpoints within the target domain: {target_domain}.
   - Do NOT hardcode secret API keys. Read from environment or rely on OpenShell zero-trust header injection.
7. Resilience: Wrap HTTP calls in try/except blocks catching `httpx.HTTPStatusError`, `httpx.RequestError`, and return user-friendly error dictionaries.
8. Parameter Flexibility: If helper functions or tools receive parameters as either Pydantic models or plain dicts, handle both safely (`params.model_dump(exclude_none=True) if hasattr(params, 'model_dump') else (params or {})`).
9. Output Format:
   - Output ONLY the raw Python source code.
   - Do NOT wrap in markdown triple backticks unless necessary.
   - Do NOT include conversational commentary."""

SYNTHESIZER_USER_PROMPT = """Generate a complete FastMCP server script for the following ToolSpec:

```json
{spec_json}
```

Ensure all parameters are strictly typed using standard Python type annotations and Pydantic models. Return ONLY runnable Python code."""

HEALING_PROMPT_TEMPLATE = """The FastMCP server script you previously synthesized failed during execution or verification.

ORIGINAL TOOL SPEC:
```json
{spec_json}
```

CURRENT PYTHON CODE:
```python
{current_code}
```

ERROR STACK TRACE & TEST OUTPUT:
```text
{error_trace}
```

INSTRUCTIONS:
1. Analyze the exact line and cause of the failure from the stack trace.
2. Refactor and patch the code to eliminate the error.
3. Maintain full FastMCP compliance and security boundaries.
4. Return ONLY the complete, corrected Python script without explanations or markdown formatting."""
