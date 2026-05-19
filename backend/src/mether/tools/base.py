"""Abstract base class and shared models for all METHER tools."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import IntEnum
from typing import Any

from pydantic import BaseModel


class SecurityLevel(IntEnum):
    """Classifies how *risky* a tool invocation is.

    READ      — no side effects (e.g. system info)
    WRITE     — mutates local state (e.g. file write)
    DANGEROUS — external / irreversible (e.g. HTTP POST)
    """

    READ = 0
    WRITE = 1
    DANGEROUS = 2


class ToolResult(BaseModel):
    """Standardised result returned by every tool execution."""

    success: bool
    data: Any = None
    error: str | None = None


class BaseTool(ABC):
    """
    Abstract base class for all METHER OS tools.
    
    All tools must inherit from this class and implement execute().
    Tools are automatically discovered and registered via ToolRegistry.
    
    To create a new tool:
        1. Inherit from BaseTool
        2. Set name, description, security_level
        3. Implement execute()
        4. Register in main.py: registry.register(MyTool())
    
    Example:
        class WeatherTool(BaseTool):
            name = "weather"
            description = "Get current weather for a location"
            security_level = SecurityLevel.READ
            
            async def execute(self, location: str) -> ToolResult:
                # implementation
                return ToolResult(success=True, data={...})
    """

    name: str
    description: str
    security_level: SecurityLevel

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Run the tool and return a :class:`ToolResult`."""
        ...

    # ------------------------------------------------------------------
    # Schema helpers (Anthropic tool-calling format)
    # ------------------------------------------------------------------

    def get_parameters_schema(self) -> dict[str, Any]:
        """Override in subclasses that accept parameters.

        Return a JSON Schema ``object`` describing accepted keyword args.
        Default: no parameters.
        """
        return {
            "type": "object",
            "properties": {},
            "required": [],
        }

    def to_llm_schema(self) -> dict[str, Any]:
        """Return the tool description in Anthropic tool-calling format.

        The returned dict is ready to be sent in the ``tools`` array of an
        Anthropic ``/v1/messages`` request.
        """
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.get_parameters_schema(),
        }
