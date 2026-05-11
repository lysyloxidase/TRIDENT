"""Tool-node compatibility layer.

TRIDENT agents are designed around LangGraph tool nodes. In test and offline
environments LangGraph may not be installed, so this module provides a tiny
drop-in runner while preserving the same "tool node owns callable tools" shape.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    func: Callable[..., Any]

    def invoke(self, arguments: dict[str, Any] | None = None) -> Any:
        return self.func(**(arguments or {}))


class LocalToolNode:
    """Small local equivalent used when LangGraph is unavailable."""

    def __init__(self, tools: list[ToolDefinition]) -> None:
        self.tools = {tool.name: tool for tool in tools}
        self.calls: list[str] = []

    def call_tool(self, name: str, **arguments: Any) -> Any:
        if name not in self.tools:
            raise KeyError(f"Unknown tool: {name}")
        self.calls.append(name)
        return self.tools[name].invoke(arguments)

    def invoke(self, payload: dict[str, Any]) -> dict[str, Any]:
        name = payload["tool"]
        arguments = payload.get("arguments") or {}
        return {"tool": name, "output": self.call_tool(name, **arguments)}


def build_tool_node(tools: list[ToolDefinition]) -> Any:
    """Return a LangGraph ToolNode when installed, otherwise LocalToolNode."""

    try:
        from langgraph.prebuilt import ToolNode

        return ToolNode([tool.func for tool in tools])
    except Exception:
        return LocalToolNode(tools)
