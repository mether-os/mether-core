"""Context memory — loads CLAUDE.md persona and keeps a rolling session log."""

from __future__ import annotations

from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)

DEFAULT_PERSONA = (
    "You are METHER, a personal AI assistant.\n"
    "You are helpful, direct, and technical.\n"
    "You respond in English and Hindi mixed (Hinglish).\n"
    "Keep responses concise."
)

# Maximum interactions to keep in the rolling window.
MAX_HISTORY = 10


class ContextMemory:
    """Manages the system persona (CLAUDE.md) and conversation history."""

    def __init__(self, claude_md_path: str) -> None:
        self._claude_md_path = Path(claude_md_path).expanduser().resolve()
        self._history: list[dict[str, str]] = []
        self._persona: str | None = None

    # ------------------------------------------------------------------
    # Persona
    # ------------------------------------------------------------------

    def load_claude_md(self) -> str:
        """Read the CLAUDE.md file and return its contents.

        If the file does not exist, a sensible default stub is returned
        and a warning is logged.
        """
        if self._persona is not None:
            return self._persona

        if self._claude_md_path.is_file():
            try:
                self._persona = self._claude_md_path.read_text(encoding="utf-8")
                logger.info(
                    "context_memory.loaded_claude_md",
                    path=str(self._claude_md_path),
                    length=len(self._persona),
                )
            except Exception:
                logger.exception("context_memory.read_error", path=str(self._claude_md_path))
                self._persona = DEFAULT_PERSONA
        else:
            logger.warning(
                "context_memory.claude_md_missing",
                path=str(self._claude_md_path),
            )
            self._persona = DEFAULT_PERSONA

        return self._persona

    # ------------------------------------------------------------------
    # Session history
    # ------------------------------------------------------------------

    def add_interaction(self, user: str, assistant: str) -> None:
        """Append a user/assistant exchange, trimming to *MAX_HISTORY*."""
        self._history.append({"role": "user", "content": user})
        self._history.append({"role": "assistant", "content": assistant})

        # Keep only the last MAX_HISTORY interactions (2 messages each).
        max_messages = MAX_HISTORY * 2
        if len(self._history) > max_messages:
            self._history = self._history[-max_messages:]

    def get_recent_context(self) -> list[dict[str, str]]:
        """Return the rolling history as a list of message dicts."""
        return list(self._history)

    def clear(self) -> None:
        """Wipe session history (persona is kept)."""
        self._history.clear()
        logger.info("context_memory.cleared")
