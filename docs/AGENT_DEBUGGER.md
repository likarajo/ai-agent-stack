# Agent Debugger + observability chat

The **final ai-agent-stack demo is about full observability**: a user asks a
question in chat, and every step of answering it appears (in order) in Agent
Debugger’s timeline and audit log — with inputs, outputs, and timing.

The gated `email.send` path still exists for the separate Debugger “breakpoint”
video, but it is **not** the focus here (only used when the user asks to
email/notify, or when you pass `--email`).

## Quick start

```bash
# Terminal A — optional Debugger stack (api :8000, ui :3000; issue-api on :8001)
make debugger-up

# Terminal B — observability chat (http://127.0.0.1:8080)
export AGENT_DEBUGGER_URL=http://127.0.0.1:8000
make chat
```

Open **http://127.0.0.1:8080**, click a suggested question, watch the local
trace pane. Copy `run_id` into Agent Debugger’s **Watch run** UI (or open
`http://localhost:3000/?run_id=<uuid>` — see
[`AGENT_DEBUGGER_UPSTREAM.md`](AGENT_DEBUGGER_UPSTREAM.md)).

Standalone (no Debugger):

```bash
make chat
# or one-shot CLI:
make integration
```

## What gets emitted (every chat turn)

Ordered events (also mirrored locally when Debugger is off):

| # | Event | Tool / type | Payload highlights |
| ---: | --- | --- | --- |
| 1 | Run start | `run.started` | scenario |
| 2 | User question | `user.message` | content |
| 3 | Plan | `think` | routing note |
| 4 | Plugins | `tool.call` / `tool.result` → `plugin.load` | manifest in, installed config out, `duration_ms` |
| 5 | Skills | `tool.call` / `tool.result` → `skill.select` | catalog, selected name, body preview, `duration_ms` |
| 6 | RAG | `tool.call` / `tool.result` → `rag.retrieve` | query, k, chunks[{source,score,text}], `duration_ms` |
| 7 | MCP | `tool.call` / `tool.result` → `mcp.search_issues_tool` | request + response ids/titles, `duration_ms` |
| 8 | Tools | `tool.call` / `tool.result` → `tools.search_issues` | schema + args in, count/ids out, `duration_ms` |
| 9 | APIs | `tool.call` / `tool.result` → `api.get_issue` | GET path in, issue body out, `duration_ms` |
| 10 | LLM | `tool.call` / `tool.result` → `llm.chat` | model, prompt_summary, tokens if available, `duration_ms` |
| 11 | Final answer | `agent.answer` | full answer text, total `duration_ms` |
| 12 | Complete | `run.completed` | summary |

Optional (only if the question asks to email/notify, or `--email`):

| … | Gated notify | `tool.call` `email.send` | pauses in Debugger until Approve/Deny |

Implementation: `shared/debugger.py` (`step()` adds timing) +
`07-integration/integration/pipeline.py` (`answer_question`).

## Suggested demo questions (exercise all six concepts)

Together these three turns hit **APIs, tools, RAG, MCP, plugins, and skills**.
Every turn runs the full stack; the “focus” column is what to narrate on camera.

### 1) `Which open issues mention login?`

**Focus:** MCP + tools + API live data (plugin/skill/RAG still appear in the trace).

**Expected trace (order):**

1. `user.message` — the question text  
2. `plugin.load` — Northwind plugin install output (mcp server + skills + commands)  
3. `skill.select` — catalog includes `issue-triage`; skill may still load  
4. `rag.retrieve` — query about login/auth; top-k chunks with `source` + `score`  
5. `mcp.search_issues_tool` — request `{state: open, text: login}` → issue ids 101/102/105/107  
6. `tools.search_issues` — same search via in-app function calling  
7. `api.get_issue` — GET detail for first hit (e.g. `#101`)  
8. `llm.chat` — prompt_summary + model (or `scripted-fallback`)  
9. `agent.answer` — list of open login issues  
10. `run.completed`

### 2) `How do we usually fix login timeouts?`

**Focus:** RAG grounding from `login-timeout-runbook.md` / auth notes.

**Expected trace (order):** same skeleton as (1), with:

- `rag.retrieve.input.query` ≈ “How do we usually fix login timeouts?”  
- chunks prominently from `login-timeout-runbook.md` and `auth-design-notes.md` with scores  
- final answer cites runbook steps (latency, cookie domain, rate limits) **and** related open issues from MCP/API

### 3) `Triage the open login issues.`

**Focus:** Skills playbook (`issue-triage`) formatting the answer.

**Expected trace (order):** same skeleton, with:

- `skill.select.output.selected` = `issue-triage`  
- `agent.answer` shaped as a triage report (matches, severity call, next step)  
- optional: append “email this to ops” / run with `--email` to show gated `email.send` once (separate Debugger video beat)

## Env vars

| Variable | Default | Meaning |
| --- | --- | --- |
| `AGENT_DEBUGGER_URL` | unset | Debugger API base (`http://127.0.0.1:8000`). Unset = standalone. |
| `AGENT_DEBUGGER_AUTO_APPROVE` | unset | Tests only — auto-approve gated tools |
| `CHAT_HOST` / `CHAT_PORT` | `127.0.0.1` / `8080` | Web chat bind |
| `SKIP_MODEL` | `0` | Force scripted LLM compose |

## Compose profile

```bash
make debugger-up          # clones third_party/agent-debugger if needed
make chat-debugger        # chat with AGENT_DEBUGGER_URL set
```

The profile starts debugger **redis + api (:8000) + ui (:3000)** and this repo’s
`issue-api` on host **:8001** (so Debugger keeps :8000, matching
agent-debugger’s compose). It **omits** the debugger outreach worker so our
chat owns the run. External-run support is already merged upstream — see
[`AGENT_DEBUGGER_UPSTREAM.md`](AGENT_DEBUGGER_UPSTREAM.md).

## Deny path

Clicking **Deny** on gated `email.send` returns HTTP 200 from
`POST /decision` and aborts the run inside agent-debugger. The integration
client must not POST another `run.aborted` (that is the HTTP 400 crash). It
records a denied `tool.result` locally and finishes the answer without further
remote events.

## Upstream notes

[`AGENT_DEBUGGER_UPSTREAM.md`](AGENT_DEBUGGER_UPSTREAM.md)
