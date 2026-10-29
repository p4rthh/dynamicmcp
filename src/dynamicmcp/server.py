"""FastAPI backend server for DynamicMCP Web UI and REST API."""

import os
import json
import time
from pathlib import Path
from typing import Optional, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from dynamicmcp.orchestrator.pipeline import DynamicMCPPipeline
from dynamicmcp.models.tool import ToolLifecycleState, ToolRecord
from dynamicmcp.registry.store import SkillStore
from dynamicmcp.config import settings

# Global pipeline instance
pipeline: Optional[DynamicMCPPipeline] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for FastAPI to initialize DynamicMCP pipeline."""
    global pipeline
    settings.ensure_directories()
    pipeline = DynamicMCPPipeline()
    yield


app = FastAPI(
    title="DynamicMCP Server",
    description="REST API & Web UI for self-assembling FastMCP servers powered by Nebius and NVIDIA.",
    version="0.1.0",
    lifespan=lifespan,
)

# Enable CORS for local development (e.g. Vite dev server on port 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request & Response Models
class AssembleRequest(BaseModel):
    input: str = Field(..., description="Raw curl command, OpenAPI spec URL/content, or CLI help string.")
    name: Optional[str] = Field(None, description="Optional custom snake_case tool name.")
    offline: Optional[bool] = Field(None, description="Force offline/mock mode.")


class ExecuteRequest(BaseModel):
    arguments: dict[str, Any] = Field(default_factory=dict, description="Arguments to pass to the tool function.")


PRESETS = [
    {
        "id": "open-meteo-weather",
        "title": "Open-Meteo Weather Forecast",
        "category": "cURL REST",
        "icon": "cloud-sun",
        "description": "Live weather forecast query with latitude, longitude, and current weather flags.",
        "input": "curl -X GET 'https://api.open-meteo.com/v1/forecast?latitude=52.52&longitude=13.41&current_weather=true'",
        "suggested_name": "open_meteo_forecast",
        "sample_args": {"latitude": 52.52, "longitude": 13.41, "current_weather": True},
    },
    {
        "id": "nasa-mars-weather",
        "title": "NASA InSight Mars Weather",
        "category": "Authenticated API",
        "icon": "rocket",
        "description": "Martian weather telemetry from Elysium Planitia with API key authentication.",
        "input": "curl -X GET 'https://api.nasa.gov/insight_weather/?api_key=DEMO_KEY&feedtype=json&ver=1.0'",
        "suggested_name": "nasa_mars_weather",
        "sample_args": {"api_key": "DEMO_KEY", "feedtype": "json", "ver": "1.0"},
    },
    {
        "id": "world-bank-data360",
        "title": "World Bank Data360 OpenAPI",
        "category": "Remote OpenAPI Spec",
        "icon": "globe",
        "description": "Full remote OpenAPI specification fetched live from World Bank GitHub repository.",
        "input": "https://raw.githubusercontent.com/worldbank/open-api-specs/refs/heads/main/Data360%20Open_API.json",
        "suggested_name": "world_bank_data360",
        "sample_args": {
            "DATABASE_ID": "WB_WDI",
            "INDICATOR": "WB_WDI_SP_POP_TOTL",
            "REF_AREA": "USA",
            "timePeriodFrom": "2020",
            "timePeriodTo": "2022",
        },
    },
    {
        "id": "exchange-rates",
        "title": "Real-Time Exchange Rates",
        "category": "Financial API",
        "icon": "coins",
        "description": "Real-time foreign currency exchange rates base USD.",
        "input": "curl -X GET 'https://open.er-api.com/v6/latest/USD'",
        "suggested_name": "exchange_rates_usd",
        "sample_args": {},
    },
    {
        "id": "github-search",
        "title": "GitHub Repositories Search",
        "category": "Developer API",
        "icon": "git-branch",
        "description": "Public GitHub REST search endpoint querying repository trends.",
        "input": "curl -X GET 'https://api.github.com/search/repositories?q=language:python&sort=stars&order=desc'",
        "suggested_name": "github_repo_search",
        "sample_args": {"q": "language:python", "sort": "stars", "order": "desc"},
    },
]


@app.get("/api/system")
async def get_system_status():
    """Retrieve system diagnostics, configured Nebius models, and sandbox state."""
    global pipeline
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    store = pipeline.store
    tools = store.list_tools()
    registered_tools = [t for t in tools if t.state == ToolLifecycleState.REGISTERED]

    # Check Nebius API key status
    api_key_configured = bool(settings.nebius_api_key and settings.nebius_api_key != "mock-key")
    masked_key = (
        f"{settings.nebius_api_key[:6]}...{settings.nebius_api_key[-4:]}"
        if api_key_configured and len(settings.nebius_api_key) > 12
        else "Offline / Mock"
    )

    return {
        "status": "HEALTHY",
        "nebius_token_factory": {
            "configured": api_key_configured,
            "url": settings.nebius_token_factory_url,
            "masked_key": masked_key,
            "nano_model": settings.nano_model,
            "ultra_model": settings.ultra_model,
        },
        "sandbox": {
            "openshell_available": pipeline.sandbox.is_openshell_available(),
            "active_sandboxes_count": len(pipeline.sandbox._active_sandboxes),
            "policy_dir": str(pipeline.sandbox.policy_dir),
        },
        "metrics": {
            "total_tools": len(tools),
            "registered_tools_count": len(registered_tools),
            "quarantined_tools_count": len([t for t in tools if t.state == ToolLifecycleState.QUARANTINED]),
        },
    }


@app.get("/api/presets")
async def get_presets():
    """Get list of curated pre-built demonstration requests."""
    return PRESETS


@app.post("/api/pipeline/assemble")
async def assemble_tool(req: AssembleRequest):
    """Run the complete DynamicMCP pipeline to ingest, synthesize, verify, sandbox, and register a tool."""
    global pipeline
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    raw_input = req.input.strip()
    if not raw_input:
        raise HTTPException(status_code=400, detail="Input cannot be empty")

    try:
        # Check if caller wants specific offline override
        active_pipeline = pipeline
        if req.offline is not None and req.offline != pipeline.offline_mode:
            active_pipeline = DynamicMCPPipeline(offline_mode=req.offline)

        result = await active_pipeline.create_tool_from_spec(raw_input, suggested_name=req.name)

        # Retrieve stored details if available
        tool_record = active_pipeline.store.get_tool(result.tool_id) or active_pipeline.store.get_tool_by_name(result.tool_name)
        tool_spec_dict = None
        if tool_record and tool_record.tool_spec_json:
            try:
                tool_spec_dict = json.loads(tool_record.tool_spec_json)
            except Exception:
                pass

        policy_yaml_content = None
        if tool_record and tool_record.policy_yaml and Path(tool_record.policy_yaml).exists():
            policy_yaml_content = Path(tool_record.policy_yaml).read_text(encoding="utf-8")

        return {
            "success": result.success,
            "tool_id": result.tool_id,
            "tool_name": result.tool_name,
            "state": result.state.value if isinstance(result.state, ToolLifecycleState) else result.state,
            "registered_tools": result.registered_tools,
            "code_path": result.code_path,
            "policy_path": result.policy_path,
            "duration_ms": result.duration_ms,
            "error_message": result.error_message,
            "tool_spec": tool_spec_dict,
            "generated_code": tool_record.generated_code if tool_record else None,
            "policy_yaml": policy_yaml_content,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")


@app.get("/api/tools")
async def list_tools(state: Optional[str] = Query(None)):
    """List all assembled tools with lifecycle state and metadata."""
    global pipeline
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    filter_state = None
    if state:
        try:
            filter_state = ToolLifecycleState(state)
        except ValueError:
            pass

    records = pipeline.store.list_tools(state=filter_state)
    results = []
    for r in records:
        spec_dict = None
        if r.tool_spec_json:
            try:
                spec_dict = json.loads(r.tool_spec_json)
            except Exception:
                pass

        # Match active registered MCP function names
        matching_reg_names = []
        if r.state == ToolLifecycleState.REGISTERED:
            for k, meta in pipeline.registry._registered_tools.items():
                if meta.get("tool_id") == r.id or meta.get("tool_name") == r.name or k.startswith(f"{pipeline.registry.NAMESPACE_PREFIX}__{r.name}"):
                    matching_reg_names.append(k)
            if not matching_reg_names:
                matching_reg_names = [f"{pipeline.registry.NAMESPACE_PREFIX}__{r.name}"]

        results.append({
            "id": r.id,
            "name": r.name,
            "version": r.version,
            "state": r.state.value if isinstance(r.state, ToolLifecycleState) else r.state,
            "target_domain": r.target_domain,
            "source_type": r.source_type,
            "created_at": r.created_at,
            "updated_at": r.updated_at,
            "registered_at": r.registered_at,
            "quarantine_reason": r.quarantine_reason,
            "registered_mcp_names": matching_reg_names,
            "spec": spec_dict,
        })
    return results


@app.get("/api/tools/{tool_id_or_name}")
async def get_tool_details(tool_id_or_name: str):
    """Retrieve full tool details including source code, NemoClaw policy, and execution history."""
    global pipeline
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    record = pipeline.store.get_tool(tool_id_or_name) or pipeline.store.get_tool_by_name(tool_id_or_name)
    if not record:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_id_or_name}' not found")

    spec_dict = None
    if record.tool_spec_json:
        try:
            spec_dict = json.loads(record.tool_spec_json)
        except Exception:
            pass

    policy_yaml = None
    if record.policy_yaml and Path(record.policy_yaml).exists():
        policy_yaml = Path(record.policy_yaml).read_text(encoding="utf-8")

    # Fetch recent execution history and lifecycle events from database
    events = []
    executions = []
    healing = []
    with pipeline.store._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM lifecycle_events WHERE tool_id = ? ORDER BY created_at DESC LIMIT 20", (record.id,))
        events = [dict(row) for row in cursor.fetchall()]

        cursor.execute("SELECT * FROM execution_logs WHERE tool_id = ? ORDER BY created_at DESC LIMIT 20", (record.id,))
        executions = [dict(row) for row in cursor.fetchall()]

        cursor.execute("SELECT * FROM healing_attempts WHERE tool_id = ? ORDER BY created_at DESC LIMIT 10", (record.id,))
        healing = [dict(row) for row in cursor.fetchall()]

    return {
        "record": {
            "id": record.id,
            "name": record.name,
            "version": record.version,
            "state": record.state.value if isinstance(record.state, ToolLifecycleState) else record.state,
            "target_domain": record.target_domain,
            "source_type": record.source_type,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
            "registered_at": record.registered_at,
            "quarantined_at": record.quarantined_at,
            "quarantine_reason": record.quarantine_reason,
            "sandbox_id": record.sandbox_id,
        },
        "spec": spec_dict,
        "generated_code": record.generated_code,
        "policy_yaml": policy_yaml,
        "lifecycle_events": events,
        "executions": executions,
        "healing_attempts": healing,
    }


@app.post("/api/tools/{tool_name}/execute")
async def execute_tool(tool_name: str, req: ExecuteRequest):
    """Execute a registered tool function with arguments."""
    global pipeline
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    start_t = time.time()
    try:
        result = await pipeline.execute_tool(tool_name, arguments=req.arguments)
        duration_ms = int((time.time() - start_t) * 1000)

        # Ensure result is JSON serializable
        if hasattr(result, "model_dump"):
            clean_result = result.model_dump()
        else:
            clean_result = result

        return {
            "success": True,
            "tool_name": tool_name,
            "result": clean_result,
            "duration_ms": duration_ms,
        }
    except Exception as e:
        duration_ms = int((time.time() - start_t) * 1000)
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "tool_name": tool_name,
                "error": str(e),
                "duration_ms": duration_ms,
            },
        )


@app.delete("/api/tools/{tool_id_or_name}")
async def delete_tool(tool_id_or_name: str):
    """Decommission and delete a tool from the skill store and registry."""
    global pipeline
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    record = pipeline.store.get_tool(tool_id_or_name) or pipeline.store.get_tool_by_name(tool_id_or_name)
    if not record:
        raise HTTPException(status_code=404, detail="Tool not found")

    pipeline.registry.unregister_tool(record.name)
    deleted = pipeline.store.delete_tool(record.id)
    return {"success": deleted, "deleted_id": record.id, "deleted_name": record.name}


# Static frontend mounting (Vite production build output)
FRONTEND_DIST_DIR = Path(__file__).parent / "static"

if FRONTEND_DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST_DIR / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Don't intercept /api routes
        if full_path.startswith("api"):
            raise HTTPException(status_code=404, detail="API route not found")
        file_path = FRONTEND_DIST_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        index_file = FRONTEND_DIST_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return JSONResponse({"status": "DynamicMCP API running. Frontend static files not yet compiled."})


def run_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """Run the FastAPI application with Uvicorn."""
    import uvicorn
    uvicorn.run("dynamicmcp.server:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    run_server()
