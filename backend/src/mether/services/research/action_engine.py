import json
import structlog
from typing import List, Dict, Optional
from mether.memory.persistent_memory import PersistentMemory
from mether.agent.llm import LLMClient

logger = structlog.get_logger(__name__)

class ActionEngineAgent:
    """Agent that translates research conclusions into prioritized action plans."""

    def __init__(self, db: PersistentMemory, llm: LLMClient) -> None:
        self.db = db
        self.llm = llm

    async def generate_action_plan(
        self,
        task_id: str,
        topic: str,
        decision_brief: Dict,
        verified_claims: List[Dict],
        unverified_claims: List[Dict],
        target_audience: str
    ) -> Dict:
        """Generates priority-ranked actions, flags speculative recommendations, and archives the plan."""
        # Convert claims lists to string context
        v_claims_str = "\n".join([f"- {c['claim_text']}" for c in verified_claims])
        u_claims_str = "\n".join([f"- {c['claim_text']}" for c in unverified_claims])
        
        brief_summary = decision_brief.get("decision_summary", "")
        
        prompt = f"""You are an Action Planning Engine. Your task is to generate an executable action plan.
Topic: "{topic}"
Target Audience: {target_audience}

Decision Brief Summary:
{brief_summary}

Verified and Partially Verified Evidence (Trustworthy):
{v_claims_str}

Unverified and Hypothesis Evidence (Unknown/Speculative):
{u_claims_str}

Please generate:
1. actions: A list of specific recommendations. Each action must contain:
   - action: The action description.
   - priority: Integer from 1 (lowest) to 10 (highest).
   - category: Operational category.
   - estimated_impact: High, Medium, or Low.
   - estimated_effort: High, Medium, or Low.
   - rationale: Rationale referencing the evidence.
   - owner_type: Target persona to execute.
   - timeline: Recommended timeline.
   - speculative: Boolean. Set to true if this action relies on or references Unverified/Hypothesis claims.

2. next_steps: List of 3-5 immediate next steps.
3. quick_wins: List of actions with High impact and Low effort.
4. long_term_actions: List of actions with High impact and High/Medium effort.

Return JSON format:
{{
  "actions": [
     {{
       "action": "...",
       "priority": 8,
       "category": "...",
       "estimated_impact": "High",
       "estimated_effort": "Low",
       "rationale": "...",
       "owner_type": "...",
       "timeline": "Immediate",
       "speculative": false
     }}
  ],
  "next_steps": ["step 1", "step 2"],
  "quick_wins": ["win 1"],
  "long_term_actions": ["action 1"]
}}
No markdown formatting, just pure JSON."""

        try:
            resp = await self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                system="You are an action plan compiler."
            )
            content = resp.get("content", [])
            text = content[0].get("text", "{}") if content else "{}"
            cleaned = text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
            data = json.loads(cleaned)
        except Exception as e:
            logger.warning("action_engine.plan_generation_failed", error=str(e))
            data = {"actions": [], "next_steps": [], "quick_wins": [], "long_term_actions": []}
            
        actions_list = data.get("actions", [])
        
        # Sort actions by priority descending
        actions_list.sort(key=lambda x: x.get("priority", 0), reverse=True)
        
        # Store in DB
        query = """
            INSERT OR REPLACE INTO research_action_plans (
                task_id, actions_json, next_steps_json, quick_wins_json, long_term_actions_json
            ) VALUES (?, ?, ?, ?, ?)
        """
        await self.db._run_query(
            query,
            task_id,
            json.dumps(actions_list),
            json.dumps(data.get("next_steps", [])),
            json.dumps(data.get("quick_wins", [])),
            json.dumps(data.get("long_term_actions", [])),
            is_write=True
        )
        logger.info("action_engine.plan_stored", task_id=task_id, action_count=len(actions_list))
        
        return {
            "actions": actions_list,
            "next_steps": data.get("next_steps", []),
            "quick_wins": data.get("quick_wins", []),
            "long_term_actions": data.get("long_term_actions", [])
        }

    async def get_for_task(self, task_id: str) -> Optional[Dict]:
        """Retrieves action plan for a task."""
        query = "SELECT * FROM research_action_plans WHERE task_id = ?"
        results = await self.db._run_query(query, task_id)
        if not results:
            return None
            
        r = results[0]
        try:
            return {
                "actions": json.loads(r["actions_json"]),
                "next_steps": json.loads(r["next_steps_json"]),
                "quick_wins": json.loads(r["quick_wins_json"]),
                "long_term_actions": json.loads(r["long_term_actions_json"])
            }
        except Exception:
            return None
