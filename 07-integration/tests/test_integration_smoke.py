"""Smoke tests for integration pipeline (no model, no debugger required)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(MODULE))
sys.path.insert(0, str(ROOT / "05-plugins"))
sys.path.insert(0, str(ROOT / "06-skills"))
sys.path.insert(0, str(ROOT / "04-mcp"))
sys.path.insert(0, str(ROOT / "03-rag"))

os.environ.pop("AGENT_DEBUGGER_URL", None)
os.environ["SKIP_MODEL"] = "1"

from integration.pipeline import build_report, run_pipeline  # noqa: E402
from shared.debugger import GATED_TOOLS, DebuggerClient  # noqa: E402


def test_gated_tools_match_debugger_policy() -> None:
    assert "email.send" in GATED_TOOLS


def test_build_report() -> None:
    report = build_report(
        [{"id": 101, "title": "Login hang", "labels": ["auth", "p1"]}],
        "runbook excerpt",
    )
    assert "#101" in report
    assert "p1" in report


def test_pipeline_standalone_no_email() -> None:
    out = run_pipeline(send_email=False)
    assert "Triage report" in out
    assert "issue-triage" in out
    assert "login" in out.lower()


def test_pipeline_standalone_with_simulated_email() -> None:
    out = run_pipeline(send_email=True)
    assert "Triage report" in out


def test_debugger_client_noop_without_url() -> None:
    with DebuggerClient(base_url=None) as dbg:
        assert not dbg.enabled
        assert dbg.start_run() is None
        result = dbg.tool_call("email.send", payload={"to": "a@b.c"})
        assert result.get("decision") == "approve"
        assert result.get("standalone") is True
