import time
from dataclasses import dataclass
from typing import List, Dict, Optional
import structlog
from mether.memory.persistent_memory import PersistentMemory
from mether.services.research.quality_scorer import (
    ConfidenceBreakdown,
    calculate_confidence,
    assign_verification_status
)

logger = structlog.get_logger(__name__)

@dataclass
class Claim:
    task_id: str
    section_id: Optional[int]
    claim_text: str
    evidence: str
    source_url: str
    vault_id: Optional[int]
    verification_status: str
    confidence: ConfidenceBreakdown
    cross_validation_count: int
    recency_score: float
    source_quality_score: float
    retrieved_timestamp: float
    id: Optional[int] = None

class ClaimVerifierAgent:
    """Agent that handles claim verification logic, storage, and calculations."""

    def __init__(self, db: PersistentMemory) -> None:
        self.db = db

    async def verify_claim(
        self,
        task_id: str,
        claim_text: str,
        evidence: str,
        source_url: str,
        source_quality: float,
        recency: float,
        independence: float,
        cross_validation_count: int,
        has_contradiction: bool,
        mode_threshold: float,
        vault_id: Optional[int] = None,
        section_id: Optional[int] = None
    ) -> Claim:
        """Runs the verification calculation on a claim and constructs a Claim object."""
        confidence = calculate_confidence(
            source_quality=source_quality,
            cross_validation_count=cross_validation_count,
            recency=recency,
            independence=independence,
            has_contradiction=has_contradiction
        )
        
        status = assign_verification_status(
            breakdown=confidence,
            mode_threshold=mode_threshold,
            cross_validation_count=cross_validation_count,
            source_quality=source_quality
        )
        
        return Claim(
            task_id=task_id,
            section_id=section_id,
            claim_text=claim_text,
            evidence=evidence,
            source_url=source_url,
            vault_id=vault_id,
            verification_status=status,
            confidence=confidence,
            cross_validation_count=cross_validation_count,
            recency_score=recency,
            source_quality_score=source_quality,
            retrieved_timestamp=time.time()
        )

    async def store_claim(self, task_id: str, claim: Claim) -> int:
        """Inserts a claim object into the SQLite database."""
        query = """
            INSERT INTO research_claims (
                task_id, section_id, claim_text, evidence, source_url, vault_id,
                verification_status, confidence_score, confidence_source_quality,
                confidence_cross_validation, confidence_recency, confidence_independence,
                contradiction_penalty, cross_validation_count, recency_score,
                source_quality_score, retrieved_timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        claim_id = await self.db._run_query(
            query,
            task_id, claim.section_id, claim.claim_text, claim.evidence, claim.source_url, claim.vault_id,
            claim.verification_status, claim.confidence.total, claim.confidence.source_quality,
            claim.confidence.cross_validation, claim.confidence.recency, claim.confidence.independence,
            claim.confidence.contradiction_penalty, claim.cross_validation_count, claim.recency_score,
            claim.source_quality_score, claim.retrieved_timestamp,
            is_write=True
        )
        claim.id = claim_id
        logger.info("claim_verifier.claim_stored", claim_id=claim_id, status=claim.verification_status, task_id=task_id)
        return claim_id

    async def get_claims_for_task(self, task_id: str) -> List[Dict]:
        """Retrieves all claims for a specific task from the database."""
        query = "SELECT * FROM research_claims WHERE task_id = ?"
        results = await self.db._run_query(query, task_id)
        return [dict(r) for r in results]

    async def update_claim_contradiction(self, claim_id: int) -> None:
        """Applies a contradiction penalty to a claim and updates its database record."""
        # Retrieve the claim
        query_get = "SELECT * FROM research_claims WHERE id = ?"
        results = await self.db._run_query(query_get, claim_id)
        if not results:
            return
            
        r = results[0]
        # Re-verify with has_contradiction = True
        # Fetch research_mode threshold from the task to assign verification status correctly
        mode_threshold = 0.75  # Default balanced threshold
        task_query = "SELECT research_mode FROM research_tasks WHERE id = ?"
        task_res = await self.db._run_query(task_query, r["task_id"])
        if task_res:
            mode = task_res[0]["research_mode"]
            from mether.services.research.budget_controller import RESEARCH_MODES
            if mode in RESEARCH_MODES:
                mode_threshold = RESEARCH_MODES[mode]["confidence_threshold"]
                
        # Recompute
        confidence = calculate_confidence(
            source_quality=r["source_quality_score"],
            cross_validation_count=r["cross_validation_count"],
            recency=r["recency_score"],
            independence=r["confidence_independence"] / 0.15, # Recompute independence raw score
            has_contradiction=True
        )
        
        status = assign_verification_status(
            breakdown=confidence,
            mode_threshold=mode_threshold,
            cross_validation_count=r["cross_validation_count"],
            source_quality=r["source_quality_score"]
        )
        
        # Update db
        query_update = """
            UPDATE research_claims SET 
                contradiction_penalty = ?, 
                confidence_score = ?, 
                verification_status = ? 
            WHERE id = ?
        """
        await self.db._run_query(
            query_update,
            confidence.contradiction_penalty,
            confidence.total,
            status,
            claim_id,
            is_write=True
        )
        logger.info("claim_verifier.contradiction_penalty_applied", claim_id=claim_id, new_score=confidence.total, new_status=status)
