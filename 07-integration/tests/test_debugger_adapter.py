"""Debugger adapter + full-stack trace emission against a fake HTTP API."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[2]
MODULE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(MODULE))
sys.path.insert(0, str(ROOT / "05-plugins"))
sys.path.insert(0, str(ROOT / "06-skills"))
sys.path.insert(0, str(ROOT / "04-mcp"))
sys.path.insert(0, str(ROOT / "03-rag"))
sys.path.insert(0, str(ROOT / "02-tools"))

os.environ["SKIP_MODEL"] = "1"

from integration.pipeline import answer_question  # noqa: E402
from shared.debugger import DebuggerClient  # noqa: E402


class _FakeTransport(httpx.BaseTransport):
    """Minimal Agent Debugger API stand-in."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []
        self.run_id = "run-test-obs-1"
        self.paused = False

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST" and path == "/runs":
            return httpx.Response(
                200,
                json={"id": self.run_id, "status": "queued", "scenario": "ai_agent_stack_issue_triage"},
            )
        if request.method == "POST" and path.endswith("/events"):
            body = json.loads(request.content.decode())
            gated = body.get("type") == "tool.call" and body.get("tool") in {
                "email.send",
                "shell.exec",
                "file.delete",
            }
            if gated:
                self.paused = True
            event = {
                **body,
                "id": f"evt-{len(self.events) + 1}",
                "run_id": self.run_id,
                "ts": 1_700_000_000 + len(self.events),
                "gated": gated,
            }
            self.events.append(event)
            return httpx.Response(200, json=event)
        if request.method == "GET" and path.endswith("/wait-decision"):
            self.paused = False
            return httpx.Response(
                200, json={"decision": "approve", "tool": "email.send"}
            )
        if request.method == "POST" and path.endswith("/decision"):
            return httpx.Response(200, json={"type": "decision"})
        return httpx.Response(404, json={"detail": "not found"})


def test_debugger_emits_and_gates_email() -> None:
    transport = _FakeTransport()
    client = DebuggerClient(base_url="http://debugger.test")
    client._client = httpx.Client(transport=transport, base_url="http://debugger.test")
    try:
        run_id = client.start_run("test")
        assert run_id == "run-test-obs-1"
        client.think("planning")
        with client.step("rag.retrieve", message="retrieve", input_payload={"q": "login"}) as bag:
            bag["output"] = {"chunks": [{"source": "x.md", "score": 0.9}]}
        decision = client.tool_call(
            "email.send",
            message="send",
            payload={"to": "ops@northwind.example"},
        )
        assert decision["decision"] == "approve"
        client.final_answer("done")
        client.complete("done")
        types = [e["type"] for e in transport.events]
        assert types[0] == "run.started"
        assert "think" in types
        assert "tool.call" in types and "tool.result" in types
        assert "agent.answer" in types
        assert "run.completed" in types
    finally:
        client._client.close()


def test_full_answer_trace_posted_to_fake_debugger() -> None:
    transport = _FakeTransport()
    dbg = DebuggerClient(base_url="http://debugger.test", auto_approve_gated=True)
    dbg._client = httpx.Client(transport=transport, base_url="http://debugger.test")
    try:
        # Bypass __enter__ creating a real client; we already injected transport.
        result = answer_question(
            "How do we usually fix login timeouts?",
            send_email=False,
            dbg=dbg,
        )
        assert "timeout" in result["answer"].lower() or "login" in result["answer"].lower()
        assert result["run_id"] == "run-test-obs-1"
        types = [e["type"] for e in transport.events]
        assert "user.message" in types
        assert "agent.answer" in types
        assert "run.completed" in types

        tools = [e.get("tool") for e in transport.events if e.get("type") == "tool.call"]
        for required in (
            "plugin.load",
            "skill.select",
            "rag.retrieve",
            "mcp.search_issues_tool",
            "tools.search_issues",
            "api.get_issue",
            "llm.chat",
        ):
            assert required in tools

        # Inputs/outputs/timing on RAG
        rag_call = next(e for e in transport.events if e.get("tool") == "rag.retrieve" and e["type"] == "tool.call")
        rag_res = next(e for e in transport.events if e.get("tool") == "rag.retrieve" and e["type"] == "tool.result")
        assert "query" in (rag_call.get("payload") or {}).get("input", {})
        out = (rag_res.get("payload") or {}).get("output") or {}
        assert out.get("chunks")
        assert "duration_ms" in (rag_res.get("payload") or {})

        # MCP request/response shape
        mcp_call = next(
            e for e in transport.events if e.get("tool") == "mcp.search_issues_tool" and e["type"] == "tool.call"
        )
        assert "request" in (mcp_call.get("payload") or {}).get("input", {})

        # LLM prompt summary
        llm_call = next(e for e in transport.events if e.get("tool") == "llm.chat" and e["type"] == "tool.call")
        assert "prompt_summary" in (llm_call.get("payload") or {}).get("input", {})
        assert "model" in (llm_call.get("payload") or {}).get("input", {})
    finally:
        dbg._client.close()
