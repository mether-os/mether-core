from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from mether.tools.base import BaseTool, ToolResult, SecurityLevel
from .base_google import BaseGoogleTool

_IST = ZoneInfo("Asia/Kolkata")

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

    async def execute(self, action: str, **kwargs) -> ToolResult:  # type: ignore[override]
        service = self._service("calendar", "v3")
        
        try:
            if action == "today":
                now = datetime.now(_IST)
                start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
                end = now.replace(hour=23, minute=59, second=59, microsecond=0).isoformat()
                
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
                now = datetime.now(_IST)
                start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
                end = (now + timedelta(days=7)).replace(hour=23, minute=59, second=59, microsecond=0).isoformat()
                
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
                now_str = datetime.now(timezone.utc).isoformat()
                events = service.events().list(
                    calendarId="primary",
                    timeMin=now_str,
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
                duration_minutes = kwargs.get("duration_minutes", 60)
                within_days = kwargs.get("within_days", 7)
                duration = timedelta(minutes=duration_minutes)

                # Search window: now → now + within_days (in IST)
                now = datetime.now(_IST)
                search_end = now + timedelta(days=within_days)

                events = service.events().list(
                    calendarId="primary",
                    timeMin=now.isoformat(),
                    timeMax=search_end.isoformat(),
                    singleEvents=True,
                    orderBy="startTime"
                ).execute()

                # Build sorted list of busy (start, end) intervals in IST
                busy: list[tuple[datetime, datetime]] = []
                for e in events.get("items", []):
                    raw_start = e["start"].get("dateTime", e["start"].get("date"))
                    raw_end = e["end"].get("dateTime", e["end"].get("date"))
                    try:
                        ev_start = datetime.fromisoformat(raw_start).astimezone(_IST)
                        ev_end = datetime.fromisoformat(raw_end).astimezone(_IST)
                        busy.append((ev_start, ev_end))
                    except Exception:
                        continue

                busy.sort(key=lambda x: x[0])

                # Scan each day from 09:00 → 21:00 IST in slot increments
                WORK_START_H, WORK_END_H = 9, 21
                for day_offset in range(within_days):
                    day = (now + timedelta(days=day_offset)).replace(
                        hour=WORK_START_H, minute=0, second=0, microsecond=0
                    )
                    day_end_limit = day.replace(hour=WORK_END_H)

                    slot_start = max(now, day)

                    while slot_start + duration <= day_end_limit:
                        slot_end = slot_start + duration
                        # Check for overlap with any busy period
                        conflict = any(
                            bs < slot_end and be > slot_start
                            for bs, be in busy
                        )
                        if not conflict:
                            return ToolResult(success=True, data={
                                "slot_start": slot_start.isoformat(),
                                "slot_end": slot_end.isoformat(),
                                "duration_minutes": duration_minutes,
                                "timezone": "Asia/Kolkata"
                            })
                        # Move past the conflicting event
                        next_free = slot_start
                        for bs, be in busy:
                            if bs < slot_end and be > slot_start:
                                next_free = max(next_free, be)
                        slot_start = next_free

                return ToolResult(success=False, error=f"No free {duration_minutes}-minute slot found in the next {within_days} days.")
                
            else:
                return ToolResult(success=False, error="Unknown action")
        except Exception as e:
            return ToolResult(success=False, error=str(e))
