"""WhatsApp message formatter — makes LLM output sound human.

Strips markdown, AI preamble, formal language, and splits long
replies into multiple short messages like a real person would text.
"""

from __future__ import annotations

import re
from typing import Union


# ── AI preamble phrases to strip ──────────────────────────────────
_AI_PREAMBLES = [
    r"^Sure!?\s*",
    r"^Certainly!?\s*",
    r"^Of course!?\s*",
    r"^Great question!?\s*",
    r"^I'd be happy to\s*",
    r"^I would be happy to\s*",
    r"^Absolutely!?\s*",
    r"^As an AI[,.]?\s*",
    r"^As your assistant[,.]?\s*",
    r"^As your AI assistant[,.]?\s*",
    r"^Here's what I found:?\s*",
    r"^Here is what I found:?\s*",
    r"^Let me help you with that[.!]?\s*",
    r"^I can help with that[.!]?\s*",
    r"^That's a great question!?\s*",
    r"^Good question!?\s*",
    r"^No problem!?\s*",
]

# ── Formal → casual word replacements ─────────────────────────────
_FORMAL_REPLACEMENTS = [
    (r"\butilize\b", "use"),
    (r"\bUtilize\b", "Use"),
    (r"\bFurthermore\b", "Also"),
    (r"\bfurthermore\b", "also"),
    (r"\bHowever\b", "But"),
    (r"\bhowever\b", "but"),
    (r"\b[Ii]n conclusion[,.]?\s*", ""),
    (r"\b[Ii]t is important to note (that )?", ""),
    (r"\bAdditionally\b", "Also"),
    (r"\badditionally\b", "also"),
    (r"\bNevertheless\b", "Still"),
    (r"\bnevertheless\b", "still"),
    (r"\bTherefore\b", "So"),
    (r"\btherefore\b", "so"),
    (r"\bConsequently\b", "So"),
    (r"\bconsequently\b", "so"),
    (r"\bMoreover\b", "Also"),
    (r"\bmoreover\b", "also"),
    (r"\bI hope this helps!?\s*", ""),
    (r"\bLet me know if you have any (more |other )?questions[.!]?\s*", ""),
    (r"\bFeel free to ask[.!]?\s*", ""),
    (r"\bDon't hesitate to reach out[.!]?\s*", ""),
    (r"\bPlease don't hesitate to\s*", ""),
    (r"\bI'm here to help[.!]?\s*", ""),
]

# ── Code detection patterns ───────────────────────────────────────
_CODE_PATTERNS = [
    r"```",                      # markdown code fence
    r"\bdef \w+\(",              # python function
    r"\bfunction \w+\(",         # js function
    r"\bclass \w+[:\(]",         # class definition
    r"\bconst \w+ = ",           # js const
    r"\blet \w+ = ",             # js let
    r"\bvar \w+ = ",             # js var
    r"\bfor \w+ in ",            # python for loop
    r"\bfor\s*\(.+;.+;",        # c-style for loop
    r"\bimport \w+",             # import statement
    r"\bfrom \w+ import ",       # python import
    r"\breturn\s+\w+",           # return statement
    r"\bif\s*\(.+\)\s*\{",       # if block (c-style)
    r"#include\s*<",             # c/cpp include
]


def detect_message_type(text: str) -> str:
    """Classify LLM output as 'code', 'factual', or 'conversational'.

    Returns one of: ``"code"`` | ``"factual"`` | ``"conversational"``
    """
    # Code: contains actual code patterns or fenced blocks
    code_hits = sum(1 for p in _CODE_PATTERNS if re.search(p, text))
    if code_hits >= 2 or "```" in text:
        return "code"

    # Factual: short, direct Q&A style (contains numbers, dates, definitions)
    if len(text) < 300 and re.search(
        r"\b(is|are|was|were|equals?|means?|defined as|refers to)\b", text, re.I
    ):
        return "factual"

    return "conversational"


def _strip_markdown(text: str) -> str:
    """Remove all markdown formatting from text."""
    # Remove code fences but keep the code inside
    text = re.sub(r"```\w*\n?", "", text)
    # Remove bold
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    # Remove italic (single * or _)
    text = re.sub(r"(?<!\w)\*(.+?)\*(?!\w)", r"\1", text)
    text = re.sub(r"(?<!\w)_(.+?)_(?!\w)", r"\1", text)
    # Remove headers
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Remove bullet points (- or *)
    text = re.sub(r"^\s*[-*]\s+", "", text, flags=re.MULTILINE)
    # Remove numbered lists
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)
    # Remove inline code backticks
    text = re.sub(r"`([^`]+)`", r"\1", text)
    # Remove horizontal rules
    text = re.sub(r"^-{3,}$", "", text, flags=re.MULTILINE)
    return text


def _strip_ai_preamble(text: str) -> str:
    """Remove common AI assistant opening phrases."""
    text = text.strip()  # Ensure anchored ^ patterns work even with leading whitespace/newlines
    for pattern in _AI_PREAMBLES:
        text = re.sub(pattern, "", text, count=1, flags=re.IGNORECASE)
    return text.strip()


def _casualize(text: str) -> str:
    """Replace formal language with casual equivalents."""
    for pattern, replacement in _FORMAL_REPLACEMENTS:
        text = re.sub(pattern, replacement, text)
    return text


def _fix_punctuation(text: str) -> str:
    """Remove excessive punctuation."""
    text = re.sub(r"!{2,}", "!", text)
    text = re.sub(r"\?{2,}", "?", text)
    text = re.sub(r"\.{4,}", "...", text)
    return text


def _collapse_whitespace(text: str) -> str:
    """Collapse excessive blank lines into single breaks."""
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_code_blocks(text: str) -> tuple[str, list[str]]:
    """Extract fenced code blocks from text, returning (prose, [code_blocks])."""
    code_blocks: list[str] = []

    def _capture(m: re.Match) -> str:
        code_blocks.append(m.group(1).strip())
        return "<<CODE_BLOCK>>"

    prose = re.sub(r"```\w*\n?(.*?)```", _capture, text, flags=re.DOTALL)
    return prose, code_blocks


def format_for_whatsapp(text: str) -> Union[str, list[str]]:
    """Post-process LLM output into human-sounding WhatsApp message(s).

    Returns either a single string or a list of strings (for multi-message
    code replies that should be sent with a delay between them).
    """
    msg_type = detect_message_type(text)

    if msg_type == "code":
        return _format_code_reply(text)

    # ── Conversational / Factual ──
    text = _strip_ai_preamble(text)
    text = _strip_markdown(text)
    text = _casualize(text)
    text = _fix_punctuation(text)
    text = _collapse_whitespace(text)

    # Enforce length: if it's too long, truncate to key content
    lines = text.split("\n")
    if len(lines) > 12:
        text = "\n".join(lines[:12])

    return text


def _format_code_reply(text: str) -> list[str]:
    """Split a code-heavy LLM reply into multiple human-like WA messages.

    Returns a list of 1-3 messages:
      [0] casual intro
      [1] the code (plain text, no fences)
      [2] brief explanation (optional)
    """
    prose, code_blocks = _extract_code_blocks(text)

    # Clean the prose part
    prose = _strip_ai_preamble(prose)
    prose = _strip_markdown(prose)
    prose = _casualize(prose)
    prose = _fix_punctuation(prose)

    # Split prose into before-code and after-code segments
    parts = prose.split("<<CODE_BLOCK>>")
    intro = parts[0].strip() if parts else ""
    outro = parts[-1].strip() if len(parts) > 1 else ""

    # Build messages
    messages: list[str] = []

    # Intro — keep it short and casual
    if intro:
        # Limit to first 2 sentences
        sentences = re.split(r"(?<=[.!?])\s+", intro)
        intro = " ".join(sentences[:2]).strip()
        if intro:
            messages.append(intro)

    # Code blocks — plain text, no fences
    for block in code_blocks:
        messages.append(block)

    # Outro — brief explanation
    if outro:
        sentences = re.split(r"(?<=[.!?])\s+", outro)
        outro = " ".join(sentences[:2]).strip()
        if outro:
            messages.append(outro)

    # If we somehow got nothing, just return the cleaned text
    if not messages:
        cleaned = _strip_markdown(text)
        cleaned = _strip_ai_preamble(cleaned)
        cleaned = _casualize(cleaned)
        return [cleaned.strip() or "..."]

    return messages
