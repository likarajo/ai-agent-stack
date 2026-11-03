"""Environment configuration. Default path is fully local and free (Ollama)."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Runtime settings for LLM and API modules."""

    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:0.5b"
    ollama_embed_model: str = "nomic-embed-text"
    # Optional hosted OpenAI-compatible endpoint (disabled by default).
    openai_base_url: str | None = None
    openai_api_key: str | None = None
    openai_model: str | None = None
    issue_api_base_url: str = "http://127.0.0.1:8000"
    skip_model: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        skip = os.getenv("SKIP_MODEL", "").lower() in {"1", "true", "yes"}
        return cls(
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
            ollama_model=os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b"),
            ollama_embed_model=os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text"),
            openai_base_url=os.getenv("OPENAI_BASE_URL") or None,
            openai_api_key=os.getenv("OPENAI_API_KEY") or None,
            openai_model=os.getenv("OPENAI_MODEL") or None,
            issue_api_base_url=os.getenv("ISSUE_API_BASE_URL", "http://127.0.0.1:8000"),
            skip_model=skip,
        )

    @property
    def use_hosted(self) -> bool:
        return bool(self.openai_base_url and self.openai_model)


SETTINGS = Settings.from_env()
