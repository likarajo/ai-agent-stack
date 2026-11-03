"""Smoke test for the observability web chat API (no model / no debugger)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
MODULE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(MODULE))
sys.path.insert(0, str(ROOT / "05-plugins"))
sys.path.insert(0, str(ROOT / "06-skills"))
sys.path.insert(0, str(ROOT / "04-mcp"))
sys.path.insert(0, str(ROOT / "03-rag"))
sys.path.insert(0, str(ROOT / "02-tools"))

os.environ.pop("AGENT_DEBUGGER_URL", None)
os.environ["SKIP_MODEL"] = "1"

from integration.chat_app import app  # noqa: E402

client = TestClient(app)


def test_health_and_demo_questions() -> None:
    assert client.get("/health").json()["ok"] is True
    qs = client.get("/api/demo-questions").json()["questions"]
    assert len(qs) >= 2


def test_chat_returns_answer_and_events() -> None:
    resp = client.post("/api/chat", json={"message": "Which open issues mention login?"})
    assert resp.status_code == 200
    body = resp.json()
    assert "login" in body["answer"].lower() or "#" in body["answer"]
    assert body["events"]
    types = [e["type"] for e in body["events"]]
    assert "user.message" in types
    assert "agent.answer" in types
    tools = [e.get("tool") for e in body["events"] if e.get("type") == "tool.call"]
    assert "rag.retrieve" in tools
    assert "mcp.search_issues_tool" in tools


def test_index_html() -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    assert "observability chat" in resp.text.lower()
