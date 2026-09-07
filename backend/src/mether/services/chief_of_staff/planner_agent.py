import json
import structlog
from typing import Any, Dict, List
from mether.agent.llm import LLMClient
from mether.events.bus import EventBus

logger = structlog.get_logger(__name__)

class PlannerAgent:
    """Planner Agent: Decomposes a high-level user goal into structured milestones, tasks, and subtasks."""

    def __init__(self, llm: LLMClient, bus: EventBus) -> None:
        self.llm = llm
        self.bus = bus

    async def generate_plan(self, goal_title: str, goal_description: str, category: str, days_target: int = 60) -> List[Dict[str, Any]]:
        """Decompose a high-level goal into a JSON-parsable list of milestones, tasks, and subtasks.

        Returns a list of dicts following the schema:
        [
          {
            "title": "Milestone Title",
            "description": "Milestone Description",
            "days_offset": 15,  # target day offset from start
            "tasks": [
              {
                "title": "Task Title",
                "description": "Task Description",
                "priority": "high",  # "high", "medium", "low"
                "time_estimate_mins": 120,
                "subtasks": ["Subtask 1", "Subtask 2"]
              }
            ]
          }
        ]
        """
        prompt = f"""You are a Strategic Planning Agent for METHER OS.
Your task is to take a high-level objective/goal and decompose it into a meticulous, realistic step-by-step milestone and task plan.

Goal Title: {goal_title}
Goal Description: {goal_description}
Category: {category}
Target Period: {days_target} days

CRITICAL RULES:
1. Decompose this goal into 3 to 6 major milestones, logically sequenced over the {days_target}-day timeline.
2. For each milestone, provide 3 to 8 actionable, concrete tasks.
3. For each task, provide 2 to 5 specific subtasks, priority level ('high', 'medium', or 'low'), and time estimate in minutes (integer).
4. Do NOT include any introductory or concluding text. Output ONLY a valid JSON block matching the structure below.
5. Do NOT include markdown blocks or code block wraps in your response, output pure raw JSON string.

EXPECTED JSON SCHEMA FORMAT:
[
  {{
    "title": "Establish Solana & Rust Fundamentals",
    "description": "Build base knowledge in Rust, Solana CLI, and anchor framework.",
    "days_offset": 15,
    "tasks": [
      {{
        "title": "Read Rust Book Chapters 1-10",
        "description": "Understand ownership, borrowing, structs, and enums.",
        "priority": "high",
        "time_estimate_mins": 240,
        "subtasks": [
          "Install Rustup and set up VS Code",
          "Complete chapters 1-4 exercises",
          "Review memory safety and borrowing rules"
        ]
      }}
    ]
  }}
]
"""
        try:
            llm_resp = await self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                system="You are an elite chief of staff and program planner who produces perfect, structured program breakdowns."
            )
            content_blocks = llm_resp.get("content", [])
            reply_text = content_blocks[0].get("text", "") if content_blocks else ""

            # Clean code wraps if any
            cleaned_text = reply_text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.startswith("```"):
                cleaned_text = cleaned_text[3:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
            cleaned_text = cleaned_text.strip()

            plan = json.loads(cleaned_text)
            logger.info("planner_agent.plan_generated", milestones_count=len(plan))
            return plan
        except Exception as e:
            logger.exception("planner_agent.plan_generation_failed", error=str(e))
            # Fallback mock plan
            return [
                {
                    "title": "Phase 1: Discovery & Strategy",
                    "description": "Research requirements, define architecture, and setup initial project structure.",
                    "days_offset": 15,
                    "tasks": [
                        {
                            "title": "Define Project Scope & Core Architecture",
                            "description": "Specify the parameters and constraints of the objective.",
                            "priority": "high",
                            "time_estimate_mins": 120,
                            "subtasks": ["Define requirements", "Draft architecture diagram", "Obtain project template"]
                        }
                    ]
                },
                {
                    "title": "Phase 2: Core Development & Implementation",
                    "description": "Construct key building blocks and foundational system components.",
                    "days_offset": 45,
                    "tasks": [
                        {
                            "title": "Initialize Repository & Environments",
                            "description": "Bootstrap the backend, database, and dev servers.",
                            "priority": "medium",
                            "time_estimate_mins": 90,
                            "subtasks": ["Setup environment files", "Create boilerplate classes", "Run basic health checks"]
                        }
                    ]
                }
            ]
