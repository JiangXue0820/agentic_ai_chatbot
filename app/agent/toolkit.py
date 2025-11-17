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
            # 优先使用 description 属性，否则使用 docstring 第一行
            description = getattr(tool, "description", None)
            if not description:
                doc = getattr(tool, "__doc__", "") or "No description provided."
                description = doc.strip().split("\n")[0]
            
            tool_desc = {
                "description": description,
            }
            
            # 包含 parameters schema（重要！让 LLM 知道正确的参数名）
            parameters = getattr(tool, "parameters", None)
            if parameters and isinstance(parameters, dict):
                tool_desc["parameters"] = parameters
            
            descriptions[name] = tool_desc
        
        return descriptions

    # -----------------------------------------------------
    # Tool invocation
    # -----------------------------------------------------
    def invoke(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        # Handle "tool.method" format - extract tool name
        if "." in tool_name:
            parts = tool_name.split(".", 1)
            tool_name = parts[0]
            logger.debug(f"Extracted tool '{tool_name}' from '{parts[0]}.{parts[1]}'")
        
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
