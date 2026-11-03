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
sys.path.insert(0, str(ROOT / "02-tools"))

os.environ.pop("AGENT_DEBUGGER_URL", None)
os.environ["SKIP_MODEL"] = "1"

from integration.pipeline import (  # noqa: E402
    DEMO_QUESTIONS,
    answer_question,
    build_report,
    run_pipeline,
)
from shared.debugger import GATED_TOOLS, DebuggerClient  # noqa: E402


def test_gated_tools_match_debugger_policy() -> None:
    assert "email.send" in GATED_TOOLS


def test_demo_questions_cover_stack_narration() -> None:
    assert len(DEMO_QUESTIONS) >= 2
    texts = " ".join(q["text"].lower() for q in DEMO_QUESTIONS)
    assert "login" in texts
    assert "triage" in texts or "timeout" in texts


def test_build_report() -> None:
    report = build_report(
        [{"id": 101, "title": "Login hang", "labels": ["auth", "p1"]}],
        "runbook excerpt",
    )
    assert "#101" in report
    assert "p1" in report


def test_pipeline_standalone_no_email() -> None:
    out = run_pipeline(send_email=False)
    assert "Triage report" in out or "login" in out.lower()
    assert "issue-triage" in out or "skill=" in out


def test_answer_emits_ordered_local_trace() -> None:
    with DebuggerClient(base_url=None) as dbg:
        result = answer_question(
            "Which open issues mention login?",
            send_email=False,
            dbg=dbg,
        )
    assert result["answer"]
    assert "plugins" in result["concepts"]
    types = dbg.event_types()
    # Critical observability markers in order
    assert types[0] == "run.started"
    assert "user.message" in types
    assert "agent.answer" in types
    assert "run.completed" in types
    assert types.index("user.message") < types.index("agent.answer")

    tools = dbg.tools_seen()
    for required in (
        "plugin.load",
        "skill.select",
        "rag.retrieve",
        "mcp.search_issues_tool",
        "tools.search_issues",
        "api.get_issue",
        "llm.chat",
    ):
        assert required in tools, f"missing {required} in {tools}"

    # Timing present on tool results
    results = [e for e in dbg.local_events if e.get("type") == "tool.result"]
    assert results
    assert all(
        isinstance((e.get("payload") or {}).get("duration_ms"), (int, float))
        for e in results
    )

    # RAG payload includes scored chunks
    rag = next(
        e
        for e in dbg.local_events
        if e.get("type") == "tool.result" and e.get("tool") == "rag.retrieve"
    )
    chunks = (rag.get("payload") or {}).get("output", {}).get("chunks") or []
    assert chunks
    assert "source" in chunks[0] and "score" in chunks[0]


def test_debugger_client_noop_without_url() -> None:
    with DebuggerClient(base_url=None) as dbg:
        assert not dbg.enabled
        assert dbg.start_run() is not None
        result = dbg.tool_call("email.send", payload={"to": "a@b.c"})
        assert result.get("decision") == "approve"
        assert result.get("standalone") is True
