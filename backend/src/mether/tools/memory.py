"""Memory search tools for the METHER OS agent.

Allows the agent to search past observations, view session timelines, and fetch
detailed logs using a token-efficient 3-layer workflow.
"""

from __future__ import annotations

from typing import Any

from mether.tools.base import BaseTool, SecurityLevel, ToolResult
from mether.memory.persistent_memory import PersistentMemory


class SearchMemoryTool(BaseTool):
    """Searches memory summaries and observations for a matching phrase."""

    name = "search_memory"
    description = "Search the agent's memory index for relevant past summaries and interactions."
    security_level = SecurityLevel.READ

    def __init__(self, persistent_memory: PersistentMemory) -> None:
        self.persistent_memory = persistent_memory

    def get_parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search term or phrase to search memory for.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of matches to return (default: 10).",
                    "default": 10,
                },
            },
            "required": ["query"],
        }

    async def execute(self, query: str, limit: int = 10) -> ToolResult:  # type: ignore[override]
        try:
            results = await self.persistent_memory.search(query, limit)
            return ToolResult(success=True, data=results)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class MemoryTimelineTool(BaseTool):
    """Retrieves context around a specific observation ID."""

    name = "memory_timeline"
    description = "Get chronological context (preceding/succeeding logs) around a specific observation ID."
    security_level = SecurityLevel.READ

    def __init__(self, persistent_memory: PersistentMemory) -> None:
        self.persistent_memory = persistent_memory

    def get_parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "observation_id": {
                    "type": "integer",
                    "description": "The ID of the target observation to get timeline for.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of preceding/succeeding logs to fetch (default: 5).",
                    "default": 5,
                },
            },
            "required": ["observation_id"],
        }

    async def execute(self, observation_id: int, limit: int = 5) -> ToolResult:  # type: ignore[override]
        try:
            results = await self.persistent_memory.get_timeline(observation_id, limit)
            return ToolResult(success=True, data=results)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class GetMemoryObservationsTool(BaseTool):
    """Fetches details for specific observation IDs."""

    name = "get_memory_observations"
    description = "Retrieve the full details (e.g. tool results, prompt text) for a list of observation IDs."
    security_level = SecurityLevel.READ

    def __init__(self, persistent_memory: PersistentMemory) -> None:
        self.persistent_memory = persistent_memory

    def get_parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "ids": {
                    "type": "array",
                    "items": {
                        "type": "integer",
                    },
                    "description": "List of integer observation IDs to fetch details for.",
                },
            },
            "required": ["ids"],
        }

    async def execute(self, ids: list[int]) -> ToolResult:  # type: ignore[override]
        try:
            results = await self.persistent_memory.get_observations(ids)
            return ToolResult(success=True, data=results)
        except Exception as e:
            return ToolResult(success=False, error=str(e))
