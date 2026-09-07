from typing import List, Dict
import structlog
from mether.memory.persistent_memory import PersistentMemory

logger = structlog.get_logger(__name__)

class SourceNetworkMapper:
    """Subsystem for mapping citations, syndications, and primary sources in a network graph."""

    def __init__(self, db: PersistentMemory) -> None:
        self.db = db

    async def build_network(
        self,
        task_id: str,
        sources: List[Dict],
        independence_records: List[Dict]
    ) -> Dict:
        """Constructs nodes and edges, identifies echo chambers, and stores the results."""
        nodes = {}
        # Parse parents from independence records
        parents = {rec["url"]: rec["duplicate_of_url"] for rec in independence_records}
        
        # Count claims per source url from research_claims
        claims_query = "SELECT source_url, COUNT(*) as cnt FROM research_claims WHERE task_id = ? GROUP BY source_url"
        claims_counts = await self.db._run_query(claims_query, task_id)
        claim_map = {row["source_url"]: row["cnt"] for row in claims_counts}
        
        # Build node objects
        for src in sources:
            url = src.get("url")
            parent = parents.get(url)
            claim_count = claim_map.get(url, 0)
            nodes[url] = {
                "url": url,
                "parent": parent,
                "claim_count": claim_count,
                "children": [],
                "depth": 0
            }
            
        # Wire children
        for url, node in nodes.items():
            parent = node["parent"]
            if parent and parent in nodes:
                nodes[parent]["children"].append(url)
                
        # Resolve depth and primary sources
        primary_sources = []
        for url, node in nodes.items():
            if not node["parent"]:
                primary_sources.append(url)
                node["depth"] = 0
            else:
                # Traverse parent chain
                depth = 0
                curr = url
                visited = set()
                while nodes.get(curr) and nodes[curr]["parent"] and nodes[curr]["parent"] not in visited:
                    visited.add(curr)
                    curr = nodes[curr]["parent"]
                    depth += 1
                node["depth"] = depth
                
        # Identify echo chambers: clusters where 5+ sources derived from one primary
        echo_chambers = []
        for primary in primary_sources:
            descendants = []
            queue = [primary]
            visited = set()
            while queue:
                curr = queue.pop(0)
                if curr in visited:
                    continue
                visited.add(curr)
                if curr != primary:
                    descendants.append(curr)
                if nodes.get(curr):
                    queue.extend(nodes[curr]["children"])
            
            # If 5+ derived sources
            if len(descendants) >= 5:
                echo_chambers.append({
                    "primary": primary,
                    "size": len(descendants) + 1,
                    "descendants": descendants
                })
                
            # Assign risk score to nodes in this cluster
            risk_score = min(1.0, len(descendants) / 8.0)
            if nodes.get(primary):
                nodes[primary]["echo_chamber_risk"] = risk_score
            for desc in descendants:
                if nodes.get(desc):
                    nodes[desc]["echo_chamber_risk"] = risk_score
                    
        # Write to db
        for url, node in nodes.items():
            risk = node.get("echo_chamber_risk", 0.0)
            query = """
                INSERT INTO source_network (
                    task_id, url, parent_url, claim_count, echo_chamber_risk_score, citation_chain_depth
                ) VALUES (?, ?, ?, ?, ?, ?)
            """
            await self.db._run_query(
                query,
                task_id, url, node["parent"], node["claim_count"], risk, node["depth"],
                is_write=True
            )
            
        summary = {
            "total_nodes": len(nodes),
            "primary_sources_count": len(primary_sources),
            "echo_chambers_detected": len(echo_chambers),
            "echo_chambers": echo_chambers
        }
        logger.info("source_network.network_mapped", summary=summary, task_id=task_id)
        return summary

    async def get_network_for_task(self, task_id: str) -> List[Dict]:
        """Retrieves network nodes for a task."""
        query = "SELECT * FROM source_network WHERE task_id = ?"
        results = await self.db._run_query(query, task_id)
        return [dict(r) for r in results]
