from datetime import datetime, timezone, timedelta
from mether.tools.base import BaseTool, ToolResult, SecurityLevel
from .base_google import BaseGoogleTool

class CalendarTool(BaseTool, BaseGoogleTool):
    name = "calendar"
    description = """
Google Calendar tool. Actions:
- today: get today's events
- week: get this week's events
- create: create an event. params: title, start (ISO datetime), end (ISO datetime), description (optional)
- upcoming: next N events. params: count (default 5)
- find_slot: find a free slot. params: duration_minutes, within_days (default 7)
"""
    security_level = SecurityLevel.WRITE

    def get_parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["today", "week", "create", "upcoming", "find_slot"]},
                "title": {"type": "string"},
                "start": {"type": "string"},
                "end": {"type": "string"},
                "description": {"type": "string"},
                "count": {"type": "integer"},
                "duration_minutes": {"type": "integer"},
                "within_days": {"type": "integer"}
            },
            "required": ["action"]
        }

    async def execute(self, action: str, **kwargs) -> ToolResult:
        service = self._service("calendar", "v3")
        
        try:
            if action == "today":
                now = datetime.now(timezone.utc)
                start = now.replace(hour=0, minute=0, second=0).isoformat()
                end = now.replace(hour=23, minute=59, second=59).isoformat()
                
                events = service.events().list(
                    calendarId="primary",
                    timeMin=start,
                    timeMax=end,
                    singleEvents=True,
                    orderBy="startTime"
                ).execute()
                
                items = events.get("items", [])
                simplified = [{
                    "id": e["id"],
                    "title": e.get("summary", "No title"),
                    "start": e["start"].get("dateTime", e["start"].get("date")),
                    "end": e["end"].get("dateTime", e["end"].get("date")),
                    "location": e.get("location", ""),
                    "description": e.get("description", "")[:200]
                } for e in items]
                
                return ToolResult(success=True, data={
                    "events": simplified,
                    "count": len(simplified),
                    "date": now.strftime("%Y-%m-%d")
                })
            
            elif action == "week":
                now = datetime.now(timezone.utc)
                start = now.replace(hour=0, minute=0, second=0).isoformat()
                end = (now + timedelta(days=7)).replace(hour=23, minute=59, second=59).isoformat()
                
                events = service.events().list(
                    calendarId="primary",
                    timeMin=start,
                    timeMax=end,
                    singleEvents=True,
                    orderBy="startTime"
                ).execute()
                
                items = events.get("items", [])
                simplified = [{
                    "id": e["id"],
                    "title": e.get("summary", "No title"),
                    "start": e["start"].get("dateTime", e["start"].get("date")),
                    "end": e["end"].get("dateTime", e["end"].get("date")),
                    "location": e.get("location", ""),
                    "description": e.get("description", "")[:200]
                } for e in items]
                
                return ToolResult(success=True, data={
                    "events": simplified,
                    "count": len(simplified)
                })
            
            elif action == "upcoming":
                count = kwargs.get("count", 5)
                now = datetime.now(timezone.utc).isoformat()
                events = service.events().list(
                    calendarId="primary",
                    timeMin=now,
                    maxResults=count,
                    singleEvents=True,
                    orderBy="startTime"
                ).execute()
                
                items = events.get("items", [])
                simplified = [{
                    "id": e["id"],
                    "title": e.get("summary", "No title"),
                    "start": e["start"].get("dateTime", e["start"].get("date")),
                    "end": e["end"].get("dateTime", e["end"].get("date")),
                    "location": e.get("location", ""),
                    "description": e.get("description", "")[:200]
                } for e in items]
                return ToolResult(success=True, data={"events": simplified, "count": len(simplified)})
            
            elif action == "create":
                title = kwargs["title"]
                start = kwargs["start"]
                end = kwargs["end"]
                description = kwargs.get("description", "")
                
                event = {
                    "summary": title,
                    "description": description,
                    "start": {"dateTime": start, "timeZone": "Asia/Kolkata"},
                    "end": {"dateTime": end, "timeZone": "Asia/Kolkata"},
                }
                
                result = service.events().insert(
                    calendarId="primary", body=event
                ).execute()
                
                return ToolResult(success=True, data={
                    "created": True,
                    "title": title,
                    "event_id": result["id"],
                    "link": result.get("htmlLink", "")
                })
            
            elif action == "find_slot":
                duration = kwargs.get("duration_minutes", 60)
                within_days = kwargs.get("within_days", 7)
                
                # Get events for the next N days
                now = datetime.now(timezone.utc)
                end_time = now + timedelta(days=within_days)
                
                events = service.events().list(
                    calendarId="primary",
                    timeMin=now.isoformat(),
                    timeMax=end_time.isoformat(),
                    singleEvents=True,
                    orderBy="startTime"
                ).execute()
                
                items = events.get("items", [])
                # Not fully implementing complex scheduling logic right now
                # Simple placeholder
                return ToolResult(success=False, error="find_slot not fully implemented yet")
                
            else:
                return ToolResult(success=False, error="Unknown action")
        except Exception as e:
            return ToolResult(success=False, error=str(e))
