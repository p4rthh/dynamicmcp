"""Hot-Reload Orchestrator for Hermes Agent and FastMCP registry synchronization."""

import httpx
import logging
from pathlib import Path
from typing import Optional
from dynamicmcp.models.tool import ToolLifecycleState
from dynamicmcp.registry.manager import RegistryManager
from dynamicmcp.registry.store import SkillStore
from dynamicmcp.config import settings

logger = logging.getLogger(__name__)


class HotReloadOrchestrator:
    """Coordinates hot-reloads between FastMCP registry and the Hermes agent session."""

    def __init__(
        self,
        registry: RegistryManager,
        store: SkillStore,
        reload_endpoint: Optional[str] = None,
    ):
        self.registry = registry
        self.store = store
        self.reload_endpoint = reload_endpoint or settings.hermes_reload_endpoint

    async def notify_hermes(self) -> bool:
        """Trigger Hermes Agent's hot-reload endpoint if active."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(self.reload_endpoint, json={"event": "tool_registered"})
                if resp.status_code == 200:
                    logger.info("Successfully notified Hermes agent to hot-reload MCP tools.")
                    return True
        except Exception:
            # Hermes may be running via stdio or offline; this is a non-blocking notification
            logger.debug(f"Hermes HTTP endpoint {self.reload_endpoint} not reachable. Stdio HMR in effect.")
        return False

    def rehydrate_from_store(self, cache_dir: Optional[Path | str] = None) -> int:
        """Re-hydrate all tools currently marked as REGISTERED from SQLite on agent restart."""
        registered_tools = self.store.list_tools(state=ToolLifecycleState.REGISTERED)
        loaded_count = 0
        cache_base = Path(cache_dir or settings.cache_dir).expanduser()

        for tool in registered_tools:
            if not tool.generated_code:
                continue

            tool_file = cache_base / "code" / f"{tool.name}.py"
            tool_file.parent.mkdir(parents=True, exist_ok=True)
            tool_file.write_text(tool.generated_code, encoding="utf-8")

            try:
                reg_names = self.registry.load_and_register_from_file(
                    source_path=tool_file,
                    tool_name=tool.name,
                    tool_id=tool.id,
                )
                if reg_names:
                    loaded_count += len(reg_names)
            except Exception as e:
                logger.error(f"Failed to rehydrate tool '{tool.name}': {e}")

        logger.info(f"Re-hydrated {loaded_count} tools from SkillStore into FastMCP registry.")
        return loaded_count
