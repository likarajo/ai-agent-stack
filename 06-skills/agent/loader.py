"""Progressive skill loading: metadata first, full SKILL.md on match."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# Generic tokens that appear in many skills — too weak to drive selection alone.
_STOP_TOKENS = frozenset(
    {
        "skill",
        "skills",
        "help",
        "user",
        "users",
        "team",
        "open",
        "issue",
        "issues",
        "using",
        "with",
        "from",
        "this",
        "that",
        "your",
        "into",
        "when",
        "what",
        "how",
        "for",
        "and",
        "the",
        "standard",
        "rules",
        "guide",
        "playbook",
        "northwind",
        "portal",
        "template",
        "report",
        "steps",
        "follow",
    }
)


@dataclass
class SkillMeta:
    name: str
    description: str
    path: Path


@dataclass
class Skill:
    meta: SkillMeta
    body: str


def _parse_front_matter_header(header: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in header.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip()
    return data


def parse_skill_meta(path: Path) -> SkillMeta:
    """Read name/description only — stop at the closing front-matter fence."""
    header_lines: list[str] = []
    with path.open(encoding="utf-8") as handle:
        first = handle.readline()
        if first.strip() != "---":
            raise ValueError(f"SKILL.md missing YAML front matter: {path}")
        for line in handle:
            if line.strip() == "---":
                break
            header_lines.append(line)
        # Intentionally do not read the rest of the file (lazy body load).
    data = _parse_front_matter_header("".join(header_lines))
    name = data.get("name") or path.parent.name
    description = data.get("description") or ""
    return SkillMeta(name=name, description=description, path=path)


def parse_skill_file(path: Path) -> Skill:
    """Load metadata + full body (only when a skill is selected)."""
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
    if not match:
        raise ValueError(f"SKILL.md missing YAML front matter: {path}")
    header, body = match.group(1), match.group(2).strip()
    data = _parse_front_matter_header(header)
    name = data.get("name") or path.parent.name
    description = data.get("description") or ""
    meta = SkillMeta(name=name, description=description, path=path)
    return Skill(meta=meta, body=body)


def catalog(skills_dir: Path) -> list[SkillMeta]:
    """Startup view: name + one-line description only (no skill bodies)."""
    metas: list[SkillMeta] = []
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        metas.append(parse_skill_meta(skill_md))
    return metas


def _tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) >= 4]


def select_skill(metas: list[SkillMeta], task: str) -> SkillMeta | None:
    """Prefer skills whose name/topic tokens appear in the task.

    Name hits outweigh description hits. Generic words like \"issue\" are ignored
    so a billing question cannot lose to a login skill via shared filler tokens.
    """
    task_l = task.lower()
    scored: list[tuple[float, str, SkillMeta]] = []
    for meta in metas:
        score = 0.0
        name_tokens = [t for t in _tokens(meta.name) if t not in _STOP_TOKENS]
        desc_tokens = [t for t in _tokens(meta.description) if t not in _STOP_TOKENS]
        for token in name_tokens:
            if token in task_l:
                score += 5.0
        for token in desc_tokens:
            if token in task_l:
                score += 1.0
        # Strong topic boosts for unambiguous demo queries.
        if "billing" in task_l and "billing" in meta.name:
            score += 20.0
        if "login" in task_l and "login" in meta.name:
            score += 20.0
        if "triage" in task_l and "triage" in meta.name:
            score += 20.0
        if score:
            scored.append((score, meta.name, meta))
    if not scored:
        return None
    # Highest score first; stable tie-break by skill name.
    scored.sort(key=lambda x: (-x[0], x[1]))
    return scored[0][2]


def load_full(meta: SkillMeta) -> Skill:
    return parse_skill_file(meta.path)
