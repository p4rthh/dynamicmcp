"""Verification Runner via Nebius Serverless Jobs and isolated local runner."""

import asyncio
import tempfile
import sys
import os
from pathlib import Path
from typing import Optional
import httpx
import logging
from dynamicmcp.models.spec import ToolSpec
from dynamicmcp.verification.mock_generator import MockGenerator
from dynamicmcp.verification.result_parser import ResultParser, VerificationResult
from dynamicmcp.config import settings

logger = logging.getLogger(__name__)


class VerificationRunner:
    """Orchestrates headless unit testing of synthesized MCP tools."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        project_id: Optional[str] = None,
        jobs_url: Optional[str] = None,
        offline_mode: Optional[bool] = None,
    ):
        self.api_key = api_key or settings.nebius_api_key
        self.project_id = project_id or settings.nebius_project_id
        self.jobs_url = jobs_url or settings.nebius_jobs_api_url
        self.offline_mode = offline_mode if offline_mode is not None else settings.offline_mode

    async def verify(self, spec: ToolSpec, code: str) -> VerificationResult:
        """Verify the synthesized tool using synthetic inputs in an isolated environment."""
        test_script = MockGenerator.generate_pytest_script(spec, tool_module_name="tool")

        if self.offline_mode or not self.api_key or self.api_key == "mock-key":
            logger.info("Executing dry-run verification via local isolated sandbox runner.")
            return await self._run_local_verification(code, test_script)
        else:
            try:
                return await self._run_nebius_job(code, test_script)
            except Exception as e:
                logger.warning(f"Nebius Serverless Job submission failed: {e}. Falling back to local runner.")
                return await self._run_local_verification(code, test_script)

    @staticmethod
    def _get_sanitized_env(extra: Optional[dict[str, str]] = None) -> dict[str, str]:
        """Produce a sanitized environment dict blocking host credentials and tokens."""
        # Baseline safe variables
        safe_keys = {
            "PATH",
            "SYSTEMROOT",
            "LANG",
            "LC_ALL",
            "LC_CTYPE",
            "TMPDIR",
            "TEMP",
            "TMP",
            "VIRTUAL_ENV",
            "HOME",
        }
        sanitized = {k: v for k, v in os.environ.items() if k in safe_keys}

        # Strip any credential-bearing variables
        sensitive_patterns = ("KEY", "TOKEN", "SECRET", "AUTH", "PASS", "CREDENTIAL", "NEBIUS", "NVIDIA", "OPENAI", "AWS", "SSH")
        for k in list(sanitized.keys()):
            if any(pat in k.upper() for pat in sensitive_patterns):
                sanitized.pop(k, None)

        if extra:
            sanitized.update(extra)
        return sanitized

    async def _run_local_verification(self, code: str, test_script: str) -> VerificationResult:
        """Run verification in an isolated temporary directory using the current Python environment."""
        with tempfile.TemporaryDirectory(prefix="dynamicmcp_verify_") as tmpdir:
            tmppath = Path(tmpdir)
            tool_path = tmppath / "tool.py"
            test_path = tmppath / "test_tool.py"

            tool_path.write_text(code, encoding="utf-8")
            test_path.write_text(test_script, encoding="utf-8")

            # Execute pytest as subprocess with scrubbed environment
            clean_env = self._get_sanitized_env({"PYTHONPATH": str(tmppath)})
            proc = await asyncio.create_subprocess_exec(
                sys.executable,
                "-m",
                "pytest",
                str(test_path),
                "-v",
                "--tb=short",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(tmppath),
                env=clean_env,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=45.0)
                stdout = stdout_bytes.decode("utf-8", errors="replace")
                stderr = stderr_bytes.decode("utf-8", errors="replace")
                exit_code = proc.returncode or 0
            except asyncio.TimeoutError:
                proc.kill()
                return VerificationResult(
                    passed=False,
                    exit_code=-1,
                    stderr="Verification timed out after 45 seconds.",
                    error_trace="ExecutionTimeout: Test run exceeded 45s threshold.",
                )

            return ResultParser.parse(exit_code, stdout, stderr)

    async def _run_nebius_job(self, code: str, test_script: str) -> VerificationResult:
        """Submit a serverless job to Nebius AI Cloud."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "project_id": self.project_id,
            "container": {
                "image": "python:3.12-slim",
                "command": [
                    "bash", "-c",
                    "pip install httpx pydantic fastmcp pytest pytest-asyncio && "
                    "python3 -c \"import os; open('/tmp/tool.py', 'w').write(os.environ.get('CODE', '')); open('/tmp/test_tool.py', 'w').write(os.environ.get('TEST', ''))\" && "
                    "python -m pytest /tmp/test_tool.py -v --tb=short"
                ],
                "env": {
                    "CODE": code,
                    "TEST": test_script,
                }
            },
            "resources": {
                "cpu": "1",
                "memory": "512Mi",
            },
            "timeout_seconds": 90,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{self.jobs_url.rstrip('/')}", headers=headers, json=payload)
            resp.raise_for_status()
            job_id = resp.json()["job_id"]

            # Poll for completion
            for _ in range(45):
                await asyncio.sleep(2.0)
                poll_resp = await client.get(f"{self.jobs_url.rstrip('/')}/{job_id}", headers=headers)
                poll_resp.raise_for_status()
                data = poll_resp.json()
                status = data.get("status")

                if status in ("COMPLETED", "FAILED"):
                    exit_code = data.get("exit_code", 0)
                    stdout = data.get("stdout", "")
                    stderr = data.get("stderr", "")
                    return ResultParser.parse(exit_code, stdout, stderr)

            return VerificationResult(
                passed=False,
                exit_code=-1,
                stderr="Nebius Serverless Job timed out while waiting for execution.",
                error_trace="NebiusJobTimeout",
            )
