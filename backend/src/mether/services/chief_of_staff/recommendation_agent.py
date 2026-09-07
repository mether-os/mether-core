import structlog
from typing import Any, Dict, List
from mether.agent.llm import LLMClient
from mether.events.bus import EventBus

logger = structlog.get_logger(__name__)

class RecommendationAgent:
    """Recommendation Agent: Compiles deep context-aware objective recommendations."""

    def __init__(self, llm: LLMClient, bus: EventBus) -> None:
        self.llm = llm
        self.bus = bus

    async def generate_recommendations(
        self,
        goals: List[Dict[str, Any]],
        upcoming_events: List[Dict[str, Any]],
        recent_chats: List[str],
        vitals: Dict[str, Any]
    ) -> str:
        """Analyze goals, calendar events, recent chats, and hardware vitals to suggest high-impact adjustments.

        Returns a markdown bulleted list of 3-5 tactical suggestions.
        """
        goals_str = "\n".join([f"- **{g['title']}** ({g['category']}) | Status: {g['status']} | Health: {g['health_score']}%" for g in goals])
        events_str = "\n".join([f"- Event: '{e.get('summary', '')}' at {e.get('start', '')}" for e in upcoming_events])
        chats_str = "\n".join([f"- {c}" for c in recent_chats])
        vitals_str = f"CPU: {vitals.get('cpu', 0)}% | RAM: {vitals.get('ram', 0)}% | System Uptime: {vitals.get('uptime', 0)}s"

        prompt = f"""You are a Strategic Recommendation Agent for METHER OS.
Your role is to analyze current active goals, upcoming calendar events, recent session conversation snippets, and system resources to make high-impact personal development recommendations.

ACTIVE GOALS:
{goals_str if goals_str else "No active goals."}

UPCOMING CALENDAR EVENTS:
{events_str if events_str else "No upcoming events scheduled."}

RECENT CONVERSATION SNIPPETS:
{chats_str if chats_str else "No recent conversations."}

HARDWARE/VITALS STATUS:
{vitals_str}

CRITICAL RULES:
1. Provide 3 to 5 extremely targeted, context-aware suggestions (e.g. suggesting preparation for an upcoming calendar event, flagging a goal with declining health score, or recommending workload balancing).
2. Write in a motivating, tactical, clear chief of staff tone.
3. Keep the output as a beautiful, concise markdown bulleted list. Do not use generic filler words or introductory remarks.
"""
        try:
            llm_resp = await self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                system="You are an proactive advisor who helps users balance their professional schedule and personal achievements."
            )
            content_blocks = llm_resp.get("content", [])
            suggestions = content_blocks[0].get("text", "") if content_blocks else "- Maintain current progression and schedule regular review syncs."
            logger.info("recommendation_agent.suggestions_generated")
            return suggestions
        except Exception as e:
            logger.error("recommendation_agent.suggestions_failed", error=str(e))
            return "- Dedicate scheduled focus periods to high-priority goals.\n- Address any overdue tasks to restore health scores."
