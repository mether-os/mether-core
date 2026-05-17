"""Centralised configuration loaded from environment variables / .env file."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime settings for the METHER backend.

    Values are read from environment variables first, then from a ``.env``
    file located in the project root (``backend/.env``).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # --- LLM Proxy ---------------------------------------------------------
    llm_proxy_url: str = "http://localhost:8082"
    llm_model: str = "nvidia_nim/z-ai/glm4.7"
    anthropic_auth_token: str = "freecc"

    # --- Server -------------------------------------------------------------
    mether_host: str = "0.0.0.0"
    mether_port: int = 8000

    # --- Memory / Context ---------------------------------------------------
    claude_md_path: str = "~/.mether/CLAUDE.md"

    # --- Logging ------------------------------------------------------------
    log_level: str = "INFO"

    # --- Derived helpers ----------------------------------------------------
    @property
    def claude_md_resolved(self) -> Path:
        """Return an absolute ``Path`` for the CLAUDE.md file."""
        return Path(self.claude_md_path).expanduser().resolve()


def get_settings() -> Settings:
    """Factory — handy for dependency injection and testing."""
    return Settings()
