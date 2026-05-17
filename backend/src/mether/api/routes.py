"""REST API routes for METHER OS backend."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
import httpx
import asyncio
import structlog
import time
from mether.tools.whatsapp import HANDLED_CONTACTS
from mether.utils.whatsapp_formatter import format_for_whatsapp

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
            
            system_prompt = """You are texting on WhatsApp on behalf of Mayank Sharma (22, CS student, India).
Mayank is busy rn. You're replying as him — not as an AI, not as an assistant.

CRITICAL RULES — follow these EXACTLY:
- Write like a 22-year-old Indian CS student would text on WhatsApp
- Use Hinglish naturally (bhai, yaar, chill, haan, nahi, kya, etc.)
- Short sentences. Keep it brief. No essays.
- NEVER use bullet points or numbered lists
- NEVER start with 'Sure' or 'Certainly' or 'Great question' or 'Absolutely'
- NEVER say 'As an AI' or 'I'm an AI assistant' or similar
- If first message: briefly mention Mayank's busy, you're helping out
- For code questions: paste code plainly, say 'yeh try karo' or 'try this'
- For casual chat: just vibe naturally, use 'lol' 'haha' 'ok' 'acha' where natural
- If you can't help: say Mayank will reply later, don't over-apologize
- Match the energy of the person you're talking to
- Typos are fine occasionally (but never in code)
- NO markdown. NO bold. NO italics. NO headers. Just plain text."""

            llm = request.app.state.llm
            ctx_msgs = hc["messages"][-5:]
            try:
                llm_response = await llm.chat(messages=ctx_msgs, system=system_prompt)
                content = llm_response.get("content", [])
                llm_reply_raw = content[0].get("text", "") if content else "..."
            except Exception as e:
                logger.error(f"Auto-reply LLM error: {e}")
                llm_reply_raw = "Hey, Mayank's busy rn — he'll get back to you soon!"

            # Post-process through the formatter to strip any remaining AI-isms
            formatted = format_for_whatsapp(llm_reply_raw)
            
            # Send as single or multi-message
            async with httpx.AsyncClient() as client:
                if isinstance(formatted, list):
                    for i, msg_part in enumerate(formatted):
                        if i > 0:
                            await asyncio.sleep(1.5)
                        await client.post("http://localhost:3001/send", json={"to": matched_id, "message": msg_part})
                    llm_reply = "\n".join(formatted)
                else:
                    await client.post("http://localhost:3001/send", json={"to": matched_id, "message": formatted})
                    llm_reply = formatted

            hc["messages"].append({"role": "assistant", "content": llm_reply})
            
            await bus.emit("ws.send", {
                "type": "whatsapp_auto_reply", 
                "to": data.get("fromName"), 
                "message": llm_reply, 
                "original": data.get("body")
            })
        else:
            # Emit wa_ping for unhandled messages
            import uuid
            ping_id = str(uuid.uuid4())
            await bus.emit("ws.send", {
                "type": "wa_ping",
                "contact_id": contact_id,
                "contact_name": data.get("fromName") or contact_id,
                "preview": data.get("body", "")[:60],
                "timestamp": data.get("timestamp", int(time.time())),
                "ping_id": ping_id
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

@router.post("/voice/event")
async def voice_event(request: Request):
    """Receive lifecycle events from the voice sidecar."""
    logger = structlog.get_logger(__name__)
    bus = request.app.state.bus
    
    body = await request.json()
    event = body.get("event")
    data = body.get("data", {})
    
    if event == "voice.online":
        logger.info("[VOICE] Pipeline online")
        await bus.emit("ws.send", {"type": "log", "module": "VOICE", "message": "Pipeline online"})
        await bus.emit("ws.send", {"type": "voice_status", "status": "online"})
        
    elif event == "voice.offline":
        logger.info("[VOICE] Pipeline offline")
        await bus.emit("ws.send", {"type": "log", "module": "VOICE", "message": "Pipeline offline"})
        await bus.emit("ws.send", {"type": "voice_status", "status": "offline"})
        
    elif event == "voice.wake":
        logger.info("[VOICE] Wake word detected")
        await bus.emit("ws.send", {"type": "orb_state", "state": "listening"})
        await bus.emit("ws.send", {"type": "log", "module": "VOICE", "message": "Wake word detected"})
        
    elif event == "voice.transcript":
        text = data.get("text", "")
        await bus.emit("ws.send", {"type": "log", "module": "VOICE", "message": f"Heard: {text}"})
        
    elif event == "voice.speaking":
        await bus.emit("ws.send", {"type": "orb_state", "state": "speaking"})
        
    elif event == "voice.done":
        await bus.emit("ws.send", {"type": "orb_state", "state": "idle"})
        
    return {"success": True}

@router.get("/google/status")
async def google_status(request: Request) -> dict[str, Any]:
    from mether.tools.google.auth import GoogleAuth
    config = request.app.state.config
    auth = GoogleAuth(config.google_credentials_path, config.google_token_path)
    if not auth.is_authenticated():
        return {"authenticated": False}
    
    try:
        from googleapiclient.discovery import build
        service = build("gmail", "v1", credentials=auth.get_credentials())
        profile = service.users().getProfile(userId="me").execute()
        email = profile.get("emailAddress")
    except Exception:
        email = None
        
    return {
        "authenticated": True,
        "email": email,
        "scopes": getattr(auth.get_credentials(), "scopes", []),
        "token_expires": str(getattr(auth.get_credentials(), "expiry", None))
    }

@router.get("/google/auth")
async def google_auth_endpoint(request: Request) -> dict[str, Any]:
    from mether.tools.google.auth import GoogleAuth
    config = request.app.state.config
    auth = GoogleAuth(config.google_credentials_path, config.google_token_path)
    if auth.is_authenticated():
        return {"authenticated": True, "message": "Already logged in"}
    
    try:
        auth.get_credentials()
        return {"authenticated": True, "email": "Connected"}
    except Exception as e:
        return {"authenticated": False, "error": str(e)}

@router.get("/google/logout")
async def google_logout(request: Request) -> dict[str, Any]:
    from mether.tools.google.auth import GoogleAuth
    config = request.app.state.config
    auth = GoogleAuth(config.google_credentials_path, config.google_token_path)
    if auth.token_path.exists():
        auth.token_path.unlink()
    return {"logged_out": True}
