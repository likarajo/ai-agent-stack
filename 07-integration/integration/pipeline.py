"""End-to-end agentic pipeline across every concept in the article.

Flow (same Northwind issue-tracker domain):
  1. Plugin load
  2. Skill selection (progressive)
  3. RAG retrieval (runbook context)
  4. MCP tool call (search issues)
  5. Plain tool/API-shaped call (get issue detail)
  6. Optional gated email.send (Agent Debugger pause when enabled)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MODULE = Path(__file__).resolve().parents[1]
for path in (
    ROOT,
    MODULE,
    ROOT / "05-plugins",
    ROOT / "06-skills",
    ROOT / "03-rag",
    ROOT / "04-mcp",
):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from shared.debugger import DebuggerClient, debugger_enabled  # noqa: E402
from shared.issue_store import get_issue, search_issues  # noqa: E402

from integration.gated_actions import simulate_email_send  # noqa: E402


def _load_plugin(dbg: DebuggerClient) -> dict[str, Any]:
    from loader.install import DEFAULT_PLUGIN, install_plugin

    dbg.think("Loading Northwind Issue Tracker plugin manifest")
    target = install_plugin(DEFAULT_PLUGIN)
    data = json.loads(target.read_text(encoding="utf-8"))
    dbg.emit(
        "tool.call",
        tool="plugin.install",
        message=f"Installed plugin {data['name']}@{data['version']}",
        payload={"path": str(target), "commands": [c["name"] for c in data["commands"]]},
    )
    dbg.tool_result(
        "plugin.install",
        message="Plugin host config written",
        payload={"name": data["name"]},
    )
    return data


def _select_skill(dbg: DebuggerClient, task: str):
    from agent.loader import catalog, load_full, select_skill

    skills_dir = ROOT / "06-skills" / "skills"
    metas = catalog(skills_dir)
    dbg.emit(
        "think",
        message=f"Skill catalog ({len(metas)}): "
        + ", ".join(f"{m.name}" for m in metas),
    )
    chosen = select_skill(metas, task)
    if chosen is None:
        raise RuntimeError("No skill matched the task")
    skill = load_full(chosen)
    dbg.emit(
        "tool.call",
        tool="skill.load",
        message=f"Loading full skill '{skill.meta.name}'",
        payload={"description": skill.meta.description},
    )
    dbg.tool_result("skill.load", message="Skill body loaded", payload={"chars": len(skill.body)})
    return skill


def _rag(dbg: DebuggerClient, question: str) -> str:
    import importlib.util

    # Load 03-rag by file path so it does not collide with integration package.
    # Prefer normal import when 03-rag is on sys.path.
    try:
        from rag_demo.index import build_index  # type: ignore
    except ImportError:
        index_path = ROOT / "03-rag" / "rag_demo" / "index.py"
        spec = importlib.util.spec_from_file_location("rag_index_mod", index_path)
        if spec is None or spec.loader is None:
            raise RuntimeError("Unable to load RAG index module")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
        build_index = mod.build_index
    index = build_index()
    hits = index.search(question, k=2)
    dbg.emit(
        "tool.call",
        tool="rag.retrieve",
        message=f"Retrieving docs for: {question}",
        payload={"k": 2},
    )
    passages = [
        {"source": c.source, "score": score, "text": c.text[:240]} for c, score in hits
    ]
    dbg.tool_result(
        "rag.retrieve",
        message=f"{len(passages)} chunks",
        payload={"passages": passages},
    )
    return "\n\n".join(f"[{p['source']}] {p['text']}" for p in passages)


def _mcp_search(dbg: DebuggerClient, text: str = "login") -> dict[str, Any]:
    """Prefer in-process MCP tool function; still labels the step as MCP."""
    from server.issue_tracker import search_issues_tool

    dbg.emit(
        "tool.call",
        tool="mcp.search_issues_tool",
        message="MCP tools/call search_issues_tool",
        payload={"state": "open", "text": text},
    )
    result = search_issues_tool(state="open", text=text)
    dbg.tool_result(
        "mcp.search_issues_tool",
        message=f"MCP returned {result.get('count')} issues",
        payload={"count": result.get("count")},
    )
    return result


def _api_get_issue(dbg: DebuggerClient, issue_id: int) -> dict[str, Any]:
    dbg.emit(
        "tool.call",
        tool="api.get_issue",
        message=f"Plain API-shaped call get_issue({issue_id})",
        payload={"issue_id": issue_id},
    )
    issue = get_issue(issue_id) or {"error": "missing"}
    dbg.tool_result("api.get_issue", message=f"Got issue {issue_id}", payload={"title": issue.get("title")})
    return issue


def _maybe_email_summary(
    dbg: DebuggerClient,
    report: str,
    *,
    send_email: bool,
) -> dict[str, Any] | None:
    if not send_email:
        return None
    payload = {
        "to": "ops@northwind.example",
        "subject": "Login issue triage summary",
        "body": report,
    }
    decision = dbg.tool_call(
        "email.send",
        message="About to send triage summary email (simulated)",
        payload=payload,
    )
    if decision.get("decision") == "deny":
        dbg.abort("Human denied email.send — stopping before send")
        return {"ok": False, "denied": True}
    # On approve via debugger, API already recorded tool.result for gated tools.
    result = simulate_email_send(payload)
    if not debugger_enabled():
        dbg.tool_result("email.send", message="Simulated send (standalone)", payload=result)
    return result


def build_report(issues: list[dict[str, Any]], context: str) -> str:
    lines = [
        "# Triage report",
        "- Scope: open issues matching 'login'",
        "- Matches:",
    ]
    overall = "p3"
    for issue in issues:
        labels = issue.get("labels") or []
        severity = next((l for l in labels if l.startswith("p")), "p?")
        if severity == "p1":
            overall = "p1"
        elif severity == "p2" and overall != "p1":
            overall = "p2"
        lines.append(
            f"  - #{issue['id']} {issue['title']} [{', '.join(labels)}] → severity {severity}"
        )
    lines.append(f"- Severity call: {overall}")
    lines.append(
        "- Next step: Confirm auth token-refresh latency; link login-timeout runbook."
    )
    lines.append("\n## RAG context (excerpt)")
    lines.append(context[:800])
    return "\n".join(lines)


def run_pipeline(
    task: str = "Triage the open login issues.",
    *,
    send_email: bool = True,
    dbg: DebuggerClient | None = None,
) -> str:
    owns_client = dbg is None
    dbg = dbg or DebuggerClient()
    if owns_client:
        dbg.__enter__()
    try:
        if dbg.enabled:
            dbg.start_run(message="ai-agent-stack integration pipeline")
        else:
            # Standalone timeline printed to stdout only
            pass

        plugin = _load_plugin(dbg)
        skill = _select_skill(dbg, task)
        context = _rag(dbg, "How do we usually fix login timeouts?")
        mcp_result = _mcp_search(dbg, text="login")
        issues = mcp_result.get("issues") or []
        detail = _api_get_issue(dbg, int(issues[0]["id"])) if issues else {}
        report = build_report(issues, context)
        report += f"\n\n## Skill used\n{skill.meta.name} — via plugin {plugin['name']}"
        if detail:
            report += f"\n\n## Sample detail\n#{detail.get('id')} {detail.get('title')}"

        email_result = _maybe_email_summary(dbg, report, send_email=send_email)
        if email_result and email_result.get("denied"):
            return report + "\n\n(email.send denied by debugger)"

        if dbg.enabled and dbg.run_id:
            # Only complete if not already aborted
            dbg.complete("Integration pipeline finished")
        return report
    finally:
        if owns_client:
            dbg.__exit__(None, None, None)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Full ai-agent-stack integration demo")
    parser.add_argument("--task", default="Triage the open login issues.")
    parser.add_argument(
        "--no-email",
        action="store_true",
        help="Skip the gated email.send demo step",
    )
    args = parser.parse_args()
    print(run_pipeline(args.task, send_email=not args.no_email))
    if debugger_enabled():
        print("\n[debugger] Timeline streamed to Agent Debugger UI (see AGENT_DEBUGGER_URL).")
    else:
        print("\n[standalone] Set AGENT_DEBUGGER_URL to emit a live debugger timeline.")


if __name__ == "__main__":
    main()
