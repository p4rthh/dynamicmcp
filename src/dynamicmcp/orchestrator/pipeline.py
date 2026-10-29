"""End-to-end DynamicMCP Pipeline Orchestrator."""

import time
import json
import logging
from pathlib import Path
from typing import Optional, Any
from pydantic import BaseModel, Field

from dynamicmcp.models.spec import ToolSpec
from dynamicmcp.models.tool import ToolRecord, ToolLifecycleState
from dynamicmcp.registry.store import SkillStore
from dynamicmcp.ingestor.extractor import SpecIngestor
from dynamicmcp.synthesizer.engine import SynthesizerEngine
from dynamicmcp.verification.runner import VerificationRunner
from dynamicmcp.healing.loop import HealingLoop
from dynamicmcp.sandbox.container import OpenShellRunner
from dynamicmcp.registry.manager import RegistryManager
from dynamicmcp.registry.hot_reload import HotReloadOrchestrator
from dynamicmcp.config import settings

logger = logging.getLogger(__name__)


class PipelineResult(BaseModel):
    """Result of an end-to-end tool assembly pipeline run."""
    success: bool
    tool_id: str
    tool_name: str
    state: ToolLifecycleState
    registered_tools: list[str] = Field(default_factory=list)
    code_path: Optional[str] = None
    policy_path: Optional[str] = None
    error_message: Optional[str] = None
    duration_ms: int = 0


class DynamicMCPPipeline:
    """Coordinates the entire life-cycle:
    UNRECOGNIZED_TOOL -> SPEC_PARSING -> CODE_SYNTHESIS -> DRY_RUN_VERIFICATION ->
    [SELF_HEALING] -> SANDBOX_MOUNT -> REGISTERED -> EXECUTING
    """

    def __init__(
        self,
        store: Optional[SkillStore] = None,
        registry: Optional[RegistryManager] = None,
        offline_mode: Optional[bool] = None,
    ):
        settings.ensure_directories()
        self.offline_mode = offline_mode if offline_mode is not None else settings.offline_mode
        self.store = store or SkillStore(settings.db_path)
        self.registry = registry or RegistryManager(store=self.store)
        self.ingestor = SpecIngestor(offline_mode=self.offline_mode)
        self.synthesizer = SynthesizerEngine(offline_mode=self.offline_mode)
        self.verifier = VerificationRunner(offline_mode=self.offline_mode)
        self.healer = HealingLoop(
            store=self.store,
            verification_runner=self.verifier,
            offline_mode=self.offline_mode,
        )
        self.sandbox = OpenShellRunner()
        self.hot_reloader = HotReloadOrchestrator(self.registry, self.store)

        # Re-hydrate existing tools on startup
        self.hot_reloader.rehydrate_from_store()

    async def create_tool_from_spec(
        self,
        raw_input: str,
        suggested_name: Optional[str] = None,
    ) -> PipelineResult:
        """Execute the full pipeline from raw input to registered, sandboxed tool."""
        start_time = time.time()
        logger.info("DynamicMCP Pipeline initiated.")

        # Stage 1: Spec Parsing
        try:
            spec = await self.ingestor.ingest(raw_input, tool_name=suggested_name)
        except Exception as e:
            logger.error(f"Spec parsing failed: {e}")
            return PipelineResult(
                success=False,
                tool_id="unknown",
                tool_name=suggested_name or "unknown",
                state=ToolLifecycleState.PARSE_FAILED,
                error_message=f"Spec parsing failed: {str(e)}",
                duration_ms=int((time.time() - start_time) * 1000),
            )

        # Check if already registered and unchanged
        existing = self.store.get_tool_by_name(spec.name)
        if existing and existing.state == ToolLifecycleState.REGISTERED:
            logger.info(f"Tool '{spec.name}' is already active and registered.")
            return PipelineResult(
                success=True,
                tool_id=existing.id,
                tool_name=existing.name,
                state=ToolLifecycleState.REGISTERED,
                registered_tools=[f"{self.registry.NAMESPACE_PREFIX}__{existing.name}"],
                duration_ms=int((time.time() - start_time) * 1000),
            )

        # Create record in store
        tool_record = ToolRecord(
            id=spec.id,
            name=spec.name,
            version=spec.version,
            state=ToolLifecycleState.SPEC_PARSING,
            tool_spec_json=spec.model_dump_json(),
            source_type=spec.source_type.value,
            target_domain=spec.target_domain,
        )
        self.store.save_tool(tool_record)

        # Stage 2: Code Synthesis
        self.store.update_tool_state(spec.id, ToolLifecycleState.CODE_SYNTHESIS, trigger="Spec validated")
        synth_res = await self.synthesizer.synthesize(spec)
        code = synth_res.code

        if not synth_res.validation.valid:
            logger.warning(f"Synthesized code failed initial AST validation: {synth_res.validation.errors}")

        # Save code to cache
        code_file = settings.cache_dir / "code" / f"{spec.name}.py"
        code_file.parent.mkdir(parents=True, exist_ok=True)
        code_file.write_text(code, encoding="utf-8")

        # Stage 3: Dry-Run Verification
        self.store.update_tool_state(spec.id, ToolLifecycleState.DRY_RUN_VERIFICATION, trigger="Code synthesized")
        verif_res = await self.verifier.verify(spec, code)

        # Stage 4: Self-Healing if verification failed
        if not verif_res.passed:
            logger.warning(f"Verification failed: {verif_res.error_trace[:200]}. Engaging self-healing.")
            heal_res = await self.healer.heal(spec, code, verif_res)
            if not heal_res.success:
                return PipelineResult(
                    success=False,
                    tool_id=spec.id,
                    tool_name=spec.name,
                    state=ToolLifecycleState.QUARANTINED,
                    error_message=heal_res.quarantine_reason or "Self-healing failed to produce a valid tool.",
                    duration_ms=int((time.time() - start_time) * 1000),
                )
            code = heal_res.patched_code or code
            code_file.write_text(code, encoding="utf-8")

        # Stage 5: Sandbox Mount (OpenShell + NemoClaw)
        self.store.update_tool_state(spec.id, ToolLifecycleState.SANDBOX_MOUNT, trigger="Verification passed")
        sandbox_id = await self.sandbox.mount_sandbox(spec, code_file)

        # Update record in store
        tool_record.generated_code = code
        tool_record.generated_code_hash = spec.compute_version_hash(code)
        tool_record.sandbox_id = sandbox_id
        tool_record.policy_yaml = str(self.sandbox.policy_dir / f"{spec.name}.yaml")
        self.store.save_tool(tool_record)

        # Stage 6: Hot-Registration into FastMCP
        registered_names = self.registry.load_and_register_from_file(
            source_path=code_file,
            tool_name=spec.name,
            tool_id=spec.id,
            description=spec.description,
        )

        self.store.update_tool_state(
            spec.id,
            ToolLifecycleState.REGISTERED,
            trigger="Sandboxed and registered in FastMCP",
            metadata={"registered_names": registered_names},
        )

        # Notify Hermes
        await self.hot_reloader.notify_hermes()

        duration = int((time.time() - start_time) * 1000)
        logger.info(f"DynamicMCP Pipeline completed successfully in {duration}ms. Active tools: {registered_names}")

        return PipelineResult(
            success=True,
            tool_id=spec.id,
            tool_name=spec.name,
            state=ToolLifecycleState.REGISTERED,
            registered_tools=registered_names,
            code_path=str(code_file),
            policy_path=tool_record.policy_yaml,
            duration_ms=duration,
        )

    async def execute_tool(
        self,
        tool_name: str,
        arguments: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Any:
        """Execute a tool while maintaining full audit logging and drift detection."""
        args_payload = dict(arguments or {})
        args_payload.update(kwargs)

        start_exec = time.time()
        exec_id = f"exec_{int(start_exec * 1000)}"
        input_hash = str(hash(json.dumps(args_payload, sort_keys=True, default=str)))

        # Find tool record
        tool_record = self.store.get_tool_by_name(tool_name)
        tool_id = tool_record.id if tool_record else "dynamic"

        try:
            result = await self.registry.execute_tool(tool_name, **args_payload)
            duration_ms = int((time.time() - start_exec) * 1000)

            self.store.record_execution(
                tool_id=tool_id,
                execution_id=exec_id,
                input_hash=input_hash,
                output_summary=json.dumps(result)[:500] if isinstance(result, (dict, list)) else str(result)[:500],
                duration_ms=duration_ms,
                success=True,
            )
            return result
        except Exception as e:
            duration_ms = int((time.time() - start_exec) * 1000)
            logger.error(f"Tool execution failed for '{tool_name}': {e}")

            self.store.record_execution(
                tool_id=tool_id,
                execution_id=exec_id,
                input_hash=input_hash,
                duration_ms=duration_ms,
                success=False,
                error_message=str(e),
            )

            # Record drift if tool previously registered
            if tool_record and tool_record.state == ToolLifecycleState.REGISTERED:
                self.store.update_tool_state(
                    tool_record.id,
                    ToolLifecycleState.DRIFT_DETECTED,
                    trigger=f"Execution error: {str(e)}",
                )

            raise
