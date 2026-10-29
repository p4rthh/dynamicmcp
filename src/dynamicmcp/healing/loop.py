"""Self-Healing & Code Refactor Loop powered by NVIDIA Nemotron 3 Ultra."""

import logging
import re
import httpx
from typing import Optional
from pydantic import BaseModel, Field
from dynamicmcp.models.spec import ToolSpec
from dynamicmcp.models.tool import ToolLifecycleState
from dynamicmcp.synthesizer.prompts import HEALING_PROMPT_TEMPLATE
from dynamicmcp.synthesizer.validator import ASTValidator
from dynamicmcp.synthesizer.engine import SynthesizerEngine
from dynamicmcp.verification.runner import VerificationRunner
from dynamicmcp.verification.result_parser import VerificationResult
from dynamicmcp.registry.store import SkillStore
from dynamicmcp.config import settings

logger = logging.getLogger(__name__)


class HealingResult(BaseModel):
    """Result of a self-healing process."""
    success: bool
    patched_code: Optional[str] = None
    attempts_used: int = 0
    final_verification: Optional[VerificationResult] = None
    quarantined: bool = False
    quarantine_reason: Optional[str] = None


class HealingLoop:
    """Manages iterative self-healing loops for failing FastMCP tools."""

    MAX_ATTEMPTS = 3

    def __init__(
        self,
        store: Optional[SkillStore] = None,
        verification_runner: Optional[VerificationRunner] = None,
        api_key: Optional[str] = None,
        token_factory_url: Optional[str] = None,
        model_name: Optional[str] = None,
        offline_mode: Optional[bool] = None,
    ):
        self.store = store
        self.verification_runner = verification_runner or VerificationRunner(offline_mode=offline_mode)
        self.api_key = api_key or settings.nebius_api_key
        self.token_factory_url = token_factory_url or settings.nebius_token_factory_url
        self.model_name = model_name or settings.ultra_model
        self.offline_mode = offline_mode if offline_mode is not None else settings.offline_mode

    async def heal(
        self,
        spec: ToolSpec,
        initial_code: str,
        initial_verification: VerificationResult,
    ) -> HealingResult:
        """Attempt to repair broken code using Nemotron 3 Ultra feedback."""
        current_code = initial_code
        last_verification = initial_verification
        attempts = 0

        logger.info(f"Starting self-healing loop for tool '{spec.name}' (max {self.MAX_ATTEMPTS} attempts)")

        if self.store:
            self.store.update_tool_state(
                spec.id,
                ToolLifecycleState.SELF_HEALING,
                trigger=f"Verification failed: {initial_verification.error_trace[:200]}",
            )

        while attempts < self.MAX_ATTEMPTS:
            attempts += 1
            logger.info(f"Self-healing attempt {attempts}/{self.MAX_ATTEMPTS} for '{spec.name}'")

            # 1. Generate patched code
            patched_code = await self._generate_patch(spec, current_code, last_verification.error_trace)

            # 2. Validate AST before running
            ast_res = ASTValidator.validate(patched_code)
            if not ast_res.valid:
                logger.warning(f"Attempt {attempts}: Patched code failed AST validation: {ast_res.errors}")
                last_verification = VerificationResult(
                    passed=False,
                    exit_code=1,
                    error_trace=f"AST ValidationError: {'; '.join(ast_res.errors)}",
                )
                if self.store:
                    self.store.record_healing_attempt(
                        tool_id=spec.id,
                        attempt_number=attempts,
                        error_trace=last_verification.error_trace,
                        fix_prompt="AST Validation",
                        patched_code=patched_code,
                        verification_result="FAIL",
                    )
                current_code = patched_code
                continue

            # 3. Dry-run verify the patched code
            verif_res = await self.verification_runner.verify(spec, patched_code)
            last_verification = verif_res

            # Record attempt in store
            if self.store:
                self.store.record_healing_attempt(
                    tool_id=spec.id,
                    attempt_number=attempts,
                    error_trace=verif_res.error_trace if not verif_res.passed else "",
                    fix_prompt=f"Attempt {attempts} patch",
                    patched_code=patched_code,
                    verification_result="PASS" if verif_res.passed else "FAIL",
                )

            if verif_res.passed:
                logger.info(f"Self-healing SUCCEEDED on attempt {attempts} for '{spec.name}'")
                return HealingResult(
                    success=True,
                    patched_code=patched_code,
                    attempts_used=attempts,
                    final_verification=verif_res,
                    quarantined=False,
                )

            current_code = patched_code

        # If we reach here, max attempts exceeded -> QUARANTINE
        logger.error(f"Self-healing EXHAUSTED {self.MAX_ATTEMPTS} attempts for '{spec.name}'. Quarantining.")
        quarantine_reason = f"Exceeded {self.MAX_ATTEMPTS} self-healing attempts. Last error: {last_verification.error_trace[:300]}"

        if self.store:
            self.store.update_tool_state(
                spec.id,
                ToolLifecycleState.QUARANTINED,
                trigger=quarantine_reason,
            )

        return HealingResult(
            success=False,
            patched_code=current_code,
            attempts_used=attempts,
            final_verification=last_verification,
            quarantined=True,
            quarantine_reason=quarantine_reason,
        )

    async def _generate_patch(self, spec: ToolSpec, current_code: str, error_trace: str) -> str:
        """Prompt Nemotron 3 Ultra to fix the code, or use rule-based patcher in offline mode."""
        if self.offline_mode or not self.api_key or self.api_key == "mock-key":
            logger.info("Operating in offline or mock mode for patch generation.")
            return self._mock_patch(spec, current_code, error_trace)

        prompt = HEALING_PROMPT_TEMPLATE.format(
            spec_json=spec.model_dump_json(indent=2),
            current_code=current_code,
            error_trace=error_trace,
        )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 4096,
            "extra_body": {
                "enable_thinking": True
            }
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.token_factory_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            message = data["choices"][0]["message"]
            raw_text = message.get("content") or ""
            if not raw_text and message.get("reasoning_content"):
                raw_text = message.get("reasoning_content", "")
            raw_text = raw_text.strip()

            if "```python" in raw_text:
                match = re.search(r"```python\s*(.*?)\s*```", raw_text, re.DOTALL)
                if match:
                    return match.group(1).strip()
            elif "```" in raw_text:
                match = re.search(r"```\s*(.*?)\s*```", raw_text, re.DOTALL)
                if match:
                    return match.group(1).strip()

            return raw_text

    def _mock_patch(self, spec: ToolSpec, current_code: str, error_trace: str) -> str:
        """Deterministic patch fallback: generates fresh clean template code for the spec."""
        synthesizer = SynthesizerEngine(offline_mode=True)
        return synthesizer._generate_template_code(spec)
