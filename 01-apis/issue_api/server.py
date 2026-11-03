"""Minimal Issue Tracker HTTP API — no AI, just a documented JSON contract."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query

ROOT = Path(__file__).resolve().parents[2]
MODULE = Path(__file__).resolve().parents[1]
for path in (ROOT, MODULE):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from shared.issue_store import get_issue, search_issues  # noqa: E402

app = FastAPI(
    title="Northwind Issue Tracker API",
    description=(
        "A tiny local API used across the ai-agent-stack modules. "
        "Same domain as the article: open issues that mention login."
    ),
    version="1.0.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/issues")
def list_issues(
    state: str = Query("open", description="open | closed | all"),
    q: str | None = Query(None, description="Case-insensitive text search"),
) -> dict:
    issues = search_issues(state=state, text=q)
    return {"count": len(issues), "issues": issues}


@app.get("/issues/{issue_id}")
def read_issue(issue_id: int) -> dict:
    issue = get_issue(issue_id)
    if issue is None:
        raise HTTPException(status_code=404, detail=f"Issue {issue_id} not found")
    return issue


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
