from __future__ import annotations

import concurrent.futures
import hashlib
import json
import logging
import os
import re
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Union

from openai import OpenAI

from skillnet_ai.prompts import (
    RELATIONSHIP_ANALYSIS_SYSTEM_PROMPT,
    RELATIONSHIP_ANALYSIS_USER_PROMPT_TEMPLATE,
    SCENARIO_ALIGNMENT_SYSTEM_PROMPT,
    SCENARIO_EXTRACTION_SYSTEM_PROMPT,
    SCENARIO_EXTRACTION_USER_PROMPT_TEMPLATE,
    SCENARIO_REDUNDANCY_SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)


class SkillRelationshipAnalyzer:
    """
    Analyzes a directory of skills to determine relationships between them.

    Relationships determined:
    - similar_to: A and B are functionally similar and interchangeable.
    - belong_to: A is a sub-task/part of B (B is the larger scope).
    - compose_with: A and B are independent but often used together.
    - depend_on: A requires B to execute (prerequisite).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "gpt-4o",
    ):
        self.api_key = api_key or os.getenv("API_KEY")
        self.base_url = base_url or os.getenv("BASE_URL") or "https://api.openai.com/v1"
        self.model = model

        if not self.api_key:
            raise ValueError("API Key is missing. Please provide it in init or set API_KEY environment variable.")

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def analyze_local_skills(self, skills_dir: str, save_to_file: bool = True) -> List[Dict[str, Any]]:
        """
        Main entry point: Scans a directory for skills and maps their relationships.

        Args:
            skills_dir: Path to the directory containing skill folders.
            save_to_file: Whether to save the result as 'relationships.json' in the dir.

        Returns:
            A list of relationship dictionaries.
        """
        logger.info("Starting relationship analysis in: %s", skills_dir)

        if not os.path.exists(skills_dir):
            raise FileNotFoundError(f"Directory not found: {skills_dir}")

        skills_metadata = self._load_skills_metadata(skills_dir)
        if len(skills_metadata) < 2:
            logger.warning("Not enough skills found to analyze relationships (need at least 2).")
            return []

        logger.info("Found %s skills. Analyzing potential connections...", len(skills_metadata))

        relationships = self._generate_relationship_graph(skills_metadata)

        if save_to_file and relationships:
            output_path = os.path.join(skills_dir, "relationships.json")
            try:
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(relationships, f, indent=2, ensure_ascii=False)
                logger.info("Relationships saved to: %s", output_path)
            except IOError as e:
                logger.error("Failed to save relationships file: %s", e)

        return relationships

    def _load_skills_metadata(self, root_dir: str) -> List[Dict[str, str]]:
        """
        Walks the directory to extract 'name' and 'description' from SKILL.md.
        """
        skills = []

        for entry in os.scandir(root_dir):
            if entry.is_dir():
                skill_path = entry.path
                skill_name = entry.name
                description = "No description provided."

                content_file = None
                if os.path.exists(os.path.join(skill_path, "SKILL.md")):
                    content_file = os.path.join(skill_path, "SKILL.md")

                if content_file:
                    try:
                        with open(content_file, "r", encoding="utf-8") as f:
                            raw_content = f.read()
                            description = self._extract_description(raw_content)
                    except Exception as e:
                        logger.warning("Could not read content for %s: %s", skill_name, e)

                skills.append(
                    {
                        "name": skill_name,
                        "description": description,
                    }
                )

        return skills

    def _extract_description(self, content: str) -> str:
        """Helper to parse description from markdown frontmatter or body."""
        frontmatter_match = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
        if frontmatter_match:
            fm_text = frontmatter_match.group(1)
            desc_match = re.search(r"description:\s*(.+)$", fm_text, re.MULTILINE)
            if desc_match:
                return desc_match.group(1).strip().strip('"').strip("'")

        clean_text = re.sub(r"#+\s.*", "", content)
        clean_text = re.sub(r"```.*?```", "", clean_text, flags=re.DOTALL)
        lines = [line.strip() for line in clean_text.split("\n") if line.strip()]

        if lines:
            return lines[0]

        return "No description available."

    def _extract_json_from_tags(self, content: str, tag_name: str) -> str:
        """Helper to extract content between XML-style tags."""
        start_tag = f"<{tag_name}>"
        end_tag = f"</{tag_name}>"

        if start_tag in content and end_tag in content:
            return content.split(start_tag)[1].split(end_tag)[0].strip()

        clean_content = content.replace("```json", "").replace("```", "").strip()

        return clean_content

    def _generate_relationship_graph(self, skills: List[Dict]) -> List[Dict]:
        """Calls LLM to infer edges between nodes."""
        skills_json = json.dumps(skills, indent=2)

        messages = [
            {"role": "system", "content": RELATIONSHIP_ANALYSIS_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": RELATIONSHIP_ANALYSIS_USER_PROMPT_TEMPLATE.format(
                    skills_list=skills_json,
                ),
            },
        ]

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
            )
            content = response.choices[0].message.content

            json_str = self._extract_json_from_tags(content, "Skill_Relationships")
            parsed_data = json.loads(json_str)

            edges = []
            if isinstance(parsed_data, list):
                edges = parsed_data
            elif isinstance(parsed_data, dict) and "relationships" in parsed_data:
                edges = parsed_data["relationships"]

            valid_edges = []
            valid_names = {s["name"] for s in skills}
            valid_types = {"similar_to", "belong_to", "compose_with", "depend_on"}

            for edge in edges:
                if not isinstance(edge, dict):
                    continue

                s_name = edge.get("source")
                t_name = edge.get("target")
                r_type = edge.get("type")

                if (
                    s_name in valid_names
                    and t_name in valid_names
                    and r_type in valid_types
                    and s_name != t_name
                ):
                    valid_edges.append(
                        {
                            "source": s_name,
                            "target": t_name,
                            "type": r_type,
                            "reason": edge.get("reason", "No reason provided"),
                        }
                    )

            logger.info("Identified %s valid relationships.", len(valid_edges))
            return valid_edges

        except json.JSONDecodeError as e:
            logger.error("Failed to parse JSON content: %s", e)
            logger.debug("Raw content was: %s", content)
            return []
        except Exception as e:
            logger.error("Failed to analyze relationships: %s", e)
            return []


class EmbeddingConfigError(ValueError):
    """Raised when scenario analysis lacks explicit embedding configuration."""


def require_embedding_config(
    *,
    api_key: Optional[str],
    base_url: Optional[str],
    model: Optional[str],
) -> tuple[str, str, str]:
    missing = []
    if not api_key:
        missing.append("EMBEDDING_API_KEY")
    if not base_url:
        missing.append("EMBEDDING_BASE_URL")
    if not model:
        missing.append("EMBEDDING_MODEL")
    if missing:
        raise EmbeddingConfigError(
            "Scenario analysis requires explicit embedding configuration: "
            + ", ".join(missing)
            + ". Pass CLI options or set the matching environment variables."
        )
    return str(api_key), str(base_url), str(model)


def text_cache_key(model: str, text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"{model}:{digest}"


def load_embedding_cache(path: Path, *, force: bool = False) -> Dict[str, List[float]]:
    if force or not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        return {}
    embeddings = payload.get("embeddings", payload)
    if not isinstance(embeddings, dict):
        return {}
    return {
        str(key): [float(x) for x in value]
        for key, value in embeddings.items()
        if isinstance(value, list) and all(isinstance(x, (int, float)) for x in value)
    }


def save_embedding_cache(path: Path, model: str, embeddings: Dict[str, List[float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump({"model": model, "count": len(embeddings), "embeddings": embeddings}, f, ensure_ascii=False, indent=2)
        f.write("\n")


class EmbeddingClient:
    """OpenAI-compatible embeddings client with batching, retry, and shape validation."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout: float = 120.0,
        retries: int = 3,
        batch_size: int = 64,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.retries = retries
        self.batch_size = batch_size

        if self.batch_size < 1:
            raise ValueError("Embedding batch_size must be at least 1.")

    def embed_texts(
        self,
        texts: List[str],
        *,
        cache: Optional[Dict[str, List[float]]] = None,
        cache_path: Optional[Path] = None,
    ) -> List[List[float]]:
        if not texts:
            return []
        cache = cache if cache is not None else {}
        keys = [text_cache_key(self.model, text) for text in texts]
        missing_indices = [index for index, key in enumerate(keys) if key not in cache]

        for start in range(0, len(missing_indices), self.batch_size):
            batch_indices = missing_indices[start : start + self.batch_size]
            vectors = self._retry_request([texts[index] for index in batch_indices])
            for index, vector in zip(batch_indices, vectors):
                cache[keys[index]] = vector
            if cache_path is not None:
                save_embedding_cache(cache_path, self.model, cache)

        vectors = [cache[key] for key in keys]
        dimensions = {len(vector) for vector in vectors}
        if len(dimensions) > 1:
            raise ValueError(f"Embedding dimensions are inconsistent: {sorted(dimensions)}")
        return vectors

    def _retry_request(self, texts: List[str]) -> List[List[float]]:
        last_error: Optional[Exception] = None
        for attempt in range(1, self.retries + 1):
            try:
                return self._request_embeddings(texts)
            except (
                urllib.error.HTTPError,
                urllib.error.URLError,
                TimeoutError,
                json.JSONDecodeError,
                ValueError,
                RuntimeError,
            ) as exc:
                last_error = exc
                if attempt < self.retries:
                    time.sleep(min(2**attempt, 20))
        raise RuntimeError(f"Embedding request failed: {last_error}") from last_error

    def _request_embeddings(self, texts: List[str]) -> List[List[float]]:
        url = self.base_url + "/embeddings"
        body = json.dumps({"model": self.model, "input": texts}).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                payload = json.loads(response.read().decode(charset))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code} from embeddings API: {body}") from exc

        data = payload.get("data")
        if not isinstance(data, list):
            raise ValueError(f"Unexpected embeddings response: {payload}")
        ordered = sorted(data, key=lambda item: int(item.get("index", 0)))
        vectors: List[List[float]] = []
        for item in ordered:
            vector = item.get("embedding")
            if not isinstance(vector, list) or not vector:
                raise ValueError(f"Invalid embedding item: {item}")
            vectors.append([float(x) for x in vector])
        if len(vectors) != len(texts):
            raise ValueError(f"Embedding count mismatch: expected {len(texts)}, got {len(vectors)}")
        return vectors


class GraphDependencyError(ImportError):
    """Raised when scenario graph optional dependencies are not installed."""


def require_graph_dependencies() -> tuple[Any, Any, Any, Any]:
    missing = []
    try:
        import numpy as np  # type: ignore
    except ImportError:
        np = None
        missing.append("numpy")
    try:
        import faiss  # type: ignore
    except ImportError:
        faiss = None
        missing.append("faiss-cpu")
    try:
        import networkx as nx  # type: ignore
    except ImportError:
        nx = None
        missing.append("networkx")
    try:
        from sklearn.cluster import AgglomerativeClustering  # type: ignore
    except ImportError:
        AgglomerativeClustering = None
        missing.append("scikit-learn")

    if missing:
        raise GraphDependencyError(
            "Scenario analysis requires optional graph dependencies: "
            + ", ".join(missing)
            + '. Install them with `pip install "skillnet-ai[graph]"`.'
        )
    if not hasattr(nx.community, "louvain_communities"):
        raise GraphDependencyError(
            "Scenario analysis requires networkx.community.louvain_communities. "
            'Install graph support with `pip install "skillnet-ai[graph]"`.'
        )
    return np, faiss, nx, AgglomerativeClustering


def normalize_scenario(text: str) -> str:
    return " ".join(str(text).split()).strip(" .;:-")


def load_scenarios_from_rows(skills: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    scenario_records: List[Dict[str, Any]] = []
    seen: set[tuple[int, str, str]] = set()
    for skill in skills:
        if "error" in skill:
            continue
        skill_id = int(skill.get("skill_id") or 0)
        skill_name = str(skill.get("skill_name") or "")
        for side in ("pre", "post"):
            values = skill.get(f"{side}_scenarios", [])
            if not isinstance(values, list):
                continue
            for text in values:
                scenario = normalize_scenario(str(text))
                if not scenario:
                    continue
                key = (skill_id, side, scenario.lower())
                if key in seen:
                    continue
                seen.add(key)
                scenario_records.append(
                    {
                        "raw_scenario_id": len(scenario_records) + 1,
                        "skill_id": skill_id,
                        "skill_name": skill_name,
                        "side": side,
                        "scenario": scenario,
                    }
                )
    return skills, scenario_records


def _l2_normalize(matrix: Any, np: Any) -> Any:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


def _build_similarity_communities(
    embeddings: Any,
    *,
    top_neighbors: int,
    threshold: float,
    seed: int,
    np: Any,
    faiss: Any,
    nx: Any,
) -> tuple[Any, List[List[int]]]:
    normalized = np.ascontiguousarray(_l2_normalize(embeddings, np).astype("float32"))
    index = faiss.IndexFlatIP(normalized.shape[1])
    index.add(normalized)
    search_k = min(normalized.shape[0], top_neighbors + 1)
    scores, indices = index.search(normalized, search_k)

    graph = nx.Graph()
    graph.add_nodes_from(range(normalized.shape[0]))
    for source_idx, (row_scores, row_indices) in enumerate(zip(scores, indices)):
        for score, target_idx in zip(row_scores, row_indices):
            target_idx = int(target_idx)
            if target_idx < 0 or target_idx == source_idx:
                continue
            score = float(score)
            if score < threshold:
                continue
            left, right = sorted((source_idx, target_idx))
            if graph.has_edge(left, right):
                if score > graph[left][right]["weight"]:
                    graph[left][right]["weight"] = score
                continue
            graph.add_edge(left, right, weight=score)

    communities = list(nx.community.louvain_communities(graph, weight="weight", seed=seed))
    communities = [sorted(list(community)) for community in communities if community]
    communities.sort(key=lambda item: (len(item), item[0]), reverse=True)
    return graph, communities


def _complete_linkage_labels(distance_matrix: Any, threshold_distance: float, AgglomerativeClustering: Any) -> Any:
    try:
        model = AgglomerativeClustering(
            n_clusters=None,
            metric="precomputed",
            linkage="complete",
            distance_threshold=threshold_distance,
        )
    except TypeError:
        model = AgglomerativeClustering(
            n_clusters=None,
            affinity="precomputed",
            linkage="complete",
            distance_threshold=threshold_distance,
        )
    return model.fit_predict(distance_matrix)


def _split_community_complete_linkage(
    community: List[int],
    embeddings: Any,
    *,
    cluster_threshold: float,
    np: Any,
    AgglomerativeClustering: Any,
) -> List[List[int]]:
    if len(community) <= 1:
        return [community]
    sub = _l2_normalize(embeddings[community].astype("float32"), np)
    similarity = np.clip(sub @ sub.T, -1.0, 1.0)
    distance = 1.0 - similarity
    np.fill_diagonal(distance, 0.0)
    labels = _complete_linkage_labels(distance, 1.0 - cluster_threshold, AgglomerativeClustering)
    clusters: Dict[int, List[int]] = defaultdict(list)
    for local_idx, label in enumerate(labels):
        clusters[int(label)].append(community[local_idx])
    result = list(clusters.values())
    result.sort(key=lambda item: (len(item), item[0]), reverse=True)
    return result


def _choose_canonical(records: List[Dict[str, Any]], member_indices: List[int]) -> str:
    texts = [records[i]["scenario"] for i in member_indices]
    counts = Counter(text.lower() for text in texts)
    return sorted(texts, key=lambda text: (-counts[text.lower()], len(text), text.lower()))[0]


def _deduplicate_records(
    scenario_records: List[Dict[str, Any]],
    embeddings: Any,
    communities: List[List[int]],
    *,
    cluster_threshold: float,
    np: Any,
    AgglomerativeClustering: Any,
) -> tuple[List[Dict[str, Any]], Dict[int, int]]:
    clusters: List[Dict[str, Any]] = []
    raw_to_cluster: Dict[int, int] = {}
    for community_id, community in enumerate(communities, start=1):
        subclusters = _split_community_complete_linkage(
            community,
            embeddings,
            cluster_threshold=cluster_threshold,
            np=np,
            AgglomerativeClustering=AgglomerativeClustering,
        )
        for subcluster in subclusters:
            cluster_id = len(clusters) + 1
            canonical = _choose_canonical(scenario_records, subcluster)
            members = []
            sides = Counter()
            skill_ids: set[int] = set()
            for index in sorted(subcluster):
                record = scenario_records[index]
                raw_to_cluster[int(record["raw_scenario_id"])] = cluster_id
                sides[str(record["side"])] += 1
                skill_ids.add(int(record["skill_id"]))
                members.append(record)
            clusters.append(
                {
                    "scenario_id": cluster_id,
                    "canonical_scenario": canonical,
                    "size": len(subcluster),
                    "community_id": community_id,
                    "side_counts": dict(sides),
                    "skill_count": len(skill_ids),
                    "members": members,
                }
            )
    return clusters, raw_to_cluster


def _build_skill_scenario_map(
    skills: List[Dict[str, Any]],
    scenario_records: List[Dict[str, Any]],
    raw_to_cluster: Dict[int, int],
    clusters: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    canonical_by_id = {int(cluster["scenario_id"]): cluster["canonical_scenario"] for cluster in clusters}
    by_skill: Dict[int, Dict[str, List[int]]] = defaultdict(lambda: {"pre": [], "post": []})
    for record in scenario_records:
        cluster_id = raw_to_cluster.get(int(record["raw_scenario_id"]))
        if cluster_id is None:
            continue
        side = str(record["side"])
        values = by_skill[int(record["skill_id"])][side]
        if cluster_id not in values:
            values.append(cluster_id)

    rows: List[Dict[str, Any]] = []
    for skill in skills:
        if "error" in skill:
            continue
        skill_id = int(skill.get("skill_id") or 0)
        pre_ids = by_skill[skill_id]["pre"]
        post_ids = by_skill[skill_id]["post"]
        rows.append(
            {
                "skill_id": skill_id,
                "skill_name": skill.get("skill_name"),
                "pre_scenario_ids": pre_ids,
                "post_scenario_ids": post_ids,
                "pre_scenarios": [canonical_by_id[item] for item in pre_ids],
                "post_scenarios": [canonical_by_id[item] for item in post_ids],
            }
        )
    return sorted(rows, key=lambda item: int(item["skill_id"]))


def deduplicate_scenarios(
    skills: List[Dict[str, Any]],
    vectors: List[List[float]],
    *,
    top_neighbors: int = 100,
    graph_threshold: float = 0.82,
    cluster_threshold: float = 0.88,
    seed: int = 13,
) -> Dict[str, Any]:
    np, faiss, nx, AgglomerativeClustering = require_graph_dependencies()
    normalized_skills, scenario_records = load_scenarios_from_rows(skills)
    if not scenario_records:
        return {
            "meta": {
                "raw_scenario_count": 0,
                "canonical_scenario_count": 0,
                "method": "FAISS sparse similarity graph -> Louvain communities -> complete-linkage agglomerative clustering",
            },
            "scenarios": [],
            "skill_scenarios": [],
        }
    if len(vectors) != len(scenario_records):
        raise ValueError(f"Expected {len(scenario_records)} scenario embeddings, got {len(vectors)}.")

    embeddings = np.array(vectors, dtype="float32")
    graph, communities = _build_similarity_communities(
        embeddings,
        top_neighbors=top_neighbors,
        threshold=graph_threshold,
        seed=seed,
        np=np,
        faiss=faiss,
        nx=nx,
    )
    clusters, raw_to_cluster = _deduplicate_records(
        scenario_records,
        embeddings,
        communities,
        cluster_threshold=cluster_threshold,
        np=np,
        AgglomerativeClustering=AgglomerativeClustering,
    )
    skill_scenarios = _build_skill_scenario_map(normalized_skills, scenario_records, raw_to_cluster, clusters)
    clusters.sort(key=lambda item: int(item["scenario_id"]))
    return {
        "meta": {
            "raw_scenario_count": len(scenario_records),
            "canonical_scenario_count": len(clusters),
            "louvain_community_count": len(communities),
            "similarity_edge_count": graph.number_of_edges(),
            "top_neighbors": top_neighbors,
            "graph_threshold": graph_threshold,
            "cluster_threshold": cluster_threshold,
            "method": "FAISS sparse similarity graph -> Louvain communities -> complete-linkage agglomerative clustering",
        },
        "scenarios": clusters,
        "skill_scenarios": skill_scenarios,
    }


def _scenario_by_id(dedup: Dict[str, Any]) -> Dict[int, str]:
    return {
        int(item["scenario_id"]): str(item.get("canonical_scenario") or "")
        for item in dedup.get("scenarios", [])
        if isinstance(item, dict) and "scenario_id" in item
    }


def _skill_scenarios(dedup: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [item for item in dedup.get("skill_scenarios", []) if isinstance(item, dict)]


def build_alignment_candidates(
    dedup: Dict[str, Any],
    vectors: List[List[float]],
    *,
    top_k: int,
    min_score: float,
) -> List[Dict[str, Any]]:
    np, faiss, _nx, _AgglomerativeClustering = require_graph_dependencies()
    scenario_by_id = _scenario_by_id(dedup)
    skills = _skill_scenarios(dedup)
    scenario_ids = sorted(scenario_by_id)
    if not scenario_ids:
        return []
    if len(vectors) != len(scenario_ids):
        raise ValueError(f"Expected {len(scenario_ids)} alignment embeddings, got {len(vectors)}.")

    scenario_index = {scenario_id: idx for idx, scenario_id in enumerate(scenario_ids)}
    embeddings = np.array(vectors, dtype="float32")
    normalized = np.ascontiguousarray(_l2_normalize(embeddings, np).astype("float32"))

    pre_ids = sorted({int(sid) for skill in skills for sid in skill.get("pre_scenario_ids", [])})
    post_ids = sorted({int(sid) for skill in skills for sid in skill.get("post_scenario_ids", [])})
    pre_ids = [sid for sid in pre_ids if sid in scenario_index]
    post_ids = [sid for sid in post_ids if sid in scenario_index]
    if not pre_ids or not post_ids:
        return []

    pre_matrix = np.ascontiguousarray(normalized[[scenario_index[sid] for sid in pre_ids]].astype("float32"))
    index = faiss.IndexFlatIP(pre_matrix.shape[1])
    index.add(pre_matrix)
    search_k = min(len(pre_ids), top_k)
    scores, indices = index.search(
        np.ascontiguousarray(normalized[[scenario_index[sid] for sid in post_ids]].astype("float32")),
        search_k,
    )

    skills_by_pre: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    skills_by_post: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    for skill in skills:
        for sid in skill.get("pre_scenario_ids", []):
            skills_by_pre[int(sid)].append(skill)
        for sid in skill.get("post_scenario_ids", []):
            skills_by_post[int(sid)].append(skill)

    candidates: List[Dict[str, Any]] = []
    seen: set[tuple[int, int, int, int]] = set()
    for post_sid, row_scores, row_indices in zip(post_ids, scores, indices):
        source_skills = skills_by_post.get(post_sid, [])
        for score, pre_position in zip(row_scores, row_indices):
            if int(pre_position) < 0:
                continue
            score = float(score)
            if score < min_score:
                continue
            pre_sid = pre_ids[int(pre_position)]
            target_skills = skills_by_pre.get(pre_sid, [])
            for source_skill in source_skills:
                for target_skill in target_skills:
                    source_skill_id = int(source_skill.get("skill_id") or 0)
                    target_skill_id = int(target_skill.get("skill_id") or 0)
                    if source_skill_id == target_skill_id:
                        continue
                    key = (source_skill_id, post_sid, target_skill_id, pre_sid)
                    if key in seen:
                        continue
                    seen.add(key)
                    candidates.append(
                        {
                            "alignment_id": f"align-{len(candidates)+1:07d}",
                            "source_skill_id": source_skill_id,
                            "source_skill_name": source_skill.get("skill_name"),
                            "source_post_scenario_id": post_sid,
                            "source_post_scenario": scenario_by_id[post_sid],
                            "target_skill_id": target_skill_id,
                            "target_skill_name": target_skill.get("skill_name"),
                            "target_pre_scenario_id": pre_sid,
                            "target_pre_scenario": scenario_by_id[pre_sid],
                            "retrieval_score": round(score, 6),
                        }
                    )

    candidates.sort(
        key=lambda item: (
            -float(item["retrieval_score"]),
            int(item["source_skill_id"]),
            int(item["target_skill_id"]),
            int(item["source_post_scenario_id"]),
            int(item["target_pre_scenario_id"]),
        )
    )
    for index_number, item in enumerate(candidates, start=1):
        item["alignment_id"] = f"align-{index_number:07d}"
    return candidates


def is_used_alignment(row: Dict[str, Any], *, min_confidence: int) -> bool:
    if row.get("compatible") is not True:
        return False
    try:
        confidence = int(row.get("confidence") or 0)
    except (TypeError, ValueError):
        confidence = 0
    if confidence < min_confidence:
        return False
    alignment_type = str(row.get("alignment_type") or "")
    return alignment_type not in {"duplicate_or_alternative", "topical_only", "incompatible"}


def _as_int_list(values: Any) -> List[int]:
    if not isinstance(values, list):
        return []
    result: List[int] = []
    for value in values:
        try:
            result.append(int(value))
        except (TypeError, ValueError):
            continue
    return sorted(set(result))


def _build_nodes(
    skill_scenarios: List[Dict[str, Any]],
    alignments: List[Dict[str, Any]],
    scenario_by_id: Dict[int, str],
) -> List[Dict[str, Any]]:
    nodes_by_id: Dict[int, Dict[str, Any]] = {}
    for skill in skill_scenarios:
        try:
            skill_id = int(skill.get("skill_id") or 0)
        except (TypeError, ValueError):
            continue
        if skill_id <= 0:
            continue
        pre_ids = _as_int_list(skill.get("pre_scenario_ids"))
        post_ids = _as_int_list(skill.get("post_scenario_ids"))
        node = {
            "id": skill_id,
            "skill_id": skill_id,
            "skill_name": str(skill.get("skill_name") or ""),
            "pre_scenario_ids": pre_ids,
            "post_scenario_ids": post_ids,
            "pre_scenarios": [scenario_by_id.get(item, "") for item in pre_ids],
            "post_scenarios": [scenario_by_id.get(item, "") for item in post_ids],
        }
        nodes_by_id[skill_id] = node

    for row in alignments:
        for prefix in ("source", "target"):
            try:
                skill_id = int(row.get(f"{prefix}_skill_id") or 0)
            except (TypeError, ValueError):
                continue
            if skill_id <= 0 or skill_id in nodes_by_id:
                continue
            nodes_by_id[skill_id] = {
                "id": skill_id,
                "skill_id": skill_id,
                "skill_name": str(row.get(f"{prefix}_skill_name") or ""),
            }
    return [nodes_by_id[key] for key in sorted(nodes_by_id)]


def _edge_connection(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "alignment_id": row.get("alignment_id"),
        "source_post_scenario_id": row.get("source_post_scenario_id"),
        "source_post_scenario": row.get("source_post_scenario"),
        "target_pre_scenario_id": row.get("target_pre_scenario_id"),
        "target_pre_scenario": row.get("target_pre_scenario"),
        "retrieval_score": row.get("retrieval_score"),
        "alignment_type": row.get("alignment_type"),
        "confidence": row.get("confidence"),
        "reason": row.get("reason"),
    }


def _average_number(values: Iterable[Any]) -> float:
    numbers: List[float] = []
    for value in values:
        try:
            numbers.append(float(value))
        except (TypeError, ValueError):
            continue
    if not numbers:
        return 0.0
    return round(sum(numbers) / len(numbers), 6)


def _build_edges(alignments: List[Dict[str, Any]], *, min_confidence: int) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    used_alignments = [row for row in alignments if is_used_alignment(row, min_confidence=min_confidence)]
    grouped: Dict[tuple[int, int], List[Dict[str, Any]]] = defaultdict(list)
    for row in used_alignments:
        try:
            source = int(row.get("source_skill_id") or 0)
            target = int(row.get("target_skill_id") or 0)
        except (TypeError, ValueError):
            continue
        if source <= 0 or target <= 0 or source == target:
            continue
        grouped[(source, target)].append(row)

    edges: List[Dict[str, Any]] = []
    for edge_id, ((source, target), rows) in enumerate(sorted(grouped.items()), start=1):
        rows.sort(key=lambda row: str(row.get("alignment_id") or ""))
        confidences = [row.get("confidence") for row in rows]
        retrieval_scores = [row.get("retrieval_score") for row in rows]
        alignment_types = sorted({str(row.get("alignment_type") or "") for row in rows if row.get("alignment_type")})
        edges.append(
            {
                "id": edge_id,
                "source": source,
                "target": target,
                "source_skill_id": source,
                "source_skill_name": rows[0].get("source_skill_name"),
                "target_skill_id": target,
                "target_skill_name": rows[0].get("target_skill_name"),
                "relation": "compose_with",
                "alignment_count": len(rows),
                "alignment_types": alignment_types,
                "avg_confidence": _average_number(confidences),
                "max_confidence": max((int(value or 0) for value in confidences), default=0),
                "avg_retrieval_score": _average_number(retrieval_scores),
                "max_retrieval_score": max((float(value or 0.0) for value in retrieval_scores), default=0.0),
                "skill_connection": f"{rows[0].get('source_skill_name')} -> {rows[0].get('target_skill_name')}",
                "scenario_connections": [_edge_connection(row) for row in rows],
            }
        )
    return edges, used_alignments


def _graph_stats(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> Dict[str, Any]:
    out_degree = Counter(int(edge["source"]) for edge in edges)
    in_degree = Counter(int(edge["target"]) for edge in edges)
    connected_skill_ids = set(out_degree) | set(in_degree)
    source_only = 0
    sink_only = 0
    bridge = 0
    isolated = 0
    for node in nodes:
        node_id = int(node["id"])
        has_in = in_degree[node_id] > 0
        has_out = out_degree[node_id] > 0
        if has_in and has_out:
            bridge += 1
        elif has_out:
            source_only += 1
        elif has_in:
            sink_only += 1
        else:
            isolated += 1
    return {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "connected_skill_count": len(connected_skill_ids),
        "source_only_skills": source_only,
        "sink_only_skills": sink_only,
        "bridge_skills": bridge,
        "isolated_skills": isolated,
        "max_out_degree": max(out_degree.values(), default=0),
        "max_in_degree": max(in_degree.values(), default=0),
    }


def build_skill_graph(
    dedup: Dict[str, Any],
    alignments: List[Dict[str, Any]],
    *,
    min_confidence: int = 3,
) -> Dict[str, Any]:
    scenario_by_id = _scenario_by_id(dedup)
    skill_scenarios = _skill_scenarios(dedup)
    nodes = _build_nodes(
        skill_scenarios,
        alignments,
        scenario_by_id,
    )
    edges, used_alignments = _build_edges(alignments, min_confidence=min_confidence)
    nodes_by_id = {int(node["id"]): node for node in nodes}
    for edge in edges:
        for prefix in ("source", "target"):
            skill_id = int(edge[f"{prefix}_skill_id"])
            if skill_id in nodes_by_id:
                continue
            nodes_by_id[skill_id] = {
                "id": skill_id,
                "skill_id": skill_id,
                "skill_name": str(edge.get(f"{prefix}_skill_name") or ""),
            }
    nodes = [nodes_by_id[key] for key in sorted(nodes_by_id)]
    stats = _graph_stats(nodes, edges)
    return {
        "directed": True,
        "multigraph": False,
        "meta": {
            "min_confidence": min_confidence,
            "raw_scenario_count": len(scenario_by_id),
            "raw_skill_scenario_count": len(skill_scenarios),
            "alignment_count": len(alignments),
            "used_alignment_count": len(used_alignments),
            "node_type": "skill",
            "edge_type": "compose_with",
            **stats,
        },
        "nodes": nodes,
        "edges": edges,
        "used_alignments": used_alignments,
    }


def relationships_from_graph(graph: Dict[str, Any]) -> List[Dict[str, Any]]:
    relationships: List[Dict[str, Any]] = []
    for edge in graph.get("edges", []):
        if not isinstance(edge, dict):
            continue
        reason = ""
        connections = edge.get("scenario_connections")
        if isinstance(connections, list) and connections:
            reason = str(connections[0].get("reason") or "")
        relationships.append(
            {
                "source": edge.get("source_skill_name"),
                "target": edge.get("target_skill_name"),
                "type": "compose_with",
                "reason": reason or f"{edge.get('source_skill_name')} can feed {edge.get('target_skill_name')} via scenario handoff.",
                "evidence_count": edge.get("alignment_count", 0),
            }
        )
    return relationships


DEDUP_EMBED_INSTRUCTION = "Instruct: Retrieve scenarios that describe the same real-world condition.\nQuery: "
ALIGN_EMBED_INSTRUCTION = "Instruct: Retrieve scenarios that describe compatible real-world task states.\nQuery: "
ALIGNMENT_TYPES = {
    "artifact_handoff",
    "data_state_handoff",
    "environment_state_handoff",
    "evidence_or_metadata_handoff",
    "same_state_merge",
    "incompatible",
    "duplicate_or_alternative",
    "topical_only",
}
REDUNDANCY_TYPES = {
    "none",
    "same_capability",
    "near_duplicate",
    "format_variant",
    "same_state_restatement",
    "replacement_not_handoff",
    "unclear",
}


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _read_rows(path: Path, field_name: str) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    payload = _read_json(path)
    if isinstance(payload, dict) and isinstance(payload.get(field_name), list):
        return [row for row in payload[field_name] if isinstance(row, dict)]
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    raise ValueError(f"{path} must contain a JSON array or object field '{field_name}'")


def _read_existing_skill_scenarios(path: Path) -> List[Dict[str, Any]]:
    return _read_rows(path, "skills")


def _read_existing_alignments(path: Path) -> List[Dict[str, Any]]:
    return _read_rows(path, "alignments")


def _read_existing_redundancy_reviews(path: Path) -> List[Dict[str, Any]]:
    return _read_rows(path, "reviews")


def _parse_model_json(text: str) -> Dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?", "", stripped, flags=re.IGNORECASE).strip()
        stripped = re.sub(r"```$", "", stripped).strip()
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
        if not match:
            raise
        payload = json.loads(match.group(0))
    if not isinstance(payload, dict):
        raise ValueError("Model output is not a JSON object")
    return payload


def _normalize_scenarios(value: Any) -> List[str]:
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, list):
        values = value
    else:
        values = []
    normalized: List[str] = []
    seen: set[str] = set()
    for item in values:
        text = re.sub(r"\s+", " ", str(item)).strip(" .;:-")
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(text)
    return normalized


def _clamp_confidence(value: Any) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 1
    return max(1, min(5, number))


def _clamp_int(value: Any, *, low: int, high: int, default: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(low, min(high, number))


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized == "true":
            return True
        if normalized == "false":
            return False
    raise ValueError("Expected a JSON boolean")


class ScenarioSkillGraphAnalyzer:
    """Builds a scenario-level workflow graph for a local skill folder."""

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "gpt-4o",
        embedding_api_key: Optional[str] = None,
        embedding_base_url: Optional[str] = None,
        embedding_model: Optional[str] = None,
        max_workers: int = 4,
        top_k: int = 30,
        min_retrieval_score: float = 0.72,
        top_neighbors: int = 100,
        graph_threshold: float = 0.82,
        cluster_threshold: float = 0.88,
        min_confidence: int = 3,
        drop_overlap_score: int = 4,
        timeout: float = 120.0,
        retries: int = 3,
        embedding_batch_size: int = 64,
        progress_callback: Optional[Callable[[str], None]] = None,
    ):
        self.api_key = api_key or os.getenv("API_KEY")
        self.base_url = base_url or os.getenv("BASE_URL") or "https://api.openai.com/v1"
        self.model = model
        self.max_workers = max_workers
        self.top_k = top_k
        self.min_retrieval_score = min_retrieval_score
        self.top_neighbors = top_neighbors
        self.graph_threshold = graph_threshold
        self.cluster_threshold = cluster_threshold
        self.min_confidence = min_confidence
        self.drop_overlap_score = drop_overlap_score
        self.timeout = timeout
        self.retries = retries
        self.progress_callback = progress_callback

        if not self.api_key:
            raise ValueError("API Key is missing. Please provide it in init or set API_KEY environment variable.")
        if self.max_workers < 1:
            raise ValueError("max_workers must be at least 1.")
        if self.top_k < 1:
            raise ValueError("top_k must be at least 1.")
        if self.drop_overlap_score < 1 or self.drop_overlap_score > 5:
            raise ValueError("drop_overlap_score must be between 1 and 5.")

        embedding_key, embedding_url, embedding_model_name = require_embedding_config(
            api_key=embedding_api_key or os.getenv("EMBEDDING_API_KEY"),
            base_url=embedding_base_url or os.getenv("EMBEDDING_BASE_URL"),
            model=embedding_model or os.getenv("EMBEDDING_MODEL"),
        )

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=timeout)
        self.embedding_model = embedding_model_name
        self.embedding_client = EmbeddingClient(
            api_key=embedding_key,
            base_url=embedding_url,
            model=embedding_model_name,
            timeout=timeout,
            retries=retries,
            batch_size=embedding_batch_size,
        )

    def analyze_local_skills(
        self,
        skills_dir: str,
        *,
        output_dir: Optional[Union[str, Path]] = None,
        force: bool = False,
        save_to_file: bool = True,
    ) -> Dict[str, Any]:
        skills_root = Path(skills_dir)
        if not skills_root.exists():
            raise FileNotFoundError(f"Directory not found: {skills_dir}")
        if not skills_root.is_dir():
            raise NotADirectoryError(f"Not a directory: {skills_dir}")
        output_path = Path(output_dir) if output_dir is not None else skills_root / "skillnet_graph"

        require_graph_dependencies()
        if save_to_file:
            output_path.mkdir(parents=True, exist_ok=True)

        skill_rows = self._load_skill_rows(skills_root)
        self._emit_progress(f"loaded {len(skill_rows)} local skills")
        if len(skill_rows) < 2:
            empty_result = self._empty_result(output_path, skill_rows)
            if save_to_file:
                self._write_all_outputs(output_path, empty_result)
            return empty_result

        existing_skill_scenarios = (
            []
            if force or not save_to_file
            else _read_existing_skill_scenarios(output_path / "skill_scenarios.json")
        )
        self._emit_progress(f"extracting scenarios with workers={self.max_workers}")
        skill_scenarios = self._extract_all_skill_scenarios(
            skill_rows,
            existing_rows=existing_skill_scenarios,
            output_path=output_path,
            save_to_file=save_to_file,
        )
        extraction_failed_count = sum(1 for row in skill_scenarios if "error" in row)
        extraction_success_count = len(skill_scenarios) - extraction_failed_count
        self._emit_progress(
            f"scenario extraction complete: success={extraction_success_count}, failed={extraction_failed_count}"
        )
        if save_to_file:
            _write_json(output_path / "skill_scenarios.json", {"skills": skill_scenarios})
        if not extraction_success_count:
            raise RuntimeError("Scenario extraction failed for all skills. Check API configuration and model output.")

        _, scenario_records = load_scenarios_from_rows(skill_scenarios)
        self._emit_progress(f"embedding {len(scenario_records)} raw scenarios for deduplication")
        dedup_cache_path = output_path / "scenario_embedding_cache.json"
        dedup_cache = load_embedding_cache(dedup_cache_path, force=force) if save_to_file else {}
        dedup_texts = [DEDUP_EMBED_INSTRUCTION + record["scenario"] for record in scenario_records]
        dedup_vectors = self.embedding_client.embed_texts(
            dedup_texts,
            cache=dedup_cache,
            cache_path=dedup_cache_path if save_to_file else None,
        )
        if save_to_file:
            save_embedding_cache(dedup_cache_path, self.embedding_model, dedup_cache)

        dedup = deduplicate_scenarios(
            skill_scenarios,
            dedup_vectors,
            top_neighbors=self.top_neighbors,
            graph_threshold=self.graph_threshold,
            cluster_threshold=self.cluster_threshold,
        )
        dedup["meta"].update(
            {
                "mode": "scenario",
                "embedding_model": self.embedding_model,
            }
        )
        self._emit_progress(
            "scenario deduplication complete: raw={}, canonical={}".format(
                dedup.get("meta", {}).get("raw_scenario_count", len(scenario_records)),
                len(dedup.get("scenarios", [])),
            )
        )
        if save_to_file:
            _write_json(output_path / "scenario_dedup.json", dedup)

        scenario_ids = sorted(int(item["scenario_id"]) for item in dedup.get("scenarios", []))
        scenario_by_id = {
            int(item["scenario_id"]): str(item.get("canonical_scenario") or "")
            for item in dedup.get("scenarios", [])
            if isinstance(item, dict) and "scenario_id" in item
        }
        self._emit_progress(f"embedding {len(scenario_ids)} canonical scenarios for alignment retrieval")
        alignment_cache_path = output_path / "scenario_alignment_embedding_cache.json"
        alignment_cache = load_embedding_cache(alignment_cache_path, force=force) if save_to_file else {}
        alignment_texts = [ALIGN_EMBED_INSTRUCTION + scenario_by_id[sid] for sid in scenario_ids]
        alignment_vectors = self.embedding_client.embed_texts(
            alignment_texts,
            cache=alignment_cache,
            cache_path=alignment_cache_path if save_to_file else None,
        )
        if save_to_file:
            save_embedding_cache(alignment_cache_path, self.embedding_model, alignment_cache)

        candidates = build_alignment_candidates(
            dedup,
            alignment_vectors,
            top_k=self.top_k,
            min_score=self.min_retrieval_score,
        )
        self._emit_progress(
            "alignment retrieval complete: candidates={}, top_k={}, min_score={}".format(
                len(candidates), self.top_k, self.min_retrieval_score
            )
        )
        existing_alignments = (
            []
            if force or not save_to_file
            else _read_existing_alignments(output_path / "scenario_alignment.json")
        )
        alignments = self._verify_alignment_candidates(
            candidates,
            dedup=dedup,
            output_path=output_path,
            save_to_file=save_to_file,
            existing_rows=existing_alignments,
        )
        keep_alignments = [
            row
            for row in alignments
            if row.get("compatible") is True
            and int(row.get("confidence") or 0) >= self.min_confidence
            and "error" not in row
        ]
        self._emit_progress(
            f"alignment verification complete: evaluated={len(alignments)}, compatible={len(keep_alignments)}"
        )
        existing_redundancy_reviews = (
            []
            if force or not save_to_file
            else _read_existing_redundancy_reviews(output_path / "skill_edge_redundancy_reviews.json")
        )
        redundancy_reviews, nonredundant_alignments, dropped_alignments = self._review_edge_redundancy(
            skill_rows,
            keep_alignments,
            output_path=output_path,
            save_to_file=save_to_file,
            existing_reviews=existing_redundancy_reviews,
        )
        self._emit_progress(
            "redundancy review complete: pairs={}, kept_alignments={}, dropped_alignments={}".format(
                len(redundancy_reviews), len(nonredundant_alignments), len(dropped_alignments)
            )
        )
        graph = build_skill_graph(
            dedup,
            nonredundant_alignments,
            min_confidence=self.min_confidence,
        )
        graph["meta"].update(
            {
                "mode": "scenario",
                "model": self.model,
                "embedding_model": self.embedding_model,
                "top_k": self.top_k,
                "min_retrieval_score": self.min_retrieval_score,
                "skills_dir": str(skills_root),
            }
        )
        relationships = relationships_from_graph(graph)

        result = {
            "meta": {
                "mode": "scenario",
                "skills_dir": str(skills_root),
                "output_dir": str(output_path),
                "skill_count": len(skill_rows),
                "extraction_success_count": extraction_success_count,
                "extraction_failed_count": extraction_failed_count,
                "scenario_count": len(dedup.get("scenarios", [])),
                "candidate_count": len(candidates),
                "alignment_count": len(alignments),
                "alignment_failed_count": sum(1 for row in alignments if "error" in row),
                "compatible_alignment_count": len(keep_alignments),
                "nonredundant_alignment_count": len(nonredundant_alignments),
                "redundancy_review_count": len(redundancy_reviews),
                "relationship_count": len(relationships),
            },
            "skill_scenarios": skill_scenarios,
            "scenario_dedup": dedup,
            "scenario_alignment": {
                "meta": self._alignment_meta(dedup, candidates, alignments),
                "alignments": alignments,
            },
            "scenario_alignment_keep": {
                "meta": self._alignment_meta(dedup, candidates, keep_alignments),
                "alignments": keep_alignments,
            },
            "skill_edge_redundancy_reviews": {
                "meta": self._redundancy_meta(keep_alignments, redundancy_reviews, nonredundant_alignments, dropped_alignments),
                "reviews": redundancy_reviews,
                "dropped_alignments": dropped_alignments,
            },
            "scenario_alignment_nonredundant_keep": {
                "meta": self._redundancy_meta(keep_alignments, redundancy_reviews, nonredundant_alignments, dropped_alignments),
                "alignments": nonredundant_alignments,
            },
            "scenario_skill_graph": graph,
            "relationships": relationships,
        }
        if save_to_file:
            self._write_all_outputs(output_path, result)
        return result

    def _load_skill_rows(self, skills_root: Path) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for entry in sorted(skills_root.iterdir(), key=lambda item: item.name):
            if not entry.is_dir():
                continue
            skill_path = entry / "SKILL.md"
            if not skill_path.exists():
                continue
            rows.append(
                {
                    "skill_id": len(rows) + 1,
                    "skill_name": entry.name,
                    "skill_path": str(skill_path),
                    "local_path": str(entry),
                }
            )
        return rows

    def _extract_all_skill_scenarios(
        self,
        skill_rows: List[Dict[str, Any]],
        *,
        existing_rows: Optional[List[Dict[str, Any]]] = None,
        output_path: Optional[Path] = None,
        save_to_file: bool = False,
    ) -> List[Dict[str, Any]]:
        rows_by_id = self._existing_scenario_rows_by_id(skill_rows, existing_rows or [])
        pending = [skill for skill in skill_rows if int(skill["skill_id"]) not in rows_by_id]
        self._emit_progress(
            "scenario extraction jobs: skills={}, existing_ok={}, pending={}, workers={}".format(
                len(skill_rows), len(rows_by_id), len(pending), self.max_workers
            )
        )
        if pending:
            completed = 0
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_skill = {
                    executor.submit(self._extract_skill_scenarios, skill): skill for skill in pending
                }
                for future in concurrent.futures.as_completed(future_to_skill):
                    skill = future_to_skill[future]
                    try:
                        row = future.result()
                    except Exception as exc:
                        row = self._normalize_scenario_row({}, skill)
                        row["error"] = f"{type(exc).__name__}: {exc}"
                    rows_by_id[int(row["skill_id"])] = row
                    completed += 1
                    if save_to_file and output_path is not None:
                        self._write_skill_scenario_output(output_path, skill_rows, rows_by_id)
                    if "error" in row:
                        self._emit_progress(f"[{completed}/{len(pending)}] extraction failed: {row['skill_name']}")
                    else:
                        self._emit_progress(
                            "[{}/{}] extraction ok: {} pre={} post={}".format(
                                completed,
                                len(pending),
                                row["skill_name"],
                                len(row["pre_scenarios"]),
                                len(row["post_scenarios"]),
                            )
                        )
        return [rows_by_id[int(skill["skill_id"])] for skill in skill_rows if int(skill["skill_id"]) in rows_by_id]

    def _existing_scenario_rows_by_id(
        self,
        skill_rows: List[Dict[str, Any]],
        existing_rows: List[Dict[str, Any]],
    ) -> Dict[int, Dict[str, Any]]:
        skills_by_id = {int(row["skill_id"]): row for row in skill_rows}
        rows_by_id: Dict[int, Dict[str, Any]] = {}
        for row in existing_rows:
            if "error" in row or not row.get("pre_scenarios") or not row.get("post_scenarios"):
                continue
            try:
                skill_id = int(row.get("skill_id") or 0)
            except (TypeError, ValueError):
                continue
            skill = skills_by_id.get(skill_id)
            if not skill or not self._scenario_row_matches_skill(row, skill):
                continue
            normalized = self._normalize_scenario_row(row, skill)
            rows_by_id[skill_id] = normalized
        return rows_by_id

    def _scenario_row_matches_skill(self, row: Dict[str, Any], skill: Dict[str, Any]) -> bool:
        if str(row.get("skill_name") or "") != str(skill.get("skill_name") or ""):
            return False
        for key in ("skill_path", "local_path"):
            if row.get(key) and str(row.get(key)) != str(skill.get(key)):
                return False
        return True

    def _write_skill_scenario_output(
        self,
        output_path: Path,
        skill_rows: List[Dict[str, Any]],
        rows_by_id: Dict[int, Dict[str, Any]],
    ) -> None:
        rows = [rows_by_id[int(skill["skill_id"])] for skill in skill_rows if int(skill["skill_id"]) in rows_by_id]
        _write_json(output_path / "skill_scenarios.json", {"skills": rows})

    def _extract_skill_scenarios(self, skill: Dict[str, Any]) -> Dict[str, Any]:
        skill_md = Path(str(skill["skill_path"])).read_text(encoding="utf-8", errors="replace")
        prompt = SCENARIO_EXTRACTION_USER_PROMPT_TEMPLATE.format(
            skill_id=int(skill["skill_id"]),
            skill_name=str(skill["skill_name"]).replace('"', '\\"'),
            skill_md=skill_md,
        )
        last_error: Optional[Exception] = None
        for attempt in range(1, self.retries + 1):
            try:
                content = self._chat_json(
                    system_prompt=SCENARIO_EXTRACTION_SYSTEM_PROMPT,
                    user_prompt=prompt,
                )
                return self._normalize_scenario_row(_parse_model_json(content), skill)
            except Exception as exc:
                last_error = exc
                if attempt < self.retries:
                    time.sleep(min(2**attempt, 20))
        row = self._normalize_scenario_row({}, skill)
        row["error"] = f"{type(last_error).__name__}: {last_error}"
        return row

    def _normalize_scenario_row(self, parsed: Dict[str, Any], skill: Dict[str, Any]) -> Dict[str, Any]:
        pre = _normalize_scenarios(parsed.get("pre_scenarios"))
        post = _normalize_scenarios(parsed.get("post_scenarios"))
        if not pre:
            pre = ["Applicable task state requiring this skill"]
        if not post:
            post = ["Task state after applying this skill"]
        return {
            "skill_id": int(skill["skill_id"]),
            "skill_name": str(skill["skill_name"]),
            "skill_path": str(skill["skill_path"]),
            "local_path": str(skill["local_path"]),
            "pre_scenarios": pre,
            "post_scenarios": post,
        }

    def _verify_alignment_candidates(
        self,
        candidates: List[Dict[str, Any]],
        *,
        dedup: Dict[str, Any],
        output_path: Path,
        save_to_file: bool,
        existing_rows: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        rows_by_id = self._existing_alignment_rows_by_id(candidates, existing_rows or [])
        if not candidates:
            if save_to_file:
                self._write_alignment_outputs(output_path, dedup, candidates, [])
            return []
        pending = [candidate for candidate in candidates if str(candidate["alignment_id"]) not in rows_by_id]
        self._emit_progress(
            "verifying scenario alignment candidates: candidates={}, existing_ok={}, pending={}, workers={}".format(
                len(candidates), len(rows_by_id), len(pending), self.max_workers
            )
        )
        if pending:
            completed = 0
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_candidate = {
                    executor.submit(self._verify_alignment, candidate): candidate for candidate in pending
                }
                for future in concurrent.futures.as_completed(future_to_candidate):
                    candidate = future_to_candidate[future]
                    try:
                        parsed = future.result()
                        row = self._normalize_alignment_result(candidate, parsed)
                    except Exception as exc:
                        row = self._failed_alignment_row(candidate, f"{type(exc).__name__}: {exc}")
                    rows_by_id[str(row["alignment_id"])] = row
                    completed += 1
                    if save_to_file:
                        self._write_alignment_outputs(output_path, dedup, candidates, list(rows_by_id.values()))
                    status = (
                        "keep"
                        if row.get("compatible") and int(row.get("confidence") or 0) >= self.min_confidence
                        else "reject"
                    )
                    if "error" in row:
                        status = "failed"
                    self._emit_progress(
                        "[{}/{}] alignment {}: {} -> {} conf={} type={}".format(
                            completed,
                            len(pending),
                            status,
                            row.get("source_skill_name"),
                            row.get("target_skill_name"),
                            row.get("confidence"),
                            row.get("alignment_type"),
                        )
                    )
        elif save_to_file:
            self._write_alignment_outputs(output_path, dedup, candidates, list(rows_by_id.values()))
        return [rows_by_id[str(candidate["alignment_id"])] for candidate in candidates]

    def _existing_alignment_rows_by_id(
        self,
        candidates: List[Dict[str, Any]],
        existing_rows: List[Dict[str, Any]],
    ) -> Dict[str, Dict[str, Any]]:
        candidates_by_id = {str(candidate["alignment_id"]): candidate for candidate in candidates}
        rows_by_id: Dict[str, Dict[str, Any]] = {}
        for row in existing_rows:
            if "error" in row or "compatible" not in row:
                continue
            alignment_id = str(row.get("alignment_id") or "")
            candidate = candidates_by_id.get(alignment_id)
            if not candidate or not self._alignment_row_matches_candidate(row, candidate):
                continue
            try:
                rows_by_id[alignment_id] = self._normalize_alignment_result(candidate, row)
            except (TypeError, ValueError):
                continue
        return rows_by_id

    def _alignment_row_matches_candidate(self, row: Dict[str, Any], candidate: Dict[str, Any]) -> bool:
        for key in (
            "source_skill_id",
            "target_skill_id",
            "source_post_scenario_id",
            "target_pre_scenario_id",
        ):
            try:
                if int(row.get(key) or 0) != int(candidate.get(key) or 0):
                    return False
            except (TypeError, ValueError):
                return False
        for key in (
            "source_skill_name",
            "target_skill_name",
            "source_post_scenario",
            "target_pre_scenario",
        ):
            if str(row.get(key) or "") != str(candidate.get(key) or ""):
                return False
        return True

    def _failed_alignment_row(self, candidate: Dict[str, Any], error: str) -> Dict[str, Any]:
        row = dict(candidate)
        row.update(
            {
                "compatible": False,
                "alignment_type": "incompatible",
                "confidence": 1,
                "reason": "",
                "error": error,
            }
        )
        return row

    def _verify_alignment(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        prompt = self._build_alignment_prompt(candidate)
        last_error: Optional[Exception] = None
        for attempt in range(1, self.retries + 1):
            try:
                content = self._chat_json(
                    system_prompt=SCENARIO_ALIGNMENT_SYSTEM_PROMPT,
                    user_prompt=prompt,
                )
                return _parse_model_json(content)
            except Exception as exc:
                last_error = exc
                if attempt < self.retries:
                    time.sleep(min(2**attempt, 20))
        return {
            "compatible": False,
            "alignment_type": "incompatible",
            "confidence": 1,
            "reason": "",
            "error": f"{type(last_error).__name__}: {last_error}",
        }

    def _chat_json(self, *, system_prompt: str, user_prompt: str) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0,
                response_format={"type": "json_object"},
            )
        except Exception as exc:
            if "response_format" not in str(exc):
                raise
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0,
            )
        return response.choices[0].message.content or ""

    def _build_alignment_prompt(self, candidate: Dict[str, Any]) -> str:
        compact = {
            "source_skill": {
                "skill_id": candidate["source_skill_id"],
                "skill_name": candidate["source_skill_name"],
            },
            "source_post_scenario": {
                "scenario_id": candidate["source_post_scenario_id"],
                "scenario": candidate["source_post_scenario"],
            },
            "target_skill": {
                "skill_id": candidate["target_skill_id"],
                "skill_name": candidate["target_skill_name"],
            },
            "target_pre_scenario": {
                "scenario_id": candidate["target_pre_scenario_id"],
                "scenario": candidate["target_pre_scenario"],
            },
            "retrieval_score": candidate["retrieval_score"],
        }
        return (
            "Evaluate whether this cross-skill scenario alignment is a valid workflow handoff.\n\n"
            + json.dumps(compact, ensure_ascii=False, indent=2)
        )

    def _normalize_alignment_result(self, candidate: Dict[str, Any], parsed: Dict[str, Any]) -> Dict[str, Any]:
        if "alignment_id" in parsed and "compatible" in parsed:
            row = dict(candidate)
            row.update(parsed)
            parsed = row
        if "error" in parsed:
            return self._failed_alignment_row(candidate, str(parsed.get("error") or "Alignment verification failed."))
        compatible = _parse_bool(parsed.get("compatible"))
        alignment_type = str(parsed.get("alignment_type") or "").strip() or "incompatible"
        if alignment_type not in ALIGNMENT_TYPES:
            alignment_type = "incompatible" if not compatible else "data_state_handoff"
        row = dict(candidate)
        row.update(
            {
                "compatible": compatible,
                "alignment_type": alignment_type,
                "confidence": _clamp_confidence(parsed.get("confidence")),
                "reason": str(parsed.get("reason", "")).strip(),
            }
        )
        return row

    def _review_edge_redundancy(
        self,
        skill_rows: List[Dict[str, Any]],
        alignments: List[Dict[str, Any]],
        *,
        output_path: Path,
        save_to_file: bool,
        existing_reviews: Optional[List[Dict[str, Any]]] = None,
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        jobs = self._build_redundancy_jobs(skill_rows, alignments)
        reviews_by_pair = self._existing_redundancy_reviews_by_pair(jobs, existing_reviews or [])
        pending = [job for job in jobs if str(job["pair_id"]) not in reviews_by_pair]
        if jobs:
            self._emit_progress(
                "reviewing skill edge pairs: pairs={}, existing_ok={}, pending={}, workers={}".format(
                    len(jobs), len(reviews_by_pair), len(pending), self.max_workers
                )
            )
        if pending:
            completed = 0
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_job = {executor.submit(self._review_redundancy_job, job): job for job in pending}
                for future in concurrent.futures.as_completed(future_to_job):
                    job = future_to_job[future]
                    try:
                        row = future.result()
                    except Exception as exc:
                        row = dict(job)
                        row.update({"error": str(exc), "keep_edge": False})
                    reviews_by_pair[str(row["pair_id"])] = row
                    completed += 1
                    reviews = [reviews_by_pair[key] for key in sorted(reviews_by_pair)]
                    kept_alignments, dropped_alignments = self._split_alignments_by_reviews(alignments, reviews_by_pair)
                    if save_to_file:
                        self._write_redundancy_outputs(
                            output_path,
                            alignments,
                            reviews,
                            kept_alignments,
                            dropped_alignments,
                        )
                    status = "keep" if row.get("keep_edge") is True else "drop"
                    if "error" in row:
                        status = "failed"
                    self._emit_progress(
                        "[{}/{}] redundancy {}: {} -> {} overlap={} type={}".format(
                            completed,
                            len(pending),
                            status,
                            row.get("source_skill_name"),
                            row.get("target_skill_name"),
                            row.get("overlap_score"),
                            row.get("redundancy_type"),
                        )
                    )

        reviews = [reviews_by_pair[key] for key in sorted(reviews_by_pair)]
        kept_alignments, dropped_alignments = self._split_alignments_by_reviews(alignments, reviews_by_pair)
        if save_to_file:
            self._write_redundancy_outputs(output_path, alignments, reviews, kept_alignments, dropped_alignments)
        return reviews, kept_alignments, dropped_alignments

    def _existing_redundancy_reviews_by_pair(
        self,
        jobs: List[Dict[str, Any]],
        existing_reviews: List[Dict[str, Any]],
    ) -> Dict[str, Dict[str, Any]]:
        jobs_by_pair = {str(job["pair_id"]): job for job in jobs}
        reviews_by_pair: Dict[str, Dict[str, Any]] = {}
        for row in existing_reviews:
            if "error" in row or "keep_edge" not in row:
                continue
            pair_id = str(row.get("pair_id") or "")
            job = jobs_by_pair.get(pair_id)
            if not job or not self._redundancy_review_matches_job(row, job):
                continue
            reviews_by_pair[pair_id] = self._normalize_redundancy_review(job, row)
        return reviews_by_pair

    def _redundancy_review_matches_job(self, row: Dict[str, Any], job: Dict[str, Any]) -> bool:
        for key in ("source_skill_id", "target_skill_id"):
            try:
                if int(row.get(key) or 0) != int(job.get(key) or 0):
                    return False
            except (TypeError, ValueError):
                return False
        for key in ("source_skill_name", "target_skill_name"):
            if str(row.get(key) or "") != str(job.get(key) or ""):
                return False
        return True

    def _split_alignments_by_reviews(
        self,
        alignments: List[Dict[str, Any]],
        reviews_by_pair: Dict[str, Dict[str, Any]],
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        kept_pairs = {
            pair_id
            for pair_id, row in reviews_by_pair.items()
            if row.get("keep_edge") is True and "error" not in row
        }
        kept_alignments: List[Dict[str, Any]] = []
        dropped_alignments: List[Dict[str, Any]] = []
        for row in alignments:
            pair_id = f"{int(row.get('source_skill_id') or 0)}->{int(row.get('target_skill_id') or 0)}"
            review = reviews_by_pair.get(pair_id)
            if pair_id in kept_pairs:
                kept_alignments.append(
                    {
                        **row,
                        "redundancy_review": {
                            "pair_id": pair_id,
                            "keep_edge": review.get("keep_edge") if review else None,
                            "redundant": review.get("redundant") if review else None,
                            "overlap_score": review.get("overlap_score") if review else None,
                            "redundancy_type": review.get("redundancy_type") if review else None,
                            "reason": review.get("reason") if review else None,
                        },
                    }
                )
            else:
                dropped_alignments.append(
                    {
                        **row,
                        "drop_reason": "redundant_or_unreviewed_skill_pair",
                        "redundancy_review": review,
                    }
                )
        return kept_alignments, dropped_alignments

    def _build_redundancy_jobs(
        self,
        skill_rows: List[Dict[str, Any]],
        alignments: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        skills_by_id = {int(row["skill_id"]): row for row in skill_rows}
        grouped: Dict[tuple[int, int], List[Dict[str, Any]]] = {}
        for row in alignments:
            try:
                source_id = int(row.get("source_skill_id") or 0)
                target_id = int(row.get("target_skill_id") or 0)
            except (TypeError, ValueError):
                continue
            if source_id <= 0 or target_id <= 0 or source_id == target_id:
                continue
            grouped.setdefault((source_id, target_id), []).append(row)

        jobs: List[Dict[str, Any]] = []
        for (source_id, target_id), rows in sorted(grouped.items()):
            source_skill = skills_by_id.get(source_id)
            target_skill = skills_by_id.get(target_id)
            if not source_skill or not target_skill:
                continue
            source_name = str(rows[0].get("source_skill_name") or source_skill["skill_name"])
            target_name = str(rows[0].get("target_skill_name") or target_skill["skill_name"])
            jobs.append(
                {
                    "pair_id": f"{source_id}->{target_id}",
                    "source_skill_id": source_id,
                    "source_skill_name": source_name,
                    "source_skill_path": str(source_skill["skill_path"]),
                    "target_skill_id": target_id,
                    "target_skill_name": target_name,
                    "target_skill_path": str(target_skill["skill_path"]),
                    "alignment_count": len(rows),
                    "scenario_connections": [
                        {
                            "alignment_id": row.get("alignment_id"),
                            "source_post_scenario": row.get("source_post_scenario"),
                            "target_pre_scenario": row.get("target_pre_scenario"),
                            "alignment_type": row.get("alignment_type"),
                            "confidence": row.get("confidence"),
                            "retrieval_score": row.get("retrieval_score"),
                        }
                        for row in rows
                    ],
                }
            )
        return jobs

    def _review_redundancy_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        source_md = Path(str(job["source_skill_path"])).read_text(encoding="utf-8", errors="replace")
        target_md = Path(str(job["target_skill_path"])).read_text(encoding="utf-8", errors="replace")
        prompt = self._build_redundancy_prompt(job, source_md, target_md)
        last_error: Optional[Exception] = None
        for attempt in range(1, self.retries + 1):
            try:
                content = self._chat_json(
                    system_prompt=SCENARIO_REDUNDANCY_SYSTEM_PROMPT,
                    user_prompt=prompt,
                )
                return self._normalize_redundancy_review(job, _parse_model_json(content))
            except Exception as exc:
                last_error = exc
                if attempt < self.retries:
                    time.sleep(min(2**attempt, 20))
        row = dict(job)
        row.update({"error": str(last_error), "keep_edge": False})
        return row

    def _build_redundancy_prompt(self, job: Dict[str, Any], source_md: str, target_md: str) -> str:
        compact = {
            "source_skill": {
                "skill_id": job["source_skill_id"],
                "skill_name": job["source_skill_name"],
                "skill_path": job["source_skill_path"],
            },
            "target_skill": {
                "skill_id": job["target_skill_id"],
                "skill_name": job["target_skill_name"],
                "skill_path": job["target_skill_path"],
            },
            "scenario_connections": job["scenario_connections"],
            "source_skill_md": source_md,
            "target_skill_md": target_md,
        }
        return (
            "Review whether this connected skill pair is functionally redundant.\n\n"
            + json.dumps(compact, ensure_ascii=False, indent=2)
        )

    def _normalize_redundancy_review(self, job: Dict[str, Any], parsed: Dict[str, Any]) -> Dict[str, Any]:
        overlap_score = _clamp_int(parsed.get("overlap_score"), low=1, high=5, default=3)
        redundant = _parse_bool(parsed.get("redundant", False))
        keep_edge = _parse_bool(parsed.get("keep_edge", not redundant and overlap_score < self.drop_overlap_score))
        if redundant or overlap_score >= self.drop_overlap_score:
            keep_edge = False

        redundancy_type = str(parsed.get("redundancy_type") or "").strip() or "none"
        if redundancy_type not in REDUNDANCY_TYPES:
            redundancy_type = "unclear"

        row = dict(job)
        row.update(
            {
                "keep_edge": keep_edge,
                "redundant": redundant,
                "overlap_score": overlap_score,
                "redundancy_type": redundancy_type,
                "reason": str(parsed.get("reason", "")).strip(),
            }
        )
        return row

    def _alignment_meta(
        self,
        dedup: Dict[str, Any],
        candidates: List[Dict[str, Any]],
        rows: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        return {
            "model": self.model,
            "embedding_model": self.embedding_model,
            "top_k": self.top_k,
            "min_retrieval_score": self.min_retrieval_score,
            "scenario_count": len(dedup.get("scenarios", [])),
            "skill_count": len(dedup.get("skill_scenarios", [])),
            "candidate_count": len(candidates),
            "evaluated_count": len(rows),
            "compatible_count": sum(
                1
                for row in rows
                if row.get("compatible") is True
                and int(row.get("confidence") or 0) >= self.min_confidence
                and "error" not in row
            ),
            "failed_count": sum(1 for row in rows if "error" in row),
        }

    def _redundancy_meta(
        self,
        original_alignments: List[Dict[str, Any]],
        reviews: List[Dict[str, Any]],
        kept_alignments: List[Dict[str, Any]],
        dropped_alignments: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        kept_pairs = sum(1 for row in reviews if row.get("keep_edge") is True and "error" not in row)
        return {
            "model": self.model,
            "drop_overlap_score": self.drop_overlap_score,
            "pair_count": len(reviews),
            "kept_pair_count": kept_pairs,
            "dropped_pair_count": len(reviews) - kept_pairs,
            "original_alignment_count": len(original_alignments),
            "kept_alignment_count": len(kept_alignments),
            "dropped_alignment_count": len(dropped_alignments),
            "skipped_alignment_count": 0,
            "failed_pair_count": sum(1 for row in reviews if "error" in row),
        }

    def _write_alignment_outputs(
        self,
        output_path: Path,
        dedup: Dict[str, Any],
        candidates: List[Dict[str, Any]],
        rows: List[Dict[str, Any]],
    ) -> None:
        rows = sorted(rows, key=lambda row: str(row.get("alignment_id") or ""))
        keep_rows = [
            row
            for row in rows
            if row.get("compatible") is True
            and int(row.get("confidence") or 0) >= self.min_confidence
            and "error" not in row
        ]
        _write_json(
            output_path / "scenario_alignment.json",
            {"meta": self._alignment_meta(dedup, candidates, rows), "alignments": rows},
        )
        _write_json(
            output_path / "scenario_alignment_keep.json",
            {"meta": self._alignment_meta(dedup, candidates, keep_rows), "alignments": keep_rows},
        )

    def _write_redundancy_outputs(
        self,
        output_path: Path,
        original_alignments: List[Dict[str, Any]],
        reviews: List[Dict[str, Any]],
        kept_alignments: List[Dict[str, Any]],
        dropped_alignments: List[Dict[str, Any]],
    ) -> None:
        meta = self._redundancy_meta(original_alignments, reviews, kept_alignments, dropped_alignments)
        _write_json(
            output_path / "skill_edge_redundancy_reviews.json",
            {
                "meta": meta,
                "reviews": sorted(reviews, key=lambda row: str(row.get("pair_id") or "")),
                "dropped_alignments": dropped_alignments,
            },
        )
        _write_json(
            output_path / "scenario_alignment_nonredundant_keep.json",
            {"meta": meta, "alignments": kept_alignments},
        )

    def _emit_progress(self, message: str) -> None:
        if self.progress_callback is not None:
            self.progress_callback(message)
        else:
            logger.info(message)

    def _empty_result(self, output_path: Path, skill_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        graph = {
            "directed": True,
            "multigraph": False,
            "meta": {
                "mode": "scenario",
                "node_count": len(skill_rows),
                "edge_count": 0,
            },
            "nodes": [
                {
                    "id": int(row["skill_id"]),
                    "skill_id": int(row["skill_id"]),
                    "skill_name": str(row["skill_name"]),
                }
                for row in skill_rows
            ],
            "edges": [],
            "used_alignments": [],
        }
        return {
            "meta": {
                "mode": "scenario",
                "output_dir": str(output_path),
                "skill_count": len(skill_rows),
                "scenario_count": 0,
                "candidate_count": 0,
                "alignment_count": 0,
                "compatible_alignment_count": 0,
                "relationship_count": 0,
            },
            "skill_scenarios": [],
            "scenario_dedup": {"meta": {"mode": "scenario"}, "scenarios": [], "skill_scenarios": []},
            "scenario_alignment": {"meta": {}, "alignments": []},
            "scenario_alignment_keep": {"meta": {}, "alignments": []},
            "skill_edge_redundancy_reviews": {"meta": {}, "reviews": [], "dropped_alignments": []},
            "scenario_alignment_nonredundant_keep": {"meta": {}, "alignments": []},
            "scenario_skill_graph": graph,
            "relationships": [],
        }

    def _write_all_outputs(self, output_path: Path, result: Dict[str, Any]) -> None:
        _write_json(output_path / "skill_scenarios.json", {"skills": result["skill_scenarios"]})
        _write_json(output_path / "scenario_dedup.json", result["scenario_dedup"])
        _write_json(output_path / "scenario_alignment.json", result["scenario_alignment"])
        _write_json(output_path / "scenario_alignment_keep.json", result["scenario_alignment_keep"])
        _write_json(output_path / "skill_edge_redundancy_reviews.json", result["skill_edge_redundancy_reviews"])
        _write_json(output_path / "scenario_alignment_nonredundant_keep.json", result["scenario_alignment_nonredundant_keep"])
        _write_json(output_path / "scenario_skill_graph.json", result["scenario_skill_graph"])
        _write_json(output_path / "relationships.json", result["relationships"])



__all__ = [
    "SkillRelationshipAnalyzer",
    "ScenarioSkillGraphAnalyzer",
]
