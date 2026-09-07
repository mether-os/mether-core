import json
import structlog
from typing import Any, Dict, List
from mether.agent.llm import LLMClient
from mether.events.bus import EventBus

logger = structlog.get_logger(__name__)

class ExecutionAgent:
    """Execution Agent: Builds the daily execution agenda, prioritizes tasks, and flags blockers."""

    def __init__(self, llm: LLMClient, bus: EventBus) -> None:
        self.llm = llm
        self.bus = bus

    async def generate_daily_priorities(
        self,
        active_tasks: List[Dict[str, Any]],
        overdue_tasks: List[Dict[str, Any]],
        context_notes: str,
        today_date: str
    ) -> Dict[str, Any]:
        """Synthesize goals, tasks, and calendar/conversation context to generate the daily focus.

        Returns a dictionary:
        {
          "priorities": [
            {
              "task_id": "task_id_string",
              "reason": "Why this is a priority today"
            }
          ],
          "blockers": [
            {
              "task_id": "task_id_string",
              "issue": "What the blocker is",
              "recommendation": "How to resolve it"
            }
          ],
          "focus_area": "Theme of the day (e.g. Core System Hardening)"
        }
        """
        # Format lists for LLM context
        tasks_context = ""
        for t in active_tasks:
            tasks_context += f"- Task [{t['id']}]: '{t['title']}' | Priority: {t['priority']} | Due: {t['due_date']} | Goal: '{t.get('goal_title', '')}'\n"

        overdue_context = ""
        for t in overdue_tasks:
            overdue_context += f"- Overdue Task [{t['id']}]: '{t['title']}' | Priority: {t['priority']} | Due: {t['due_date']} | Goal: '{t.get('goal_title', '')}'\n"

        prompt = f"""You are a Daily Execution Agent for METHER OS.
Your task is to analyze the user's active goals, pending tasks, overdue items, and recent calendar/conversation context to formulate a high-impact Daily Agenda.

Today's Date: {today_date}

ACTIVE TASKS:
{tasks_context if tasks_context else "No active tasks."}

OVERDUE TASKS:
{overdue_context if overdue_context else "No overdue tasks."}

RECENT CONTEXT / VITALS / EVENTS / LOGS:
{context_notes if context_notes else "No recent context logged."}

CRITICAL RULES:
1. Select 2 to 4 highest-leverage tasks from the active or overdue list to form the 'priorities' list. Explain clearly why each was selected.
2. Scan the context and overdue list to flag any blockers (tasks that are overdue, have dependency issues, or conflict with daily vitals/events). If none, return an empty blockers list.
3. Formulate a 1-sentence 'focus_area' representing the main theme for the day.
4. Output ONLY a valid JSON block matching the structure below.
5. Do NOT include markdown wraps or backticks outside the JSON.

EXPECTED JSON SCHEMA FORMAT:
{{
  "priorities": [
    {{
      "task_id": "task_1",
      "reason": "High priority task overdue since yesterday. Crucial to unblock Chapter 3 milestones."
    }}
  ],
  "blockers": [
    {{
      "task_id": "task_2",
      "issue": "Overdue by 5 days; missing dependency coordinates.",
      "recommendation": "Allocate 30 minutes to review SolDev integration specs."
    }}
  ],
  "focus_area": "Anchor Smart Contract Core Architecture Design"
}}
"""
        try:
            llm_resp = await self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                system="You are a tactical operations expert who helps executives prioritize their day flawlessly."
            )
            content_blocks = llm_resp.get("content", [])
            reply_text = content_blocks[0].get("text", "") if content_blocks else ""

            cleaned_text = reply_text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.startswith("```"):
                cleaned_text = cleaned_text[3:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
            cleaned_text = cleaned_text.strip()

            result = json.loads(cleaned_text)
            logger.info("execution_agent.priorities_generated", priorities_count=len(result.get("priorities", [])))
            return result
        except Exception as e:
            logger.exception("execution_agent.priorities_failed", error=str(e))
            # Fallback mock priorities
            fallback_priorities = []
            if active_tasks:
                fallback_priorities.append({
                    "task_id": active_tasks[0]["id"],
                    "reason": "Top active task to maintain velocity."
                })
            return {
                "priorities": fallback_priorities,
                "blockers": [],
                "focus_area": "General Goal Progression & Review"
            }
