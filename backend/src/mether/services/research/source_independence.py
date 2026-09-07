import time
from typing import List, Dict, Optional
import structlog
from mether.memory.persistent_memory import PersistentMemory

logger = structlog.get_logger(__name__)

class SourceIndependenceAnalyzer:
    """Subsystem that identifies duplicated reporting and citation loops."""

    def __init__(self, db: PersistentMemory) -> None:
        self.db = db

    async def analyze_independence(self, task_id: str, sources: List[Dict]) -> List[Dict]:
        """Calculates independence score and classification for each source."""
        records = []
        n_sources = len(sources)
        if n_sources == 0:
            return records
            
        texts = [s.get("snapshot_text") or s.get("snippet") or "" for s in sources]
        urls = [s.get("url") for s in sources]
        
        # Calculate similarity matrix
        similarities = self._calculate_similarities(texts)
        
        for i in range(n_sources):
            url = urls[i]
            max_sim = 0.0
            duplicate_url = None
            
            for j in range(n_sources):
                if i != j:
                    sim = similarities[i][j]
                    if sim > max_sim:
                        max_sim = sim
                        duplicate_url = urls[j]
                        
            indep_score = 1.0 - max_sim
            
            # Categorize duplication type
            if max_sim > 0.95:
                dup_type = "copied"
            elif 0.80 < max_sim <= 0.95:
                dup_type = "syndicated"
            elif 0.20 < max_sim <= 0.80:
                dup_type = "derivative"
            else:
                dup_type = "original"
                duplicate_url = None
                
            # Store in database
            query = """
                INSERT INTO source_independence (
                    task_id, url, independence_score, duplicate_of_url, duplication_type,
                    similarity_score, flagged_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            await self.db._run_query(
                query,
                task_id, url, indep_score, duplicate_url, dup_type, max_sim, time.time(),
                is_write=True
            )
            
            # Update evidence vault score
            vault_res = await self.db._run_query(
                "SELECT id FROM evidence_vault WHERE task_id = ? AND url = ?",
                task_id, url
            )
            if vault_res:
                vault_id = vault_res[0]["id"]
                await self.db._run_query(
                    "UPDATE evidence_vault SET independence_score = ? WHERE id = ?",
                    indep_score, vault_id, is_write=True
                )
                
            records.append({
                "url": url,
                "independence_score": indep_score,
                "duplicate_of_url": duplicate_url,
                "duplication_type": dup_type,
                "similarity_score": max_sim
            })
            
        logger.info("source_independence.analysis_complete", count=len(records), task_id=task_id)
        return records

    def _calculate_similarities(self, texts: List[str]) -> List[List[float]]:
        """Computes pairwise cosine similarity using scikit-learn or fallback overlap."""
        n = len(texts)
        matrix = [[0.0] * n for _ in range(n)]
        
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
            
            # If all texts are empty, return zero matrix
            if not any(texts):
                return matrix
                
            vectorizer = TfidfVectorizer(stop_words='english')
            tfidf = vectorizer.fit_transform(texts)
            sim_matrix = cosine_similarity(tfidf, tfidf)
            
            for i in range(n):
                for j in range(n):
                    matrix[i][j] = float(sim_matrix[i][j])
        except Exception:
            # Fallback to Jaccard-like word overlap similarity
            logger.debug("source_independence.sklearn_unavailable_using_fallback")
            for i in range(n):
                for j in range(n):
                    if i == j:
                        matrix[i][j] = 1.0
                    else:
                        set_a = set(re.findall(r"\b\w+\b", texts[i].lower()))
                        set_b = set(re.findall(r"\b\w+\b", texts[j].lower()))
                        union_len = len(set_a | set_b)
                        if union_len > 0:
                            matrix[i][j] = len(set_a & set_b) / union_len
                        else:
                            matrix[i][j] = 0.0
        return matrix

    async def get_independence_for_task(self, task_id: str) -> List[Dict]:
        """Retrieves independence scores for a specific task."""
        query = "SELECT * FROM source_independence WHERE task_id = ?"
        results = await self.db._run_query(query, task_id)
        return [dict(r) for r in results]

    def _compute_echo_chamber_risk(self, sources: List[Dict]) -> float:
        """Returns the ratio of non-original sources to total sources."""
        if not sources:
            return 0.0
        non_original = sum(1 for s in sources if s.get("duplication_type") != "original")
        return non_original / len(sources)
