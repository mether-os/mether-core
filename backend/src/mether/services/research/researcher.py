import time
import json
import urllib.parse
from typing import Any, Dict, List, Optional
import httpx
import structlog
from mether.events.bus import EventBus
from mether.memory.persistent_memory import PersistentMemory
from mether.agent.llm import LLMClient
from mether.services.research.budget_controller import BudgetController
from mether.services.research.evidence_vault import EvidenceVault

logger = structlog.get_logger(__name__)

class PlannerAgent:
    """Planner Agent: Decomposes a research topic into a structured outline."""

    def __init__(self, llm: LLMClient, bus: EventBus) -> None:
        self.llm = llm
        self.bus = bus

    async def generate_outline(self, topic: str, depth: str, length_target: str) -> List[Dict[str, Any]]:
        prompt = f"""You are a Technical Planner Agent for METHER OS.
Your task is to decompose the following research topic into a detailed outline:
Topic: "{topic}"
Depth: {depth}
Target Length: {length_target}

Generate a list of sections. Each section must have a title and brief instructions for what information the section should cover.
Return your response as a JSON array of objects, where each object has "title" and "instructions" fields. Do not include markdown wraps or backticks outside the valid JSON.

Example:
[
  {{"title": "1. Introduction to Quantum Computing", "instructions": "Explain basic quantum mechanics concepts, qubits, superposition."}},
  {{"title": "2. Quantum Entanglement & Gates", "instructions": "Explain gates like Hadamard, CNOT, and entanglement experiments."}}
]
"""
        try:
            llm_resp = await self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                system="You are an expert technical planner."
            )
            content_blocks = llm_resp.get("content", [])
            reply_text = content_blocks[0].get("text", "") if content_blocks else "[]"
            
            # Clean reply text in case LLM wrapped in backticks
            cleaned = reply_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            
            outline = json.loads(cleaned)
            if isinstance(outline, list) and len(outline) > 0:
                return outline
        except Exception as e:
            logger.error("planner.outline_failed", error=str(e))
            
        # Fallback outline
        return [
            {"title": "1. Executive Summary", "instructions": f"Provide a high-level overview of {topic}."},
            {"title": "2. Historical Context & Background", "instructions": f"Explain the origin and history of {topic}."},
            {"title": "3. Core Architecture & Components", "instructions": f"Detail the primary systems and mechanisms of {topic}."},
            {"title": "4. Key Challenges & Current Bottlenecks", "instructions": "Identify problems and limits in the field."},
            {"title": "5. Future Directions & Conclusion", "instructions": "Assess future developments and summarize findings."}
        ]


class ResearchAgent:
    """Research Agent: Gathers information with recursive verification loop.
    
    CRITICAL: No fallback fact generation. Search fails = Unknown. Always.
    """
    
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
    
    async def gather_information(self, task_id: str, topic: str, sections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Main entry point. Returns {claims: list, unknowns: list, sources: list}"""
        await self._ingest_local_files_if_any(task_id, topic)
        
        all_claims = []
        all_unknowns = []
        all_sources = []
        
        from mether.services.research.quality_scorer import score_source, recency_score as get_recency
        from mether.services.research.claim_verifier import ClaimVerifierAgent
        verifier = ClaimVerifierAgent(self.db)
        
        for idx, sec in enumerate(sections):
            section_title = sec["title"]
            search_query = f"{topic} {section_title}"
            section_claims = []
            section_searches = 0
            max_section_searches = self.budget.searches_per_section
            
            while section_searches < max_section_searches and self.budget.can_search():
                web_results = await self._search_duckduckgo(search_query)
                await self.budget.record_search()
                section_searches += 1
                
                if not web_results:
                    # Search failed. Mark unknown. Never fabricate.
                    await self._record_unknown(
                        task_id, sec["id"], section_title,
                        "general_information",
                        "Web search returned no results",
                        [search_query]
                    )
                    break
                
                for res in web_results[:3]:
                    url = res["url"]
                    title = res["title"]
                    snippet = res["snippet"]
                    
                    quality = score_source(url)
                    recency = get_recency(None)  # snippet has no date; default 0.3
                    
                    # Vault the source snapshot
                    vault_id = await self.evidence_vault.store_snapshot(
                        task_id, url, title, snippet, quality
                    )
                    
                    # Store raw source
                    source_id = await self._store_source(task_id, url, title, snippet, quality)
                    all_sources.append({"id": source_id, "url": url, "quality": quality, "snapshot_text": snippet})
                    
                    # Extract and verify claims
                    extracted = await self._extract_claims_from_source(title, snippet)
                    for claim_text in extracted:
                        claim = await verifier.verify_claim(
                            task_id=task_id,
                            claim_text=claim_text,
                            evidence=snippet,
                            source_url=url,
                            source_quality=quality,
                            recency=recency,
                            independence=0.7,  # default, updated by SourceIndependenceAnalyzer later
                            cross_validation_count=0,
                            has_contradiction=False,
                            mode_threshold=self.budget.confidence_threshold,
                            vault_id=vault_id,
                            section_id=sec["id"]
                        )
                        claim_id = await verifier.store_claim(task_id, claim)
                        
                        # Store in lists
                        claim_dict = {
                            "id": claim_id,
                            "claim_text": claim.claim_text,
                            "verification_status": claim.verification_status,
                            "confidence_score": claim.confidence.total,
                            "cross_validation_count": claim.cross_validation_count,
                            "source_quality_score": claim.source_quality_score,
                            "recency_score": claim.recency_score,
                            "confidence_independence": claim.confidence.independence,
                            "source_url": claim.source_url,
                            "section_id": sec["id"]
                        }
                        section_claims.append(claim_dict)
                        all_claims.append(claim_dict)
                
                # Check if confidence threshold reached for this section
                if section_claims:
                    avg = sum(c["confidence_score"] for c in section_claims) / len(section_claims)
                    if avg >= self.budget.confidence_threshold:
                        break
                
                # Refine query for next iteration
                search_query = f"{topic} {section_title} details evidence"
            
            # Detect missing information after loop
            section_unknowns = await self._detect_missing_information(
                task_id, sec["id"], section_title, topic, section_claims
            )
            all_unknowns.extend(section_unknowns)
        
        return {"claims": all_claims, "unknowns": all_unknowns, "sources": all_sources}
    
    async def _record_unknown(self, task_id: str, section_id: int, section_title: str, field: str, reason: str, queries: List[str]) -> None:
        """Record a field as explicitly Unknown. This is a first-class output."""
        import json
        await self.db._run_query(
            """INSERT INTO research_claims (
                task_id, section_id, claim_text, evidence, source_url, vault_id,
                verification_status, confidence_score,
                confidence_source_quality, confidence_cross_validation,
                confidence_recency, confidence_independence, contradiction_penalty,
                cross_validation_count, recency_score, source_quality_score, retrieved_timestamp
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            task_id, section_id,
            f"UNKNOWN: {field} for {section_title}",
            f"No evidence found. Queries attempted: {json.dumps(queries)}",
            "unknown://not-found", None,
            "Unverified", 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
            0, 0.0, 0.0, time.time(),
            is_write=True
        )
    
    async def _detect_missing_information(self, task_id: str, section_id: int, section_title: str, topic: str, section_claims: List[Dict]) -> List[Dict]:
        """After search loop: flag expected fields with no verified evidence."""
        unknowns = []
        expected_fields = self._get_expected_fields(topic)
        verified_texts = " ".join(
            c["claim_text"].lower() for c in section_claims
            if c["verification_status"] in ("Verified", "Partially Verified")
        )
        for field in expected_fields:
            if not any(kw in verified_texts for kw in field["keywords"]):
                # Record in DB
                await self._record_unknown(
                    task_id, section_id, section_title, field["name"],
                    "No verified evidence found", [topic, section_title]
                )
                unknowns.append({
                    "field": field["name"],
                    "section_id": section_id,
                    "section": section_title,
                    "reason": "No verified evidence found"
                })
        return unknowns
    
    def _get_expected_fields(self, topic: str) -> List[Dict]:
        """Return expected research fields based on topic keywords."""
        topic_lower = topic.lower()
        if any(k in topic_lower for k in ["company", "startup", "corp", "inc", "ltd", "venture"]):
            return [
                {"name": "founding_date", "keywords": ["founded", "established", "started", "incorporated"]},
                {"name": "headquarters", "keywords": ["located", "headquartered", "office", "based in"]},
                {"name": "employee_count", "keywords": ["employees", "team", "staff", "headcount"]},
                {"name": "funding", "keywords": ["funding", "raised", "investment", "series", "seed"]},
                {"name": "revenue", "keywords": ["revenue", "sales", "income", "arr", "mrr"]},
                {"name": "products", "keywords": ["product", "service", "solution", "platform"]},
            ]
        elif any(k in topic_lower for k in ["person", "ceo", "founder", "director"]):
            return [
                {"name": "education", "keywords": ["university", "degree", "studied", "graduated"]},
                {"name": "career", "keywords": ["worked", "position", "role", "career", "experience"]},
                {"name": "current_role", "keywords": ["current", "now", "presently", "ceo", "founder"]},
            ]
        else:
            return [
                {"name": "key_facts", "keywords": ["is", "was", "has", "are", "were"]},
                {"name": "timeline", "keywords": ["year", "date", "when", "since", "from"]},
                {"name": "metrics", "keywords": ["number", "count", "amount", "size", "scale"]},
            ]
    
    async def _extract_claims_from_source(self, title: str, snippet: str) -> List[str]:
        """Extract factual claims from source. Returns list of claim strings."""
        prompt = f"""You are a forensic research analyst.
Extract 3-5 specific, verifiable factual claims from this source. 
Each claim must be a concrete, checkable statement — not vague, not opinion.
Source: "{title}"
Content: "{snippet}"

Rules:
- Only extract what the text explicitly states
- Never invent or infer beyond the text
- If no clear facts exist, return empty array

Return JSON array of strings. No markdown wraps."""
        try:
            resp = await self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                system="You are a forensic facts extractor. Extract only what is explicitly stated."
            )
            content = resp.get("content", [])
            text = content[0].get("text", "[]") if content else "[]"
            cleaned = text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
            result = json.loads(cleaned)
            if isinstance(result, list):
                return [str(f) for f in result]
        except Exception as e:
            logger.warning("researcher.extract_claims_failed", error=str(e))
        return []
    
    async def _store_source(self, task_id: str, url: str, title: str, snippet: str, quality: float) -> int:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        query = """INSERT INTO research_sources (
            task_id, url, title, snippet, source_type, domain, credibility_score, trust_score
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"""
        return await self.db._run_query(
            query, task_id, url, title, snippet,
            "Web", domain, quality / 10.0, quality / 10.0,
            is_write=True
        )

    async def _search_duckduckgo(self, query: str) -> List[Dict[str, str]]:
        """DuckDuckGo HTML search scraper fallback."""
        try:
            escaped_query = urllib.parse.quote_plus(query)
            url = f"https://html.duckduckgo.com/html/?q={escaped_query}"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(resp.text, "html.parser")
                    results = []
                    for link in soup.find_all("a", class_="result__url"):
                        title_elem = link.find_previous("a", class_="result__snippet")
                        title = title_elem.text.strip() if title_elem else "Result Link"
                        snippet = title_elem.text.strip() if title_elem else ""
                        href = link.get("href", "")
                        href_str = href[0] if isinstance(href, list) else href
                        href_str = (href_str or "").strip()
                        results.append({
                            "url": href_str,
                            "title": title[:100],
                            "snippet": snippet[:300]
                        })
                    return results
        except Exception as e:
            logger.warning("researcher.web_search_failed", query=query, error=str(e))
        return []

    async def _ingest_local_files_if_any(self, task_id: str, topic: str) -> None:
        """Scan workspace folder for files matching the topic and save them in local_knowledge."""
        from pathlib import Path
        import glob
        
        workspace_dir = Path("c:/Users/mayan/Free_claude_codde")
        if not workspace_dir.is_dir():
            return
            
        search_pattern = f"*{topic.split()[0]}*"
        matched = []
        for ext in ["*.md", "*.txt"]:
            matched.extend(glob.glob(str(workspace_dir / "**" / f"{search_pattern}{ext}"), recursive=True))
            
        for m in matched[:3]:
            p = Path(m)
            try:
                content = p.read_text(encoding="utf-8", errors="ignore")[:2000]
                query = """
                    INSERT INTO local_knowledge (task_id, file_path, file_type, file_size, ingested_at, extracted_text_snippet)
                    VALUES (?, ?, ?, ?, ?, ?)
                """
                await self.db._run_query(
                    query,
                    task_id, str(p), p.suffix[1:], p.stat().st_size, time.time(), content,
                    is_write=True
                )
                logger.info("researcher.local_knowledge_ingested", path=str(p))
            except Exception as e:
                logger.warning("researcher.local_ingest_failed", path=str(p), error=str(e))
