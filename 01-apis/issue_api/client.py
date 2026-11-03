"""Deterministic client for the Issue Tracker API (no LLM)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.config import SETTINGS  # noqa: E402


def search_open_login_issues(base_url: str | None = None) -> dict:
    base = (base_url or SETTINGS.issue_api_base_url).rstrip("/")
    with httpx.Client(base_url=base, timeout=10.0) as client:
        resp = client.get("/issues", params={"state": "open", "q": "login"})
        resp.raise_for_status()
        return resp.json()


def main() -> None:
    parser = argparse.ArgumentParser(description="Call GET /issues?state=open&q=login")
    parser.add_argument("--base-url", default=SETTINGS.issue_api_base_url)
    args = parser.parse_args()
    data = search_open_login_issues(args.base_url)
    print(json.dumps(data, indent=2))
    print(f"\nFound {data['count']} open issue(s) mentioning login.")


if __name__ == "__main__":
    main()
