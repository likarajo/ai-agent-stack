"""Tool definitions and executors. The model proposes; this code runs."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.issue_store import get_issue, search_issues  # noqa: E402

# Ollama / OpenAI-compatible tool schema (function calling).
TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_issues",
            "description": "Search the issue tracker by state and free-text query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "state": {
                        "type": "string",
                        "enum": ["open", "closed", "all"],
                        "description": "Issue state filter",
                    },
                    "text": {
                        "type": "string",
                        "description": "Text to match in title, body, or labels",
                    },
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_issue",
            "description": "Fetch one issue by numeric id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "issue_id": {"type": "integer", "description": "Issue id"},
                },
                "required": ["issue_id"],
            },
        },
    },
]


def run_search_issues(state: str = "open", text: str = "") -> dict[str, Any]:
    issues = search_issues(state=state, text=text)
    return {"count": len(issues), "issues": issues}


def run_get_issue(issue_id: int) -> dict[str, Any]:
    issue = get_issue(int(issue_id))
    if issue is None:
        return {"error": f"Issue {issue_id} not found"}
    return issue


EXECUTORS: dict[str, Callable[..., dict[str, Any]]] = {
    "search_issues": lambda **kw: run_search_issues(
        state=kw.get("state", "open"), text=kw.get("text", "")
    ),
    "get_issue": lambda **kw: run_get_issue(issue_id=int(kw["issue_id"])),
}


def execute_tool(name: str, arguments: dict[str, Any] | str) -> dict[str, Any]:
    if isinstance(arguments, str):
        arguments = json.loads(arguments) if arguments else {}
    if name not in EXECUTORS:
        return {"error": f"Unknown tool: {name}"}
    return EXECUTORS[name](**arguments)
