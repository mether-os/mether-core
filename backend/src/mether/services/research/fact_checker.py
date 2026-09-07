import json
import structlog
from typing import List, Dict, Callable
from mether.memory.persistent_memory import PersistentMemory
from mether.agent.llm import LLMClient
from mether.events.bus import EventBus
from mether.services.research.budget_controller import BudgetController
from mether.services.research.evidence_vault import EvidenceVault
from mether.services.research.quality_scorer import (
    calculate_confidence,
    assign_verification_status,
    score_source
)

logger = structlog.get_logger(__name__)

class FactCheckerAgent:
    """Agent that performs active cross-validation of challenged claims."""

    def __init__(
        self,
        db: PersistentMemory,
        llm: LLMClient,
        bus: EventBus,
        budget_controller: BudgetController,
        evidence_vault: EvidenceVault
    ) -> None:
        self.db = db
        self.llm = llm
        self.bus = bus
        self.budget = budget_controller
        self.evidence_vault = evidence_vault

    async def fact_check_claims(
        self,
        task_id: str,
        challenged_claims: List[Dict],
        search_fn: Callable
    ) -> Dict:
        """Processes high-severity challenges by performing targeted searches."""
        results_summary = {"checked": 0, "corroborated": 0, "unverified": 0}
        
        for challenge in challenged_claims:
            if challenge.get("severity") != "high":
                continue
                
            claim_id = challenge.get("claim_id")
            query = challenge.get("suggested_verification_query")
            
            # Fetch claim text
            claim_res = await self.db._run_query("SELECT * FROM research_claims WHERE id = ?", claim_id)
            if not claim_res:
                continue
                
            claim = claim_res[0]
            claim_text = claim["claim_text"]
            
            if not self.budget.can_search():
                logger.info("fact_checker.budget_exhausted_during_check", claim_id=claim_id)
                break
                
            results_summary["checked"] += 1
            logger.info("fact_checker.searching_to_verify", claim_id=claim_id, query=query)
            
            # Perform search
            search_results = await search_fn(query)
            await self.budget.record_search()
            
            if not search_results:
                results_summary["unverified"] += 1
                logger.info("fact_checker.search_no_results", claim_id=claim_id)
                continue
                
            # Evaluate using LLM if the new results corroborate the claim
            corroborated = await self._evaluate_corroboration(claim_text, search_results)
            
            if corroborated:
                results_summary["corroborated"] += 1
                # Store the new evidence in the vault
                for res in search_results[:2]:
                    url = res.get("url", "unknown://corroboration")
                    title = res.get("title", "")
                    snippet = res.get("snippet", "")
                    quality = score_source(url)
                    
                    await self.evidence_vault.store_snapshot(
                        task_id=task_id,
                        url=url,
                        title=title,
                        snapshot_text=snippet,
                        quality_score=quality,
                        extracted_claim_ids=[claim_id]
                    )
                
                # Update claim
                await self._verify_claim_with_new_evidence(claim_id, search_results, task_id)
            else:
                results_summary["unverified"] += 1
                
        return results_summary

    async def _evaluate_corroboration(self, claim_text: str, search_results: List[Dict]) -> bool:
        """Asks LLM to determine if the search results corroborate the claim."""
        results_text = "\n\n".join([
            f"Title: {r.get('title')}\nURL: {r.get('url')}\nSnippet: {r.get('snippet')}"
            for r in search_results[:3]
        ])
        
        prompt = f"""You are a forensic fact checking assistant.
Determine if the provided web search results corroborate, support, or verify the factual claim.
Only say yes if the results explicitly mention or verify the claim without contradiction.

Claim: "{claim_text}"

Web Search Results:
{results_text}

Respond in JSON format:
{{
  "corroborated": true or false,
  "explanation": "Brief explanation why"
}}
No markdown formatting, just pure JSON."""

        try:
            resp = await self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                system="You are a forensic facts verifier."
            )
            content = resp.get("content", [])
            text = content[0].get("text", "{}") if content else "{}"
            cleaned = text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
            data = json.loads(cleaned)
            return bool(data.get("corroborated", False))
        except Exception as e:
            logger.warning("fact_checker.corroboration_check_failed", error=str(e))
            return False

    async def _verify_claim_with_new_evidence(self, claim_id: int, new_results: List[Dict], task_id: str) -> None:
        """Increases verification count and recalculates claim status/confidence."""
        claim_res = await self.db._run_query("SELECT * FROM research_claims WHERE id = ?", claim_id)
        if not claim_res:
            return
            
        r = claim_res[0]
        # Increase cross-validation count
        new_cv_count = r["cross_validation_count"] + len(new_results[:2])
        
        # Determine research mode threshold
        mode_threshold = 0.75
        task_query = "SELECT research_mode FROM research_tasks WHERE id = ?"
        task_res = await self.db._run_query(task_query, task_id)
        if task_res:
            mode = task_res[0]["research_mode"]
            from mether.services.research.budget_controller import RESEARCH_MODES
            if mode in RESEARCH_MODES:
                mode_threshold = RESEARCH_MODES[mode]["confidence_threshold"]
                
        # Recalculate confidence
        confidence = calculate_confidence(
            source_quality=r["source_quality_score"],
            cross_validation_count=new_cv_count,
            recency=r["recency_score"],
            independence=r["confidence_independence"] / 0.15,
            has_contradiction=False
        )
        
        status = assign_verification_status(
            breakdown=confidence,
            mode_threshold=mode_threshold,
            cross_validation_count=new_cv_count,
            source_quality=r["source_quality_score"]
        )
        
        # Update db
        query = """
            UPDATE research_claims SET
                cross_validation_count = ?,
                confidence_score = ?,
                confidence_cross_validation = ?,
                verification_status = ?
            WHERE id = ?
        """
        await self.db._run_query(
            query,
            new_cv_count,
            confidence.total,
            confidence.cross_validation,
            status,
            claim_id,
            is_write=True
        )
        logger.info(
            "fact_checker.claim_updated",
            claim_id=claim_id,
            new_cv_count=new_cv_count,
            new_confidence=confidence.total,
            new_status=status
        )

    def can_generate_recommendation(self, claim: Dict) -> bool:
        """Returns True only if the claim is Verified or Partially Verified."""
        return claim.get("verification_status") in ("Verified", "Partially Verified")
