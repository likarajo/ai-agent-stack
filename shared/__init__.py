"""Shared fixtures and helpers for the ai-agent-stack modules."""

from pathlib import Path

SHARED_DIR = Path(__file__).resolve().parent
DATA_DIR = SHARED_DIR / "data"
ISSUES_PATH = DATA_DIR / "issues.json"
DOCS_DIR = DATA_DIR / "docs"

__all__ = ["SHARED_DIR", "DATA_DIR", "ISSUES_PATH", "DOCS_DIR"]
