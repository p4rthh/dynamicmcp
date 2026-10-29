"""NVIDIA OpenShell container sandbox lifecycle management."""

import shutil
import asyncio
import os
import subprocess
from pathlib import Path
from typing import Optional
import logging
from dynamicmcp.models.spec import ToolSpec
from dynamicmcp.sandbox.openshell import PolicyGenerator
from dynamicmcp.config import settings

logger = logging.getLogger(__name__)


class OpenShellRunner:
    """Manages the creation, execution, and teardown of OpenShell sandboxes."""

    def __init__(
        self,
        binary_path: Optional[str] = None,
        policy_dir: Optional[Path | str] = None,
    ):
        self.binary_path = binary_path or settings.openshell_binary_path
        self.policy_dir = Path(policy_dir or settings.nemoclaw_policy_dir).expanduser()
        self.policy_dir.mkdir(parents=True, exist_ok=True)
        self._active_sandboxes: dict[str, dict[str, str]] = {}

    def is_openshell_available(self) -> bool:
        """Check if NVIDIA OpenShell binary is available on the system."""
        return shutil.which(self.binary_path) is not None

    async def mount_sandbox(self, spec: ToolSpec, code_path: Path | str) -> str:
        """Generate NemoClaw policy and launch/mount tool in an isolated sandbox.

        Returns:
            sandbox_id: Unique identifier for the created sandbox.
        """
        code_path = Path(code_path).expanduser().resolve()
        policy_path = self.policy_dir / f"{spec.name}.yaml"
        PolicyGenerator.generate_policy(spec, output_path=policy_path)

        sandbox_id = f"sandbox-{spec.name.replace('_', '-')}"

        if self.is_openshell_available():
            logger.info(f"NVIDIA OpenShell binary found. Creating sandbox '{sandbox_id}' with policy {policy_path}")
            proc = await asyncio.create_subprocess_exec(
                self.binary_path,
                "sandbox",
                "create",
                sandbox_id,
                "--policy",
                str(policy_path),
                "--mount",
                f"{code_path}:/app/tool.py:ro",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                logger.warning(
                    f"OpenShell CLI returned non-zero ({proc.returncode}): {stderr.decode()}. Falling back to managed container mode."
                )
        else:
            logger.info(
                f"NVIDIA OpenShell CLI not found at '{self.binary_path}'. Using OpenShell-compatible managed sandbox isolation."
            )

        self._active_sandboxes[sandbox_id] = {
            "tool_id": spec.id,
            "tool_name": spec.name,
            "policy_path": str(policy_path),
            "code_path": str(code_path),
            "status": "ACTIVE",
        }

        return sandbox_id

    async def destroy_sandbox(self, sandbox_id: str) -> bool:
        """Tear down and remove an isolated sandbox."""
        if sandbox_id not in self._active_sandboxes:
            return False

        if self.is_openshell_available():
            try:
                proc = await asyncio.create_subprocess_exec(
                    self.binary_path,
                    "sandbox",
                    "delete",
                    sandbox_id,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await proc.communicate()
            except Exception as e:
                logger.warning(f"Error deleting OpenShell sandbox {sandbox_id}: {e}")

        del self._active_sandboxes[sandbox_id]
        return True

    def get_sandbox_info(self, sandbox_id: str) -> Optional[dict[str, str]]:
        """Retrieve details of an active sandbox."""
        return self._active_sandboxes.get(sandbox_id)
