"""REST API routes for METHER OS backend."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request, BackgroundTasks
import httpx
from mether.agent.agent import METHERAgent
from mether.events.bus import EventBus
import structlog
import time
from mether.tools.whatsapp import HANDLED_CONTACTS

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
        contact_id = data.get("from")
        contact_num = data.get("contactNumber")
        logger.info(f"Incoming WA msg from: {contact_id} / Num: {contact_num} / {data.get('fromName')}")
        logger.info(f"Current HANDLED_CONTACTS: {list(HANDLED_CONTACTS.keys())}")
        
        matched_id = None
        if contact_id in HANDLED_CONTACTS:
            matched_id = contact_id
        elif contact_num:
            for hid in HANDLED_CONTACTS:
                if hid.startswith(str(contact_num) + "@"):
                    matched_id = hid
                    break
                    
        # Ultimate fallback: match by name
        if not matched_id and data.get("fromName"):
            for hid, hc in HANDLED_CONTACTS.items():
                if hc.get("name") == data.get("fromName"):
                    matched_id = hid
                    break
        
        if matched_id:
            logger.info(f"[WA-AUTO] Auto-handling message from {data.get('fromName')}")
            hc = HANDLED_CONTACTS[matched_id]
            hc["last_activity"] = time.time()
            hc["messages"].append({"role": "user", "content": data.get("body", "")})
            
            system_prompt = """You are handling WhatsApp messages on behalf of Mayank Sharma.
Mayank is currently not available. You are his personal AI assistant.

Rules:
- For the FIRST message in a conversation, introduce yourself:
  "Hey! Mayank's not available rn, I'm his AI assistant. I'll pass along your message and help if I can 🙏"
- For subsequent messages: just reply naturally and helpfully
- Keep track of conversation context
- If someone asks something you can't handle, say Mayank will get back to them
- Match Mayank's casual tone (Hinglish is fine)
- Do NOT sound like an AI assistant from a company
- Sound like a real person helping a friend"""

            llm = request.app.state.llm
            ctx_msgs = hc["messages"][-5:]
            try:
                llm_response = await llm.chat(messages=ctx_msgs, system=system_prompt)
                content = llm_response.get("content", [])
                llm_reply = content[0].get("text", "") if content else "..."
            except Exception as e:
                logger.error(f"Auto-reply LLM error: {e}")
                llm_reply = "Hey, Mayank's AI here — I ran into a small error processing your message!"

            hc["messages"].append({"role": "assistant", "content": llm_reply})
            
            async with httpx.AsyncClient() as client:
                await client.post("http://localhost:3001/send", json={"to": matched_id, "message": llm_reply})
            
            await bus.emit("ws.send", {
                "type": "whatsapp_auto_reply", 
                "to": data.get("fromName"), 
                "message": llm_reply, 
                "original": data.get("body")
            })

        # Forward message to the frontend and log
        await bus.emit("whatsapp.message", data)
        await bus.emit("ws.send", {"type": "log", "module": "WA", "message": f"Message from {data.get('fromName')}: {data.get('body', '')[:50]}"})
    
    elif event == "whatsapp.ready":
        logger.info("whatsapp.ready", status="connected")
        await bus.emit("ws.send", {"type": "log", "module": "WA", "message": "WhatsApp connected"})
        
    elif event == "whatsapp.qr":
        # Can be emitted to frontend to display the QR code
        await bus.emit("whatsapp.qr", data)
        await bus.emit("ws.send", {"type": "log", "module": "WA", "message": "New QR code generated"})
        
    elif event == "whatsapp.disconnected":
        logger.warning("whatsapp.disconnected", reason=data.get("reason"))
        await bus.emit("ws.send", {"type": "log", "module": "WA", "message": f"Disconnected: {data.get('reason')}"})

    return {"success": True}

@router.get("/whatsapp/handled")
async def get_handled():
    """Return currently handled contacts."""
    return HANDLED_CONTACTS

@router.get("/whatsapp/status")
async def whatsapp_status():
    """Proxy status check to the WhatsApp sidecar."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("http://localhost:3001/status")
            return resp.json()
    except httpx.HTTPError as e:
        return {"status": "disconnected", "error": str(e)}
