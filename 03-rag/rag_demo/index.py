"""Build and query a tiny local vector index over shared docs."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared import DOCS_DIR  # noqa: E402
from shared.embeddings import chunk_markdown, embed_texts, top_k  # noqa: E402


@dataclass
class Chunk:
    source: str
    text: str


@dataclass
class Index:
    chunks: list[Chunk]
    matrix: np.ndarray

    def search(self, query: str, k: int = 3) -> list[tuple[Chunk, float]]:
        q = embed_texts([query])[0]
        hits = top_k(q, self.matrix, k=k)
        return [(self.chunks[i], score) for i, score in hits]


def build_index(docs_dir: Path | None = None) -> Index:
    base = docs_dir or DOCS_DIR
    chunks: list[Chunk] = []
    for path in sorted(base.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        for piece in chunk_markdown(text):
            chunks.append(Chunk(source=path.name, text=piece))
    matrix = embed_texts([c.text for c in chunks]) if chunks else np.zeros((0, 256))
    return Index(chunks=chunks, matrix=matrix)
