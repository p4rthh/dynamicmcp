"""SQLite persistent Skill Store for DynamicMCP tools and lifecycle tracking."""

import sqlite3
import json
from pathlib import Path
from typing import Optional, Any
from datetime import datetime, timezone
from dynamicmcp.models.tool import (
    ToolLifecycleState,
    ToolRecord,
    LifecycleEvent,
    ExecutionRecord,
    HealingRecord,
)
from dynamicmcp.models.spec import ToolSpec


class SkillStore:
    """Manages SQLite persistence for DynamicMCP skills, states, and audit trails."""

    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        """Create tables and indexes if they do not exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.executescript(
                """
                CREATE TABLE IF NOT EXISTS tools (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    version TEXT NOT NULL,
                    state TEXT NOT NULL DEFAULT 'UNRECOGNIZED_TOOL',
                    tool_spec_json TEXT NOT NULL,
                    generated_code TEXT,
                    generated_code_hash TEXT,
                    policy_yaml TEXT,
                    sandbox_id TEXT,
                    source_type TEXT NOT NULL,
                    target_domain TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                    registered_at TEXT,
                    quarantined_at TEXT,
                    quarantine_reason TEXT
                );

                CREATE TABLE IF NOT EXISTS lifecycle_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tool_id TEXT NOT NULL REFERENCES tools(id),
                    from_state TEXT NOT NULL,
                    to_state TEXT NOT NULL,
                    trigger TEXT NOT NULL,
                    metadata_json TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS execution_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tool_id TEXT NOT NULL REFERENCES tools(id),
                    execution_id TEXT NOT NULL UNIQUE,
                    input_hash TEXT NOT NULL,
                    output_summary TEXT,
                    duration_ms INTEGER,
                    success INTEGER NOT NULL,
                    error_message TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS healing_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tool_id TEXT NOT NULL REFERENCES tools(id),
                    attempt_number INTEGER NOT NULL,
                    error_trace TEXT NOT NULL,
                    fix_prompt TEXT NOT NULL,
                    patched_code TEXT,
                    verification_result TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                );

                CREATE INDEX IF NOT EXISTS idx_tools_state ON tools(state);
                CREATE INDEX IF NOT EXISTS idx_tools_name ON tools(name);
                CREATE INDEX IF NOT EXISTS idx_lifecycle_tool_id ON lifecycle_events(tool_id);
                CREATE INDEX IF NOT EXISTS idx_execution_tool_id ON execution_logs(tool_id);
                """
            )
            conn.commit()

    def save_tool(self, tool: ToolRecord) -> None:
        """Insert or update a tool record."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO tools (
                    id, name, version, state, tool_spec_json, generated_code,
                    generated_code_hash, policy_yaml, sandbox_id, source_type,
                    target_domain, created_at, updated_at, registered_at,
                    quarantined_at, quarantine_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    version=excluded.version,
                    state=excluded.state,
                    tool_spec_json=excluded.tool_spec_json,
                    generated_code=excluded.generated_code,
                    generated_code_hash=excluded.generated_code_hash,
                    policy_yaml=excluded.policy_yaml,
                    sandbox_id=excluded.sandbox_id,
                    target_domain=excluded.target_domain,
                    updated_at=?,
                    registered_at=excluded.registered_at,
                    quarantined_at=excluded.quarantined_at,
                    quarantine_reason=excluded.quarantine_reason
                """,
                (
                    tool.id,
                    tool.name,
                    tool.version,
                    tool.state.value if isinstance(tool.state, ToolLifecycleState) else tool.state,
                    tool.tool_spec_json,
                    tool.generated_code,
                    tool.generated_code_hash,
                    tool.policy_yaml,
                    tool.sandbox_id,
                    tool.source_type,
                    tool.target_domain,
                    tool.created_at,
                    tool.updated_at,
                    tool.registered_at,
                    tool.quarantined_at,
                    tool.quarantine_reason,
                    now,
                ),
            )
            conn.commit()

    def get_tool(self, tool_id: str) -> Optional[ToolRecord]:
        """Retrieve a tool record by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tools WHERE id = ?", (tool_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return ToolRecord(**dict(row))

    def get_tool_by_name(self, name: str) -> Optional[ToolRecord]:
        """Retrieve a tool record by its unique tool name."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tools WHERE name = ?", (name,))
            row = cursor.fetchone()
            if not row:
                return None
            return ToolRecord(**dict(row))

    def update_tool_state(
        self,
        tool_id: str,
        new_state: ToolLifecycleState,
        trigger: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Update a tool's state and record the lifecycle transition event."""
        now = datetime.now(timezone.utc).isoformat()
        metadata_json = json.dumps(metadata) if metadata else None

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT state FROM tools WHERE id = ?", (tool_id,))
            row = cursor.fetchone()
            old_state = row["state"] if row else "UNKNOWN"

            extra_fields = ""
            params: list[Any] = [new_state.value, now]
            if new_state == ToolLifecycleState.REGISTERED:
                extra_fields = ", registered_at = ?"
                params.append(now)
            elif new_state == ToolLifecycleState.QUARANTINED:
                extra_fields = ", quarantined_at = ?, quarantine_reason = ?"
                params.append(now)
                params.append(trigger)

            params.append(tool_id)
            cursor.execute(
                f"UPDATE tools SET state = ?, updated_at = ?{extra_fields} WHERE id = ?",
                tuple(params),
            )

            # Record lifecycle event
            cursor.execute(
                """
                INSERT INTO lifecycle_events (tool_id, from_state, to_state, trigger, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (tool_id, old_state, new_state.value, trigger, metadata_json, now),
            )
            conn.commit()

    def list_tools(
        self, state: Optional[ToolLifecycleState] = None
    ) -> list[ToolRecord]:
        """List all tools, optionally filtering by lifecycle state."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if state:
                cursor.execute(
                    "SELECT * FROM tools WHERE state = ? ORDER BY updated_at DESC",
                    (state.value,),
                )
            else:
                cursor.execute("SELECT * FROM tools ORDER BY updated_at DESC")
            rows = cursor.fetchall()
            return [ToolRecord(**dict(row)) for row in rows]

    def record_execution(
        self,
        tool_id: str,
        execution_id: str,
        input_hash: str,
        output_summary: Optional[str] = None,
        duration_ms: Optional[int] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> None:
        """Record a tool execution audit event."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO execution_logs (
                    tool_id, execution_id, input_hash, output_summary,
                    duration_ms, success, error_message, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tool_id,
                    execution_id,
                    input_hash,
                    output_summary[:1000] if output_summary else None,
                    duration_ms,
                    1 if success else 0,
                    error_message,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()

    def record_healing_attempt(
        self,
        tool_id: str,
        attempt_number: int,
        error_trace: str,
        fix_prompt: str,
        patched_code: Optional[str],
        verification_result: str,
    ) -> None:
        """Record an automated healing attempt."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO healing_attempts (
                    tool_id, attempt_number, error_trace, fix_prompt,
                    patched_code, verification_result, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tool_id,
                    attempt_number,
                    error_trace,
                    fix_prompt,
                    patched_code,
                    verification_result,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()

    def get_healing_attempt_count(self, tool_id: str) -> int:
        """Get the number of healing attempts recorded for a tool."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM healing_attempts WHERE tool_id = ?",
                (tool_id,),
            )
            row = cursor.fetchone()
            return row["cnt"] if row else 0

    def delete_tool(self, tool_id: str) -> bool:
        """Delete a tool and its associated history."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM lifecycle_events WHERE tool_id = ?", (tool_id,))
            cursor.execute("DELETE FROM execution_logs WHERE tool_id = ?", (tool_id,))
            cursor.execute("DELETE FROM healing_attempts WHERE tool_id = ?", (tool_id,))
            cursor.execute("DELETE FROM tools WHERE id = ?", (tool_id,))
            conn.commit()
            return cursor.rowcount > 0
