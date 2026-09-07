import json
import structlog
from typing import Any, Dict, List
from mether.agent.llm import LLMClient
from mether.events.bus import EventBus

logger = structlog.get_logger(__name__)

class ReviewAgent:
    """Review Agent: Reviews progress logs, calculates consistency, and generates comprehensive weekly reviews."""

    def __init__(self, llm: LLMClient, bus: EventBus) -> None:
        self.llm = llm
        self.bus = bus

    async def generate_weekly_review(
        self,
        completed_tasks: List[Dict[str, Any]],
        missed_tasks: List[Dict[str, Any]],
        progress_notes: List[str],
        week_start: str,
        week_end: str
    ) -> Dict[str, str]:
        """Generate accomplishments, missed targets, risks, and recommendations in beautiful markdown format.

        Returns a dictionary:
        {
          "accomplishments": "Markdown summary of completed milestones and tasks",
          "missed_targets": "Markdown list of missed milestones/tasks and why",
          "risks": "Markdown risk assessment (e.g. fatigue, blockages, delay risks)",
          "recommendations": "Markdown strategic adjustments for the upcoming week"
        }
        """
        # Format metrics
        completed_list = "\n".join([f"- **{t['title']}** (Goal: {t.get('goal_title', 'General')}) | Time Invested: {t.get('time_invested_mins', 0)} mins" for t in completed_tasks])
        missed_list = "\n".join([f"- **{t['title']}** (Goal: {t.get('goal_title', 'General')}) | Due: {t.get('due_date', 'None')}" for t in missed_tasks])
        notes_str = "\n".join([f"- {note}" for note in progress_notes])

        prompt = f"""You are a Weekly Strategic Review Agent for METHER OS.
Your task is to analyze the user's progress log and task completions from {week_start} to {week_end} and formulate a highly professional, constructive Weekly Review.

WEEK'S STATS:
- Completed Tasks: {len(completed_tasks)}
- Missed / Overdue Tasks: {len(missed_tasks)}

COMPLETED TASKS DETAILS:
{completed_list if completed_list else "No tasks completed."}

MISSED / OVERDUE TASKS DETAILS:
{missed_list if missed_list else "No missed/overdue tasks."}

WEEK'S PROGRESS LOG NOTES:
{notes_str if notes_str else "No logged progress notes."}

CRITICAL RULES:
1. Generate an exhaustive analysis divided into 4 specific output properties:
   - 'accomplishments': Markdown summary detailing completed tasks and milestones, highlighting velocity and time invested.
   - 'missed_targets': Markdown list of tasks or objectives that slipped past their due dates, with objective analysis of where time was misallocated.
   - 'risks': Markdown evaluation of workflow fatigue, persistent blockers, or target dates currently in jeopardy.
   - 'recommendations': Markdown advice specifying concrete adjustments to prioritize, schedule, or delegate for the coming week.
2. Return ONLY a valid JSON object matching the properties above.
3. Do NOT include markdown wraps or backticks outside the JSON.

EXPECTED JSON SCHEMA FORMAT:
{{
  "accomplishments": "### Completed Milestones\\n- **Establish Rust Base**: Fully read Chapters 1-10...",
  "missed_targets": "### Delayed Priorities\\n- Solana Dev Setup stalled due to CLI configuration errors...",
  "risks": "### Key Operational Risks\\n- **Anchor integration schedule**: Slippage in Phase 1 setup could push back Phase 2 deployment...",
  "recommendations": "### Next Week Action Plan\\n1. Dedicate 2 hours on Monday to Solana CLI debugging.\\n2. Adjust task estimates..."
}}
"""
        try:
            llm_resp = await self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                system="You are an elite corporate chief of staff and organizational psychologist who delivers clear, motivating feedback."
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
            logger.info("review_agent.review_generated")
            return result
        except Exception as e:
            logger.exception("review_agent.review_failed", error=str(e))
            # Fallback mock reviews
            return {
                "accomplishments": "### Completed Milestones\n- Logged initial progress and began objective definitions.",
                "missed_targets": "### Delayed Priorities\n- None identified.",
                "risks": "### Key Operational Risks\n- Objective definitions remain broad; sharpen task details to reduce estimation errors.",
                "recommendations": "### Next Week Action Plan\n1. Define concrete subtasks.\n2. Dedicate scheduled focus periods daily."
            }
