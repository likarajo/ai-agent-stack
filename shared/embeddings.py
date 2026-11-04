"""Local embeddings: deterministic bag-of-words for free offline use,
optional Ollama embeddings when a model is available.
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Iterable

import httpx
import numpy as np

from shared.config import SETTINGS, Settings
from shared.llm import ModelUnavailable, model_available

_TOKEN = re.compile(r"[a-z0-9_]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


def _stable_token_index(token: str, dim: int) -> int:
    """Process-stable bucket index (avoids PYTHONHASHSEED-randomized hash())."""
    digest = hashlib.sha256(token.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "little") % dim


def hash_embed(text: str, dim: int = 256) -> np.ndarray:
    """Deterministic local embedding that needs no model download."""
    vec = np.zeros(dim, dtype=np.float32)
    for token in tokenize(text):
        vec[_stable_token_index(token, dim)] += 1.0
    norm = float(np.linalg.norm(vec))
    if norm:
        vec /= norm
    return vec


def ollama_embed(text: str, settings: Settings | None = None) -> np.ndarray:
    cfg = settings or SETTINGS
    try:
        with httpx.Client(base_url=cfg.ollama_base_url, timeout=60.0) as client:
            resp = client.post(
                "/api/embeddings",
                json={"model": cfg.ollama_embed_model, "prompt": text},
            )
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPError, OSError) as exc:
        raise ModelUnavailable(f"Ollama embeddings failed: {exc}") from exc
    return np.asarray(data["embedding"], dtype=np.float32)


def embed_texts(
    texts: Iterable[str],
    *,
    settings: Settings | None = None,
    prefer_ollama: bool = True,
) -> np.ndarray:
    cfg = settings or SETTINGS
    items = list(texts)
    if prefer_ollama and model_available(cfg) and not cfg.skip_model:
        try:
            return np.vstack([ollama_embed(t, cfg) for t in items])
        except ModelUnavailable:
            pass
    return np.vstack([hash_embed(t) for t in items])


def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if not denom:
        return 0.0
    return float(np.dot(a, b) / denom)


def top_k(
    query_vec: np.ndarray,
    matrix: np.ndarray,
    k: int = 3,
) -> list[tuple[int, float]]:
    if matrix.size == 0:
        return []
    scores = [
        (i, cosine_sim(query_vec, matrix[i]))
        for i in range(matrix.shape[0])
    ]
    # Highest score first; stable tie-break by chunk index for determinism.
    scores.sort(key=lambda x: (-x[1], x[0]))
    return scores[:k]


def chunk_markdown(text: str, max_chars: int = 500) -> list[str]:
    """Split markdown into rough paragraph chunks for RAG demos."""
    parts = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    for part in parts:
        if len(part) <= max_chars:
            chunks.append(part)
            continue
        for i in range(0, len(part), max_chars):
            chunks.append(part[i : i + max_chars])
    return chunks
