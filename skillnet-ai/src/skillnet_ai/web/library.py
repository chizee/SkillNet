"""Local library browsing. Reading a library never analyzes or executes skills."""

from pathlib import Path
from typing import Any

from skillnet_ai.core.library import load_snapshot, read_source, validate_snapshot_evidence
from skillnet_ai.core.validation import parse_frontmatter

MAX_BYTES = 20 * 1024 * 1024
MAX_SKILLS = 5000
MAX_RELATIONS = 20000


def absolute_directory(value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise ValueError("Enter an absolute folder path.")
    path = path.resolve(strict=True)
    if not path.is_dir():
        raise ValueError("The selected path is not a directory.")
    return path


def read_library(source_path: str, index_path: str | None = None) -> dict[str, Any]:
    root = absolute_directory(source_path)
    paths = sorted(p for p in root.glob("*/SKILL.md") if not p.parent.name.startswith("."))
    if len(paths) > MAX_SKILLS:
        raise ValueError("A library can contain at most 5,000 skills.")
    skills = []
    warnings = []
    remaining = MAX_BYTES
    for path in paths:
        try:
            size = path.stat().st_size
        except OSError as exc:
            warnings.append(f"{path.parent.name}: {exc}")
            continue
        if size > remaining:
            raise ValueError("Skill sources exceed 20 MB. Choose a smaller library.")
        remaining -= size
        try:
            skill = read_source(path, max_bytes=size)
            metadata = parse_frontmatter(skill.source)
            description = metadata.get("description", "")
            skills.append(
                {
                    "id": skill.skill_id,
                    "name": skill.name,
                    "description": description if isinstance(description, str) else "",
                    "source": skill.source,
                    "path": str(path),
                }
            )
        except (OSError, ValueError) as exc:
            warnings.append(f"{path.parent.name}: {exc}")
    result: dict[str, Any] = {
        "name": root.name,
        "sourcePath": str(root),
        "source": {"kind": "source", "title": root.name, "skills": skills, "relations": []},
        "graph": None,
        "analysisStatus": "missing",
        "analysisError": None,
        "warnings": warnings,
        "changedSkills": 0,
        "removedSkills": 0,
        "addedSkills": 0,
    }
    try:
        index = absolute_directory(index_path) if index_path else root / ".skillnet"
        if not index_path and not (index / "CURRENT").exists():
            return result
        _, graph = load_snapshot(index, max_bytes=MAX_BYTES)
        if len(graph.skills) > MAX_SKILLS or len(graph.relations) > MAX_RELATIONS:
            raise ValueError("Analysis exceeds 5,000 skills or 20,000 relationships.")
        validate_snapshot_evidence(graph)
        current = {skill["id"]: skill["source"] for skill in skills}
        analyzed = {skill.skill_id: skill.source for skill in graph.skills}
        if current and not current.keys() & analyzed.keys():
            raise ValueError("The analysis folder and skill library have no skills in common.")
        result.update(
            graph=graph.model_dump(),
            analysisStatus="ready",
            changedSkills=sum(
                current[key] != analyzed[key] for key in current.keys() & analyzed.keys()
            ),
            removedSkills=len(analyzed.keys() - current.keys()),
            addedSkills=len(current.keys() - analyzed.keys()),
        )
    except (OSError, ValueError) as exc:
        result.update(analysisStatus="error", analysisError=str(exc))
    return result
