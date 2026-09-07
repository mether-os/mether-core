from typing import List, Dict
import structlog
from mether.memory.persistent_memory import PersistentMemory

logger = structlog.get_logger(__name__)

class SkepticAgent:
    """Agent that challenges factual claims based on source quality and validation counts."""

    def __init__(self, db: PersistentMemory) -> None:
        self.db = db

    async def challenge_claims(self, task_id: str, claims: List[Dict]) -> List[Dict]:
        """Scans claims for vulnerability and generates structured challenge records."""
        challenges = []
        
        for c in claims:
            claim_id = c.get("id")
            cv_count = c.get("cross_validation_count", 0)
            source_quality = c.get("source_quality_score", 5.0)
            confidence_score = c.get("confidence_score", 0.0)
            recency = c.get("recency_score", 0.3)
            claim_text = c.get("claim_text", "")
            
            # Determine severity
            severity = None
            reason = ""
            query_suggestion = f"{claim_text} source proof cross-validate"
            
            if cv_count == 0 or source_quality < 4.0:
                severity = "high"
                reason = "Claim lacks any independent cross-validation or comes from a low-quality source."
            elif cv_count == 1 or confidence_score < 0.50:
                severity = "medium"
                reason = "Claim has only a single cross-validation or low overall confidence."
            elif recency < 0.40:
                severity = "low"
                reason = "Claim source information is outdated."
                
            if severity:
                # If medium severity, apply a -0.10 confidence penalty
                if severity == "medium":
                    new_score = max(0.0, confidence_score - 0.10)
                    # Update database record
                    await self.db._run_query(
                        "UPDATE research_claims SET confidence_score = ? WHERE id = ?",
                        new_score, claim_id, is_write=True
                    )
                    logger.info("skeptic.applied_medium_penalty", claim_id=claim_id, old_score=confidence_score, new_score=new_score)
                
                challenges.append({
                    "claim_id": claim_id,
                    "challenge_reason": reason,
                    "severity": severity,
                    "suggested_verification_query": query_suggestion
                })
                
        logger.info("skeptic.challenges_generated", count=len(challenges), task_id=task_id)
        return challenges
