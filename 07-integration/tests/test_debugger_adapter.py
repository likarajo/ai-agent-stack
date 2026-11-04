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

    def __init__(self, *, decision: str = "approve") -> None:
        self.events: list[dict[str, Any]] = []
        self.run_id = "run-test-obs-1"
        self.paused = False
        self.status = "created"
        self.decision = decision
        self.event_posts_after_abort = 0

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST" and path == "/runs":
            body = json.loads(request.content.decode()) if request.content else {}
            assert body.get("enqueue") is False
            self.status = "created"
            return httpx.Response(
                200,
                json={
                    "id": self.run_id,
                    "status": "created",
                    "scenario": body.get("scenario") or "ai_agent_stack_issue_triage",
                },
            )
        if request.method == "POST" and path.endswith("/events"):
            if self.status in {"completed", "aborted"}:
                self.event_posts_after_abort += 1
                return httpx.Response(
                    400, json={"detail": f"run already {self.status}"}
                )
            body = json.loads(request.content.decode())
            gated = body.get("type") == "tool.call" and body.get("tool") in {
                "email.send",
                "shell.exec",
                "file.delete",
            }
            if gated:
                self.paused = True
                self.status = "paused"
            elif body.get("type") == "run.started":
                self.status = "running"
            elif body.get("type") == "run.completed":
                self.status = "completed"
            elif body.get("type") == "run.aborted":
                self.status = "aborted"
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
            # Mirror agent-debugger: Deny aborts the run server-side (200 on
            # /decision); waiters then see the decision payload.
            self.paused = False
            if self.decision == "deny":
                self.status = "aborted"
                self.events.append(
                    {
                        "type": "decision",
                        "message": "Human denied email.send",
                        "tool": "email.send",
                        "payload": {"decision": "deny", "tool": "email.send"},
                        "id": f"evt-{len(self.events) + 1}",
                        "run_id": self.run_id,
                        "ts": 1_700_000_000 + len(self.events),
                    }
                )
                self.events.append(
                    {
                        "type": "run.aborted",
                        "message": "Run aborted after deny — email was not sent",
                        "tool": None,
                        "payload": None,
                        "id": f"evt-{len(self.events) + 1}",
                        "run_id": self.run_id,
                        "ts": 1_700_000_000 + len(self.events),
                    }
                )
            else:
                self.status = "running"
            return httpx.Response(
                200, json={"decision": self.decision, "tool": "email.send"}
            )
        if request.method == "POST" and path.endswith("/decision"):
            body = json.loads(request.content.decode())
            self.decision = body.get("decision", self.decision)
            if self.decision == "deny":
                self.status = "aborted"
            else:
                self.status = "running"
            return httpx.Response(200, json={"type": "decision", "decision": self.decision})
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


def test_deny_path_ends_cleanly_without_posting_after_abort() -> None:
    """Deny returns 200 and aborts remotely; client must not 400 on follow-ups."""
    transport = _FakeTransport(decision="deny")
    dbg = DebuggerClient(base_url="http://debugger.test")
    dbg._client = httpx.Client(transport=transport, base_url="http://debugger.test")
    try:
        result = answer_question(
            "Triage the open login issues and email ops",
            send_email=True,
            dbg=dbg,
        )
        assert result["denied_email"] is True
        assert "email.send denied" in result["answer"]
        assert dbg.remote_closed is True

        # Remote timeline: tool.call for email, then server-side decision + abort.
        remote_types = [e["type"] for e in transport.events]
        assert "tool.call" in remote_types
        assert "decision" in remote_types
        assert "run.aborted" in remote_types
        # Critically: no further successful remote event posts after abort,
        # and the client must not have raised on HTTP 400.
        assert transport.event_posts_after_abort == 0

        # Local audit still records the denied tool call + closing notes.
        local_denied = [
            e
            for e in dbg.local_events
            if e.get("type") == "tool.result"
            and e.get("tool") == "email.send"
            and (e.get("payload") or {}).get("denied")
        ]
        assert local_denied, "expected local denied tool.result in audit trail"
        assert any(e.get("type") == "agent.answer" for e in dbg.local_events)
        # agent.answer after deny is local-only (remote already aborted).
        answer_ev = next(e for e in dbg.local_events if e.get("type") == "agent.answer")
        assert answer_ev.get("local_only") is True
    finally:
        dbg._client.close()


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
