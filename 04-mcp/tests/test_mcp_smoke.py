"""Smoke tests for MCP server (no LLM)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "04-mcp"))

from server.issue_tracker import mcp, search_issues_tool  # noqa: E402


def test_tools_registered() -> None:
    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    assert "search_issues_tool" in names
    assert "get_issue_tool" in names


def test_search_tool_direct() -> None:
    result = search_issues_tool(state="open", text="login")
    assert result["count"] >= 1


def test_stdio_client_roundtrip() -> None:
    from client.demo import run_demo

    out = asyncio.run(run_demo())
    assert "search_issues_tool" in out["tools"]
    assert "login" in out["raw"].lower() or "101" in out["raw"]
