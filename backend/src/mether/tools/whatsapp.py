import httpx
import asyncio
from typing import Any
import time

from mether.utils.whatsapp_formatter import format_for_whatsapp
from mether.tools.base import BaseTool, SecurityLevel, ToolResult

HANDLED_CONTACTS: dict[str, Any] = {}
HANDLED_CONTACTS_LOCK = asyncio.Lock()


class WhatsAppTool(BaseTool):
    name = "whatsapp"
    description = """
    WhatsApp tool. Subactions:
    - send: send a message. params: to (phone or name), message (text)
    - chats: get recent chats list
    - messages: get messages from a chat. params: chat_id
    - resolve: resolve a contact name to their phone ID. params: query (name)
    - handle: start or stop auto-handling messages from a contact. params: contact_name (name), active (boolean, default True)
    
    Use 'send' to reply to someone on behalf of user.
    Always confirm with user before sending.
    Use 'handle' when user asks you to take over or auto-reply to someone.
    """
    security_level = SecurityLevel.WRITE  # WRITE = needs confirmation
    
    def get_parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["send", "chats", "messages", "resolve", "handle"],
                    "description": "The action to perform."
                },
                "to": {
                    "type": "string",
                    "description": "Phone number or name of the contact (for 'send' action)."
                },
                "message": {
                    "type": "string",
                    "description": "The text message to send (for 'send' action)."
                },
                "chat_id": {
                    "type": "string",
                    "description": "The ID of the chat (for 'messages' action)."
                },
                "query": {
                    "type": "string",
                    "description": "The contact name to search for (for 'resolve' action)."
                },
                "contact_name": {
                    "type": "string",
                    "description": "The contact name to handle messages for."
                },
                "active": {
                    "type": "boolean",
                    "description": "Whether to start (true) or stop (false) handling."
                }
            },
            "required": ["action"]
        }
        
    async def execute(self, action: str = "send", **kwargs) -> ToolResult:
        base = "http://localhost:3001"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                if action == "send":
                    if "to" not in kwargs or "message" not in kwargs:
                        return ToolResult(success=False, error="Missing 'to' or 'message' parameters.")
                    
                    to_param = kwargs["to"]
                    resolved_name = None
                    
                    # If 'to' looks like a name (not just digits and @), try to resolve it first
                    if "@" not in to_param and not to_param.replace("+", "").isdigit():
                        res_resp = await client.post(f"{base}/resolve", json={"query": to_param})
                        if res_resp.status_code == 200:
                            resolved = res_resp.json()
                            to_param = resolved["id"]
                            resolved_name = resolved["name"]
                    
                    raw_message = kwargs["message"]
                    formatted = format_for_whatsapp(raw_message)
                    
                    # Multi-message (code replies) — send each part with delay
                    if isinstance(formatted, list):
                        for i, msg_part in enumerate(formatted):
                            if i > 0:
                                await asyncio.sleep(1.5)
                            await client.post(f"{base}/send", json={
                                "to": to_param,
                                "message": msg_part
                            })
                        result_data = {"success": True, "to": to_param, "messages_sent": len(formatted)}
                    else:
                        resp = await client.post(f"{base}/send", json={
                            "to": to_param,
                            "message": formatted
                        })
                        resp.raise_for_status()
                        result_data = resp.json()
                    
                    if resolved_name:
                        result_data["resolved_name"] = resolved_name
                        result_data["resolved_number"] = to_param
                        
                    return ToolResult(success=True, data=result_data)
                
                elif action == "chats":
                    resp = await client.get(f"{base}/chats")
                    resp.raise_for_status()
                    return ToolResult(success=True, data=resp.json())
                
                elif action == "messages":
                    if "chat_id" not in kwargs:
                        return ToolResult(success=False, error="Missing 'chat_id' parameter.")
                    resp = await client.get(f"{base}/messages/{kwargs['chat_id']}")
                    resp.raise_for_status()
                    return ToolResult(success=True, data=resp.json())
                    
                elif action == "resolve":
                    if "query" not in kwargs:
                        return ToolResult(success=False, error="Missing 'query' parameter.")
                    resp = await client.post(f"{base}/resolve", json={"query": kwargs["query"]})
                    resp.raise_for_status()
                    return ToolResult(success=True, data=resp.json())
                    
                elif action == "handle":
                    contact_name = kwargs.get("contact_name")
                    active = kwargs.get("active", True)
                    if not contact_name:
                        return ToolResult(success=False, error="Missing 'contact_name' parameter.")
                        
                    res_resp = await client.post(f"{base}/resolve", json={"query": contact_name})
                    if res_resp.status_code != 200:
                        return ToolResult(success=False, error=f"Could not resolve {contact_name}")
                        
                    resolved = res_resp.json()
                    contact_id = resolved["id"]
                    resolved_name = resolved["name"]
                    
                    async with HANDLED_CONTACTS_LOCK:
                        if active:
                            HANDLED_CONTACTS[contact_id] = {
                                "name": resolved_name,
                                "start_time": time.time(),
                                "last_activity": time.time(),
                                "messages": []
                            }
                            return ToolResult(success=True, data={"message": f"Now handling {resolved_name}", "contact": resolved_name})
                        else:
                            if contact_id in HANDLED_CONTACTS:
                                HANDLED_CONTACTS[contact_id]["stop_requested"] = True
                            return ToolResult(success=True, data={"message": f"Stopped handling {resolved_name}. Summary is being generated."})
                
                return ToolResult(success=False, error=f"Unknown action: {action}")
            except httpx.HTTPError as e:
                return ToolResult(success=False, error=f"WhatsApp sidecar request failed: {e}")
