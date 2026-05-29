import base64
import asyncio
from email.mime.text import MIMEText
from mether.tools.base import BaseTool, ToolResult, SecurityLevel
from .base_google import BaseGoogleTool

class GmailTool(BaseTool, BaseGoogleTool):
    name = "gmail"
    description = """
Gmail tool. Actions:
- search: search emails. params: query (Gmail search string), max_results (default 10)
- read: read a specific email. params: message_id
- send: send an email. params: to, subject, body
- reply: reply to an email. params: message_id, body
- list_unread: list unread emails, no params needed
- mark_read: mark email as read. params: message_id
"""
    security_level = SecurityLevel.WRITE

    def get_parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["search", "read", "send", "reply", "list_unread", "mark_read"]},
                "query": {"type": "string"},
                "max_results": {"type": "integer"},
                "message_id": {"type": "string"},
                "to": {"type": "string"},
                "subject": {"type": "string"},
                "body": {"type": "string"}
            },
            "required": ["action"]
        }

    async def execute(self, action: str, **kwargs) -> ToolResult:  # type: ignore[override]
        service = self._service("gmail", "v1")
        
        try:
            if action == "list_unread":
                results = await asyncio.to_thread(
                    service.users().messages().list(
                        userId="me",
                        q="is:unread",
                        maxResults=10
                    ).execute
                )
                
                messages = results.get("messages", [])
                
                def get_msg_metadata(msg_id):
                    return service.users().messages().get(
                        userId="me", id=msg_id,
                        format="metadata",
                        metadataHeaders=["From", "Subject", "Date"]
                    ).execute()
                
                msg_list = messages[:10]
                detailed_raw = await asyncio.gather(*(
                    asyncio.to_thread(get_msg_metadata, msg["id"])
                    for msg in msg_list
                ))
                
                detailed = []
                for msg_info, m in zip(msg_list, detailed_raw):
                    headers = {h["name"]: h["value"] for h in m["payload"]["headers"]}
                    detailed.append({
                        "id": msg_info["id"],
                        "from": headers.get("From", ""),
                        "subject": headers.get("Subject", ""),
                        "date": headers.get("Date", ""),
                        "snippet": m.get("snippet", "")
                    })
                return ToolResult(success=True, data={"emails": detailed, "count": len(detailed)})
            
            elif action == "search":
                query = kwargs.get("query", "")
                max_results = kwargs.get("max_results", 10)
                results = await asyncio.to_thread(
                    service.users().messages().list(
                        userId="me", q=query, maxResults=max_results
                    ).execute
                )
                messages = results.get("messages", [])
                
                def get_msg_metadata(msg_id):
                    return service.users().messages().get(
                        userId="me", id=msg_id,
                        format="metadata",
                        metadataHeaders=["From", "Subject", "Date"]
                    ).execute()
                
                msg_list = messages[:max_results]
                detailed_raw = await asyncio.gather(*(
                    asyncio.to_thread(get_msg_metadata, msg["id"])
                    for msg in msg_list
                ))
                
                detailed = []
                for msg_info, m in zip(msg_list, detailed_raw):
                    headers = {h["name"]: h["value"] for h in m["payload"]["headers"]}
                    detailed.append({
                        "id": msg_info["id"],
                        "from": headers.get("From", ""),
                        "subject": headers.get("Subject", ""),
                        "date": headers.get("Date", ""),
                        "snippet": m.get("snippet", "")
                    })
                return ToolResult(success=True, data={"emails": detailed, "count": len(detailed)})
            
            elif action == "read":
                message_id = kwargs["message_id"]
                msg = service.users().messages().get(
                    userId="me", id=message_id, format="full"
                ).execute()
                
                headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
                
                def get_body(payload):
                    if "body" in payload and payload["body"].get("data"):
                        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")
                    if "parts" in payload:
                        for part in payload["parts"]:
                            body = get_body(part)
                            if body:
                                return body
                    return ""
                
                body = get_body(msg["payload"])
                
                return ToolResult(success=True, data={
                    "id": message_id,
                    "from": headers.get("From", ""),
                    "to": headers.get("To", ""),
                    "subject": headers.get("Subject", ""),
                    "date": headers.get("Date", ""),
                    "body": body[:3000]  # truncate
                })
            
            elif action == "send":
                to = kwargs["to"]
                subject = kwargs["subject"]
                body = kwargs["body"]
                
                message = MIMEText(body)
                message["to"] = to
                message["subject"] = subject
                
                raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
                
                result = service.users().messages().send(
                    userId="me",
                    body={"raw": raw}
                ).execute()
                
                return ToolResult(success=True, data={
                    "sent": True,
                    "to": to,
                    "subject": subject,
                    "message_id": result["id"]
                })
            
            elif action == "reply":
                message_id = kwargs["message_id"]
                body_text = kwargs["body"]
                
                orig = service.users().messages().get(
                    userId="me", id=message_id, format="metadata",
                    metadataHeaders=["Subject", "From", "Message-ID"]
                ).execute()
                
                headers = {h["name"]: h["value"] for h in orig["payload"]["headers"]}
                thread_id = orig["threadId"]
                
                msg = MIMEText(body_text)
                msg["to"] = headers.get("From", "")
                msg["subject"] = "Re: " + headers.get("Subject", "").replace("Re: ", "")
                msg["In-Reply-To"] = headers.get("Message-ID", "")
                msg["References"] = headers.get("Message-ID", "")
                
                raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
                
                result = service.users().messages().send(
                    userId="me",
                    body={"raw": raw, "threadId": thread_id}
                ).execute()
                
                return ToolResult(success=True, data={"replied": True, "thread_id": thread_id})
            
            elif action == "mark_read":
                service.users().messages().modify(
                    userId="me",
                    id=kwargs["message_id"],
                    body={"removeLabelIds": ["UNREAD"]}
                ).execute()
                return ToolResult(success=True, data={"marked_read": kwargs["message_id"]})
            
            else:
                return ToolResult(success=False, error="Unknown action")
        
        except Exception as e:
            return ToolResult(success=False, error=str(e))
