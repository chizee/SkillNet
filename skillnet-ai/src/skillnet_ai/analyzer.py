"""Scenario analysis: source profiles, candidate pairs and two-type skill relations."""

import json
import logging
import re
import shutil
import sqlite3
import tempfile
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from skillnet_ai.core.library import read_source
from skillnet_ai.core.llm import embed, structured_call
from skillnet_ai.core.models import (
    AnalysisOptions,
    AnalysisResult,
    AnalyzedSkill,
    Endpoint,
    GraphSnapshot,
    Relation,
    RelationJudgment,
    SkillProfile,
    SkillSource,
)
from skillnet_ai.core.prompts import (
    PROFILE_PROMPT,
    PROFILE_VERSION,
    RELATION_PROMPT,
    RELATION_VERSION,
)
from skillnet_ai.core.validation import validate_citations, validate_profile
from skillnet_ai.router.index import (
    Matrix,
    build_bm25,
    fuse,
    nearest,
    normalize,
    profile_text,
    publish,
    search_bm25,
)
from skillnet_ai.router.wiki import materialize_wiki, numbered

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmbeddingText:
    """One capability or state vector associated with a stable skill ID."""

    skill_id: str
    kind: str
    text: str


def analyze(
    skills_dir: Path,
    output_dir: Path,
    *,
    endpoint: Endpoint,
    embedding: Endpoint,
    options: AnalysisOptions,
    force: bool = False,
) -> AnalysisResult:
    """Extract, validate, index and publish; failures never publish a partial graph."""

    sources = read_skills(skills_dir)
    if output_dir == skills_dir or output_dir in skills_dir.parents:
        raise ValueError("Analysis output must not replace the skill root or its ancestors.")
    output_dir.mkdir(parents=True, exist_ok=True)
    cache = ModelCache(output_dir / "cache.sqlite", force=force)
    stage = Path(tempfile.mkdtemp(prefix="snapshot-", dir=output_dir))
    model_key: list[object] = [
        endpoint.base_url,
        endpoint.model,
        options.json_mode,
        options.reasoning_effort,
    ]

    def extract(source: SkillSource) -> tuple[AnalyzedSkill, bool]:
        key = [*model_key, PROFILE_VERSION, source.skill_id, source.content_hash]
        cached = cache.get("profile", key)
        profile = (
            SkillProfile.model_validate_json(cached)
            if cached is not None
            else structured_call(
                endpoint,
                options,
                PROFILE_PROMPT,
                {"skill_id": source.skill_id, "source": numbered(source.source)},
                SkillProfile,
            )
        )
        validate_profile(profile, source.source)
        if cached is None:
            cache.put("profile", key, profile.model_dump_json())
        return AnalyzedSkill(**source.model_dump(), profile=profile), cached is not None

    try:
        logger.info("Extracting profiles for %d skills", len(sources))
        with ThreadPoolExecutor(max_workers=options.max_workers) as pool:
            extracted = list(pool.map(extract, sources))
        skills = [s for s, _ in extracted]
        build_bm25(skills, stage / "bm25.sqlite")
        texts, matrix, embedding_hits = build_vectors(
            embedding,
            skills,
            cache,
            timeout=options.timeout,
            retries=options.request_retries,
            batch_size=options.embedding_batch_size,
        )
        pairs = candidate_pairs(
            skills, texts, matrix, stage / "bm25.sqlite", options.candidate_limit
        )
        by_id = {s.skill_id: s for s in skills}

        def judge(pair: CandidatePair) -> tuple[list[Relation], bool]:
            first, second = by_id[pair.first], by_id[pair.second]
            key = [
                *model_key,
                PROFILE_VERSION,
                RELATION_VERSION,
                first.skill_id,
                first.content_hash,
                second.skill_id,
                second.content_hash,
                first.profile.model_dump(),
                second.profile.model_dump(),
            ]
            cached = cache.get("relation", key)
            judgment = (
                RelationJudgment.model_validate_json(cached)
                if cached is not None
                else structured_call(
                    endpoint,
                    options,
                    RELATION_PROMPT,
                    {
                        "skills": [
                            {
                                "skill_id": s.skill_id,
                                "profile": s.profile.model_dump(),
                                "source": numbered(s.source),
                            }
                            for s in (first, second)
                        ],
                        "retrieval_hints": pair.hints,
                    },
                    RelationJudgment,
                    output_schema=relation_schema(first, second),
                )
            )
            edges = normalize_relations(judgment, first, second)
            if cached is None:
                if judgment.decision.outcome == "related":
                    judgment.decision.relations = edges
                cache.put("relation", key, judgment.model_dump_json())
            return edges, cached is not None

        logger.info("Validating %d candidate skill pairs", len(pairs))
        with ThreadPoolExecutor(max_workers=options.max_workers) as pool:
            judgments = list(pool.map(judge, pairs))
        relations = [edge for edges, _ in judgments for edge in edges]
        graph = GraphSnapshot(
            embedding_model=embedding.model,
            embedding_base_url=embedding.base_url,
            skills=skills,
            relations=relations,
        )
        (stage / "graph.json").write_text(graph.model_dump_json(indent=2), encoding="utf-8")
        np.savez(
            stage / "embeddings.npz",
            ids=np.asarray([s.skill_id for s in skills]),
            vectors=matrix[: len(skills)],
        )
        materialize_wiki(stage / "wiki", skills, relations)
        publish(output_dir, stage)
    except BaseException:
        try:
            shutil.rmtree(stage)
        except OSError:
            logger.warning("Could not remove failed analysis staging directory: %s", stage)
        raise
    return AnalysisResult(
        index_dir=output_dir,
        skill_count=len(skills),
        relation_counts={
            kind: sum(e.type == kind for e in relations) for kind in ("compose_with", "similar_to")
        },
        cache_hits={
            "profiles": sum(hit for _, hit in extracted),
            "embeddings": embedding_hits,
            "relations": sum(hit for _, hit in judgments),
        },
    )


def read_skills(root: Path) -> list[SkillSource]:
    """Read direct child packages and keep folder identity independent of display name."""

    if not root.is_dir():
        raise ValueError(f"Skill root is not a directory: {root}")
    skills = []
    for path in sorted(root.glob("*/SKILL.md")):
        if path.parent.name.startswith("."):
            continue
        skills.append(read_source(path))
    if not skills:
        raise ValueError("No SKILL.md files found in direct child directories.")
    return skills


@dataclass(frozen=True)
class CandidatePair:
    """An unordered skill pair aggregating all retrieval channels and state matches."""

    first: str
    second: str
    hints: tuple[str, ...]


def candidate_pairs(
    skills: list[AnalyzedSkill],
    texts: list[EmbeddingText],
    vectors: Matrix,
    bm25_path: Path,
    limit: int,
) -> list[CandidatePair]:
    """Retrieve handoffs and fused capability matches, plus unambiguous named references."""

    ids = [s.skill_id for s in skills]
    hits: dict[tuple[str, str], set[str]] = defaultdict(set)

    def add(first: str, second: str, hint: str) -> None:
        if first != second:
            a, b = sorted((first, second))
            hits[a, b].add(hint)

    for i, skill in enumerate(skills):
        semantic = [
            s
            for s in nearest(vectors[i], vectors[: len(ids)], ids, limit + 1)
            if s != skill.skill_id
        ][:limit]
        lexical = [
            s for s in search_bm25(bm25_path, profile_text(skill), limit + 1) if s != skill.skill_id
        ][:limit]
        for other in fuse([semantic, lexical], limit):
            add(skill.skill_id, other, "capability retrieval")

    before = [i for i, t in enumerate(texts) if t.kind == "before"]
    before_vectors = vectors[before]
    handoff_scores: dict[tuple[str, str], float] = {}
    handoff_hints: dict[tuple[str, str], set[str]] = defaultdict(set)
    for i, after in enumerate(texts):
        if after.kind != "after" or not before:
            continue
        scores = before_vectors @ vectors[i]
        order = sorted(range(len(before)), key=lambda n: (-float(scores[n]), before[n]))
        selected: set[str] = set()
        for n in order:
            target = texts[before[n]]
            if target.skill_id == after.skill_id:
                continue
            if target.skill_id not in selected and len(selected) >= limit:
                continue
            selected.add(target.skill_id)
            pair = (after.skill_id, target.skill_id)
            handoff_scores[pair] = max(handoff_scores.get(pair, -1), float(scores[n]))
            handoff_hints[pair].add(
                f"{after.skill_id}: {after.text} -> {target.skill_id}: {target.text}"
            )

    # A skill with many scenarios still gets one handoff budget, not one per state.
    for source in ids:
        targets = sorted(
            (b for a, b in handoff_scores if a == source),
            key=lambda b: (-handoff_scores[source, b], b),
        )[:limit]
        for target_id in targets:
            for hint in handoff_hints[source, target_id]:
                add(source, target_id, hint)

    name_counts = Counter(s.name for s in skills)
    aliases = {s.skill_id: s.skill_id for s in skills}
    aliases.update(
        {
            s.name: s.skill_id
            for s in skills
            if name_counts[s.name] == 1 and (s.name not in aliases or aliases[s.name] == s.skill_id)
        }
    )
    for skill in skills:
        references = set(re.findall(r"`([^`\n]+)`", skill.source))
        for name in references & aliases.keys():
            add(skill.skill_id, aliases[name], f"explicit reference in {skill.skill_id}: {name}")
    return [CandidatePair(a, b, tuple(sorted(hints))) for (a, b), hints in sorted(hits.items())]


def relation_schema(first: AnalyzedSkill, second: AnalyzedSkill) -> dict[str, Any]:
    """Constrain IDs and each endpoint's citation bounds at the generation boundary.

    Each document starts at line one. Two direction-specific variants prevent a
    model from attaching the longer document's line numbers to the shorter one.
    """

    schema = RelationJudgment.model_json_schema()
    definitions = schema.pop("$defs")
    variants = []
    for source, target in ((first, second), (second, first)):
        edge = deepcopy(definitions["Relation"])
        edge["properties"]["source"]["enum"] = [source.skill_id]
        edge["properties"]["target"]["enum"] = [target.skill_id]
        context = deepcopy(definitions["RelationContext"])
        for name, skill in (("source_evidence", source), ("target_evidence", target)):
            citation = deepcopy(definitions["Citation"])
            citation["properties"]["line"]["maximum"] = len(skill.source.splitlines())
            context["properties"][name]["items"] = citation
        edge["properties"]["contexts"]["items"] = context
        variants.append(edge)
    positive = deepcopy(definitions["RelatedSkills"])
    positive["properties"]["relations"]["items"] = {"anyOf": variants}
    schema["properties"]["decision"] = {"anyOf": [definitions["NoRelation"], positive]}
    return schema


def normalize_relations(
    judgment: RelationJudgment, first: AnalyzedSkill, second: AnalyzedSkill
) -> list[Relation]:
    """Validate endpoints and evidence, then merge repeated scenario contexts."""

    if judgment.decision.outcome == "none":
        return []
    skills = {s.skill_id: s for s in (first, second)}
    merged: dict[tuple[str, str, str], Relation] = {}
    for edge in judgment.decision.relations:
        if {edge.source, edge.target} != set(skills):
            raise ValueError("Relation must connect exactly the two candidate skills.")
        for context in edge.contexts:
            validate_citations(context.source_evidence, skills[edge.source].source)
            validate_citations(context.target_evidence, skills[edge.target].source)
        if edge.type == "similar_to" and edge.source > edge.target:
            edge = edge.model_copy(
                update={
                    "source": edge.target,
                    "target": edge.source,
                    "contexts": [
                        c.model_copy(
                            update={
                                "source_evidence": c.target_evidence,
                                "target_evidence": c.source_evidence,
                            }
                        )
                        for c in edge.contexts
                    ],
                }
            )
        key = (edge.type, edge.source, edge.target)
        if key not in merged:
            merged[key] = edge.model_copy(update={"contexts": []})
        for context in edge.contexts:
            if context not in merged[key].contexts:
                merged[key].contexts.append(context)
    return [merged[key] for key in sorted(merged)]


class ModelCache:
    """Cache successful API results, including negative relation judgments."""

    def __init__(self, path: Path, *, force: bool = False) -> None:
        self.path = path
        self.force = force
        with closing(sqlite3.connect(path)) as connection, connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS results "
                "(namespace TEXT, key TEXT, value TEXT, PRIMARY KEY(namespace, key))"
            )

    def get(self, namespace: str, key: list[object]) -> str | None:
        if self.force:
            return None
        with closing(sqlite3.connect(self.path)) as connection, connection:
            row = connection.execute(
                "SELECT value FROM results WHERE namespace=? AND key=?",
                (namespace, json.dumps(key, sort_keys=True)),
            ).fetchone()
        return str(row[0]) if row else None

    def put(self, namespace: str, key: list[object], value: str) -> None:
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute(
                "INSERT OR REPLACE INTO results VALUES (?, ?, ?)",
                (namespace, json.dumps(key, sort_keys=True), value),
            )


def embedding_texts(skills: list[AnalyzedSkill]) -> list[EmbeddingText]:
    """Represent both whole skills and individual handoff states."""

    texts = [EmbeddingText(s.skill_id, "skill", profile_text(s)) for s in skills]
    for skill in skills:
        profile = skill.profile
        before = [*profile.inputs, *(f for s in profile.scenarios for f in s.before)]
        after = [*profile.outputs, *(f for s in profile.scenarios for f in s.after)]
        for kind, fields in (("before", before), ("after", after)):
            for text in dict.fromkeys(f.text for f in fields):
                texts.append(EmbeddingText(skill.skill_id, kind, text))
    return texts


def build_vectors(
    endpoint: Endpoint,
    skills: list[AnalyzedSkill],
    cache: ModelCache,
    *,
    timeout: float,
    retries: int,
    batch_size: int = 8,
) -> tuple[list[EmbeddingText], Matrix, int]:
    """Reuse vectors by exact text and model identity; no additional text hashes."""

    texts = embedding_texts(skills)
    keys: list[list[object]] = [[endpoint.base_url, endpoint.model, text.text] for text in texts]
    cached = [cache.get("embedding", key) for key in keys]
    missing = [i for i, item in enumerate(cached) if item is None]
    for offset in range(0, len(missing), batch_size):
        batch = missing[offset : offset + batch_size]
        fresh = embed(endpoint, [texts[i].text for i in batch], timeout=timeout, retries=retries)
        normalize(fresh)
        for i, vector in zip(batch, fresh, strict=True):
            value = json.dumps(vector)
            cache.put("embedding", keys[i], value)
            cached[i] = value
    vectors = [json.loads(value) for value in cached if value is not None]
    return texts, normalize(vectors), len(texts) - len(missing)
