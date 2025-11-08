# =====================================================
# app/agent/toolkit.py
# ToolRegistry: unified access layer for all adapters
# =====================================================

from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Central registry for all external tools (weather, gmail, vdb, etc.).
    Provides a unified interface for describing and invoking tools dynamically.
    """

    def __init__(self, tools: Optional[Dict[str, Any]] = None):
        """
        Args:
            tools: Mapping of tool name → adapter instance
        """
        self.tools = tools or {}
        logger.info(f"Initialized ToolRegistry with tools: {list(self.tools.keys())}")

    # -----------------------------------------------------
    # Tool metadata and inspection
    # -----------------------------------------------------
    def describe(self) -> Dict[str, Any]:
        """
        Return a structured description of all available tools.
        Useful for prompting the LLM during planning.
        """
        descriptions = {}
        for name, tool in self.tools.items():
            doc = getattr(tool, "__doc__", "") or "No description provided."
            descriptions[name] = {
                "description": doc.strip().split("\n")[0],
                "methods": [
                    fn for fn in dir(tool)
                    if not fn.startswith("_") and callable(getattr(tool, fn))
                ]
            }
        return descriptions

    # -----------------------------------------------------
    # Tool invocation
    # -----------------------------------------------------
    def invoke(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        Safely invoke a registered tool by name.
        
        Args:
            tool_name: Key name in the registry (e.g. 'weather', 'gmail', 'vdb')
            **kwargs: Parameters passed to the tool method

        Returns:
            A structured dict with either results or error message.
        """
        if tool_name not in self.tools:
            logger.warning(f"Tool '{tool_name}' not found in registry")
            return {"error": f"Unknown tool: {tool_name}"}

        tool = self.tools[tool_name]
        logger.info(f"Invoking tool '{tool_name}' with params: {kwargs}")

        call_kwargs = dict(kwargs)
        method_override = call_kwargs.pop("method", None)
        params_payload = call_kwargs.pop("params", None)
        if isinstance(params_payload, dict):
            call_kwargs = {**params_payload, **call_kwargs}

        method = None
        candidate_methods = []
        if method_override:
            candidate_methods.append(method_override)
        candidate_methods.extend([name for name in ["run", "query", "current", "execute", "search", "invoke"] if name not in candidate_methods])

        for candidate in candidate_methods:
            if hasattr(tool, candidate) and callable(getattr(tool, candidate)):
                method = getattr(tool, candidate)
                logger.debug(f"Tool '{tool_name}' using method '{candidate}' with args: {call_kwargs}")
                break

        if not method:
            return {"error": f"No callable interface found for tool '{tool_name}'"}

        try:
            result = method(**call_kwargs)
            # Ensure consistent structure
            if isinstance(result, dict):
                return result
            elif isinstance(result, list):
                return {"results": result}
            elif isinstance(result, str):
                return {"text": result}
            else:
                return {"result": result}
        except Exception as e:
            logger.error(f"Error invoking tool '{tool_name}': {e}", exc_info=True)
            return {"error": str(e)}

    # -----------------------------------------------------
    # Registry maintenance
    # -----------------------------------------------------
    def register(self, name: str, tool_instance: Any):
        """Dynamically register a new tool."""
        self.tools[name] = tool_instance
        logger.info(f"Registered new tool: {name}")

    def unregister(self, name: str):
        """Remove a tool from registry."""
        if name in self.tools:
            del self.tools[name]
            logger.info(f"Unregistered tool: {name}")
