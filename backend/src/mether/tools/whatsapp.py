import httpx
from typing import Any, Dict

from mether.tools.base import BaseTool, SecurityLevel, ToolResult


class WhatsAppTool(BaseTool):
    name = "whatsapp"
    description = """
    WhatsApp tool. Subactions:
    - send: send a message. params: to (phone or name), message (text)
    - chats: get recent chats list
    - messages: get messages from a chat. params: chat_id
    
    Use 'send' to reply to someone on behalf of user.
    Always confirm with user before sending.
    """
    security_level = SecurityLevel.WRITE  # WRITE = needs confirmation
    
    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["send", "chats", "messages"],
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
                }
            },
            "required": ["action"]
        }
        
    async def execute(self, action: str, **kwargs) -> ToolResult:
        base = "http://localhost:3001"
        
        async with httpx.AsyncClient() as client:
            try:
                if action == "send":
                    if "to" not in kwargs or "message" not in kwargs:
                        return ToolResult(success=False, error="Missing 'to' or 'message' parameters.")
                    resp = await client.post(f"{base}/send", json={
                        "to": kwargs["to"],
                        "message": kwargs["message"]
                    })
                    resp.raise_for_status()
                    return ToolResult(success=True, data=resp.json())
                
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
                
                return ToolResult(success=False, error=f"Unknown action: {action}")
            except httpx.HTTPError as e:
                return ToolResult(success=False, error=f"WhatsApp sidecar request failed: {e}")
