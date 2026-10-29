"""Lifecycle and database models for DynamicMCP tools."""

from enum import Enum
from typing import Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ToolLifecycleState(str, Enum):
    """Finite State Machine states defined in ARCHITECTURE.md."""
    UNRECOGNIZED_TOOL = "UNRECOGNIZED_TOOL"
    SPEC_PARSING = "SPEC_PARSING"
    CODE_SYNTHESIS = "CODE_SYNTHESIS"
    DRY_RUN_VERIFICATION = "DRY_RUN_VERIFICATION"
    SELF_HEALING = "SELF_HEALING"
    SANDBOX_MOUNT = "SANDBOX_MOUNT"
    REGISTERED = "REGISTERED"
    EXECUTING = "EXECUTING"
    DRIFT_DETECTED = "DRIFT_DETECTED"
    QUARANTINED = "QUARANTINED"
    DECOMMISSIONED = "DECOMMISSIONED"
    PARSE_FAILED = "PARSE_FAILED"


class ToolRecord(BaseModel):
    """Database record of a managed tool in SQLite."""
    id: str
    name: str
    version: str
    state: ToolLifecycleState = ToolLifecycleState.UNRECOGNIZED_TOOL
    tool_spec_json: str
    generated_code: Optional[str] = None
    generated_code_hash: Optional[str] = None
    policy_yaml: Optional[str] = None
    sandbox_id: Optional[str] = None
    source_type: str = "curl"
    target_domain: Optional[str] = None
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    registered_at: Optional[str] = None
    quarantined_at: Optional[str] = None
    quarantine_reason: Optional[str] = None


class LifecycleEvent(BaseModel):
    """Transition event recorded in SQLite lifecycle_events table."""
    id: Optional[int] = None
    tool_id: str
    from_state: str
    to_state: str
    trigger: str
    metadata_json: Optional[str] = None
    created_at: str = Field(default_factory=utc_now_iso)


class ExecutionRecord(BaseModel):
    """Execution audit log recorded in SQLite execution_logs table."""
    id: Optional[int] = None
    tool_id: str
    execution_id: str
    input_hash: str
    output_summary: Optional[str] = None
    duration_ms: Optional[int] = None
    success: bool = True
    error_message: Optional[str] = None
    created_at: str = Field(default_factory=utc_now_iso)


class HealingRecord(BaseModel):
    """Self-healing attempt record in SQLite healing_attempts table."""
    id: Optional[int] = None
    tool_id: str
    attempt_number: int
    error_trace: str
    fix_prompt: str
    patched_code: Optional[str] = None
    verification_result: str  # "PASS" or "FAIL"
    created_at: str = Field(default_factory=utc_now_iso)
