from typing import Any, Dict
import structlog
from mether.events.bus import EventBus
from mether.memory.persistent_memory import PersistentMemory
from mether.agent.llm import LLMClient

logger = structlog.get_logger(__name__)

class ReviewerAgent:
    """Reviewer Agent: Fact-checks, de-duplicates, and refines section transitions."""

    def __init__(self, db: PersistentMemory, llm: LLMClient, bus: EventBus) -> None:
        self.db = db
        self.llm = llm
        self.bus = bus

    async def verify_and_polish(self, task_id: str, section: Dict[str, Any]) -> str:
        draft = section["content"] or ""
        
        # 1. Fetch citations and sources for fact checking
        citations = await self.db._run_query(
            "SELECT quote, source_url FROM citations WHERE task_id = ? AND section_reference = ?",
            task_id, section["title"]
        )
        
        # Format citations
        citations_context = ""
        for idx, cit in enumerate(citations):
            citations_context += f"Citation [{idx + 1}]:\n  Quote: \"{cit['quote']}\"\n  Source: {cit['source_url']}\n\n"

        # 2. Fact check and polish via LLM
        prompt = f"""You are a Peer Reviewer Agent for METHER OS.
Your task is to fact-check, refine transitions, and verify academic rigor for this section:

Section Title: {section['title']}
Draft Content:
\"\"\"
{draft}
\"\"\"

Below are the recorded source quotes for this section. Cross-reference them to ensure there are no exaggerated or halluncinated facts:
{citations_context}

CRITICAL REVIEW CHECKS:
1. Verify facts: Ensure every claim aligns with the source quotes. Fix or remove any hallucinated claims.
2. Polish styling: Check markdown formatting, remove repetitions or duplication.
3. Improve transition: Ensure smooth logical progression between paragraphs.
4. Keep inline bracket citations (e.g. [1]) intact.

Return the finalized, polished markdown text of the section. Do not include markdown wraps or code backticks outside the actual draft content.
"""
        try:
            llm_resp = await self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                system="You are an expert technical editor and peer reviewer."
            )
            content_blocks = llm_resp.get("content", [])
            polished = content_blocks[0].get("text", "") if content_blocks else draft
            return polished
        except Exception as e:
            logger.error("reviewer.polish_failed", section=section["title"], error=str(e))
            return draft
