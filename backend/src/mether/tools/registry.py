"""Tool registry — register, look up, and enumerate METHER tools."""

from __future__ import annotations

from typing import Any

import structlog

from mether.tools.base import BaseTool

logger = structlog.get_logger(__name__)


class ToolRegistry:
    """Central catalogue of all available tools.

    Tools are stored by *name* and must be unique.
    """

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool instance.  Overwrites silently if name exists."""
        self._tools[tool.name] = tool
        logger.info("tool_registry.registered", tool=tool.name)

    def get(self, name: str) -> BaseTool | None:
        """Return the tool with *name*, or ``None``."""
        return self._tools.get(name)

    def all_schemas(self) -> list[dict[str, Any]]:
        """Return Anthropic-format tool schemas for every registered tool."""
        return [t.to_llm_schema() for t in self._tools.values()]

    def list_names(self) -> list[str]:
        """Return a sorted list of registered tool names."""
        return sorted(self._tools.keys())

    def list_descriptions(self) -> list[dict[str, str]]:
        """Return ``[{name, description, security}]`` for each tool."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "security_level": t.security_level.name,
            }
            for t in self._tools.values()
        ]

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools
