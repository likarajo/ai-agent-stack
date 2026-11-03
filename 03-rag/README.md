# 03 — RAG (Retrieval-Augmented Generation)

## What it is (plain English)

**RAG** gives an LLM relevant information from *your* data at question time. The model doesn’t learn anything new — you find the right passages and put them in the prompt.

Two phases:
1. **Index** — chunk docs, embed them, store vectors locally.
2. **Ask** — embed the question, retrieve top chunks, generate a grounded answer with sources.

## When to use it vs the others

| Reach for | When |
| --- | --- |
| **RAG (this module)** | Answers must come from your docs and be traceable |
| Tools | Live actions / live data fetches |
| API | Deterministic call you already know |
| MCP / Plugins / Skills | How tools and playbooks are exposed/packaged |

Article one-liner: *RAG brings knowledge into the prompt. Tools let the model take actions or fetch live data.*

## Running example

Question: **“How do we usually fix login timeouts?”**  
Retrieval searches shared runbooks under `shared/data/docs/` (same Northwind portal domain).

## Prerequisites

- Python 3.11+ + `numpy`
- Optional Ollama chat model for generation; embeddings default to a **free deterministic local hash embedder** (no download). If Ollama is up and `nomic-embed-text` is pulled, it is preferred automatically.

## Setup

```bash
cd 03-rag
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH=.   # from repo root
```

## Run

```bash
SKIP_MODEL=1 PYTHONPATH=. python 03-rag/rag_demo/ask.py
# or with Ollama generation:
PYTHONPATH=. python 03-rag/rag_demo/ask.py
```

Docker:

```bash
cd 03-rag && docker compose up
```

## Expected output

Extractive mode prints top passages from `login-timeout-runbook.md` (and related docs) plus a `Sources:` line.

## Smoke test

```bash
PYTHONPATH=. pytest 03-rag/tests -q
```

## Code walkthrough

1. `rag_demo/index.py` — chunk markdown, embed, cosine top-k.
2. `rag_demo/ask.py` — build prompt from retrieved chunks; LLM or extractive fallback.
3. `shared/embeddings.py` — local hash embeddings by default; optional Ollama.

## Next

**04-mcp** standardizes how tools are exposed to any compatible host.
