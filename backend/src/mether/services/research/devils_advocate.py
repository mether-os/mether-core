import json
import structlog
from typing import List, Dict, Optional
from mether.memory.persistent_memory import PersistentMemory
from mether.agent.llm import LLMClient
from mether.events.bus import EventBus

logger = structlog.get_logger(__name__)

class DevilsAdvocateAgent:
    """Agent that critiques preliminary reports to highlight risks and counter-arguments."""

    def __init__(self, db: PersistentMemory, llm: LLMClient, bus: EventBus) -> None:
        self.db = db
        self.llm = llm
        self.bus = bus

    async def challenge_report(
        self,
        task_id: str,
        report_sections: List[Dict],
        decision_preliminary: Dict
    ) -> Dict:
        """Constructs prompt, requests critique from LLM, and archives the resulting challenge."""
        sections_text = "\n\n".join([
            f"### Section: {sec.get('title')}\nContent:\n{sec.get('content') or sec.get('validated_content')}"
            for sec in report_sections
        ])
        
        prelim_summary = json.dumps(decision_preliminary, indent=2)
        
        prompt = f"""You are a devil's advocate and critical analyst. Your job is to challenge every conclusion.
Review the report sections and the preliminary decision summary, and critique them thoroughly.

Report Content:
{sections_text}

Preliminary Decision Summary:
{prelim_summary}

Tasks:
1. Generate counter-arguments (reasons the findings might be incorrect or misleading).
2. Generate alternative interpretations (other ways to explain the same evidence).
3. Identify confidence risks (reasons the confidence score might be over-inflated or unreliable).
4. Explain "why we might be wrong" (scenarios under which the entire conclusion fails).

Return your critique in JSON format. Do not use markdown wraps:
{{
  "counter_arguments": ["argument 1", "argument 2"],
  "alternative_interpretations": ["interpretation 1", "interpretation 2"],
  "confidence_risks": ["risk 1", "risk 2"],
  "why_wrong": ["scenario 1", "scenario 2"]
}}"""

        system_instruction = (
            "You are a devil's advocate and critical analyst. Your job is to challenge every conclusion. "
            "Find weaknesses. Identify alternative explanations. Surface hidden assumptions. "
            "Your output must be honest, specific, and evidence-referenced."
        )

        try:
            resp = await self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                system=system_instruction
            )
            content = resp.get("content", [])
            text = content[0].get("text", "{}") if content else "{}"
            cleaned = text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
            data = json.loads(cleaned)
        except Exception as e:
            logger.warning("devils_advocate.critique_generation_failed", error=str(e))
            data = {
                "counter_arguments": ["Insufficient verification of primary sources."],
                "alternative_interpretations": ["The findings may represent correlation rather than causation."],
                "confidence_risks": ["Limited search breadth may skew results."],
                "why_wrong": ["If the source publications are outdated or biased."]
            }
            
        # Serialize fields
        counter_args = json.dumps(data.get("counter_arguments", []))
        alt_int = json.dumps(data.get("alternative_interpretations", []))
        conf_risks = json.dumps(data.get("confidence_risks", []))
        why_wrong = json.dumps(data.get("why_wrong", []))
        
        # Save to DB
        query = """
            INSERT OR REPLACE INTO devils_advocate (
                task_id, counter_arguments_json, alternative_interpretations_json,
                confidence_risks_json, why_wrong_json
            ) VALUES (?, ?, ?, ?, ?)
        """
        await self.db._run_query(query, task_id, counter_args, alt_int, conf_risks, why_wrong, is_write=True)
        logger.info("devils_advocate.critique_stored", task_id=task_id)
        
        # Return dict representation
        return {
            "counter_arguments": data.get("counter_arguments", []),
            "alternative_interpretations": data.get("alternative_interpretations", []),
            "confidence_risks": data.get("confidence_risks", []),
            "why_wrong": data.get("why_wrong", [])
        }

    async def get_for_task(self, task_id: str) -> Optional[Dict]:
        """Retrieves critique for a specific task."""
        query = "SELECT * FROM devils_advocate WHERE task_id = ?"
        results = await self.db._run_query(query, task_id)
        if not results:
            return None
            
        r = results[0]
        try:
            return {
                "counter_arguments": json.loads(r["counter_arguments_json"]),
                "alternative_interpretations": json.loads(r["alternative_interpretations_json"]),
                "confidence_risks": json.loads(r["confidence_risks_json"]),
                "why_wrong": json.loads(r["why_wrong_json"])
            }
        except Exception:
            return {
                "counter_arguments": [],
                "alternative_interpretations": [],
                "confidence_risks": [],
                "why_wrong": []
            }
