import time
import hashlib
from typing import List, Dict, Optional
import structlog
from mether.memory.persistent_memory import PersistentMemory

logger = structlog.get_logger(__name__)

class OutcomeTrackerAgent:
    """Agent that stores research recommendations and tracks their resolution accuracy over time."""

    def __init__(self, db: PersistentMemory) -> None:
        self.db = db

    async def store_predictions(
        self,
        task_id: str,
        topic: str,
        action_plan: Dict,
        decision_brief: Dict
    ) -> None:
        """Stores each recommended action as a trackable prediction in the database."""
        actions = action_plan.get("actions", [])
        confidence = decision_brief.get("confidence_level", 0.75)
        
        # Calculate topic hash
        topic_hash = hashlib.md5(topic.lower().strip().encode("utf-8")).hexdigest()[:12]
        
        for act in actions:
            text = act.get("action", "")
            predicted = f"Impact: {act.get('estimated_impact', 'Unknown')}. Rationale: {act.get('rationale', '')}"
            
            query = """
                INSERT INTO recommendation_outcomes (
                    task_id, recommendation_text, confidence_at_time,
                    predicted_outcome, topic_hash
                ) VALUES (?, ?, ?, ?, ?)
            """
            await self.db._run_query(query, task_id, text, confidence, predicted, topic_hash, is_write=True)
            
        logger.info("outcome_tracker.predictions_stored", count=len(actions), task_id=task_id)

    async def record_outcome(
        self,
        recommendation_id: int,
        actual_outcome: str,
        user_feedback: Optional[str],
        correct: bool
    ) -> None:
        """Updates a recommendation prediction with actual outcomes and accuracy verification."""
        query = """
            UPDATE recommendation_outcomes SET
                actual_outcome = ?,
                user_feedback = ?,
                outcome_timestamp = ?,
                correct = ?
            WHERE id = ?
        """
        await self.db._run_query(
            query,
            actual_outcome,
            user_feedback,
            time.time(),
            1 if correct else 0,
            recommendation_id,
            is_write=True
        )
        logger.info("outcome_tracker.outcome_recorded", recommendation_id=recommendation_id, correct=correct)

    async def get_historical_accuracy(self, topic_hash: str) -> Dict:
        """Calculates total resolved outcomes, correct outcomes, and accuracy percentage for a topic."""
        query = "SELECT * FROM recommendation_outcomes WHERE topic_hash = ? AND correct IS NOT NULL"
        results = await self.db._run_query(query, topic_hash)
        
        total = len(results)
        correct = sum(1 for r in results if r["correct"] == 1)
        accuracy = (correct / total) if total > 0 else 0.0
        
        return {
            "topic_hash": topic_hash,
            "total_resolved": total,
            "correct_resolved": correct,
            "accuracy_percent": round(accuracy * 100, 1),
            "historical_outcomes": [dict(r) for r in results]
        }

    async def get_outcomes_for_task(self, task_id: str) -> List[Dict]:
        """Retrieves all tracked recommendations for a task."""
        query = "SELECT * FROM recommendation_outcomes WHERE task_id = ?"
        results = await self.db._run_query(query, task_id)
        return [dict(r) for r in results]
