"""Demo agent: progressive skill load, then follow the playbook with tools."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.issue_store import search_issues  # noqa: E402

from agent.loader import catalog, load_full, select_skill  # noqa: E402

SKILLS_DIR = Path(__file__).resolve().parents[1] / "skills"


def run(task: str) -> str:
    metas = catalog(SKILLS_DIR)
    lines = ["# Skill catalog (startup — names/descriptions only)"]
    for m in metas:
        lines.append(f"- {m.name}: {m.description}")

    chosen = select_skill(metas, task)
    if chosen is None:
        lines.append("\nNo skill matched; refusing to invent a playbook.")
        return "\n".join(lines)

    skill = load_full(chosen)
    lines.append(f"\n# Selected skill: {skill.meta.name}")
    lines.append("(Full SKILL.md loaded on demand)\n")
    preview = skill.body
    if "## Report template" in preview:
        preview = preview.split("## Report template")[0].strip()
    elif "## Rules" in preview:
        preview = preview.split("## Rules")[0].strip()
    lines.append(preview)

    task_l = task.lower()
    if "billing" in task_l:
        needle = "billing"
    elif "login" in task_l or "auth" in task_l or "triage" in task_l:
        needle = "login"
    else:
        needle = task
    issues = search_issues(state="open", text=needle)

    if skill.meta.name == "billing-refunds":
        lines.append("\n# Billing summary")
        lines.append(f"- Scope: open issues matching '{needle}'")
        lines.append("- Matches:")
        for issue in issues:
            labels = issue.get("labels") or []
            lines.append(f"  - #{issue['id']} {issue['title']} [{', '.join(labels)}]")
        lines.append("- Next step: Draft refund request fields; do not silently issue credits.")
        return "\n".join(lines)

    if skill.meta.name == "login-reset":
        lines.append("\n# Login access summary")
        lines.append(f"- Scope: open issues matching '{needle}'")
        lines.append("- Matches:")
        for issue in issues:
            labels = issue.get("labels") or []
            lines.append(f"  - #{issue['id']} {issue['title']} [{', '.join(labels)}]")
        lines.append(
            "- Next step: Confirm lockout vs timeout; follow login-timeout runbook if spinner hangs."
        )
        return "\n".join(lines)

    # Default: issue-triage playbook
    lines.append("\n# Triage report")
    lines.append(f"- Scope: open issues matching '{needle}'")
    lines.append("- Matches:")
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
    lines.append(
        f"- Severity call: {overall} (from labels + auth runbook guidance in the skill)"
    )
    lines.append(
        "- Next step: Confirm /health/auth latency and link the login-timeout runbook on each open auth bug."
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", default="Triage the open login issues.")
    args = parser.parse_args()
    print(run(args.task))


if __name__ == "__main__":
    main()
