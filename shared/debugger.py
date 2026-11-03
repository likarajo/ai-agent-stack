"""Optional Agent Debugger client (off by default).

When AGENT_DEBUGGER_URL is unset, methods record a local in-memory timeline
(for tests/CLI) and gated tools run immediately (still simulated).

Protocol mirrors https://github.com/likarajo/agent-debugger
(api/app/main.py, runs.py, policy.py, agent/worker.py):
  POST /runs
  POST /runs/{id}/events
  GET  /runs/{id}/wait-decision
"""

from __future__ import annotations

import os
import time
import uuid
from contextlib import contextmanager
from typing import Any, Iterator

import httpx

# Same policy set as agent-debugger/api/app/policy.py
GATED_TOOLS = frozenset({"email.send", "shell.exec", "file.delete"})


def debugger_url() -> str | None:
    raw = os.getenv("AGENT_DEBUGGER_URL", "").strip()
    return raw.rstrip("/") if raw else None


def debugger_enabled() -> bool:
    return debugger_url() is not None


class DebuggerClient:
    """Thin adapter over the Agent Debugger HTTP API + local trace buffer."""

    def __init__(
        self,
        base_url: str | None = None,
        *,
        scenario: str = "ai_agent_stack_issue_triage",
        auto_approve_gated: bool = False,
    ) -> None:
        self.base_url = base_url if base_url is not None else debugger_url()
        self.scenario = scenario
        self.auto_approve_gated = auto_approve_gated or os.getenv(
            "AGENT_DEBUGGER_AUTO_APPROVE", ""
        ).lower() in {"1", "true", "yes"}
        self.run_id: str | None = None
        self._client: httpx.Client | None = None
        self.local_events: list[dict[str, Any]] = []

    @property
    def enabled(self) -> bool:
        return bool(self.base_url)

    def __enter__(self) -> "DebuggerClient":
        if self.enabled:
            self._client = httpx.Client(base_url=self.base_url, timeout=30.0)
        return self

    def __exit__(self, *exc: object) -> None:
        if self._client:
            self._client.close()
            self._client = None

    def start_run(self, message: str = "Integration agent started") -> str | None:
        if self.enabled and self._client:
            resp = self._client.post("/runs", json={"scenario": self.scenario})
            resp.raise_for_status()
            self.run_id = resp.json()["id"]
        else:
            self.run_id = f"local-{uuid.uuid4().hex[:8]}"
        self.emit("run.started", message=message, payload={"scenario": self.scenario})
        return self.run_id

    def emit(
        self,
        event_type: str,
        *,
        message: str | None = None,
        tool: str | None = None,
        payload: Any = None,
    ) -> dict[str, Any]:
        body = {
            "type": event_type,
            "message": message,
            "tool": tool,
            "payload": payload,
        }
        recorded = {
            **body,
            "id": str(uuid.uuid4()),
            "run_id": self.run_id,
            "ts": time.time(),
            "gated": False,
        }
        if not self.enabled or not self._client or not self.run_id:
            self.local_events.append(recorded)
            return recorded

        resp = self._client.post(f"/runs/{self.run_id}/events", json=body)
        resp.raise_for_status()
        remote = resp.json()
        self.local_events.append(remote)
        return remote

    def think(self, message: str, payload: Any = None) -> dict[str, Any]:
        return self.emit("think", message=message, payload=payload)

    def user_message(self, text: str) -> dict[str, Any]:
        return self.emit(
            "user.message",
            message=text,
            payload={"role": "user", "content": text},
        )

    def final_answer(self, text: str, *, duration_ms: float | None = None) -> dict[str, Any]:
        return self.emit(
            "agent.answer",
            message="Final answer ready",
            payload={"content": text, "duration_ms": duration_ms},
        )

    @contextmanager
    def step(
        self,
        tool: str,
        *,
        message: str,
        input_payload: Any = None,
        phase: str | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Emit timed tool.call → (yield bag) → tool.result with duration_ms."""
        started = time.perf_counter()
        call_payload = {
            "phase": phase or tool,
            "input": input_payload,
            "started_at": time.time(),
        }
        call = self.emit(
            "tool.call",
            tool=tool,
            message=message,
            payload=call_payload,
        )
        bag: dict[str, Any] = {"call": call, "output": None, "message": None}
        try:
            yield bag
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            # Gated tools: debugger API already records tool.result on approve.
            if tool in GATED_TOOLS and self.enabled and not bag.get("force_result"):
                bag["duration_ms"] = duration_ms
            else:
                result_payload = {
                    "phase": phase or tool,
                    "input": input_payload,
                    "output": bag.get("output"),
                    "duration_ms": duration_ms,
                }
                self.emit(
                    "tool.result",
                    tool=tool,
                    message=bag.get("message") or f"{tool} completed in {duration_ms}ms",
                    payload=result_payload,
                )
                bag["duration_ms"] = duration_ms

    def tool_call(
        self,
        tool: str,
        *,
        message: str | None = None,
        payload: Any = None,
    ) -> dict[str, Any]:
        """Emit tool.call; if gated and debugger is on, block for a decision."""
        if not self.enabled:
            event = self.emit(
                "tool.call",
                tool=tool,
                message=message or f"Calling {tool}",
                payload=payload,
            )
            return {
                "gated": tool in GATED_TOOLS,
                "decision": "approve",
                "standalone": True,
                "event": event,
            }

        result = self.emit(
            "tool.call",
            tool=tool,
            message=message or f"Calling {tool}",
            payload=payload,
        )
        if not result.get("gated") and tool not in GATED_TOOLS:
            return result

        if self.auto_approve_gated and self.run_id and self._client:
            dec = self._client.post(
                f"/runs/{self.run_id}/decision",
                json={"decision": "approve", "note": "auto-approve for smoke test"},
            )
            dec.raise_for_status()
            return {"gated": True, "decision": "approve", "auto": True}

        decision = self.wait_decision()
        return {"gated": True, "decision": decision.get("decision"), "raw": decision}

    def tool_result(
        self,
        tool: str,
        *,
        message: str | None = None,
        payload: Any = None,
    ) -> dict[str, Any]:
        if tool in GATED_TOOLS and self.enabled:
            return {"skipped": True}
        return self.emit("tool.result", tool=tool, message=message, payload=payload)

    def wait_decision(self, timeout: int = 600) -> dict[str, Any]:
        if not self.enabled or not self._client or not self.run_id:
            return {"decision": "approve"}
        resp = self._client.get(
            f"/runs/{self.run_id}/wait-decision",
            params={"timeout": timeout},
            timeout=float(timeout) + 10.0,
        )
        resp.raise_for_status()
        return resp.json()

    def complete(self, message: str = "Run completed") -> dict[str, Any]:
        return self.emit("run.completed", message=message)

    def abort(self, message: str = "Run aborted") -> dict[str, Any]:
        return self.emit("run.aborted", message=message)

    def event_types(self) -> list[str]:
        return [e.get("type") for e in self.local_events if e.get("type")]

    def tools_seen(self) -> list[str]:
        return [e.get("tool") for e in self.local_events if e.get("tool")]


def noop_client() -> DebuggerClient:
    return DebuggerClient(base_url=None)
