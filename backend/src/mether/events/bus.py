"""Lightweight async publish / subscribe event bus.

Events used across the system
------------------------------
- ``message.received``  — user sends a message
- ``agent.thinking``    — agent is processing
- ``agent.response``    — agent finished responding
- ``tool.start``        — tool execution started
- ``tool.done``         — tool execution completed
- ``ws.send``           — forward payload to the frontend WebSocket
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any, Callable, Coroutine

import structlog

logger = structlog.get_logger(__name__)

# Type alias for an async event handler.
Handler = Callable[..., Coroutine[Any, Any, None]]


class EventBus:
    """Simple in-process async event bus (pub / sub)."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Handler]] = defaultdict(list)

    async def subscribe(self, event_name: str, handler: Handler) -> None:
        """Register *handler* for *event_name*.

        Parameters
        ----------
        event_name:
            Event name, e.g. ``"agent.thinking"``.
        handler:
            An async callable ``(data) -> None``.
        """
        self._subscribers[event_name].append(handler)
        logger.debug("event_bus.subscribe", event_name=event_name, handler=handler.__qualname__)

    async def unsubscribe(self, event_name: str, handler: Handler) -> None:
        """Remove *handler* from *event_name* listeners."""
        try:
            self._subscribers[event_name].remove(handler)
        except ValueError:
            pass

    async def emit(self, event_name: str, data: Any = None) -> None:
        """Emit *event_name* with optional *data* to all registered handlers.

        Handlers are invoked concurrently via ``asyncio.gather``.
        Individual handler exceptions are logged but do **not** propagate.
        """
        handlers = list(self._subscribers.get(event_name, []))
        if not handlers:
            return

        logger.debug("event_bus.emit", event_name=event_name, handler_count=len(handlers))

        async def _safe_call(h: Handler) -> None:
            try:
                await h(data)
            except Exception:
                logger.exception(
                    "event_bus.handler_error",
                    event_name=event_name,
                    handler=h.__qualname__,
                )

        await asyncio.gather(*(_safe_call(h) for h in handlers))
