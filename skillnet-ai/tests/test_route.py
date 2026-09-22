"""Routing and the two SDK contracts; all model and agent calls stay offline."""

import asyncio
import json
import sys
import threading
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
from pydantic import RootModel, SecretStr
from typer.testing import CliRunner

from skillnet_ai import Endpoint, RouteOptions, SkillNetClient
from skillnet_ai.core.config import ENVIRONMENT
from skillnet_ai.core.models import (
    AnalyzedSkill,
    Exploration,
    GraphSnapshot,
    Relation,
    SkillProfile,
    SkillSelection,
)
from skillnet_ai.interfaces.cli import app
from skillnet_ai.router.explorer import ClaudeExplorer, CodexExplorer

ENDPOINT = Endpoint(api_key=SecretStr("test-key"), base_url="https://model.test/v1", model="test")


def selection(skill_id: str = "stats") -> SkillSelection:
    """A small SDK response; paths must still be resolved by SkillNet."""
    return SkillSelection.model_validate(
        {
            "skills": [
                {
                    "skill_id": skill_id,
                    "reason": "The user already has CSV.",
                    "evidence": [{"line": 1}],
                }
            ],
            "coverage_gaps": [],
        }
    )


@pytest.fixture
def index(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Persist three skill records without using analysis or any model."""
    np = pytest.importorskip("numpy")
    from skillnet_ai.router import router
    from skillnet_ai.router.index import build_bm25

    for variable in ENVIRONMENT.values():
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setenv("SKILLNET_CONFIG", str(tmp_path / "config.json"))
    for prefix in ("EMBEDDING_", "SKILLNET_EXPLORER_"):
        monkeypatch.setenv(prefix + "API_KEY", "test-key")
        monkeypatch.setenv(prefix + "BASE_URL", ENDPOINT.base_url)
        monkeypatch.setenv(prefix + "MODEL", ENDPOINT.model)
    skills = []
    for key, text in {
        "stats": "Compute statistics from CSV.",
        "extract": "Extract CSV from PDF.",
        "alternative": "Extract CSV using another PDF engine.",
    }.items():
        profile = SkillProfile.model_validate(
            {
                "capability": {"text": text, "evidence": [{"line": 1}]},
                "when_to_use": [],
                "inputs": [],
                "outputs": [],
                "scenarios": [],
                "constraints": [],
                "tools": [],
            }
        )
        skills.append(
            AnalyzedSkill(
                skill_id=key,
                name=key,
                path=str(tmp_path / "original" / key),
                source=text,
                content_hash=key,
                profile=profile,
            )
        )
    relations = [
        Relation.model_validate(
            {
                "source": "extract",
                "target": target,
                "type": kind,
                "contexts": [
                    {
                        "scenario": "CSV analysis",
                        "explanation": "A CSV handoff or alternative.",
                        "conditions": [],
                        "source_evidence": [{"line": 1}],
                        "target_evidence": [{"line": 1}],
                    }
                ],
            }
        )
        for target, kind in (("stats", "compose_with"), ("alternative", "similar_to"))
    ]
    graph = GraphSnapshot(
        embedding_model=ENDPOINT.model,
        embedding_base_url=ENDPOINT.base_url,
        skills=skills,
        relations=relations,
    )
    snapshot = tmp_path / "snapshot-test"
    snapshot.mkdir()
    (snapshot / "graph.json").write_text(graph.model_dump_json(), encoding="utf-8")
    (tmp_path / "CURRENT").write_text(snapshot.name, encoding="utf-8")
    np.savez(
        snapshot / "embeddings.npz",
        ids=[s.skill_id for s in skills],
        vectors=[[1.0, 0.0], [0.0, 1.0], [0.0, 1.0]],
    )
    build_bm25(skills, snapshot / "bm25.sqlite")
    monkeypatch.setattr(router, "embed", lambda *args, **kwargs: [[1.0, 0.0]])
    return tmp_path


@pytest.mark.parametrize("supported", [True, False])
def test_route_selects_from_snapshot(
    index: Path, monkeypatch: pytest.MonkeyPatch, supported: bool
) -> None:
    """Retrieval expands the graph, but does not force related skills or fill k."""
    from skillnet_ai.router import router as explorer

    def explore(
        root: Path, query: str, k: int, endpoint: Endpoint, options: RouteOptions
    ) -> Exploration:
        assert all(
            (root / f"sources/{key}.md").is_file() for key in ("stats", "extract", "alternative")
        )
        assert json.loads((root / "relations.json").read_text())[0]["source"] == "extract"
        answer = (
            selection()
            if supported
            else SkillSelection(skills=[], coverage_gaps=["No video editor."])
        )
        return Exploration(answer, {"sources/stats.md"})

    monkeypatch.setattr(explorer, "backend_for", lambda backend: SimpleNamespace(explore=explore))
    result = SkillNetClient().route(
        "statistics from existing CSV" if supported else "edit a video",
        index_dir=index,
        options=RouteOptions(seed_limit=1, candidate_limit=3),
    )
    assert [s.skill_id for s in result.skills] == (["stats"] if supported else [])
    if supported:
        assert result.skills[0].path == str(index / "original/stats")
        assert not Path(result.skills[0].path).exists()  # Routing uses the source snapshot.
    else:
        assert result.coverage_gaps
    cli = CliRunner().invoke(app, ["route", "statistics CSV", "--index-dir", str(index), "--json"])
    assert cli.exit_code == 0 and json.loads(cli.stdout)["ok"] is True


@pytest.mark.parametrize("problem", ["unread", "unknown", "duplicate"])
def test_route_rejects_unsupported_selection(index: Path, problem: str) -> None:
    """Selection needs known, unique IDs and an observed original-source read."""
    from skillnet_ai.router.index import load_snapshot
    from skillnet_ai.router.router import validate_selection

    answer = selection("missing" if problem == "unknown" else "stats")
    if problem == "duplicate":
        answer.skills *= 2
    reads = {"index.md"} if problem == "unread" else {"sources/stats.md"}
    with pytest.raises(ValueError):
        validate_selection(Exploration(answer, reads), load_snapshot(index)[1].skills, 5)


@pytest.mark.parametrize("problem", ["model", "dimension"])
def test_embedding_mismatch_fails(
    index: Path, monkeypatch: pytest.MonkeyPatch, problem: str
) -> None:
    """An incompatible index must fail before starting an Explorer."""
    from skillnet_ai.router import router

    def unexpected(*args: object, **kwargs: object) -> None:
        pytest.fail("An incompatible embedding must not start an Explorer")

    monkeypatch.setattr(router, "explore", unexpected)
    monkeypatch.setattr(router, "embed", lambda *args, **kwargs: [[1.0, 0.0, 0.0]])
    embedding = ENDPOINT.model_copy(update={"model": "other"}) if problem == "model" else ENDPOINT
    with pytest.raises(ValueError, match="endpoint/model" if problem == "model" else "dimension"):
        SkillNetClient().route("task", index_dir=index, embedding=embedding)


@pytest.mark.parametrize("timeout", [False, True])
def test_claude_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, timeout: bool) -> None:
    """Exercise SDK options, read hooks, structured output and timeout cleanup."""
    sdk = ModuleType("claude_agent_sdk")
    sdk.ClaudeAgentOptions = sdk.HookMatcher = SimpleNamespace
    sdk.ResultMessage = type("ResultMessage", (SimpleNamespace,), {})
    closed = threading.Event()

    async def query(
        *, prompt: AsyncIterator[dict], options: SimpleNamespace
    ) -> AsyncIterator[object]:
        try:
            assert [item async for item in prompt]
            assert options.model == ENDPOINT.model and options.setting_sources == []
            assert options.env["ANTHROPIC_BASE_URL"] == ENDPOINT.base_url
            assert options.output_format["schema"]["additionalProperties"] is False
            if timeout:
                await asyncio.Event().wait()
            hook = options.hooks["PreToolUse"][0]
            assert hook.matcher == "Read|LS|Glob|Grep"
            denied = await hook.hooks[0](
                {"tool_name": "Read", "tool_input": {"file_path": "../outside"}}, None, {}
            )
            assert denied["hookSpecificOutput"]["permissionDecision"] == "deny"
            read = {"tool_name": "Read", "tool_input": {"file_path": "sources/stats.md"}}
            allowed = await hook.hooks[0](read, None, {})
            assert allowed["hookSpecificOutput"]["permissionDecision"] == "allow"
            await options.hooks["PostToolUse"][0].hooks[0](read, None, {})
            yield sdk.ResultMessage(
                is_error=False,
                structured_output=selection().model_dump(),
                usage={"input_tokens": 5},
            )
        finally:
            closed.set()

    sdk.query = query
    monkeypatch.setitem(sys.modules, "claude_agent_sdk", sdk)
    if timeout:
        with pytest.raises(TimeoutError):
            ClaudeExplorer().explore(tmp_path, "task", 1, ENDPOINT, RouteOptions(timeout=0.05))
    else:
        result = ClaudeExplorer().explore(tmp_path, "task", 1, ENDPOINT, RouteOptions())
        assert result.pages_read == {"sources/stats.md"} and result.selection == selection()
        assert result.usage == {"input_tokens": 5}
    assert closed.is_set()


@pytest.mark.parametrize("failure", [None, "provider", "timeout"])
def test_codex_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str | None
) -> None:
    """Exercise parsed SDK tool events and close the session on all exit paths."""
    sdk, types = ModuleType("openai_codex"), ModuleType("openai_codex.types")
    sdk.CodexConfig, types.ReasoningEffort = SimpleNamespace, str
    sdk.ApprovalMode, sdk.Sandbox = (
        SimpleNamespace(deny_all="never"),
        SimpleNamespace(read_only="read-only"),
    )
    closed = threading.Event()

    def event(method: str, payload: dict[str, object]) -> SimpleNamespace:
        return SimpleNamespace(method=method, payload=RootModel[dict](payload))

    class Turn:
        def stream(self) -> Iterator[SimpleNamespace]:
            if failure == "timeout":
                assert closed.wait(2)
                return
            if failure == "provider":
                raise RuntimeError("provider failed")
            item = {
                "type": "commandExecution",
                "cwd": str(tmp_path),
                "exitCode": None,
                "commandActions": [{"type": "read", "path": "sources/stats.md"}],
            }
            yield event("item/started", {"item": item})
            yield event("item/completed", {"item": {**item, "exitCode": 0}})
            yield event(
                "item/completed",
                {
                    "item": {
                        "type": "agentMessage",
                        "phase": "final_answer",
                        "text": selection().model_dump_json(),
                    }
                },
            )
            yield event("turn/completed", {"turn": {"status": "completed"}})

    class Codex:
        def __init__(self, *, config: SimpleNamespace) -> None:
            assert config.env["OPENAI_API_KEY"] == "test-key"

        def __enter__(self) -> "Codex":
            return self

        def login_api_key(self, key: str) -> None:
            assert key == "test-key"

        def thread_start(self, **kwargs: object) -> SimpleNamespace:
            assert kwargs["sandbox"] == "read-only" and kwargs["ephemeral"] is True
            assert kwargs["config"]["model_providers"]["skillnet"]["base_url"] == ENDPOINT.base_url
            return SimpleNamespace(turn=self.turn)

        def turn(self, prompt: str, **kwargs: object) -> Turn:
            assert kwargs["output_schema"]["additionalProperties"] is False
            return Turn()

        def close(self) -> None:
            closed.set()

    sdk.Codex = Codex
    monkeypatch.setitem(sys.modules, "openai_codex", sdk)
    monkeypatch.setitem(sys.modules, "openai_codex.types", types)
    options = RouteOptions(timeout=0.05 if failure == "timeout" else 300)
    if failure:
        with pytest.raises(TimeoutError if failure == "timeout" else RuntimeError):
            CodexExplorer().explore(tmp_path, "task", 1, ENDPOINT, options)
    else:
        result = CodexExplorer().explore(tmp_path, "task", 1, ENDPOINT, options)
        assert result.pages_read == {"sources/stats.md"} and result.selection == selection()
    assert closed.is_set()
