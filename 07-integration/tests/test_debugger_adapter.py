"""Debugger adapter tests with a fake HTTP API (no live Agent Debugger)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from shared.debugger import DebuggerClient  # noqa: E402


class _FakeTransport(httpx.BaseTransport):
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []
        self.run_id = "run-test-1"
        self.paused = False

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST" and path == "/runs":
            return httpx.Response(200, json={"id": self.run_id, "status": "queued"})
        if request.method == "POST" and path.endswith("/events"):
            body = json.loads(request.content.decode())
            self.events.append(body)
            gated = body.get("type") == "tool.call" and body.get("tool") == "email.send"
            if gated:
                self.paused = True
            return httpx.Response(
                200,
                json={**body, "gated": gated, "id": f"evt-{len(self.events)}"},
            )
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
        assert run_id == "run-test-1"
        client.think("planning")
        client.emit("tool.call", tool="rag.retrieve", message="retrieve")
        decision = client.tool_call(
            "email.send",
            message="send",
            payload={"to": "ops@northwind.example"},
        )
        assert decision["decision"] == "approve"
        client.complete("done")
        types = [e["type"] for e in transport.events]
        assert "run.started" in types
        assert "think" in types
        assert types.count("tool.call") >= 2
        assert "run.completed" in types
    finally:
        client._client.close()
