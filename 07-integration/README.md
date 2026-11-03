# 07 — Integration (full agentic stack)

## What it is (plain English)

This module **stacks** every concept from the article into one runnable agent:

1. **Plugin** load (packaging)
2. **Skill** selection with progressive loading (playbook)
3. **RAG** retrieval (runbook context)
4. **MCP** tool call (standardized tools)
5. Plain **tool / API**-shaped call (deterministic detail fetch)
6. Optional gated **`email.send`** (human-in-the-loop via Agent Debugger)

They stack; they don’t compete.

## When to use this module

Use it after you’ve walked the individual modules — as the end-to-end demo and as a template for wiring your own stack.

## Running example

Task: **“Triage the open login issues.”**  
Same Northwind portal issue-tracker domain used everywhere in this repo.

## Prerequisites

- Python 3.11+
- Dependencies from `requirements.txt` (includes `mcp`, `numpy`, `httpx`, …)
- Optional: [Agent Debugger](https://github.com/likarajo/agent-debugger) for the live timeline UI
- Optional: Ollama (not required for the default scripted path)

## Setup

```bash
cd 07-integration
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# from repo root:
export PYTHONPATH=.:05-plugins:06-skills:04-mcp
```

## Run (standalone — default)

```bash
# No debugger, no model keys required
SKIP_MODEL=1 PYTHONPATH=.:05-plugins:06-skills:04-mcp \
  python 07-integration/integration/pipeline.py

# Skip the gated email step entirely
SKIP_MODEL=1 PYTHONPATH=.:05-plugins:06-skills:04-mcp \
  python 07-integration/integration/pipeline.py --no-email
```

Docker (standalone):

```bash
cd 07-integration && docker compose up
```

## Run with Agent Debugger (optional)

See [`../docs/AGENT_DEBUGGER.md`](../docs/AGENT_DEBUGGER.md) and the top-level compose profile:

```bash
# from repo root — starts issue-stack + debugger (ui :3000, debugger api :18000)
make debugger-up
# in another shell:
make integration-debugger
```

Set:

| Env var | Meaning |
| --- | --- |
| `AGENT_DEBUGGER_URL` | Base URL of debugger API (e.g. `http://127.0.0.1:18000`). **Unset = standalone.** |
| `AGENT_DEBUGGER_AUTO_APPROVE` | `1` to auto-approve gated tools (tests only) |

## Expected output

A triage report listing open login issues, skill/plugin provenance, RAG excerpt, and (if enabled) a debugger note. With the debugger UI open you should see timeline events for plugin load, skill load, RAG, MCP, API, and a **paused** `email.send` until Approve/Deny.

## Smoke test

```bash
PYTHONPATH=.:05-plugins:06-skills:04-mcp pytest 07-integration/tests -q
```

Model-dependent and live-debugger tests are not required for CI.

## Code walkthrough

1. `integration/pipeline.py` — orchestrates the stack; emits debugger events when configured.
2. `integration/gated_actions.py` — simulated `email.send` (never sends real mail).
3. `../shared/debugger.py` — optional adapter to Agent Debugger’s runs/events/decision protocol.

## Known limitations

- Default path is deterministic/scripted so it runs free without Ollama.
- Combined Docker profile expects a local clone of `agent-debugger` as a sibling or via `AGENT_DEBUGGER_PATH` (see docs).
- Creating a run in Agent Debugger also enqueues its Redis worker; the compose profile **does not start** that worker so our pipeline can drive events. See PR notes for a suggested upstream tweak.
