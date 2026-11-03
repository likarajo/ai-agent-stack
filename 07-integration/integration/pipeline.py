"""Observability-first integration pipeline.

Every chat question exercises the six article concepts in order and emits a
timed debugger timeline (when AGENT_DEBUGGER_URL is set, or a local buffer):

  user.message → plugin → skill → RAG → MCP → tools → API → LLM → agent.answer
  (+ optional gated email.send when the user asks to notify/email)
"""

from __future__ import annotations

import json
import re
import sys
import time
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
    ROOT / "02-tools",
):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from shared.config import SETTINGS  # noqa: E402
from shared.debugger import DebuggerClient, debugger_enabled  # noqa: E402
from shared.issue_store import get_issue  # noqa: E402
from shared.llm import ModelUnavailable, chat, model_available  # noqa: E402

from integration.gated_actions import simulate_email_send  # noqa: E402

# Suggested demo questions — together they exercise all six concepts.
DEMO_QUESTIONS = [
    {
        "id": "q1-login-issues",
        "text": "Which open issues mention login?",
        "focus": "MCP + tools + API for live issue data (plugin/skill/RAG still run)",
    },
    {
        "id": "q2-login-timeouts",
        "text": "How do we usually fix login timeouts?",
        "focus": "RAG runbook grounding + related open issues via MCP/API",
    },
    {
        "id": "q3-triage",
        "text": "Triage the open login issues.",
        "focus": "Skills playbook + full stack; optional notify via gated email.send",
    },
]


def _wants_email(question: str) -> bool:
    q = question.lower()
    return any(w in q for w in ("email", "notify", "send summary", "mail ops"))


def _rag_query_for(question: str) -> str:
    q = question.lower()
    if "timeout" in q or "fix" in q or "usually" in q:
        return "How do we usually fix login timeouts?"
    if "triage" in q or "severity" in q:
        return "issue triage conventions severity labels auth"
    return "login authentication session cookie issues"


def _search_text_for(question: str) -> str:
    q = question.lower()
    if "billing" in q:
        return "billing"
    if "login" in q or "auth" in q or "triage" in q or "timeout" in q:
        return "login"
    # fallback: first meaningful token
    tokens = re.findall(r"[a-z0-9]{3,}", q)
    return tokens[0] if tokens else "login"


def _load_plugin(dbg: DebuggerClient) -> dict[str, Any]:
    from loader.install import DEFAULT_PLUGIN, install_plugin

    with dbg.step(
        "plugin.load",
        message="Loading Northwind Issue Tracker plugin",
        input_payload={"manifest": str(DEFAULT_PLUGIN)},
        phase="plugins",
    ) as bag:
        target = install_plugin(DEFAULT_PLUGIN)
        data = json.loads(target.read_text(encoding="utf-8"))
        bag["output"] = {
            "name": data["name"],
            "version": data["version"],
            "mcp_servers": [s["name"] for s in data["mcp_servers"]],
            "skills": [Path(s).name for s in data["skills"]],
            "commands": [c["name"] for c in data["commands"]],
            "installed_path": str(target),
        }
        bag["message"] = f"Plugin {data['name']}@{data['version']} installed"
        return data


def _select_skill(dbg: DebuggerClient, task: str):
    from agent.loader import catalog, load_full, select_skill

    skills_dir = ROOT / "06-skills" / "skills"
    with dbg.step(
        "skill.select",
        message="Selecting skill from catalog (progressive load)",
        input_payload={"task": task},
        phase="skills",
    ) as bag:
        metas = catalog(skills_dir)
        catalog_view = [{"name": m.name, "description": m.description} for m in metas]
        chosen = select_skill(metas, task) or (metas[0] if metas else None)
        if chosen is None:
            raise RuntimeError("No skills available")
        skill = load_full(chosen)
        bag["output"] = {
            "catalog": catalog_view,
            "selected": skill.meta.name,
            "description": skill.meta.description,
            "body_chars": len(skill.body),
            "body_preview": skill.body[:280],
        }
        bag["message"] = f"Loaded skill '{skill.meta.name}'"
        return skill


def _rag(dbg: DebuggerClient, query: str, k: int = 3) -> dict[str, Any]:
    try:
        from rag_demo.index import build_index  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("RAG module not importable") from exc

    with dbg.step(
        "rag.retrieve",
        message=f"RAG retrieve k={k}",
        input_payload={"query": query, "k": k},
        phase="rag",
    ) as bag:
        started = time.perf_counter()
        index = build_index()
        hits = index.search(query, k=k)
        passages = [
            {
                "source": c.source,
                "score": round(float(score), 4),
                "text": c.text[:400],
            }
            for c, score in hits
        ]
        context = "\n\n".join(f"[{p['source']} | {p['score']}] {p['text']}" for p in passages)
        bag["output"] = {
            "query": query,
            "k": k,
            "chunk_count": len(passages),
            "chunks": passages,
            "index_build_ms": round((time.perf_counter() - started) * 1000, 2),
        }
        bag["message"] = f"Retrieved {len(passages)} chunks"
        return {"context": context, "passages": passages, "query": query}


def _mcp_search(dbg: DebuggerClient, text: str, state: str = "open") -> dict[str, Any]:
    from server.issue_tracker import search_issues_tool

    request = {"state": state, "text": text}
    with dbg.step(
        "mcp.search_issues_tool",
        message="MCP tools/call search_issues_tool",
        input_payload={"server": "northwind-issue-tracker", "request": request},
        phase="mcp",
    ) as bag:
        result = search_issues_tool(state=state, text=text)
        bag["output"] = {
            "response": {
                "count": result.get("count"),
                "issue_ids": [i.get("id") for i in result.get("issues", [])],
                "titles": [i.get("title") for i in result.get("issues", [])],
            },
            "raw_count": result.get("count"),
        }
        bag["message"] = f"MCP returned {result.get('count')} issues"
        return result


def _tools_search(dbg: DebuggerClient, text: str, state: str = "open") -> dict[str, Any]:
    """Plain in-app function calling (tools module) — distinct from MCP."""
    from tools_demo.tools import TOOL_DEFINITIONS, execute_tool

    args = {"state": state, "text": text}
    with dbg.step(
        "tools.search_issues",
        message="Function-calling tool search_issues",
        input_payload={
            "tool_schema": next(
                t for t in TOOL_DEFINITIONS if t["function"]["name"] == "search_issues"
            ),
            "arguments": args,
        },
        phase="tools",
    ) as bag:
        result = execute_tool("search_issues", args)
        bag["output"] = {
            "count": result.get("count"),
            "issue_ids": [i.get("id") for i in result.get("issues", [])],
        }
        bag["message"] = f"Tool returned {result.get('count')} issues"
        return result


def _api_get_issue(dbg: DebuggerClient, issue_id: int) -> dict[str, Any]:
    """Deterministic API-shaped call (shared store = same contract as 01-apis)."""
    with dbg.step(
        "api.get_issue",
        message=f"API GET /issues/{issue_id}",
        input_payload={"method": "GET", "path": f"/issues/{issue_id}"},
        phase="apis",
    ) as bag:
        issue = get_issue(issue_id) or {"error": "missing", "id": issue_id}
        bag["output"] = {
            "status": 200 if "error" not in issue else 404,
            "body": {
                "id": issue.get("id"),
                "title": issue.get("title"),
                "state": issue.get("state"),
                "labels": issue.get("labels"),
                "assignee": issue.get("assignee"),
            },
        }
        bag["message"] = f"API returned issue {issue_id}"
        return issue


def _llm_compose(
    dbg: DebuggerClient,
    *,
    question: str,
    skill_name: str,
    rag: dict[str, Any],
    issues: list[dict[str, Any]],
    detail: dict[str, Any],
) -> str:
    issue_lines = "\n".join(
        f"- #{i['id']} {i['title']} [{', '.join(i.get('labels') or [])}]"
        for i in issues
    )
    prompt_summary = {
        "system": "Answer using provided RAG context + issue data; cite issue ids and sources.",
        "user_question": question,
        "skill": skill_name,
        "rag_sources": [p["source"] for p in rag.get("passages", [])],
        "issue_count": len(issues),
        "detail_id": detail.get("id"),
    }
    user_prompt = (
        f"Question: {question}\n\n"
        f"Skill playbook in use: {skill_name}\n\n"
        f"RAG context:\n{rag.get('context', '')[:1200]}\n\n"
        f"Open issues:\n{issue_lines or '(none)'}\n\n"
        f"Sample detail: {json.dumps(detail, indent=2)[:500]}\n"
    )

    model_name = SETTINGS.openai_model if SETTINGS.use_hosted else SETTINGS.ollama_model
    with dbg.step(
        "llm.chat",
        message=f"LLM compose via {model_name}",
        input_payload={
            "model": model_name,
            "prompt_summary": prompt_summary,
            "prompt_chars": len(user_prompt),
        },
        phase="llm",
    ) as bag:
        if model_available(SETTINGS) and not SETTINGS.skip_model:
            try:
                reply = chat(
                    [
                        {
                            "role": "system",
                            "content": prompt_summary["system"],
                        },
                        {"role": "user", "content": user_prompt},
                    ],
                    settings=SETTINGS,
                )
                text = (reply.get("content") or "").strip()
                bag["output"] = {
                    "model": model_name,
                    "content_preview": text[:500],
                    "content_chars": len(text),
                    "tokens": reply.get("usage"),
                    "mode": "live",
                }
                bag["message"] = "LLM response received"
                if text:
                    return text
            except ModelUnavailable as exc:
                bag["output"] = {"error": str(exc), "mode": "fallback"}

        # Deterministic compose for free/default path
        sources = ", ".join(p["source"] for p in rag.get("passages", [])[:3]) or "n/a"
        if "triage" in question.lower():
            text = _triage_answer(issues, rag, skill_name)
        elif "timeout" in question.lower() or "usually" in question.lower() or "fix" in question.lower():
            text = (
                f"From the runbooks ({sources}), login timeouts usually come from "
                f"token-refresh latency, cookie domain mismatch, or QA rate limits. "
                f"Standard fix order: check /health/auth latency, temporarily raise the "
                f"client timeout, verify SameSite/domain, allowlist staging IPs if needed. "
                f"Related open issues:\n{issue_lines or '(none)'}"
            )
        else:
            text = (
                f"Found {len(issues)} open issue(s) matching the query "
                f"(skill={skill_name}; sources={sources}):\n{issue_lines or '(none)'}"
            )
            if detail.get("id"):
                text += f"\n\nClosest detail: #{detail['id']} — {detail.get('title')}"
        bag["output"] = {
            "model": "scripted-fallback",
            "content_preview": text[:500],
            "content_chars": len(text),
            "tokens": None,
            "mode": "scripted",
        }
        bag["message"] = "Scripted answer composed (no live model)"
        return text


def _triage_answer(issues: list[dict[str, Any]], rag: dict[str, Any], skill_name: str) -> str:
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
    lines.append(f"- Skill: {skill_name}")
    if rag.get("passages"):
        lines.append(
            "- RAG sources: "
            + ", ".join(f"{p['source']} ({p['score']})" for p in rag["passages"][:3])
        )
    return "\n".join(lines)


def _maybe_email(
    dbg: DebuggerClient,
    question: str,
    answer: str,
    *,
    force: bool = False,
) -> dict[str, Any] | None:
    if not force and not _wants_email(question):
        return None
    payload = {
        "to": "ops@northwind.example",
        "subject": "Northwind agent summary",
        "body": answer[:2000],
    }
    decision = dbg.tool_call(
        "email.send",
        message="Optional gated notify (simulated email.send)",
        payload=payload,
    )
    if decision.get("decision") == "deny":
        dbg.abort("Human denied email.send")
        return {"ok": False, "denied": True}
    result = simulate_email_send(payload)
    if not debugger_enabled():
        dbg.tool_result(
            "email.send",
            message="Simulated send (standalone)",
            payload={**result, "duration_ms": 0},
        )
    return result


def answer_question(
    question: str,
    *,
    send_email: bool | None = None,
    dbg: DebuggerClient | None = None,
) -> dict[str, Any]:
    """Run the full stack for one user question; return answer + trace metadata."""
    owns = dbg is None
    dbg = dbg or DebuggerClient()
    if owns:
        dbg.__enter__()

    t0 = time.perf_counter()
    try:
        dbg.start_run(message="ai-agent-stack chat turn")
        dbg.user_message(question)
        dbg.think(
            "Routing through plugin → skill → RAG → MCP → tools → API → LLM",
            payload={"demo_questions": [d["text"] for d in DEMO_QUESTIONS]},
        )

        plugin = _load_plugin(dbg)
        skill = _select_skill(dbg, question)
        rag = _rag(dbg, _rag_query_for(question), k=3)
        needle = _search_text_for(question)
        mcp_result = _mcp_search(dbg, text=needle)
        tool_result = _tools_search(dbg, text=needle)
        # Prefer MCP issues; tools should agree on the free path.
        issues = mcp_result.get("issues") or tool_result.get("issues") or []
        detail = _api_get_issue(dbg, int(issues[0]["id"])) if issues else {}
        answer = _llm_compose(
            dbg,
            question=question,
            skill_name=skill.meta.name,
            rag=rag,
            issues=issues,
            detail=detail,
        )
        answer += (
            f"\n\n—\nstack: plugin={plugin['name']} · skill={skill.meta.name} · "
            f"rag_chunks={len(rag.get('passages', []))} · mcp={mcp_result.get('count', 0)} · "
            f"tools={tool_result.get('count', 0)}"
        )

        email_mode = send_email if send_email is not None else _wants_email(question)
        email_result = _maybe_email(dbg, question, answer, force=bool(send_email)) if email_mode else None
        if email_result and email_result.get("denied"):
            answer += "\n\n(email.send denied — answer not emailed)"

        duration_ms = round((time.perf_counter() - t0) * 1000, 2)
        dbg.final_answer(answer, duration_ms=duration_ms)
        if dbg.run_id and not (email_result and email_result.get("denied")):
            dbg.complete(f"Chat turn finished in {duration_ms}ms")

        return {
            "answer": answer,
            "run_id": dbg.run_id,
            "duration_ms": duration_ms,
            "debugger": dbg.enabled,
            "events": list(dbg.local_events),
            "concepts": ["plugins", "skills", "rag", "mcp", "tools", "apis"],
        }
    finally:
        if owns:
            dbg.__exit__(None, None, None)


# Back-compat for earlier README/make targets
def run_pipeline(
    task: str = "Triage the open login issues.",
    *,
    send_email: bool = False,
    dbg: DebuggerClient | None = None,
) -> str:
    result = answer_question(task, send_email=send_email, dbg=dbg)
    return result["answer"]


def build_report(issues: list[dict[str, Any]], context: str) -> str:
    return _triage_answer(
        issues,
        {"passages": [{"source": "context", "score": 1.0, "text": context}]},
        "issue-triage",
    )


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Observability integration (single turn)")
    parser.add_argument("--question", default=DEMO_QUESTIONS[0]["text"])
    parser.add_argument(
        "--email",
        action="store_true",
        help="Also attempt gated email.send (optional side path)",
    )
    args = parser.parse_args()
    result = answer_question(args.question, send_email=args.email)
    print(result["answer"])
    print(f"\n[run_id={result['run_id']} duration_ms={result['duration_ms']}]")
    if result["debugger"]:
        print("[debugger] Full timed timeline emitted to Agent Debugger.")
    else:
        print("[standalone] Set AGENT_DEBUGGER_URL to stream the same timeline remotely.")


if __name__ == "__main__":
    main()
