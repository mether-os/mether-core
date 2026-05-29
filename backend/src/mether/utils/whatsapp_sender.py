import asyncio
import httpx
from typing import Any, Union

async def send_whatsapp_message(client: httpx.AsyncClient, to: str, formatted: Union[str, list[str]], base_url: str = "http://localhost:3001") -> dict[str, Any]:
    """Helper to send single or multi-part messages to WhatsApp sidecar with a delay."""
    if isinstance(formatted, list):
        for i, msg_part in enumerate(formatted):
            if i > 0:
                await asyncio.sleep(1.5)
            resp = await client.post(f"{base_url}/send", json={"to": to, "message": msg_part})
            resp.raise_for_status()
        return {"success": True, "to": to, "messages_sent": len(formatted)}
    else:
        resp = await client.post(f"{base_url}/send", json={"to": to, "message": formatted})
        resp.raise_for_status()
        return resp.json()
