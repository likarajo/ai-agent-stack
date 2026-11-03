# 02 — Tools (function calling)

## What it is (plain English)

**Tools** (also called function calling) let an LLM *request* an action. You describe functions to the model: a name, a plain-English description, and a JSON schema for the inputs. When the model decides a function would help, it replies with a structured tool call instead of text.

The part beginners often miss: **the model doesn’t run anything**. Your application runs the function, then sends the result back so the model can finish its answer.

## When to use it vs the others

| Reach for | When |
| --- | --- |
| API | You already know which endpoint to call |
| **Tools (this module)** | The model must choose which action to take inside *your* app |
| MCP | You want the same tools reusable across many AI hosts |
| Plugin | Packaging/distribution of capabilities |
| Skills | Playbooks / conventions on top of tools |
| RAG | Ground answers in documents (knowledge in, not actions out) |

Article decision guide: *Want the model to choose between a few actions in your own app? Define tools.*

## Running example

Question: **“Which open issues mention login?”**  
The model (or a scripted stand-in) proposes `search_issues(state="open", text="login")`; our code executes it against the shared issue store (same data as the API module).

## Prerequisites

- Python 3.11+
- Optional: [Ollama](https://ollama.com) with `qwen2.5:0.5b` (or set `OLLAMA_MODEL`) for the live tool loop
- Default path works **without** a model via a scripted demo (`SKIP_MODEL=1` or when Ollama is down)

## Setup

```bash
cd 02-tools
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# from repo root:
export PYTHONPATH=.
```

## Run

```bash
# Scripted / free path (no model)
SKIP_MODEL=1 PYTHONPATH=. python 02-tools/tools_demo/agent.py

# Live Ollama path (after: ollama pull qwen2.5:0.5b)
PYTHONPATH=. python 02-tools/tools_demo/agent.py

# Optional hosted OpenAI-compatible endpoint
# OPENAI_BASE_URL=... OPENAI_API_KEY=... OPENAI_MODEL=... PYTHONPATH=. python 02-tools/tools_demo/agent.py
```

Docker (scripted):

```bash
cd 02-tools && docker compose up
```

## Expected output

Something like:

```text
[scripted tools mode — no LLM]
Tool call: search_issues({"state": "open", "text": "login"})
Found 4 open issue(s) mentioning login:
- #101 Login page hangs after SSO redirect
...
```

## Smoke test

```bash
PYTHONPATH=. pytest 02-tools/tests -q
```

## Code walkthrough

1. `tools_demo/tools.py` — tool JSON schemas + `execute_tool` that calls `shared.issue_store`.
2. `tools_demo/agent.py` — chat loop with tools when Ollama is up; otherwise `scripted_tool_loop`.
3. Your code always executes tools — permissions stay in the application.

## Next

**03-rag** shows how to ground answers in docs; **04-mcp** wraps these same tools in a reusable MCP server.
