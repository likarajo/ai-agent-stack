"""Retrieve relevant chunks, then answer (Ollama or extractive fallback)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE = Path(__file__).resolve().parents[1]
for path in (ROOT, MODULE):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from shared.config import SETTINGS  # noqa: E402
from shared.llm import ModelUnavailable, chat, model_available  # noqa: E402

from rag_demo.index import Index, build_index  # noqa: E402


def format_context(index: Index, query: str, k: int = 3) -> tuple[str, list[str]]:
    hits = index.search(query, k=k)
    blocks = []
    sources: list[str] = []
    for chunk, score in hits:
        blocks.append(f"[{chunk.source} | score={score:.3f}]\n{chunk.text}")
        if chunk.source not in sources:
            sources.append(chunk.source)
    return "\n\n---\n\n".join(blocks), sources


def answer_with_rag(question: str, index: Index | None = None) -> str:
    index = index or build_index()
    context, sources = format_context(index, question)
    if model_available(SETTINGS) and not SETTINGS.skip_model:
        try:
            reply = chat(
                [
                    {
                        "role": "system",
                        "content": (
                            "Answer only from the provided context. "
                            "Cite source filenames. If missing, say you don't know."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Context:\n{context}\n\nQuestion: {question}",
                    },
                ]
            )
            text = reply.get("content") or ""
            return f"{text}\n\nSources: {', '.join(sources)}"
        except ModelUnavailable:
            pass
    # Extractive fallback — shows retrieval works without an LLM.
    return (
        f"[extractive RAG — no LLM]\n"
        f"Question: {question}\n\n"
        f"Top passages:\n{context}\n\n"
        f"Sources: {', '.join(sources)}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--question",
        default="How do we usually fix login timeouts?",
    )
    args = parser.parse_args()
    print(answer_with_rag(args.question))


if __name__ == "__main__":
    main()
