import json
import time
from typing import List, Dict, Optional
import structlog
from mether.memory.persistent_memory import PersistentMemory

logger = structlog.get_logger(__name__)

class EvidenceVault:
    """Vault for permanently archiving source content and metadata."""

    def __init__(self, db: PersistentMemory) -> None:
        self.db = db

    async def store_snapshot(
        self,
        task_id: str,
        url: str,
        title: Optional[str],
        snapshot_text: str,
        quality_score: float,
        extracted_claim_ids: List[int] = None
    ) -> int:
        """Stores a source snapshot in the evidence vault database table."""
        if extracted_claim_ids is None:
            extracted_claim_ids = []
            
        claims_json = json.dumps(extracted_claim_ids)
        now = time.time()
        
        query = """
            INSERT INTO evidence_vault (
                task_id, url, title, snapshot_text, retrieved_at,
                quality_score, independence_score, extracted_claims_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        vault_id = await self.db._run_query(
            query,
            task_id, url, title, snapshot_text, now,
            quality_score, 1.0, claims_json,
            is_write=True
        )
        logger.info("evidence_vault.snapshot_stored", vault_id=vault_id, url=url, task_id=task_id)
        return vault_id

    async def get_snapshot(self, vault_id: int) -> Optional[Dict]:
        """Retrieves a single vaulted snapshot by ID."""
        query = "SELECT * FROM evidence_vault WHERE id = ?"
        results = await self.db._run_query(query, vault_id)
        if not results:
            return None
        
        res = dict(results[0])
        try:
            res["extracted_claims"] = json.loads(res["extracted_claims_json"])
        except Exception:
            res["extracted_claims"] = []
        return res

    async def get_all_for_task(self, task_id: str) -> List[Dict]:
        """Retrieves all vaulted snapshots for a specific task."""
        query = "SELECT * FROM evidence_vault WHERE task_id = ?"
        results = await self.db._run_query(query, task_id)
        
        out = []
        for r in results:
            item = dict(r)
            try:
                item["extracted_claims"] = json.loads(item["extracted_claims_json"])
            except Exception:
                item["extracted_claims"] = []
            out.append(item)
        return out

    async def update_independence_score(self, vault_id: int, score: float) -> None:
        """Updates the independence score of a vaulted snapshot."""
        query = "UPDATE evidence_vault SET independence_score = ? WHERE id = ?"
        await self.db._run_query(query, score, vault_id, is_write=True)
        logger.debug("evidence_vault.independence_updated", vault_id=vault_id, score=score)
