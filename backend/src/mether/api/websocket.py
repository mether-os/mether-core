"""WebSocket handler for real-time frontend ↔ backend communication."""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import WebSocket, WebSocketDisconnect

from mether.agent.agent import METHERAgent
from mether.events.bus import EventBus

logger = structlog.get_logger(__name__)


async def websocket_endpoint(
    websocket: WebSocket,
    agent: METHERAgent,
    bus: EventBus,
) -> None:
    """Handle a single WebSocket client session.

    Protocol
    --------
    **Inbound** (client → server):

    - ``{"type": "message", "text": "..."}`` — user chat message
    - ``{"type": "ping"}``                    — keep-alive

    **Outbound** (server → client):

    - ``{"type": "response", "text": "..."}`` — agent reply
    - ``{"type": "pong"}``                     — ping reply
    - Any payload forwarded by the ``ws.send`` event bus channel.
    """
    await websocket.accept()
    logger.info("ws.connected", client=websocket.client)

    # Track connection count on app state.
    app = websocket.app
    app.state.ws_client_count = getattr(app.state, "ws_client_count", 0) + 1

    # ------- Bus → WebSocket forwarder -----------------------------------
    async def _forward_to_ws(data: Any) -> None:
        try:
            await websocket.send_json(data)
        except Exception:
            logger.debug("ws.forward_failed")

    await bus.subscribe("ws.send", _forward_to_ws)

    # Also forward real-time agent events so the frontend can show spinners.
    async def _forward_thinking(data: Any) -> None:
        try:
            await websocket.send_json({"type": "agent.thinking", "data": data})
        except Exception:
            pass

    async def _forward_tool_start(data: Any) -> None:
        try:
            await websocket.send_json({"type": "tool.start", "data": data})
        except Exception:
            pass

    async def _forward_tool_done(data: Any) -> None:
        try:
            await websocket.send_json({"type": "tool.done", "data": data})
        except Exception:
            pass

    await bus.subscribe("agent.thinking", _forward_thinking)
    await bus.subscribe("tool.start", _forward_tool_start)
    await bus.subscribe("tool.done", _forward_tool_done)

    # ------- Main receive loop -------------------------------------------
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "message":
                text = data.get("text", "").strip()
                if not text:
                    await websocket.send_json({"type": "error", "text": "Empty message"})
                    continue

                logger.info("ws.message_received", text=text[:100])
                await bus.emit("message.received", {"text": text})

                # Process through the agent (may involve tool calls).
                response = await agent.process(text)

                await websocket.send_json({"type": "response", "text": response})

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            else:
                await websocket.send_json(
                    {"type": "error", "text": f"Unknown message type: {msg_type}"}
                )

    except WebSocketDisconnect:
        logger.info("ws.disconnected", client=websocket.client)

    except Exception:
        logger.exception("ws.unexpected_error")

    finally:
        # Clean up subscriptions
        await bus.unsubscribe("ws.send", _forward_to_ws)
        await bus.unsubscribe("agent.thinking", _forward_thinking)
        await bus.unsubscribe("tool.start", _forward_tool_start)
        await bus.unsubscribe("tool.done", _forward_tool_done)
        app.state.ws_client_count = max(0, getattr(app.state, "ws_client_count", 1) - 1)
