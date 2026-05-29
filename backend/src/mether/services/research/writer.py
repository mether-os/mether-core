import time
import json
from typing import Any, Dict, List
import structlog
from mether.events.bus import EventBus
from mether.memory.persistent_memory import PersistentMemory
from mether.agent.llm import LLMClient

logger = structlog.get_logger(__name__)

class WriterAgent:
    """Writer Agent: Generates detailed section drafts with inline academic citations."""

    def __init__(self, db: PersistentMemory, llm: LLMClient, bus: EventBus) -> None:
        self.db = db
        self.llm = llm
        self.bus = bus

    async def draft_section(self, task_id: str, section: Dict[str, Any]) -> str:
        # 1. Fetch available sources/facts for this task
        sources = await self.db._run_query(
            "SELECT id, url, title, extracted_facts FROM research_sources WHERE task_id = ?",
            task_id
        )
        
        # 2. Format sources for LLM context
        sources_context = ""
        for idx, src in enumerate(sources):
            facts_list = json.loads(src.get("extracted_facts") or "[]")
            facts_str = "\n  - ".join(facts_list) if facts_list else "No specific facts extracted."
            sources_context += f"[{idx + 1}] Source: {src['title']} ({src['url']})\n  Facts:\n  - {facts_str}\n\n"

        # 3. Request section drafting from LLM
        prompt = f"""You are a Technical Writer Agent for METHER OS.
Your task is to draft a comprehensive, detailed section for a research report.

Section Title: {section['title']}
Section Instructions: {section['instructions']}

Below are the verified sources and facts gathered for this research. You MUST integrate them and use their bracket citation index (e.g. [1], [2]) directly in the text when mentioning facts from them:

{sources_context}

CRITICAL WRITING RULES:
- Write in a highly professional, academic, or technical style.
- Be exhaustive, write detailed paragraphs (aim for 500-1000 words for this section).
- Cite your sources inline using bracket numbers corresponding to the source index provided (e.g., "[1]").
- Do NOT add a references list or bibliography at the end of this section (it will be compiled globally).
- Use clean Markdown headers and lists where appropriate.
"""
        try:
            llm_resp = await self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                system="You are an expert technical report writer."
            )
            content_blocks = llm_resp.get("content", [])
            draft = content_blocks[0].get("text", "") if content_blocks else ""
            
            # Save citations to citation layer DB
            await self._record_citations(task_id, section["title"], draft, sources)
            
            return draft
        except Exception as e:
            logger.error("writer.draft_failed", section=section["title"], error=str(e))
            return f"### {section['title']}\n\nDraft generation failed for this section."

    async def _record_citations(self, task_id: str, section_title: str, draft: str, sources: List[Dict[str, Any]]) -> None:
        """Scan draft content for citations and record them in the citations table."""
        import re
        # Find all brackets like [1], [2], [3]
        indices = re.findall(r"\[(\d+)\]", draft)
        unique_indices = sorted(list(set(int(i) for i in indices)))
        
        for idx in unique_indices:
            if idx <= len(sources):
                src = sources[idx - 1]
                
                # Fetch quote (we can extract a surrounding sentence from the draft or just simulate a mock quote from the source facts)
                facts = json.loads(src.get("extracted_facts") or "[]")
                quote = facts[0] if facts else "Source data points."
                
                citation_text = f"{src.get('title') or 'Source'} ({src.get('url')})"
                
                query = """
                    INSERT INTO citations (
                        task_id, source_url, title, quote, citation_text, section_reference, retrieval_timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """
                await self.db._run_query(
                    query,
                    task_id, src["url"], src["title"], quote, citation_text, section_title, time.time(),
                    is_write=True
                )
                logger.info("writer.citation_recorded", url=src["url"])
