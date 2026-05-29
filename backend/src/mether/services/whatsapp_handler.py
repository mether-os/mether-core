import time
import httpx
import structlog
from typing import Any
from mether.tools.whatsapp import HANDLED_CONTACTS, HANDLED_CONTACTS_LOCK
from mether.utils.whatsapp_formatter import format_for_whatsapp
from mether.utils.whatsapp_sender import send_whatsapp_message

logger = structlog.get_logger(__name__)

def _enforce_alternating_roles(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    """Ensure messages follow the strict user/assistant alternating pattern.

    1. Merge consecutive messages from the same role by joining content.
    2. Drop leading assistant messages so the list always starts with 'user'.
    """
    if not messages:
        return messages

    # Step 1: merge consecutive same-role messages
    merged: list[dict[str, str]] = []
    for msg in messages:
        if merged and merged[-1]["role"] == msg["role"]:
            # Append content with a newline separator
            merged[-1]["content"] = merged[-1]["content"] + "\n" + msg["content"]
        else:
            merged.append({"role": msg["role"], "content": msg["content"]})

    # Step 2: drop leading assistant messages
    while merged and merged[0]["role"] != "user":
        merged.pop(0)

    return merged

async def handle_incoming_whatsapp_message(data: dict[str, Any], llm: Any, bus: Any) -> None:
    """Processes incoming WhatsApp messages, calls LLM, sends auto-reply, and posts updates to WebSocket."""
    contact_id = data.get("from")
    contact_num = data.get("contactNumber")
    
    matched_id = None
    async with HANDLED_CONTACTS_LOCK:
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
        
        async with HANDLED_CONTACTS_LOCK:
            if matched_id in HANDLED_CONTACTS:
                hc = HANDLED_CONTACTS[matched_id]
                hc["last_activity"] = time.time()
                hc["messages"].append({"role": "user", "content": data.get("body", "")})
                ctx_msgs = list(hc["messages"][-5:])
            else:
                matched_id = None
                
        if matched_id:
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

            ctx_msgs = _enforce_alternating_roles(ctx_msgs)
            try:
                llm_response = await llm.chat(messages=ctx_msgs, system=system_prompt)
                content = llm_response.get("content", [])
                llm_reply_raw = content[0].get("text", "") if content else "..."
            except Exception as e:
                logger.error(f"Auto-reply LLM error: {e}")
                llm_reply_raw = "Hey, Mayank's busy rn — he'll get back to you soon!"

            formatted = format_for_whatsapp(llm_reply_raw)
            
            async with httpx.AsyncClient() as client:
                try:
                    await send_whatsapp_message(client, matched_id, formatted)
                    llm_reply = "\n".join(formatted) if isinstance(formatted, list) else formatted
                except Exception as e:
                    logger.error(f"Failed to send auto-reply: {e}")
                    llm_reply = "Hey, Mayank's busy rn — he'll get back to you soon!"
                    
            async with HANDLED_CONTACTS_LOCK:
                if matched_id in HANDLED_CONTACTS:
                    HANDLED_CONTACTS[matched_id]["messages"].append({"role": "assistant", "content": llm_reply})
                    
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
        
    await bus.emit("whatsapp.message", data)
    await bus.emit("ws.send", {"type": "log", "module": "WA", "message": f"Message from {data.get('fromName')}: {data.get('body', '')[:50]}"})
