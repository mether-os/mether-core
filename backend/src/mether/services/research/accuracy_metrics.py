import time
from typing import List, Dict, Optional
import structlog
from mether.memory.persistent_memory import PersistentMemory

logger = structlog.get_logger(__name__)

class AccuracyMetricsEngine:
    """Subsystem for tracking global system accuracy metrics and calibration scores."""

    def __init__(self, db: PersistentMemory) -> None:
        self.db = db

    async def compute_metrics(self) -> Dict:
        """Runs calculations across database tables to assess system reliability."""
        now_str = time.strftime("%Y-%m-%d", time.gmtime())
        
        # 1. Prediction Accuracy (resolved outcomes)
        outcomes = await self.db._run_query(
            "SELECT correct, confidence_at_time FROM recommendation_outcomes WHERE correct IS NOT NULL"
        )
        total_pred = len(outcomes)
        correct_pred = sum(1 for o in outcomes if o["correct"] == 1)
        pred_acc = (correct_pred / total_pred) if total_pred > 0 else 1.0
        
        # 2. Verification success rate (Verified / All)
        claims = await self.db._run_query("SELECT verification_status FROM research_claims")
        total_claims = len(claims)
        verified_claims = sum(1 for c in claims if c["verification_status"] in ("Verified", "Partially Verified"))
        success_rate = (verified_claims / total_claims) if total_claims > 0 else 1.0
        
        # 3. Contradiction rate (Tasks with contradictions / Total tasks)
        tasks = await self.db._run_query("SELECT id FROM research_tasks")
        total_tasks = len(tasks)
        
        contras_tasks = await self.db._run_query("SELECT DISTINCT task_id FROM research_contradictions")
        total_contras_tasks = len(contras_tasks)
        contra_rate = (total_contras_tasks / total_tasks) if total_tasks > 0 else 0.0
        
        # 4. Confidence calibration score (MAE between confidence and outcome)
        mae = 0.0
        if total_pred > 0:
            total_err = sum(abs(o["confidence_at_time"] - float(o["correct"])) for o in outcomes)
            mae = total_err / total_pred
            
        # 5. Average source independence score
        indep = await self.db._run_query("SELECT independence_score FROM source_independence")
        avg_indep = sum(i["independence_score"] for i in indep) / len(indep) if indep else 1.0
        
        # Save snapshot
        query = """
            INSERT INTO accuracy_metrics (
                snapshot_date, total_predictions, correct_predictions, prediction_accuracy,
                verification_success_rate, contradiction_detection_rate, confidence_calibration_score,
                avg_source_independence_score, computed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        await self.db._run_query(
            query,
            now_str, total_pred, correct_pred, pred_acc,
            success_rate, contra_rate, mae, avg_indep, time.time(),
            is_write=True
        )
        
        metrics = {
            "snapshot_date": now_str,
            "total_predictions": total_pred,
            "correct_predictions": correct_pred,
            "prediction_accuracy": round(pred_acc, 4),
            "verification_success_rate": round(success_rate, 4),
            "contradiction_detection_rate": round(contra_rate, 4),
            "confidence_calibration_score": round(mae, 4),
            "avg_source_independence_score": round(avg_indep, 4)
        }
        logger.info("accuracy_metrics.computed", metrics=metrics)
        return metrics

    async def get_latest_metrics(self) -> Optional[Dict]:
        """Retrieves the most recently calculated accuracy metrics snapshot."""
        query = "SELECT * FROM accuracy_metrics ORDER BY id DESC LIMIT 1"
        results = await self.db._run_query(query)
        return dict(results[0]) if results else None

    async def get_metrics_history(self, limit: int = 10) -> List[Dict]:
        """Retrieves historical accuracy metric snapshots ordered by date."""
        query = "SELECT * FROM accuracy_metrics ORDER BY id DESC LIMIT ?"
        results = await self.db._run_query(query, limit)
        return [dict(r) for r in results]
