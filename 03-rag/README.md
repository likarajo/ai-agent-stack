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

With the default deterministic hash embedder, the **top-ranked** passage is the “Agent-friendly tip” chunk in `auth-design-notes.md` (it quotes that question verbatim). Related chunks from `login-timeout-runbook.md` follow.

## Prerequisites

- Python 3.11+ + `numpy`
- Optional Ollama chat model for generation; embeddings default to a **free deterministic local hash embedder** (no download). If Ollama is up and `nomic-embed-text` is pulled, it is preferred automatically.

## Setup

All commands below are run **from the repository root**.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r 03-rag/requirements.txt
export PYTHONPATH=.
```

## Run

From the repo root:

```bash
SKIP_MODEL=1 PYTHONPATH=. python 03-rag/rag_demo/ask.py
# or with Ollama generation:
PYTHONPATH=. python 03-rag/rag_demo/ask.py
```

Docker, from the repo root:

```bash
docker compose -f 03-rag/docker-compose.yml up
```

## Expected output

Extractive mode (no LLM) prints ranked passages. For the default question, the top hit is from `auth-design-notes.md`:

```text
[extractive RAG — no LLM]
Question: How do we usually fix login timeouts?

Top passages:
[auth-design-notes.md | score=0.611]
## Agent-friendly tip
When someone asks "how do we usually fix login timeouts?", start from the login-timeout runbook, then search open issues mentioning login.

---

[login-timeout-runbook.md | score=0.218]
# Login timeout runbook
...

Sources: auth-design-notes.md, login-timeout-runbook.md
```

Scores are stable across runs (fixed embedding hash + index-order tie-break).

## Smoke test

From the repo root:

```bash
PYTHONPATH=. pytest 03-rag/tests -q -rA
```

Expected summary:

```text
....                                                                     [100%]
==================================== PASSES ====================================
PASSED 03-rag/tests/test_rag_smoke.py::test_index_has_chunks
PASSED 03-rag/tests/test_rag_smoke.py::test_retrieval_finds_login_runbook
PASSED 03-rag/tests/test_rag_smoke.py::test_example_query_top_passage_is_deterministic
PASSED 03-rag/tests/test_rag_smoke.py::test_extractive_answer
=========================== short test summary info ============================
PASSED 03-rag/tests/test_rag_smoke.py::test_index_has_chunks
PASSED 03-rag/tests/test_rag_smoke.py::test_retrieval_finds_login_runbook
PASSED 03-rag/tests/test_rag_smoke.py::test_example_query_top_passage_is_deterministic
PASSED 03-rag/tests/test_rag_smoke.py::test_extractive_answer
```

## Code walkthrough

1. `rag_demo/index.py` — chunk markdown, embed, cosine top-k.
2. `rag_demo/ask.py` — build prompt from retrieved chunks; LLM or extractive fallback.
3. `shared/embeddings.py` — local hash embeddings by default; optional Ollama.

## Next

**04-mcp** standardizes how tools are exposed to any compatible host.
