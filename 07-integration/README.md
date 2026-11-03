# 07 — Integration (observability chat)

## What it is (plain English)

This module **stacks** every concept from the article into one agentic answer
loop and makes the whole path **observable**:

1. **Plugin** load (packaging)
2. **Skill** selection with progressive loading (playbook)
3. **RAG** retrieval (runbook chunks + scores)
4. **MCP** tool call (standardized tools)
5. Plain **tools** / function calling
6. **API** detail fetch
7. **LLM** compose (Ollama or scripted fallback)
8. Final answer

They stack; they don’t compete. The demo is a **small web chat** (films well)
plus an optional Agent Debugger timeline — not an email-gate showcase.

## When to use this module

After the individual modules — as the end-to-end / YouTube finale for
observability across the stack.

## Running example

Ask in chat: **“Which open issues mention login?”**, **“How do we usually fix
login timeouts?”**, or **“Triage the open login issues.”**  
Same Northwind issue-tracker domain as every other module.

## Prerequisites

- Python 3.11+ and `requirements.txt`
- Optional: [Agent Debugger](https://github.com/likarajo/agent-debugger)
- Optional: Ollama (default path is scripted / free)

## Setup

```bash
cd 07-integration
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# from repo root:
export PYTHONPATH=.:07-integration:05-plugins:06-skills:04-mcp:03-rag:02-tools
```

## Run — web chat (preferred for filming)

```bash
# Standalone (local trace pane in the UI)
SKIP_MODEL=1 make chat
# open http://127.0.0.1:8080
```

With Agent Debugger:

```bash
make debugger-up
AGENT_DEBUGGER_URL=http://127.0.0.1:18000 SKIP_MODEL=1 make chat
```

One-shot CLI (same pipeline):

```bash
SKIP_MODEL=1 make integration
# or:
SKIP_MODEL=1 PYTHONPATH=.:07-integration:05-plugins:06-skills:04-mcp:03-rag:02-tools \
  python 07-integration/integration/pipeline.py --question "Which open issues mention login?"
```

Docker (standalone chat):

```bash
cd 07-integration && docker compose up
```

## Expected output

- Chat returns an answer citing issues and/or runbook sources.
- Local trace sidebar lists ordered steps with JSON payloads (`duration_ms`,
  RAG chunks, MCP request/response, LLM prompt summary, …).
- With Debugger: the same events are POSTed to `/runs/{id}/events` (copy
  `run_id` into the Debugger UI after the upstream Watch-run patch).

## Smoke test

```bash
PYTHONPATH=.:07-integration:05-plugins:06-skills:04-mcp:03-rag:02-tools \
  pytest 07-integration/tests -q
```

## Code walkthrough

1. `integration/chat_app.py` — FastAPI web chat + suggested question chips.
2. `integration/pipeline.py` — `answer_question()` runs all six concepts and
   records timed steps.
3. `../shared/debugger.py` — optional Debugger adapter (`step()`,
   `user.message`, `agent.answer`).
4. Docs: [`../docs/AGENT_DEBUGGER.md`](../docs/AGENT_DEBUGGER.md),
   [`../docs/AGENT_DEBUGGER_UPSTREAM.md`](../docs/AGENT_DEBUGGER_UPSTREAM.md).

## Known limitations

- Default LLM path is scripted when `SKIP_MODEL=1` / Ollama is down.
- Debugger UI needs a small upstream patch to “Watch run” by id (documented;
  not applied from this repo).
- Gated `email.send` is available when the user asks to notify/email; it is a
  side path for the separate Debugger breakpoint video.
