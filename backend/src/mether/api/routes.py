"""REST API routes for METHER OS backend."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request, BackgroundTasks
import httpx
from mether.agent.agent import METHERAgent
from mether.events.bus import EventBus
import structlog

router = APIRouter(tags=["mether"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe — always returns OK."""
    return {"status": "ok", "version": "0.1.0"}


@router.get("/status")
async def status(request: Request) -> dict[str, Any]:
    """Readiness / status check with runtime details."""
    tools: list[str] = request.app.state.tools.list_names()
    ws_clients: int = getattr(request.app.state, "ws_client_count", 0)
    return {
        "agent": "ready",
        "tools": tools,
        "ws_clients": ws_clients,
    }


@router.get("/tools")
async def list_tools(request: Request) -> list[dict[str, str]]:
    """Return descriptions of all registered tools."""
    return request.app.state.tools.list_descriptions()


@router.post("/whatsapp/event")
async def whatsapp_event(request: Request):
    """Receive events from the WhatsApp Node.js sidecar."""
    logger = structlog.get_logger(__name__)
    bus = request.app.state.bus
    
    body = await request.json()
    event = body.get("event")
    data = body.get("data", {})
    
    if event == "whatsapp.message":
        # Forward message to the frontend and log
        await bus.publish("whatsapp.message", data)
        await bus.publish("ws.send", {"type": "log", "data": {"module": "WA", "message": f"Message from {data.get('fromName')}: {data.get('body', '')[:50]}"}})
    
    elif event == "whatsapp.ready":
        logger.info("whatsapp.ready", status="connected")
        await bus.publish("ws.send", {"type": "log", "data": {"module": "WA", "message": "WhatsApp connected"}})
        
    elif event == "whatsapp.qr":
        # Can be emitted to frontend to display the QR code
        await bus.publish("whatsapp.qr", data)
        await bus.publish("ws.send", {"type": "log", "data": {"module": "WA", "message": "New QR code generated"}})
        
    elif event == "whatsapp.disconnected":
        logger.warning("whatsapp.disconnected", reason=data.get("reason"))
        await bus.publish("ws.send", {"type": "log", "data": {"module": "WA", "message": f"Disconnected: {data.get('reason')}"}})

    return {"success": True}


@router.get("/whatsapp/status")
async def whatsapp_status():
    """Proxy status check to the WhatsApp sidecar."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("http://localhost:3001/status")
            return resp.json()
    except httpx.HTTPError as e:
        return {"status": "disconnected", "error": str(e)}
