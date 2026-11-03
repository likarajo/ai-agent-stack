# 06 — Skills

## What it is (plain English)

**Skills** are reusable instruction packages — usually a folder with a `SKILL.md`: a short name and description at the top, then step-by-step instructions, rules, templates, and sometimes helpers.

**Progressive loading:** at startup the agent sees only each skill’s name and one-line description. It loads the full instructions only when a task matches, keeping the context window small.

Tools give an agent hands. Skills give it a playbook.

## When to use it vs the others

| Reach for | When |
| --- | --- |
| Tools / MCP | The agent can already *do* things |
| **Skills (this module)** | It needs to do them *your* way (conventions, checklists, format) |
| Plugin | Shipping skills together with MCP configs |
| RAG | Looking up facts from docs (skills teach procedure) |

Article decision guide: *Keep explaining the same procedure to your agent? Write a skill.*

## Running example

Task: **“Triage the open login issues.”**  
The agent matches `issue-triage`, loads `SKILL.md` in full, searches open login issues, and prints a triage report in the team template.

## Prerequisites

- Python 3.11+

## Setup

```bash
cd 06-skills
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH=06-skills:.
```

## Run

```bash
PYTHONPATH=06-skills:. python 06-skills/agent/run.py
```

Docker:

```bash
cd 06-skills && docker compose up
```

## Expected output

A skill catalog, then a selected `issue-triage` skill, then a `# Triage report` listing open login issues with severity calls.

## Smoke test

```bash
PYTHONPATH=06-skills:. pytest 06-skills/tests -q
```

## Code walkthrough

1. `skills/issue-triage/SKILL.md` — front matter (name/description) + full playbook.
2. `agent/loader.py` — `catalog` → `select_skill` → `load_full`.
3. `agent/run.py` — follows the skill steps using `shared.issue_store`.

## Next

**07-integration** wires APIs, tools, RAG, MCP, plugins, and skills into one agentic demo (optional Agent Debugger timeline).
