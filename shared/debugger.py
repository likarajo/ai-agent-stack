"""Optional Agent Debugger client (off by default).

When AGENT_DEBUGGER_URL is unset, all methods are no-ops and gated tools
run immediately (still simulated — nothing is really sent/deleted/executed).

Protocol mirrors https://github.com/likarajo/agent-debugger
(api/app/main.py, runs.py, policy.py, agent/worker.py):
  POST /runs
  POST /runs/{id}/events   types: run.started | think | tool.call | tool.result | run.completed | run.aborted
  GET  /runs/{id}/wait-decision  (blocks while status=paused on gated tools)
"""

from __future__ import annotations

import os
from typing import Any

import httpx

# Same policy set as agent-debugger/api/app/policy.py
GATED_TOOLS = frozenset({"email.send", "shell.exec", "file.delete"})


def debugger_url() -> str | None:
    raw = os.getenv("AGENT_DEBUGGER_URL", "").strip()
    return raw.rstrip("/") if raw else None


def debugger_enabled() -> bool:
    return debugger_url() is not None


class DebuggerClient:
    """Thin adapter over the Agent Debugger HTTP API."""

    def __init__(
        self,
        base_url: str | None = None,
        *,
        scenario: str = "ai_agent_stack_issue_triage",
        auto_approve_gated: bool = False,
    ) -> None:
        self.base_url = (base_url if base_url is not None else debugger_url())
        self.scenario = scenario
        # For automated tests: approve gated tools without a human UI.
        self.auto_approve_gated = auto_approve_gated or os.getenv(
            "AGENT_DEBUGGER_AUTO_APPROVE", ""
        ).lower() in {"1", "true", "yes"}
        self.run_id: str | None = None
        self._client: httpx.Client | None = None

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
        if not self.enabled or not self._client:
            return None
        resp = self._client.post("/runs", json={"scenario": self.scenario})
        resp.raise_for_status()
        self.run_id = resp.json()["id"]
        self.emit("run.started", message=message)
        return self.run_id

    def emit(
        self,
        event_type: str,
        *,
        message: str | None = None,
        tool: str | None = None,
        payload: Any = None,
    ) -> dict[str, Any]:
        if not self.enabled or not self._client or not self.run_id:
            return {"gated": False, "skipped": True}
        body = {
            "type": event_type,
            "message": message,
            "tool": tool,
            "payload": payload,
        }
        resp = self._client.post(f"/runs/{self.run_id}/events", json=body)
        resp.raise_for_status()
        return resp.json()

    def think(self, message: str) -> None:
        self.emit("think", message=message)

    def tool_call(
        self,
        tool: str,
        *,
        message: str | None = None,
        payload: Any = None,
    ) -> dict[str, Any]:
        """Emit tool.call; if gated and debugger is on, block for a decision."""
        if not self.enabled:
            # Standalone: gated tools are still simulated locally.
            return {"gated": tool in GATED_TOOLS, "decision": "approve", "standalone": True}

        result = self.emit(
            "tool.call",
            tool=tool,
            message=message or f"Calling {tool}",
            payload=payload,
        )
        if not result.get("gated") and tool not in GATED_TOOLS:
            return result

        if self.auto_approve_gated and self.run_id and self._client:
            # Test helper: submit approve ourselves so CI can exercise the path.
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
    ) -> None:
        # Debugger already writes tool.result on approve for gated tools;
        # still emit for non-gated so the timeline stays complete.
        if tool in GATED_TOOLS and self.enabled:
            return
        self.emit("tool.result", tool=tool, message=message, payload=payload)

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

    def complete(self, message: str = "Run completed") -> None:
        self.emit("run.completed", message=message)

    def abort(self, message: str = "Run aborted") -> None:
        self.emit("run.aborted", message=message)


def noop_client() -> DebuggerClient:
    return DebuggerClient(base_url=None)
