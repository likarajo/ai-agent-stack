"""Smoke tests for skills progressive loading (no model)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(MODULE))

from agent.loader import catalog, load_full, select_skill  # noqa: E402
from agent.run import run  # noqa: E402

SKILLS = MODULE / "skills"


def test_catalog_is_metadata_only() -> None:
    metas = catalog(SKILLS)
    assert any(m.name == "issue-triage" for m in metas)
    # catalog returns SkillMeta, not full body
    assert all(hasattr(m, "description") for m in metas)


def test_select_and_load() -> None:
    metas = catalog(SKILLS)
    chosen = select_skill(metas, "Triage the open login issues.")
    assert chosen is not None
    skill = load_full(chosen)
    assert "Report template" in skill.body
    assert "p1" in skill.body


def test_run_produces_report() -> None:
    out = run("Triage the open login issues.")
    assert "issue-triage" in out
    assert "# Triage report" in out
    assert "#101" in out or "#102" in out
