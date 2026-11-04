"""Smoke tests for RAG (retrieval works without a model)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(MODULE))

from rag_demo.ask import answer_with_rag, format_context  # noqa: E402
from rag_demo.index import build_index  # noqa: E402


def test_index_has_chunks() -> None:
    index = build_index()
    assert len(index.chunks) >= 3
    assert index.matrix.shape[0] == len(index.chunks)


EXAMPLE_QUERY = "How do we usually fix login timeouts?"


def test_retrieval_finds_login_runbook() -> None:
    index = build_index()
    context, sources = format_context(index, EXAMPLE_QUERY, k=3)
    assert "login" in context.lower() or "timeout" in context.lower()
    assert any("login" in s or "auth" in s or "runbook" in s for s in sources)


def test_example_query_top_passage_is_deterministic() -> None:
    """README example query: top hit is the auth-design tip that quotes the question."""
    index = build_index()
    first = index.search(EXAMPLE_QUERY, k=1)
    assert first, "expected at least one retrieval hit"
    chunk, score = first[0]
    assert chunk.source == "auth-design-notes.md"
    assert "how do we usually fix login timeouts?" in chunk.text.lower()
    # Stable across rebuilds (fixed hash embedder + tie-break).
    again = build_index().search(EXAMPLE_QUERY, k=3)
    assert [(c.source, c.text, s) for c, s in again] == [
        (c.source, c.text, s) for c, s in index.search(EXAMPLE_QUERY, k=3)
    ]
    assert score > 0


def test_extractive_answer() -> None:
    os.environ["SKIP_MODEL"] = "1"
    out = answer_with_rag(EXAMPLE_QUERY)
    assert "Sources:" in out
    assert "login" in out.lower() or "timeout" in out.lower()
    assert "auth-design-notes.md" in out
