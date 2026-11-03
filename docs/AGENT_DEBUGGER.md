# Optional Agent Debugger integration

Off by default. When `AGENT_DEBUGGER_URL` is unset, the integration module runs fully standalone.

## What Agent Debugger is

[likarajo/agent-debugger](https://github.com/likarajo/agent-debugger) is a local Docker stack:

| Service | Port | Role |
| --- | --- | --- |
| UI | 3000 | Timeline + Approve / Deny |
| FastAPI | 8000 (mapped to **18000** in our combined compose) | Runs, SSE, decisions, policy |
| Redis | 6379 | Queue, events, pub/sub |
| Scripted agent worker | — | Demo outreach scenario (we **omit** this service in the combined profile) |

Gated tools (from its `api/app/policy.py`): `email.send`, `shell.exec`, `file.delete`.

## Protocol we speak

Learned from `api/app/main.py`, `runs.py`, `policy.py`, and `agent/worker.py`:

1. `POST /runs` `{ "scenario": "ai_agent_stack_issue_triage" }` → create run  
2. `POST /runs/{id}/events` with bodies like:
   - `{ "type": "run.started", "message": "..." }`
   - `{ "type": "think", "message": "..." }`
   - `{ "type": "tool.call", "tool": "...", "message": "...", "payload": {...} }`
   - `{ "type": "tool.result", "tool": "...", "message": "...", "payload": {...} }`
   - `{ "type": "run.completed" | "run.aborted", "message": "..." }`
3. If `tool.call` names a gated tool, the API sets status=`paused` and returns `gated: true`
4. Agent blocks on `GET /runs/{id}/wait-decision`
5. Human clicks Approve/Deny in the UI → `POST /runs/{id}/decision`

Our adapter: `shared/debugger.py`.

## Timeline events emitted by 07-integration

| Step | Event tool / type |
| --- | --- |
| Plugin load | `plugin.install` |
| Skill selection | `skill.load` |
| RAG retrieval | `rag.retrieve` |
| MCP tool call | `mcp.search_issues_tool` |
| Plain API call | `api.get_issue` |
| Gated demo action | `email.send` (pauses) |

## One-command bring-up (combined)

From this repo (after cloning Agent Debugger — see below):

```bash
make debugger-up          # compose profile: our services + debugger ui/api/redis
make integration-debugger # run pipeline with AGENT_DEBUGGER_URL set
```

Open http://localhost:3000 — when the pipeline hits `email.send`, Approve or Deny.

## Clone Agent Debugger (read-only dependency)

```bash
# default path expected by compose
git clone https://github.com/likarajo/agent-debugger.git third_party/agent-debugger
# or:
export AGENT_DEBUGGER_PATH=/path/to/agent-debugger
```

This repo does **not** vendor or modify Agent Debugger.

## Minimal upstream change suggested for Agent Debugger

Needed later (separate PR, with Raj’s OK) — **not done from this agent**:

1. **External / idle scenario** — In `agent/worker.py`, treat scenarios such as `ai_agent_stack_issue_triage` (or any `external*`) as no-ops: do **not** post `run.aborted` for unknown scenarios; simply skip so an external driver can own the run.
2. **Optional `enqueue: false` on `POST /runs`** — In `api/app/runs.py` / `main.py`, allow creating a run **without** `lpush` to `runs:queue`, so external agents never race the scripted worker.

Until that lands, our compose profile starts debugger **api + ui + redis only** (no `agent` worker). That is enough for demos today.

## Env reference

```bash
export AGENT_DEBUGGER_URL=http://127.0.0.1:18000
# tests only:
export AGENT_DEBUGGER_AUTO_APPROVE=1
```
