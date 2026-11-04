# 05 — Plugins

## What it is (plain English)

A **plugin** is a packaged extension for a specific application. In AI apps and IDEs it usually bundles several pieces into one install: MCP server configs, skills, slash commands, settings, and sometimes UI.

A plugin is about **packaging and distribution**, not a new way of communicating. Once installed, work still flows through tools, MCP, skills, and APIs.

## When to use it vs the others

| Reach for | When |
| --- | --- |
| MCP | Building the reusable connector |
| Skills | Writing the playbook |
| **Plugin (this module)** | Shipping MCP + skills + commands as one install |
| API / Tools | What actually runs after install |

Article decision guide: *Want other people to install your setup in one step? Ship a plugin.*

## Running example

The `northwind-issue-tracker` plugin manifest lists:
- an MCP server config pointing at `04-mcp/server/issue_tracker.py`
- the `issue-triage` skill
- slash commands `/issues-login` and `/triage-login`

## Prerequisites

- Python 3.11+

## Setup

All commands below are run **from the repository root**.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r 05-plugins/requirements.txt
export PYTHONPATH=.
```

## Run

From the repo root:

```bash
PYTHONPATH=. python 05-plugins/loader/install.py
```

Docker, from the repo root:

```bash
docker compose -f 05-plugins/docker-compose.yml up
```

## Expected output

```text
Installed plugin: Northwind Issue Tracker (northwind-issue-tracker@1.0.0)
MCP servers: northwind-issue-tracker
Skills: issue-triage
Commands: issues-login, triage-login
Key point: packaging only — runtime still uses MCP/tools/skills/APIs.

Wrote host config → .../05-plugins/.installed/northwind-issue-tracker.json
```

The installed host config resolves `python` to `sys.executable` and turns relative MCP script paths into absolute paths, so it works without PATH tweaks.

## Smoke test

From the repo root:

```bash
PYTHONPATH=. pytest 05-plugins/tests -q -rA
```

Expected summary:

```text
..                                                                       [100%]
==================================== PASSES ====================================
PASSED 05-plugins/tests/test_plugins_smoke.py::test_manifest_valid
PASSED 05-plugins/tests/test_plugins_smoke.py::test_install_writes_config
=========================== short test summary info ============================
PASSED 05-plugins/tests/test_plugins_smoke.py::test_manifest_valid
PASSED 05-plugins/tests/test_plugins_smoke.py::test_install_writes_config
```

## Code walkthrough

1. `plugin/northwind-issue-tracker/plugin.json` — the delivery box (manifest).
2. `loader/install.py` — validates the manifest and writes a resolved host config under `.installed/`.

## Next

**06-skills** shows progressive loading of a triage playbook.
