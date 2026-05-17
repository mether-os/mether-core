"""WebSocket handler for real-time frontend ↔ backend communication."""

from __future__ import annotations

from typing import Any

import httpx
import time
import structlog
from fastapi import WebSocket, WebSocketDisconnect

from mether.agent.agent import METHERAgent
from mether.events.bus import EventBus
from mether.tools.whatsapp import HANDLED_CONTACTS

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
            
    async def _forward_whatsapp(data: Any) -> None:
        try:
            await websocket.send_json({
                "type": "whatsapp_message",
                "from": data.get("fromName"),
                "body": data.get("body"),
                "isGroup": data.get("isGroup"),
                "groupName": data.get("groupName")
            })
        except Exception:
            pass

    await bus.subscribe("agent.thinking", _forward_thinking)
    await bus.subscribe("tool.start", _forward_tool_start)
    await bus.subscribe("tool.done", _forward_tool_done)
    await bus.subscribe("whatsapp.message", _forward_whatsapp)

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
                
                # Emit to bus for other components
                await bus.emit("agent.thinking", {"message": text})

                # Send processing state and log to frontend immediately
                await websocket.send_json({"type": "orb_state", "state": "processing"})
                await websocket.send_json({
                    "type": "log",
                    "module": "AGENT",
                    "message": f"Processing: {text}"
                })

                # Process through the agent (may involve tool calls).
                response = await agent.process(text)

                # Broadcast to voice sidecar so it speaks the text too
                await bus.emit("voice.speak", {"text": response})

                # Send response and reset orb state to idle
                await websocket.send_json({"type": "response", "text": response})
                await websocket.send_json({"type": "orb_state", "state": "idle"})

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif msg_type == "handle_start":
                contact_id = data.get("contact_id")
                contact_name = data.get("contact_name") or contact_id
                ping_id = data.get("ping_id")
                
                logger.info(f"Starting auto-handle for {contact_name} ({contact_id}) via ping")
                
                # Fetch recent messages
                intro_msg = "Hey! Mayank's not available rn, I'm his AI assistant. I'll pass the message along, but is there anything I can help with?"
                
                try:
                    async with httpx.AsyncClient() as client:
                        # Add to handled contacts
                        HANDLED_CONTACTS[contact_id] = {
                            "name": contact_name,
                            "start_time": time.time(),
                            "last_activity": time.time(),
                            "messages": []
                        }
                        
                        resp = await client.get(f"http://localhost:3001/messages/{contact_id}")
                        if resp.status_code == 200:
                            msgs = resp.json().get("messages", [])
                            # Limit to last 3 msgs for context
                            for m in msgs[-3:]:
                                role = "assistant" if m.get("fromMe") else "user"
                                HANDLED_CONTACTS[contact_id]["messages"].append({"role": role, "content": m.get("body", "")})
                        
                        # Send the introductory reply
                        HANDLED_CONTACTS[contact_id]["messages"].append({"role": "assistant", "content": intro_msg})
                        await client.post("http://localhost:3001/send", json={"to": contact_id, "message": intro_msg})
                except Exception as e:
                    logger.error(f"Failed to start auto-handle: {e}")
                
                await bus.emit("whatsapp.handle_started", {"contact": contact_name})
                await websocket.send_json({"type": "wa_ping_resolved", "ping_id": ping_id})
                await websocket.send_json({
                    "type": "log",
                    "module": "WA",
                    "message": f"Now handling {contact_name}"
                })

            elif msg_type == "ping_dismissed":
                ping_id = data.get("ping_id")
                await websocket.send_json({"type": "wa_ping_resolved", "ping_id": ping_id})

            elif msg_type == "confirm_action":
                action_id = data.get("action_id")
                approved = data.get("approved", False)
                await agent.confirm_action(action_id, approved)

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


async def voice_ws(websocket: WebSocket):
    """WebSocket connection exclusively for the Voice Pipeline Sidecar."""
    logger = structlog.get_logger(__name__)
    await websocket.accept()
    logger.info("Voice sidecar connected")
    
    app = websocket.app
    bus = app.state.bus
    agent = app.state.agent
    
    async def _forward_speak(data: Any) -> None:
        try:
            await websocket.send_json({
                "type": "speak",
                "text": data.get("text")
            })
        except Exception:
            pass

    await bus.subscribe("voice.speak", _forward_speak)

    try:
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "voice_input":
                text = data.get("text", "")
                
                # 1. Emit orb to processing state
                await bus.emit("ws.send", {"type": "orb_state", "state": "processing"})
                
                # 2. Add to frontend log
                await bus.emit("ws.send", {
                    "type": "log", "module": "VOICE", 
                    "message": f"Processing: {text}"
                })
                
                # 3. Run through agent
                try:
                    response = await agent.process(text)
                except Exception as e:
                    logger.error(f"Voice agent error: {e}")
                    response = "Sorry, I encountered an error."
                
                # 4. Send response back to voice sidecar
                await websocket.send_json({
                    "type": "voice_response",
                    "text": response
                })
                
                # 5. Also send to frontend display
                await bus.emit("ws.send", {
                    "type": "response",
                    "text": response,
                    "source": "voice"
                })
    
    except WebSocketDisconnect:
        logger.info("Voice sidecar disconnected")
        await bus.emit("ws.send", {"type": "log", "module": "VOICE", "message": "Pipeline disconnected"})
        await bus.emit("ws.send", {"type": "voice_status", "status": "offline"})
    finally:
        await bus.unsubscribe("voice.speak", _forward_speak)
