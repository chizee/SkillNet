"""Build and load routing indexes, publish snapshots and retrieve skill candidates.

Retrieval adapted from SkillFabric; Copyright (c) 2026 SkillFabric Contributors, MIT.
"""

import os
import re
import sqlite3
import uuid
from collections import defaultdict
from contextlib import closing
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from skillnet_ai.core.library import load_snapshot as load_snapshot
from skillnet_ai.core.models import AnalyzedSkill

Matrix = NDArray[np.float32]


def publish(index_dir: Path, staging: Path) -> None:
    """Publish one completed immutable snapshot through a single pointer replacement.

    Previous snapshots remain available to in-flight readers. They are not used as
    a fallback if the current snapshot is damaged.
    """

    pointer = index_dir / f".CURRENT-{uuid.uuid4().hex}"
    try:
        pointer.write_text(staging.name + "\n", encoding="utf-8")
        os.replace(pointer, index_dir / "CURRENT")
    finally:
        pointer.unlink(missing_ok=True)


def profile_text(skill: AnalyzedSkill) -> str:
    """Index capability and operational conditions without JSON or citation noise."""

    profile = skill.profile
    fields = [
        profile.capability,
        *profile.when_to_use,
        *profile.inputs,
        *profile.outputs,
        *profile.constraints,
        *profile.tools,
    ]
    scenarios = [
        f"{s.name}: " + "; ".join(f.text for f in [*s.before, *s.after]) for s in profile.scenarios
    ]
    return "\n".join([skill.name, *(f.text for f in fields), *scenarios])


def build_bm25(skills: list[AnalyzedSkill], path: Path) -> None:
    """Build an FTS5 index; unavailable FTS5 is an explicit environment error."""

    with closing(sqlite3.connect(path)) as db, db:
        db.execute("CREATE VIRTUAL TABLE skills USING fts5(id UNINDEXED, body)")
        db.executemany(
            "INSERT INTO skills VALUES (?, ?)", [(s.skill_id, profile_text(s)) for s in skills]
        )


def search_bm25(path: Path, query: str, limit: int) -> list[str]:
    """Retrieve using an escaped OR query; empty lexical matches remain empty."""

    tokens = list(dict.fromkeys(re.findall(r"[^\W_]+", query.lower())))[:64]
    if not tokens:
        return []
    expression = " OR ".join('"' + t.replace('"', '""') + '"' for t in tokens)
    with closing(sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)) as db:
        rows = db.execute(
            "SELECT id FROM skills WHERE skills MATCH ? ORDER BY bm25(skills), id LIMIT ?",
            (expression, limit),
        ).fetchall()
    return [str(row[0]) for row in rows]


def normalize(vectors: list[list[float]] | Matrix) -> Matrix:
    """Validate external vectors once and normalize for exact cosine scoring."""

    matrix = np.asarray(vectors, dtype=np.float32)
    if matrix.ndim != 2 or matrix.shape[1] == 0 or not np.isfinite(matrix).all():
        raise ValueError("Embedding vectors must be a finite, nonempty matrix.")
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    if (norms <= 0).any():
        raise ValueError("Embedding vectors must have nonzero norm.")
    return np.asarray(matrix / norms, dtype=np.float32)


def nearest(query: Matrix, matrix: Matrix, ids: list[str], limit: int) -> list[str]:
    """Rank exact cosine scores with stable skill-ID tie breaking."""

    if query.shape != (matrix.shape[1],):
        raise ValueError("Query embedding dimension differs from the analysis index.")
    scores = matrix @ query
    order = sorted(range(len(ids)), key=lambda i: (-float(scores[i]), ids[i]))
    return [ids[i] for i in order[:limit]]


def fuse(channels: list[list[str]], limit: int) -> list[str]:
    """Fuse ranks without interpreting lexical or vector scores as confidence."""

    scores: dict[str, float] = defaultdict(float)
    for channel in channels:
        for rank, skill_id in enumerate(dict.fromkeys(channel), start=1):
            scores[skill_id] += 1 / (60 + rank)
    return sorted(scores, key=lambda key: (-scores[key], key))[:limit]
