# 01 — APIs

## What it is (plain English)

An **API** is a documented contract that lets one program talk to another. For this demo that means HTTPS-style HTTP requests and JSON responses: you call an endpoint, and you get data back in the shape the docs promise.

There is **no AI** in this module. You decide exactly which call to make and when. Everything else in this repo eventually calls an API somewhere.

## When to use it vs the others

| Reach for | When |
| --- | --- |
| **API (this module)** | You know exactly which call to make from regular code |
| Tools | The model must choose which action to take |
| MCP | You want one integration many AI apps can reuse |
| Plugin | You want to ship a ready-made capability in one install |
| Skills | The agent has tools but needs your team’s playbook |
| RAG | Answers must be grounded in your documents |

Article decision guide: *Need to call one known endpoint from regular code? Use the API directly.*

## Running example

Same question as the article: **“Which open issues mention login?”**  
This module answers it with `GET /issues?state=open&q=login` against a local Northwind Issue Tracker.

## Prerequisites

- Python 3.11+
- Optional: Docker Compose for one-command bring-up

## Setup

```bash
cd 01-apis
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

From the repo root (so `shared/` imports resolve):

```bash
export PYTHONPATH=.
```

## Run

Start the API:

```bash
# from repo root
PYTHONPATH=.:01-apis python -m uvicorn issue_api.server:app --host 127.0.0.1 --port 8000
```

In another terminal, call the client:

```bash
PYTHONPATH=.:01-apis python 01-apis/issue_api/client.py
```

One-command Docker bring-up:

```bash
cd 01-apis && docker compose up --build
```

## Expected output

JSON listing open issues whose title/body/labels contain `login` (for example issues 101, 102, 105, 107), plus a count line:

```text
Found 4 open issue(s) mentioning login.
```

## Smoke test

```bash
# from repo root
PYTHONPATH=. pytest 01-apis/tests -q
```

No model or network keys required.

## Code walkthrough

1. `issue_api/server.py` — FastAPI app exposing `/health`, `/issues`, `/issues/{id}`.
2. `../shared/issue_store.py` — loads `shared/data/issues.json` and filters by state/text.
3. `issue_api/client.py` — deterministic `GET /issues?state=open&q=login` (you choose the call; the model never does).

## Next

Continue to **02-tools** to let an LLM *propose* this same search as a tool call while your code still executes it.
