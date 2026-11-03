"""Smoke tests for tools module (no model required)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(MODULE))

from tools_demo.agent import scripted_tool_loop  # noqa: E402
from tools_demo.tools import TOOL_DEFINITIONS, execute_tool  # noqa: E402


def test_tool_schemas_present() -> None:
    names = {t["function"]["name"] for t in TOOL_DEFINITIONS}
    assert names == {"search_issues", "get_issue"}


def test_execute_search_issues() -> None:
    result = execute_tool("search_issues", {"state": "open", "text": "login"})
    assert result["count"] >= 1


def test_execute_get_issue() -> None:
    result = execute_tool("get_issue", {"issue_id": 101})
    assert result["id"] == 101


def test_unknown_tool() -> None:
    assert "error" in execute_tool("nope", {})


def test_scripted_loop() -> None:
    out = scripted_tool_loop("Which open issues mention login?")
    assert "login" in out.lower()
    assert "#" in out
