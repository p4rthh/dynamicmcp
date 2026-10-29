"""FastMCP Dynamic Registry Manager for runtime tool registration and routing."""

import importlib.util
import inspect
import sys
import logging
from pathlib import Path
from typing import Callable, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel
from fastmcp import FastMCP
from dynamicmcp.models.tool import ToolLifecycleState
from dynamicmcp.registry.store import SkillStore

logger = logging.getLogger(__name__)


class RegistryManager:
    """Manages the dynamic lifecycle of generated MCP tools within FastMCP."""

    NAMESPACE_PREFIX = "dynamic"

    def __init__(self, mcp_server: Optional[FastMCP] = None, store: Optional[SkillStore] = None):
        self._server = mcp_server or FastMCP("DynamicMCP", instructions="Self-assembling MCP Factory")
        self.store = store
        self._registered_tools: dict[str, dict[str, Any]] = {}

    @property
    def server(self) -> FastMCP:
        return self._server

    def register_tool_function(
        self,
        tool_name: str,
        tool_function: Callable,
        description: str = "",
        source_path: str = "",
        tool_id: Optional[str] = None,
    ) -> str:
        """Register a Python callable into the FastMCP server at runtime."""
        namespaced_name = f"{self.NAMESPACE_PREFIX}__{tool_name}"

        # If already registered, remove old version first
        if namespaced_name in self._registered_tools:
            self.deregister_tool(tool_name)

        # Register with FastMCP
        try:
            self._server.tool(
                name=namespaced_name,
                description=description or tool_function.__doc__ or f"Dynamic tool {tool_name}",
            )(tool_function)
        except Exception:
            # Fallback for alternative FastMCP variants
            self._server.add_tool(tool_function)

        self._registered_tools[namespaced_name] = {
            "tool_id": tool_id or tool_name,
            "original_name": tool_name,
            "namespaced_name": namespaced_name,
            "function": tool_function,
            "description": description or tool_function.__doc__ or "",
            "source_path": source_path,
            "registered_at": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(f"Registered tool: {namespaced_name}")
        return namespaced_name

    def load_and_register_from_file(
        self,
        source_path: Path | str,
        tool_name: str,
        tool_id: Optional[str] = None,
        description: str = "",
    ) -> list[str]:
        """Dynamically load functions from a generated Python file and register them."""
        path = Path(source_path).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f"Tool script not found: {path}")

        module_name = f"dynamicmcp_tool_{tool_name}"
        spec = importlib.util.spec_from_file_location(module_name, str(path))
        if not spec or not spec.loader:
            raise ImportError(f"Cannot load module from spec at {path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        registered_names: list[str] = []

        # Check for FastMCP instance tools in the loaded module
        if hasattr(module, "mcp") and isinstance(module.mcp, FastMCP):
            # Iterate through the server's tools
            try:
                # FastMCP 2.x/4.x provides access to tool registry
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if inspect.iscoroutinefunction(attr) or inspect.isfunction(attr):
                        # If function has docstring and was defined in the module
                        if attr.__module__ == module_name and not attr_name.startswith("_"):
                            reg_name = self.register_tool_function(
                                tool_name=attr_name,
                                tool_function=attr,
                                description=attr.__doc__ or description,
                                source_path=str(path),
                                tool_id=tool_id,
                            )
                            registered_names.append(reg_name)
            except Exception as e:
                logger.warning(f"Error extracting tools from loaded module: {e}")

        # Fallback scan all functions if nothing matched
        if not registered_names:
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (inspect.iscoroutinefunction(attr) or inspect.isfunction(attr)) and attr.__module__ == module_name:
                    if not attr_name.startswith("_"):
                        reg_name = self.register_tool_function(
                            tool_name=attr_name,
                            tool_function=attr,
                            description=attr.__doc__ or description,
                            source_path=str(path),
                            tool_id=tool_id,
                        )
                        registered_names.append(reg_name)

        return registered_names

    def deregister_tool(self, tool_name: str) -> bool:
        """Remove a tool from FastMCP."""
        namespaced_name = tool_name if tool_name.startswith(f"{self.NAMESPACE_PREFIX}__") else f"{self.NAMESPACE_PREFIX}__{tool_name}"
        if namespaced_name in self._registered_tools:
            try:
                # Remove tool if method exists
                if hasattr(self._server, "remove_tool"):
                    self._server.remove_tool(namespaced_name)
            except Exception as e:
                logger.warning(f"Could not remove tool from fastmcp: {e}")

            del self._registered_tools[namespaced_name]
            logger.info(f"Deregistered tool: {namespaced_name}")
            return True
        return False

    async def execute_tool(self, tool_name: str, **kwargs: Any) -> Any:
        """Execute a registered tool function by name with automatic Pydantic coercion."""
        namespaced_name = tool_name if tool_name.startswith(f"{self.NAMESPACE_PREFIX}__") else f"{self.NAMESPACE_PREFIX}__{tool_name}"
        target_name = None

        if namespaced_name in self._registered_tools:
            target_name = namespaced_name
        elif tool_name in self._registered_tools:
            target_name = tool_name
        else:
            # Fuzzy / prefix matching (e.g. tool name matches prefix of registered function)
            prefix = f"{self.NAMESPACE_PREFIX}__{tool_name}"
            for reg_k, meta in self._registered_tools.items():
                if reg_k.startswith(prefix) or meta.get("tool_id") == tool_name or meta.get("tool_name") == tool_name:
                    target_name = reg_k
                    break

        if not target_name:
            available = list(self._registered_tools.keys())
            raise KeyError(f"Tool '{namespaced_name}' is not registered in FastMCP registry. Available tools: {available}")

        tool_meta = self._registered_tools[target_name]
        fn = tool_meta["function"]

        # Automatic Pydantic model conversion if argument was passed as dict
        sig = inspect.signature(fn)
        call_kwargs = dict(kwargs)

        for p_name, param in sig.parameters.items():
            ann = param.annotation
            if isinstance(ann, type) and issubclass(ann, BaseModel):
                if p_name in call_kwargs and isinstance(call_kwargs[p_name], dict):
                    try:
                        call_kwargs[p_name] = ann(**call_kwargs[p_name])
                    except Exception:
                        pass
                elif p_name not in call_kwargs and len(sig.parameters) == 1:
                    try:
                        call_kwargs = {p_name: ann(**kwargs)}
                    except Exception:
                        pass

        if inspect.iscoroutinefunction(fn):
            return await fn(**call_kwargs)
        return fn(**call_kwargs)

    def list_registered_tools(self) -> list[dict[str, Any]]:
        """List all active tools currently loaded in the registry."""
        return [
            {
                "name": meta["namespaced_name"],
                "original_name": meta["original_name"],
                "description": meta["description"],
                "source_path": meta["source_path"],
                "registered_at": meta["registered_at"],
            }
            for meta in self._registered_tools.values()
        ]
