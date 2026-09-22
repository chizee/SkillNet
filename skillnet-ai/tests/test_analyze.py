"""Analysis contracts using real storage/indexing and an offline model transport."""

import json
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from openai import APIStatusError, OpenAI
from pydantic import SecretStr, ValidationError
from typer.testing import CliRunner

from skillnet_ai import AnalysisOptions, Endpoint, SkillNetClient
from skillnet_ai.core.config import ENVIRONMENT
from skillnet_ai.core.llm import structured_call
from skillnet_ai.core.models import RelationJudgment
from skillnet_ai.interfaces.cli import app

ENDPOINT = Endpoint(api_key=SecretStr("test-key"), base_url="https://model.test/v1", model="test")


def edge(source: str, target: str, kind: str = "compose_with") -> dict[str, object]:
    """A supported CSV handoff or alternative with evidence from both sources."""
    return {
        "source": source,
        "target": target,
        "type": kind,
        "contexts": [
            {
                "scenario": "CSV analysis",
                "explanation": "Extract CSV, then compute statistics.",
                "conditions": ["CSV input"],
                "source_evidence": [{"line": 5}],
                "target_evidence": [{"line": 5}],
            }
        ],
    }


@pytest.fixture
def library(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, SimpleNamespace]:
    """Three same-name skills; only the HTTP model boundary is replaced."""
    pytest.importorskip("numpy")
    root = tmp_path / "skills"
    for key, text in {
        "extract": "Extract CSV tables from PDF.",
        "stats": "Compute statistics from CSV.",
        "alternative": "Extract CSV with a different PDF engine.",
    }.items():
        folder = root / key
        folder.mkdir(parents=True)
        (folder / "SKILL.md").write_text(
            f"---\nname: same-name\ndescription: CSV tools\n---\n{text}\n", encoding="utf-8"
        )
    for variable in ENVIRONMENT.values():
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setenv("SKILLNET_CONFIG", str(tmp_path / "config.json"))
    for prefix in ("", "EMBEDDING_"):
        monkeypatch.setenv(prefix + "API_KEY", "test-key")
        monkeypatch.setenv(prefix + "BASE_URL", ENDPOINT.base_url)
    monkeypatch.setenv("SKILLNET_MODEL", "test")
    monkeypatch.setenv("EMBEDDING_MODEL", "test")
    state = SimpleNamespace(calls=[], fail=False, malformed=False)

    def respond(request: httpx.Request) -> httpx.Response:
        state.calls.append(request.url.path)
        if state.fail:
            return httpx.Response(503, json={"error": {"message": "offline test failure"}})
        body = json.loads(request.content)
        if request.url.path.endswith("/embeddings"):
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "index": i,
                            "embedding": [1.0, 0.2] if "statistics" in text else [0.2, 1.0],
                        }
                        for i, text in enumerate(body["input"])
                    ]
                },
            )
        assert body["response_format"]["json_schema"]["strict"] is True
        payload = json.loads(body["messages"][1]["content"])
        if "skill_id" in payload:
            field = {"text": payload["source"].splitlines()[4][3:], "evidence": [{"line": 5}]}
            answer = {
                "capability": field,
                "when_to_use": [field],
                "inputs": [field],
                "outputs": [field],
                "scenarios": [],
                "constraints": [],
                "tools": [],
            }
        else:
            pair = {s["skill_id"] for s in payload["skills"]}
            relations = (
                [edge("extract", "stats")]
                if pair == {"extract", "stats"}
                else [edge("extract", "alternative", "similar_to")]
                if pair == {"extract", "alternative"}
                else []
            )
            answer = {
                "decision": {"outcome": "related", "relations": relations}
                if relations
                else {"outcome": "none", "reason": "No supported relation."}
            }
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": "not JSON" if state.malformed else json.dumps(answer),
                        },
                    }
                ]
            },
        )

    def client(**kwargs: object) -> OpenAI:
        assert kwargs["max_retries"] == 0
        return OpenAI(**kwargs, http_client=httpx.Client(transport=httpx.MockTransport(respond)))

    monkeypatch.setattr("skillnet_ai.core.llm.OpenAI", client)
    return root, state


def test_analyze_builds_index_and_reuses_cache(library: tuple[Path, SimpleNamespace]) -> None:
    """Public SDK/CLI preserve identity, evidence and cache invalidation."""
    from skillnet_ai.router.index import load_snapshot

    root, state = library
    index = root.parent / "index"
    client = SkillNetClient()
    result = client.analyze(root, output_dir=index)
    snapshot, graph = load_snapshot(index)
    assert result.relation_counts == {"compose_with": 1, "similar_to": 1}
    assert [s.skill_id for s in graph.skills] == ["alternative", "extract", "stats"]
    assert {s.name for s in graph.skills} == {"same-name"}
    assert "5: Extract CSV" in (snapshot / "wiki/sources/extract.md").read_text()
    assert "CSV analysis" in (snapshot / "wiki/cards/extract.md").read_text()
    calls = len(state.calls)
    cached = client.analyze(root, output_dir=index)
    assert cached.cache_hits["profiles"] == cached.cache_hits["relations"] == 3
    assert cached.cache_hits["embeddings"] > 0 and len(state.calls) == calls
    source = root / "stats/SKILL.md"
    source.write_text(source.read_text() + "Requires a CSV header.\n", encoding="utf-8")
    changed = client.analyze(root, output_dir=index)
    assert changed.cache_hits["profiles"] == 2 and changed.cache_hits["relations"] == 1
    output = CliRunner().invoke(app, ["analyze", str(root), "--output-dir", str(index), "--json"])
    assert output.exit_code == 0 and json.loads(output.stdout)["data"]["skill_count"] == 3


def test_failed_analysis_preserves_snapshot(library: tuple[Path, SimpleNamespace]) -> None:
    """Forced provider failure cannot publish a partial replacement."""
    root, state = library
    index = SkillNetClient().analyze(root).index_dir
    previous = (index / "CURRENT").read_text()
    state.fail = True
    with pytest.raises(APIStatusError):
        SkillNetClient().analyze(root, force=True)
    assert (index / "CURRENT").read_text() == previous
    assert len(list(index.glob("snapshot-*"))) == 1


def test_relation_direction_and_evidence(library: tuple[Path, SimpleNamespace]) -> None:
    """Merge duplicates, retain both composition directions and reject bad citations."""
    import jsonschema

    from skillnet_ai.analyzer import normalize_relations, relation_schema
    from skillnet_ai.router.index import load_snapshot

    root, _ = library
    result = SkillNetClient().analyze(root)
    _, graph = load_snapshot(result.index_dir)
    first, second = graph.skills[:2]
    a, b = first.skill_id, second.skill_id
    data = {
        "decision": {
            "outcome": "related",
            "relations": [
                edge(a, b),
                edge(b, a),
                edge(a, b),
                edge(b, a, "similar_to"),
            ],
        }
    }
    normalized = normalize_relations(RelationJudgment.model_validate(data), first, second)
    assert [(r.type, r.source, r.target) for r in normalized] == [
        ("compose_with", a, b),
        ("compose_with", b, a),
        ("similar_to", a, b),
    ]
    schema = relation_schema(first, second)
    jsonschema.validate(data, schema)
    data["decision"]["relations"][0]["contexts"][0]["source_evidence"][0]["line"] = 99
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(data, schema)
    with pytest.raises(ValueError, match="outside"):
        normalize_relations(RelationJudgment.model_validate(data), first, second)


def test_invalid_model_output_is_not_repaired(library: tuple[Path, SimpleNamespace]) -> None:
    """Malformed JSON fails after one request without a protocol fallback."""
    _, state = library
    state.malformed = True
    with pytest.raises(ValidationError):
        structured_call(ENDPOINT, AnalysisOptions(), "system", {"skills": []}, RelationJudgment)
    assert len(state.calls) == 1
