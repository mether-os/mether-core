"""Built-in tool: system_info — CPU, RAM, uptime, platform."""

from __future__ import annotations

import sys
import time
from typing import Any

import psutil

from mether.tools.base import BaseTool, SecurityLevel, ToolResult


class SystemTool(BaseTool):
    """Report basic system telemetry (read-only)."""

    name: str = "system_info"
    description: str = (
        "Get current system information including CPU usage, RAM usage, "
        "system uptime, and platform identifier."
    )
    security_level: SecurityLevel = SecurityLevel.READ

    def get_parameters_schema(self) -> dict[str, Any]:
        """No parameters required."""
        return {
            "type": "object",
            "properties": {},
            "required": [],
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Collect and return system metrics via psutil."""
        try:
            mem = psutil.virtual_memory()
            data = {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "ram_percent": mem.percent,
                "ram_used_gb": round(mem.used / (1024**3), 1),
                "ram_total_gb": round(mem.total / (1024**3), 1),
                "uptime_seconds": int(time.time() - psutil.boot_time()),
                "platform": sys.platform,
            }
            return ToolResult(success=True, data=data)
        except Exception as exc:
            return ToolResult(success=False, data=None, error=str(exc))
