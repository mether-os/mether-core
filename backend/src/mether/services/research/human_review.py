import time
import json
from typing import List, Dict
import structlog
from mether.memory.persistent_memory import PersistentMemory

logger = structlog.get_logger(__name__)

class HumanReviewGate:
    """Gatekeeper for optional human evidence review and verification correction."""

    def __init__(self, db: PersistentMemory) -> None:
        self.db = db

    async def queue_for_review(
        self,
        task_id: str,
        claim_id: int,
        source_url: str,
        snapshot_excerpt: str,
        review_reason: str
    ) -> int:
        """Adds a claim to the human review queue."""
        query = """
            INSERT INTO human_review_queue (
                task_id, claim_id, source_url, snapshot_excerpt, review_reason, status
            ) VALUES (?, ?, ?, ?, ?, 'pending')
        """
        queue_id = await self.db._run_query(
            query,
            task_id, claim_id, source_url, snapshot_excerpt, review_reason,
            is_write=True
        )
        logger.info("human_review.queued", queue_id=queue_id, claim_id=claim_id, task_id=task_id)
        return queue_id

    async def get_pending_reviews(self, task_id: str) -> List[Dict]:
        """Retrieves all pending human reviews for a task."""
        query = "SELECT * FROM human_review_queue WHERE task_id = ? AND status = 'pending'"
        results = await self.db._run_query(query, task_id)
        return [dict(r) for r in results]

    async def submit_review(self, review_id: int, decision: str, notes: str = "") -> None:
        """Submits reviewer decision, updating queue item status and target claim verification."""
        # 1. Fetch queue item
        item_res = await self.db._run_query("SELECT * FROM human_review_queue WHERE id = ?", review_id)
        if not item_res:
            logger.warning("human_review.review_item_not_found", review_id=review_id)
            return
            
        item = item_res[0]
        claim_id = item["claim_id"]
        task_id = item["task_id"]
        
        # 2. Determine verification status mapping
        new_status = "Unverified"
        if decision == "approved":
            new_status = "Verified"
        elif decision == "rejected":
            new_status = "Unverified"
        elif decision == "flagged":
            new_status = "Hypothesis"
            
        # 3. Update the claim verification status and potentially its confidence score
        claim_res = await self.db._run_query("SELECT claim_text FROM research_claims WHERE id = ?", claim_id)
        if claim_res:
            claim_text = claim_res[0]["claim_text"]
            
            # Update claim in DB
            confidence_val = 1.0 if decision == "approved" else (0.4 if decision == "flagged" else 0.0)
            update_claim = """
                UPDATE research_claims SET 
                    verification_status = ?,
                    confidence_score = ?
                WHERE id = ?
            """
            await self.db._run_query(update_claim, new_status, confidence_val, claim_id, is_write=True)
            
            # If flagged, add to open_questions in decision_layer
            if decision == "flagged":
                decision_res = await self.db._run_query("SELECT * FROM decision_layer WHERE task_id = ?", task_id)
                if decision_res:
                    dl = decision_res[0]
                    oq_str = dl["open_questions"]
                    # If it looks like JSON list
                    try:
                        oq_list = json.loads(oq_str)
                        if isinstance(oq_list, list):
                            oq_list.append(f"Human Flagged: {claim_text} ({notes})")
                            new_oq = json.dumps(oq_list)
                        else:
                            new_oq = oq_str + f"\n- Flagged Claim: {claim_text} ({notes})"
                    except Exception:
                        new_oq = oq_str + f"\n- Flagged Claim: {claim_text} ({notes})"
                        
                    await self.db._run_query(
                        "UPDATE decision_layer SET open_questions = ? WHERE task_id = ?",
                        new_oq, task_id, is_write=True
                    )
        
        # 4. Update the queue item
        update_queue = """
            UPDATE human_review_queue SET
                status = ?,
                reviewer_notes = ?,
                reviewed_at = ?
            WHERE id = ?
        """
        await self.db._run_query(update_queue, decision, notes, time.time(), review_id, is_write=True)
        logger.info("human_review.submitted", review_id=review_id, decision=decision, claim_id=claim_id)

    async def is_review_complete(self, task_id: str) -> bool:
        """Checks if there are no pending reviews left in the queue for a task."""
        pending = await self.get_pending_reviews(task_id)
        return len(pending) == 0
