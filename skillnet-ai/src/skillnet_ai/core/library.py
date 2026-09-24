"""Read skill sources and published snapshots without model or vector dependencies."""

import hashlib
from pathlib import Path

from skillnet_ai.core.models import GraphSnapshot, SkillSource
from skillnet_ai.core.validation import parse_frontmatter, validate_citations, validate_profile


def read_source(path: Path, *, max_bytes: int | None = None) -> SkillSource:
    """Read one SKILL.md using the same identity and normalization as analysis."""
    with path.open("rb") as stream:
        raw = stream.read() if max_bytes is None else stream.read(max_bytes + 1)
    if max_bytes is not None and len(raw) > max_bytes:
        raise ValueError(f"Skill source exceeds the size limit: {path}")
    source = raw.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    if not source.strip():
        raise ValueError(f"Empty skill source: {path}")
    metadata = parse_frontmatter(source)
    name = metadata.get("name") or path.parent.name
    if not isinstance(name, str):
        raise ValueError(f"Skill name must be a string: {path}")
    return SkillSource(
        skill_id=path.parent.name,
        name=name,
        path=str(path.parent.resolve()),
        source=source,
        content_hash=hashlib.sha256(source.encode()).hexdigest(),
    )


def load_snapshot(index_dir: Path, *, max_bytes: int | None = None) -> tuple[Path, GraphSnapshot]:
    """Resolve CURRENT once and read a complete snapshot; never fall back silently."""
    try:
        with (index_dir / "CURRENT").open(encoding="utf-8") as stream:
            name = stream.read(256).strip()
        if not name or Path(name).name != name or not name.startswith("snapshot-"):
            raise ValueError("invalid snapshot pointer")
        root = index_dir / name
        with (root / "graph.json").open("rb") as stream:
            raw = stream.read() if max_bytes is None else stream.read(max_bytes + 1)
        if max_bytes is not None and len(raw) > max_bytes:
            raise ValueError("Analysis snapshot exceeds the size limit.")
        graph = GraphSnapshot.model_validate_json(raw)
    except (OSError, ValueError) as exc:
        raise ValueError("Cannot load analysis snapshot; run skillnet analyze again.") from exc
    ids = [skill.skill_id for skill in graph.skills]
    known_ids = set(ids)
    if not ids or len(known_ids) != len(ids):
        raise ValueError("Analysis must contain unique, nonempty skill identities.")
    if any(
        edge.source not in known_ids or edge.target not in known_ids for edge in graph.relations
    ):
        raise ValueError("Analysis relation references an unknown skill.")
    return root, graph


def validate_snapshot_evidence(graph: GraphSnapshot) -> None:
    """Validate displayed citations against the snapshot's own source files."""
    sources = {skill.skill_id: skill.source for skill in graph.skills}
    for skill in graph.skills:
        validate_profile(skill.profile, skill.source)
    for edge in graph.relations:
        if edge.source == edge.target:
            raise ValueError("A relationship must connect two different skills.")
        for context in edge.contexts:
            validate_citations(context.source_evidence, sources[edge.source])
            validate_citations(context.target_evidence, sources[edge.target])
