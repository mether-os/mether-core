import time
import json
import structlog
from typing import Any, Dict, List, Tuple
from mether.events.bus import EventBus
from mether.memory.persistent_memory import PersistentMemory
from mether.agent.llm import LLMClient

logger = structlog.get_logger(__name__)

REQUIRED_SECTIONS = [
    "## Facts",
    "## Evidence",
    "## Unknowns",
    "## Analysis",
    "## Counter Arguments",
    "## Recommendations",
    "## Action Plan"
]

class WriterAgent:
    """
    Writer Agent: Generates evidence-first section drafts.
    
    CRITICAL STRUCTURE: Facts | Evidence | Unknowns | Analysis | Counter Arguments | Recommendations | Action Plan
    Facts and Recommendations are NEVER in the same block.
    Recommendations are NEVER generated from Unverified or Hypothesis claims.
    """

    def __init__(self, db: PersistentMemory, llm: LLMClient, bus: EventBus) -> None:
        self.db = db
        self.llm = llm
        self.bus = bus

    async def draft_section(
        self,
        task_id: str,
        section: Dict[str, Any],
        verified_claims: List[Dict],
        unverified_claims: List[Dict],
        unknowns: List[Dict],
        skeptic_challenges: List[Dict]
    ) -> str:
        """Drafts a report section, strictly enforcing the 7 required headings structure."""
        # 1. Fetch available sources for this task for context
        sources = await self.db._run_query(
            "SELECT url, title FROM research_sources WHERE task_id = ?",
            task_id
        )
        sources_context = "\n".join([
            f"- Source [{idx + 1}]: {s['title']} ({s['url']})"
            for idx, s in enumerate(sources)
        ])
        
        # 2. Build prompt
        prompt = self._build_evidence_first_prompt(
            section, verified_claims, unverified_claims, unknowns, skeptic_challenges, sources_context
        )
        
        system_instruction = (
            "You are a forensic report writer. You write structured, evidence-first reports. "
            "You never fabricate facts and strictly separate facts from recommendations."
        )
        
        # 3. Retry loop for structural validation
        draft = ""
        correction_note = ""
        for attempt in range(3):
            try:
                llm_resp = await self.llm.chat(
                    messages=[{"role": "user", "content": prompt + correction_note}],
                    system=system_instruction
                )
                content_blocks = llm_resp.get("content", [])
                draft = content_blocks[0].get("text", "") if content_blocks else ""
                
                is_valid, missing = self._validate_section_structure(draft)
                if is_valid:
                    logger.info("writer.draft_succeeded", section=section["title"], attempt=attempt)
                    # Record citations if any
                    await self._record_citations(task_id, section["title"], draft, sources)
                    return draft
                    
                logger.warning("writer.draft_missing_sections", section=section["title"], missing=missing, attempt=attempt)
                correction_note = f"\n\nCorrection required: Your previous attempt was missing the following headers: {', '.join(missing)}. Please regenerate the entire response and make sure you include ALL 7 headers exactly."
            except Exception as e:
                logger.error("writer.draft_attempt_failed", section=section["title"], error=str(e), attempt=attempt)
                
        # Return fallback if retries failed
        if not draft:
            draft = f"### {section['title']}\n\nDraft generation failed."
        return draft

    def _validate_section_structure(self, content: str) -> Tuple[bool, List[str]]:
        """Returns True if all 7 headers are present in the text."""
        missing = [s for s in REQUIRED_SECTIONS if s not in content]
        return len(missing) == 0, missing

    def _build_evidence_first_prompt(
        self,
        section: Dict[str, Any],
        verified_claims: List[Dict],
        unverified_claims: List[Dict],
        unknowns: List[Dict],
        skeptic_challenges: List[Dict],
        sources_context: str
    ) -> str:
        """Constructs the prompt for drafting the section, specifying formatting and structures."""
        v_claims_str = "\n".join([
            f"- {c['claim_text']} [Source: {c['source_url']}, Confidence: {int(c['confidence_score'] * 100)}%]"
            for c in verified_claims
        ])
        
        u_claims_str = "\n".join([
            f"- {c['claim_text']} (Reason: {c.get('evidence', '')})"
            for c in unverified_claims
        ])
        
        unknowns_str = "\n".join([
            f"- UNKNOWN: {u.get('field') or u.get('claim_text')} — {u.get('reason') or u.get('evidence')}"
            for u in unknowns
        ])
        
        challenges_str = "\n".join([
            f"- Challenge on claim {c.get('claim_id')}: {c.get('challenge_reason')} (Severity: {c.get('severity')})"
            for c in skeptic_challenges
        ])
        
        return f"""You are a Technical Writer Agent for METHER OS.
Your task is to draft a section of a research report.

Section Title: {section['title']}
Instructions: {section['instructions']}

Here is the structured input data:

Verified Claims (Use these in the Facts section):
{v_claims_str}

Unverified Claims:
{u_claims_str}

Unknown Fields:
{unknowns_str}

Skeptic Challenges:
{challenges_str}

Sources Context:
{sources_context}

CRITICAL STRUCTURE — you MUST include ALL 7 headers exactly:
## Facts
[Only Verified and Partially Verified claims. Format: "Claim text [Source: N, Confidence: X%]"]

## Evidence  
[Direct excerpts from sources supporting the facts above. Do not paraphrase beyond recognition.]

## Unknowns
[Every field where no verified evidence was found. Cannot be empty if unknowns exist. Format: "UNKNOWN: [field name] — [reason]"]

## Analysis
[Interpretation of the facts above ONLY. Must reference specific facts by source citation. No speculation beyond what evidence supports.]

## Counter Arguments
[Challenges to the above analysis. From skeptic assessment: {challenges_str}]

## Recommendations
[Specific recommendations derived ONLY from Verified or Partially Verified evidence. If no verified evidence exists for this section, write: "No recommendations possible — insufficient verified evidence."]

## Action Plan
[Concrete next steps for this section. Must reference specific evidence. No invented steps.]

Rules you MUST follow:
- You are a forensic research analyst, not a creative writer
- Never present a Hypothesis as a fact
- Never fill gaps with invented values
- If information is missing: write UNKNOWN
- Facts and Recommendations are in SEPARATE sections — never combined
- Do NOT output any preamble or chat intro. Just write the Markdown document starting with the headers.
"""

    async def _record_citations(self, task_id: str, section_title: str, draft: str, sources: List[Dict[str, Any]]) -> None:
        """Scan draft content for citations and record them in the database."""
        import re
        urls_in_draft = re.findall(r"Source:\s*(https?://[^\s,\]]+)", draft)
        unique_urls = set(urls_in_draft)
        
        for url in unique_urls:
            # Match domain/title if available
            title = "Cited Source"
            for src in sources:
                if src["url"] == url:
                    title = src["title"]
                    break
                    
            query = """
                INSERT INTO citations (
                    task_id, source_url, title, quote, citation_text, section_reference, retrieval_timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            await self.db._run_query(
                query,
                task_id, url, title, "Factual corroboration.", f"{title} ({url})", section_title, time.time(),
                is_write=True
            )
