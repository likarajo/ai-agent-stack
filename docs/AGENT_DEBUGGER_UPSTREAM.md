# Agent Debugger upstream notes

External-run support for this companion repo landed in
[likarajo/agent-debugger#1](https://github.com/likarajo/agent-debugger/pull/1)
(**merged**). You no longer need to apply local patches for:

- `POST /runs` with `enqueue: false` (external drivers own the run)
- Worker idle / non-abort for `ai_agent_stack_*` / `external*` scenarios
- Broader audit types (`user.message`, `agent.answer`, …)
- **Watch run** UI (`/?run_id=` and paste-id)

## How ai-agent-stack uses it

1. `make debugger-up` brings up Debugger API on **host :8000** and UI on
   **:3000** (same ports as agent-debugger’s own `docker-compose.yml`). The
   stack’s Docker `issue-api` is published on host **:8001** so it does not
   collide with the Debugger console.
2. Chat / pipeline set `AGENT_DEBUGGER_URL=http://127.0.0.1:8000` and create
   runs with `enqueue: false` (scenario `ai_agent_stack_issue_triage`).
3. Every step is a timed `tool.call` / `tool.result` pair, plus `user.message`
   and `agent.answer`.
4. **Deny** on gated `email.send`: agent-debugger’s `POST /decision` returns
   200 and already aborts the run. The integration client must **not** post
   another `run.aborted` (or other events) to that run — that yields HTTP 400.
   See `shared/debugger.py` (`mark_remote_closed` / local-only audit) and
   `07-integration/tests/test_debugger_adapter.py::test_deny_path_ends_cleanly_without_posting_after_abort`.

## Historical patch sketches

The diff sketches that used to live in this file are obsolete now that PR #1
is merged. Refer to the agent-debugger repo history if you need the original
patch text.
