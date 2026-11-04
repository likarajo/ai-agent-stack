"""Smoke tests for skills progressive loading (no model)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(MODULE))

import agent.loader as loader  # noqa: E402
from agent.loader import catalog, load_full, parse_skill_file, select_skill  # noqa: E402
from agent.run import run  # noqa: E402

SKILLS = MODULE / "skills"


def test_catalog_is_metadata_only() -> None:
    metas = catalog(SKILLS)
    assert any(m.name == "issue-triage" for m in metas)
    assert any(m.name == "billing-refunds" for m in metas)
    assert any(m.name == "login-reset" for m in metas)
    # catalog returns SkillMeta, not full body
    assert all(hasattr(m, "description") for m in metas)
    assert all(not hasattr(m, "body") for m in metas)


def test_catalog_is_lazy_no_full_parse(monkeypatch) -> None:
    """Catalog must not load skill bodies — only front matter."""
    full_reads: list[Path] = []
    real_parse = parse_skill_file

    def spy_full(path: Path):
        full_reads.append(path)
        return real_parse(path)

    monkeypatch.setattr(loader, "parse_skill_file", spy_full)
    metas = catalog(SKILLS)
    assert metas
    assert full_reads == []

    chosen = select_skill(metas, "Triage the open login issues.")
    assert chosen is not None
    load_full(chosen)
    assert full_reads == [chosen.path]


def test_billing_question_selects_billing_skill() -> None:
    metas = catalog(SKILLS)
    chosen = select_skill(metas, "How do I handle a billing refund dispute?")
    assert chosen is not None
    assert chosen.name == "billing-refunds"
    # Login skill must not win on shared filler words like "issue".
    login = select_skill(metas, "I cannot login after SSO redirect")
    assert login is not None
    assert login.name == "login-reset"


def test_select_and_load() -> None:
    metas = catalog(SKILLS)
    chosen = select_skill(metas, "Triage the open login issues.")
    assert chosen is not None
    assert chosen.name == "issue-triage"
    skill = load_full(chosen)
    assert "Report template" in skill.body
    assert "p1" in skill.body


def test_run_produces_report() -> None:
    out = run("Triage the open login issues.")
    assert "issue-triage" in out
    assert "# Triage report" in out
    assert "#101" in out or "#102" in out
