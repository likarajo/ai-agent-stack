"""Progressive skill loading: metadata first, full SKILL.md on match."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

FRONT_MATTER = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


@dataclass
class SkillMeta:
    name: str
    description: str
    path: Path


@dataclass
class Skill:
    meta: SkillMeta
    body: str


def parse_skill_file(path: Path) -> Skill:
    text = path.read_text(encoding="utf-8")
    match = FRONT_MATTER.match(text)
    if not match:
        raise ValueError(f"SKILL.md missing YAML front matter: {path}")
    header, body = match.group(1), match.group(2).strip()
    data: dict[str, str] = {}
    for line in header.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip()
    name = data.get("name") or path.parent.name
    description = data.get("description") or ""
    return Skill(meta=SkillMeta(name=name, description=description, path=path), body=body)


def catalog(skills_dir: Path) -> list[SkillMeta]:
    """Startup view: name + one-line description only."""
    metas: list[SkillMeta] = []
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        skill = parse_skill_file(skill_md)
        metas.append(skill.meta)
    return metas


def select_skill(metas: list[SkillMeta], task: str) -> SkillMeta | None:
    """Naive matcher: prefer skills whose name/description tokens appear in the task."""
    task_l = task.lower()
    scored: list[tuple[int, SkillMeta]] = []
    for meta in metas:
        score = 0
        for token in re.findall(r"[a-z0-9-]+", f"{meta.name} {meta.description}".lower()):
            if len(token) < 4:
                continue
            if token in task_l:
                score += 1
        if "triage" in task_l and "triage" in meta.name:
            score += 5
        if score:
            scored.append((score, meta))
    if not scored:
        return None
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1]


def load_full(meta: SkillMeta) -> Skill:
    return parse_skill_file(meta.path)
