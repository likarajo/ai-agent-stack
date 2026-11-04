# 04 — MCP (Model Context Protocol)

## What it is (plain English)

**MCP** is an open protocol that standardizes how AI applications connect to external tools and data. Think USB-C for AI apps: build the connector once, and any compatible host can use it.

Roles:
- **Host** — the AI app the user works in
- **Client** — inside the host; talks to one MCP server
- **Server** — wraps a real system (here, the issue tracker) and exposes tools, resources, and prompts

MCP doesn’t replace tool calling — it standardizes how tools are *discovered and invoked* across apps.

## When to use it vs the others

| Reach for | When |
| --- | --- |
| Tools (in-app) | One app owns the schemas |
| **MCP (this module)** | One integration many AI apps/IDEs can reuse |
| Plugin | Ship MCP + skills + commands as one install |
| API | The underlying contract the server still calls |

## Running example

An MCP server exposes `search_issues_tool` / `get_issue_tool`. A stdio client lists tools and calls `search_issues_tool(state="open", text="login")`.

## Prerequisites

- Python 3.11+
- Official SDK: `mcp` (Python)

## Setup

All commands below are run **from the repository root**.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r 04-mcp/requirements.txt
export PYTHONPATH=.
```

## Run

From the repo root:

```bash
# Client spawns the server over stdio and calls a tool
PYTHONPATH=. python 04-mcp/client/demo.py
```

Docker, from the repo root:

```bash
docker compose -f 04-mcp/docker-compose.yml up
```

## Expected output

JSON with discovered tool names and a tool result containing open login-related issues.

## Smoke test

From the repo root:

```bash
PYTHONPATH=. pytest 04-mcp/tests -q -rA
```

Expected summary:

```text
...                                                                      [100%]
==================================== PASSES ====================================
PASSED 04-mcp/tests/test_mcp_smoke.py::test_tools_registered
PASSED 04-mcp/tests/test_mcp_smoke.py::test_search_tool_direct
PASSED 04-mcp/tests/test_mcp_smoke.py::test_stdio_client_roundtrip
=========================== short test summary info ============================
PASSED 04-mcp/tests/test_mcp_smoke.py::test_tools_registered
PASSED 04-mcp/tests/test_mcp_smoke.py::test_search_tool_direct
PASSED 04-mcp/tests/test_mcp_smoke.py::test_stdio_client_roundtrip
```

## Code walkthrough

1. `server/issue_tracker.py` — `MCPServer` from the official SDK; tools + `issues://open` resource + prompt.
2. `client/demo.py` — `stdio_client` + `ClientSession.initialize` → `list_tools` → `call_tool`.
3. Under the hood the server still uses `shared.issue_store` (an API-shaped data access layer).

## Next

**05-plugins** packages an MCP server config (plus skills/commands) into an installable bundle.
