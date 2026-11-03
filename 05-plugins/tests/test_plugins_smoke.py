"""Smoke tests for plugin packaging (no model)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "05-plugins"))

from loader.install import describe_install, install_plugin, load_manifest  # noqa: E402

MANIFEST = ROOT / "05-plugins" / "plugin" / "northwind-issue-tracker" / "plugin.json"


def test_manifest_valid() -> None:
    data = load_manifest(MANIFEST)
    assert data["name"] == "northwind-issue-tracker"
    assert data["mcp_servers"]
    assert data["skills"]
    assert data["commands"]


def test_install_writes_config(tmp_path: Path) -> None:
    target = install_plugin(MANIFEST, install_dir=tmp_path)
    assert target.exists()
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["mcp_servers"][0]["args"]
    text = describe_install(target)
    assert "Northwind Issue Tracker" in text
    assert "packaging only" in text.lower() or "Packaging" in text or "packaging" in text
