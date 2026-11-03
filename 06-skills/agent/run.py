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
    lines.append(skill.body.split("## Report template")[0].strip())

    # Follow the skill steps against live issue data (tools/API layer).
    needle = "login" if "login" in task.lower() else task
    issues = search_issues(state="open", text=needle)
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
