import re
import json
import structlog
from typing import List, Dict, Tuple, Optional
from mether.memory.persistent_memory import PersistentMemory
from mether.agent.llm import LLMClient
from mether.services.research.quality_scorer import (
    calculate_confidence,
    assign_verification_status
)

logger = structlog.get_logger(__name__)

SEMANTIC_CATEGORIES = {
    "funding": ["raised", "funding", "seed", "series", "round", "investment", "valuation"],
    "headcount": ["employees", "headcount", "staff", "team size"],
    "revenue": ["revenue", "arr", "sales", "earnings", "arr of", "revenue of"],
    "timeline": ["founded", "established", "started in", "incorporated"],
    "location": ["headquartered", "based in", "headquarters in"]
}

class ContradictionEngine:
    """Subsystem for detecting semantic or numeric contradictions across sources."""

    def __init__(self, db: PersistentMemory, llm: LLMClient) -> None:
        self.db = db
        self.llm = llm

    async def detect_contradictions(self, task_id: str, claims: List[Dict]) -> List[Dict]:
        """Detects contradictions between claims and applies penalties."""
        contradictions = []
        n_claims = len(claims)
        
        for i in range(n_claims):
            for j in range(i + 1, n_claims):
                claim_a = claims[i]
                claim_b = claims[j]
                
                # Ensure they are different claims
                if claim_a.get("id") == claim_b.get("id"):
                    continue
                    
                match, field_type, details = self._check_conflict(claim_a, claim_b)
                if match:
                    # Generate explanation using LLM
                    explanations = await self._generate_explanations(claim_a["claim_text"], claim_b["claim_text"])
                    
                    # Apply penalty in DB
                    await self._apply_contradiction_penalty(claim_a["id"], claim_b["id"])
                    
                    # Store contradiction in database
                    query = """
                        INSERT INTO research_contradictions (
                            task_id, claim_a_id, claim_b_id, source_a_url, source_b_url,
                            field_type, possible_explanations, human_review_recommended,
                            confidence, confidence_penalty_applied
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, 0.80, 0.20)
                    """
                    contra_id = await self.db._run_query(
                        query,
                        task_id, claim_a["id"], claim_b["id"],
                        claim_a.get("source_url", ""), claim_b.get("source_url", ""),
                        field_type, json.dumps(explanations),
                        is_write=True
                    )
                    
                    contradictions.append({
                        "id": contra_id,
                        "claim_a_id": claim_a["id"],
                        "claim_b_id": claim_b["id"],
                        "claim_a_text": claim_a["claim_text"],
                        "claim_b_text": claim_b["claim_text"],
                        "field_type": field_type,
                        "possible_explanations": explanations
                    })
                    
        logger.info("contradiction_engine.detection_complete", count=len(contradictions), task_id=task_id)
        return contradictions

    def _check_conflict(self, claim_a: Dict, claim_b: Dict) -> Tuple[bool, str, str]:
        """Runs deterministic checks for numeric or categorical conflicts."""
        text_a = claim_a["claim_text"].lower()
        text_b = claim_b["claim_text"].lower()
        
        # Check semantic fields
        for category, keywords in SEMANTIC_CATEGORIES.items():
            # Check if both claims share at least one keyword in this category
            has_kw_a = any(kw in text_a for kw in keywords)
            has_kw_b = any(kw in text_b for kw in keywords)
            
            if has_kw_a and has_kw_b:
                # 1. Numeric Check
                nums_a = self._extract_numbers(text_a)
                nums_b = self._extract_numbers(text_b)
                
                if nums_a and nums_b:
                    val_a = nums_a[0]
                    val_b = nums_b[0]
                    
                    if category == "timeline":
                        # Years must match exactly
                        if val_a != val_b:
                            return True, "timeline", f"Timeline discrepancy: {val_a} vs {val_b}"
                    else:
                        # Value discrepancy > 20%
                        max_val = max(val_a, val_b)
                        if max_val > 0:
                            diff = abs(val_a - val_b) / max_val
                            if diff > 0.20:
                                return True, category, f"Numeric discrepancy: {val_a} vs {val_b} (>20% difference)"
                                
                # 2. Location/Categorical Check
                if category == "location":
                    # Simple check for headquarters city mismatch
                    # Headquarters in New York vs Headquarters in London
                    cities_a = re.findall(r"(?:headquartered|based|headquarters)\s+in\s+([a-zA-Z\s]+)", text_a)
                    cities_b = re.findall(r"(?:headquartered|based|headquarters)\s+in\s+([a-zA-Z\s]+)", text_b)
                    if cities_a and cities_b:
                        city_a = cities_a[0].strip().split()[0]  # First word of city
                        city_b = cities_b[0].strip().split()[0]
                        if city_a != city_b:
                            return True, "location", f"Location discrepancy: {city_a} vs {city_b}"
                            
        return False, "", ""

    def _extract_numbers(self, text: str) -> List[float]:
        """Helper to extract numbers, converting scale suffixes (k, m, b, million, billion)."""
        # Clean text from common currency symbols
        text = text.replace("$", "").replace("€", "").replace("£", "")
        
        # Regex to find numbers
        pattern = r"\b(\d+(?:\.\d+)?)\s*(m|b|k|million|billion|thousand)?\b"
        matches = re.findall(pattern, text)
        
        nums = []
        for val_str, scale in matches:
            try:
                val = float(val_str)
                if scale in ("m", "million"):
                    val *= 1_000_000
                elif scale in ("b", "billion"):
                    val *= 1_000_000_000
                elif scale in ("k", "thousand"):
                    val *= 1_000
                nums.append(val)
            except ValueError:
                continue
        return nums

    async def _generate_explanations(self, claim_a: str, claim_b: str) -> List[str]:
        """Uses LLM to generate potential explanations for the contradiction."""
        prompt = f"""You are a forensic critical analyst.
Two search sources have returned contradicting claims for a research topic.
Claim A: "{claim_a}"
Claim B: "{claim_b}"

Provide 2-3 logical, evidence-based explanations for how this discrepancy might have occurred (e.g., date of reports, changes over time, confusion of definitions, or reporting errors).
Return a JSON array of strings. No markdown formatting, just pure JSON."""

        try:
            resp = await self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                system="You are a forensic contradiction resolver."
            )
            content = resp.get("content", [])
            text = content[0].get("text", "[]") if content else "[]"
            cleaned = text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
            data = json.loads(cleaned)
            if isinstance(data, list):
                return [str(item) for item in data]
        except Exception as e:
            logger.warning("contradiction_engine.explanation_generation_failed", error=str(e))
        return ["Discrepancy due to reporting time differences.", "Definition differences between sources."]

    async def _apply_contradiction_penalty(self, claim_a_id: int, claim_b_id: int) -> None:
        """Applies contradiction penalty to both claims and recalculates confidence."""
        # We can reuse ClaimVerifier's update_claim_contradiction method if imported, or implement it here
        from mether.services.research.claim_verifier import ClaimVerifierAgent
        verifier = ClaimVerifierAgent(self.db)
        await verifier.update_claim_contradiction(claim_a_id)
        await verifier.update_claim_contradiction(claim_b_id)
        logger.info("contradiction_engine.penalty_applied", claim_a=claim_a_id, claim_b=claim_b_id)

    async def get_contradictions_for_task(self, task_id: str) -> List[Dict]:
        """Retrieves contradictions for a specific task."""
        query = "SELECT * FROM research_contradictions WHERE task_id = ?"
        results = await self.db._run_query(query, task_id)
        
        out = []
        for r in results:
            item = dict(r)
            try:
                item["possible_explanations"] = json.loads(item["possible_explanations"])
            except Exception:
                item["possible_explanations"] = []
            out.append(item)
        return out
