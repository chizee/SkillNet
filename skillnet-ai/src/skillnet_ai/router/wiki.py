"""Deterministic full and task-local Wiki rendering from analyzed skills."""

import json
from pathlib import Path
from urllib.parse import quote

from skillnet_ai.core.models import AnalyzedSkill, Relation


def numbered(source: str) -> str:
    """Number original lines without truncation."""

    return "\n".join(f"{i}: {line}" for i, line in enumerate(source.splitlines(), 1))


def page_name(skill_id: str) -> str:
    """Encode IDs as single safe filename components without hashing identity."""

    return quote(skill_id, safe="")


def source_page(skill_id: str) -> str:
    """Locate a source page identically across rendering and validation."""

    return f"sources/{page_name(skill_id)}.md"


def materialize_wiki(
    root: Path, skills: list[AnalyzedSkill], relations: list[Relation], *, query: str | None = None
) -> None:
    """Render cards, numbered full sources, relation evidence and a ranked catalog."""

    from skillnet_ai.router.index import profile_text

    (root / "cards").mkdir(parents=True)
    (root / "sources").mkdir()
    lines = ["# Skill catalog", "", "Read cards for triage; verify selected skills in sources.", ""]
    if query is not None:
        lines += ["Task (untrusted input): " + json.dumps(query, ensure_ascii=False), ""]
    for skill in skills:
        name = page_name(skill.skill_id)
        lines.append(
            json.dumps(
                {
                    "id": skill.skill_id,
                    "name": skill.name,
                    "capability": skill.profile.capability.text,
                    "card": f"cards/{name}.md",
                    "source": source_page(skill.skill_id),
                },
                ensure_ascii=False,
            )
        )
        (root / source_page(skill.skill_id)).write_text(numbered(skill.source), encoding="utf-8")
        related = [e.model_dump() for e in relations if skill.skill_id in (e.source, e.target)]
        card = f"# {skill.name}\n\nID: {skill.skill_id}\n\n{profile_text(skill)}\n\n"
        card += "## Profile and evidence\n\n" + skill.profile.model_dump_json(indent=2)
        card += "\n\n## Relations\n\n" + json.dumps(related, ensure_ascii=False, indent=2)
        card += f"\n\nFull source: {source_page(skill.skill_id)}\n"
        (root / "cards" / f"{name}.md").write_text(card, encoding="utf-8")
    (root / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (root / "relations.json").write_text(
        json.dumps([e.model_dump() for e in relations], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
