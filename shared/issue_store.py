"""File-backed issue store used by the local Issue Tracker API and tools."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from shared import ISSUES_PATH


def load_issues(path: Path | None = None) -> list[dict[str, Any]]:
    data_path = path or ISSUES_PATH
    with data_path.open(encoding="utf-8") as fh:
        return json.load(fh)


def get_issue(issue_id: int, path: Path | None = None) -> dict[str, Any] | None:
    for issue in load_issues(path):
        if int(issue["id"]) == int(issue_id):
            return issue
    return None


def search_issues(
    *,
    state: str | None = "open",
    text: str | None = None,
    path: Path | None = None,
) -> list[dict[str, Any]]:
    """Filter issues by optional state and case-insensitive text match."""
    results: list[dict[str, Any]] = []
    needle = (text or "").strip().lower()
    for issue in load_issues(path):
        if state and state != "all" and issue.get("state") != state:
            continue
        if needle:
            haystack = " ".join(
                [
                    str(issue.get("title", "")),
                    str(issue.get("body", "")),
                    " ".join(issue.get("labels") or []),
                ]
            ).lower()
            if needle not in haystack:
                continue
        results.append(issue)
    return results
