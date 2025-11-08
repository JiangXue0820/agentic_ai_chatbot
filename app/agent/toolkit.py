# =====================================================
# app/agent/toolkit.py
# Tool Registry & Invocation Logic
# =====================================================

from typing import Dict, Any


class ToolRegistry:
    """
    Central registry for all callable tools (weather, gmail, vdb, etc.).
    Provides schema descriptions and safe invocation.
    """

    def __init__(self, tools: Dict[str, Any]):
        self.tools = tools

    def describe(self) -> Dict[str, Any]:
        """
        Returns a JSON-like description of available tools.
        """
        descriptions = {}
        for name, tool in self.tools.items():
            descriptions[name] = {
                "description": getattr(tool, "description", ""),
                "parameters": getattr(tool, "parameters", {}),
            }
        return descriptions

    def invoke(self, name: str, **kwargs) -> Dict[str, Any]:
        """
        Invokes the given tool safely.
        """
        if name not in self.tools:
            raise ValueError(f"Tool '{name}' not found in registry.")
        tool = self.tools[name]
        if not hasattr(tool, "run"):
            raise TypeError(f"Tool '{name}' does not implement 'run()'.")
        return tool.run(**kwargs)
