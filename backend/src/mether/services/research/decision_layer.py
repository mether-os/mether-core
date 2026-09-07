import json
import structlog
from typing import List, Dict, Optional
from mether.memory.persistent_memory import PersistentMemory
from mether.agent.llm import LLMClient

logger = structlog.get_logger(__name__)

AUDIENCE_FRAMING = {
    "investor": "Focus on ROI, financial risk, runway, defensibility, exit potential, and market size.",
    "founder": "Focus on partnership value, competitive threats, opportunity sizing, and strategic pivot points.",
    "researcher": "Focus on methodology validity, evidence gaps, scientific contribution, and detail precision.",
    "recruiter": "Focus on candidate talent signals, culture indicators, potential red flags, and career progression.",
    "manager": "Focus on operational risk, resource constraints, timeline requirements, and project execution."
}

class DecisionLayerAgent:
    """Agent that synthesizes reports into tailored decision briefs for target audiences."""

    def __init__(self, db: PersistentMemory, llm: LLMClient) -> None:
        self.db = db
        self.llm = llm

    async def generate_decision(
        self,
        task_id: str,
        topic: str,
        sections_content: List[Dict],
        claims_summary: List[Dict],
        contradictions: List[Dict],
        unknowns: List[Dict],
        da_report: Dict,
        target_audience: str,
        avg_confidence: float,
        research_failed: bool,
        failure_reason: Optional[str]
    ) -> Dict:
        """Constructs prompt, requests synthesis from LLM, and logs the decision layer record."""
        # Map audience
        audience = target_audience.lower() if target_audience.lower() in AUDIENCE_FRAMING else "researcher"
        framing_instruction = AUDIENCE_FRAMING[audience]
        
        # Build contents
        contents_str = "\n\n".join([
            f"Section: {s.get('title')}\nContent:\n{s.get('content') or s.get('validated_content')}"
            for s in sections_content
        ])
        
        claims_str = "\n".join([
            f"- {c['claim_text']} (Status: {c['verification_status']}, Conf: {c['confidence_score']})"
            for c in claims_summary[:20] # top 20 claims
        ])
        
        contras_str = "\n".join([
            f"- Discrepancy between {c['claim_a_id']} and {c['claim_b_id']} on {c['field_type']}"
            for c in contradictions
        ])
        
        unknowns_str = "\n".join([
            f"- Field: {u.get('field') or u.get('claim_text')} (Reason: {u.get('reason') or u.get('evidence')})"
            for u in unknowns
        ])
        
        # Summarize devil's advocate
        da_summary = "Devil's Advocate Counter-Arguments:\n" + "\n".join([
            f"- {arg}" for arg in da_report.get("counter_arguments", [])[:5]
        ])
        
        prompt = f"""You are a Decision Intelligence Engine. Your task is to produce a trustworthy decision brief.
Topic: "{topic}"
Target Audience: {audience}
Framing Instruction: {framing_instruction}

Research Sections Content:
{contents_str}

Claims Summary:
{claims_str}

Contradictions:
{contras_str}

Unknown/Unverified Fields:
{unknowns_str}

{da_summary}

Please synthesize this into a structured decision brief.
Extract:
1. key_findings: List of 3-5 core takeaways.
2. green_flags: List of positive signals or opportunities.
3. red_flags: List of negative signals or risks.
4. open_questions: Remaining queries or gaps.
5. risks: Specific risks associated with acting.
6. opportunities: Strategic opportunities.
7. decision_summary: A 1-2 paragraph executive summary.

Return JSON format:
{{
  "key_findings": ["finding 1", "finding 2"],
  "green_flags": ["flag 1"],
  "red_flags": ["flag 1"],
  "open_questions": ["question 1"],
  "risks": ["risk 1"],
  "opportunities": ["opportunity 1"],
  "decision_summary": "..."
}}
No markdown formatting, just pure JSON."""

        try:
            resp = await self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                system="You are a decision synthesis engine."
            )
            content = resp.get("content", [])
            text = content[0].get("text", "{}") if content else "{}"
            cleaned = text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
            data = json.loads(cleaned)
        except Exception as e:
            logger.warning("decision_layer.generation_failed", error=str(e))
            data = {
                "key_findings": ["No findings generated due to model error."],
                "green_flags": [],
                "red_flags": [],
                "open_questions": [],
                "risks": [],
                "opportunities": [],
                "decision_summary": "Model failed to generate decision summary."
            }
            
        # Store in DB
        query = """
            INSERT OR REPLACE INTO decision_layer (
                task_id, key_findings, green_flags, red_flags, open_questions,
                risks, opportunities, decision_summary, confidence_level,
                target_audience, devils_advocate_summary, research_failure, failure_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        await self.db._run_query(
            query,
            task_id,
            json.dumps(data.get("key_findings", [])),
            json.dumps(data.get("green_flags", [])),
            json.dumps(data.get("red_flags", [])),
            json.dumps(data.get("open_questions", [])),
            json.dumps(data.get("risks", [])),
            json.dumps(data.get("opportunities", [])),
            data.get("decision_summary", ""),
            avg_confidence,
            audience,
            da_summary,
            1 if research_failed else 0,
            failure_reason,
            is_write=True
        )
        logger.info("decision_layer.brief_stored", task_id=task_id, audience=audience)
        
        # Prepare dict representation
        return {
            "key_findings": data.get("key_findings", []),
            "green_flags": data.get("green_flags", []),
            "red_flags": data.get("red_flags", []),
            "open_questions": data.get("open_questions", []),
            "risks": data.get("risks", []),
            "opportunities": data.get("opportunities", []),
            "decision_summary": data.get("decision_summary", ""),
            "confidence_level": avg_confidence,
            "target_audience": audience,
            "devils_advocate_summary": da_summary,
            "research_failure": research_failed,
            "failure_reason": failure_reason
        }

    async def get_for_task(self, task_id: str) -> Optional[Dict]:
        """Retrieves the decision brief for a task."""
        query = "SELECT * FROM decision_layer WHERE task_id = ?"
        results = await self.db._run_query(query, task_id)
        if not results:
            return None
            
        r = results[0]
        try:
            return {
                "key_findings": json.loads(r["key_findings"]),
                "green_flags": json.loads(r["green_flags"]),
                "red_flags": json.loads(r["red_flags"]),
                "open_questions": json.loads(r["open_questions"]),
                "risks": json.loads(r["risks"]),
                "opportunities": json.loads(r["opportunities"]),
                "decision_summary": r["decision_summary"],
                "confidence_level": r["confidence_level"],
                "target_audience": r["target_audience"],
                "devils_advocate_summary": r["devils_advocate_summary"],
                "research_failure": bool(r["research_failure"]),
                "failure_reason": r["failure_reason"]
            }
        except Exception:
            return None
