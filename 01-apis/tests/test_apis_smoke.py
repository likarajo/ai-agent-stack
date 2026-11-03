"""Smoke tests for the API module (no model required)."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
MODULE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(MODULE))

from issue_api.server import app  # noqa: E402

client = TestClient(app)


def test_health() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_search_open_login_issues() -> None:
    resp = client.get("/issues", params={"state": "open", "q": "login"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] >= 1
    titles = " ".join(i["title"].lower() for i in body["issues"])
    assert "login" in titles
    assert all(i["state"] == "open" for i in body["issues"])


def test_get_issue() -> None:
    resp = client.get("/issues/101")
    assert resp.status_code == 200
    assert resp.json()["id"] == 101


def test_missing_issue() -> None:
    resp = client.get("/issues/9999")
    assert resp.status_code == 404
