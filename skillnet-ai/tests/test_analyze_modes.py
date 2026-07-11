import json
import sys
import types
import tempfile
import unittest
from pathlib import Path
from unittest import mock


def install_import_stubs() -> None:
    if "openai" not in sys.modules:
        openai = types.ModuleType("openai")

        class OpenAI:
            def __init__(self, *args, **kwargs):
                self.chat = types.SimpleNamespace(
                    completions=types.SimpleNamespace(create=mock.Mock())
                )

        openai.OpenAI = OpenAI
        sys.modules["openai"] = openai

    if "requests" not in sys.modules:
        requests = types.ModuleType("requests")

        class Response:
            status_code = 200

            def json(self):
                return {}

            def raise_for_status(self):
                return None

        class Session:
            def __init__(self):
                self.headers = {}

            def get(self, *args, **kwargs):
                raise RuntimeError("requests stub does not perform HTTP")

        requests.Response = Response
        requests.Session = Session
        requests.get = lambda *args, **kwargs: Response()
        sys.modules["requests"] = requests

    if "pydantic" not in sys.modules:
        pydantic = types.ModuleType("pydantic")

        class BaseModel:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)

        def Field(default=None, **kwargs):
            return default

        pydantic.BaseModel = BaseModel
        pydantic.Field = Field
        sys.modules["pydantic"] = pydantic

    if "json_repair" not in sys.modules:
        json_repair = types.ModuleType("json_repair")
        json_repair.repair_json = lambda value: value
        sys.modules["json_repair"] = json_repair

    if "tqdm" not in sys.modules:
        tqdm = types.ModuleType("tqdm")
        tqdm.tqdm = lambda iterable=None, *args, **kwargs: iterable if iterable is not None else []
        sys.modules["tqdm"] = tqdm


install_import_stubs()

from skillnet_ai.client import SkillNetClient, SkillNetError


def write_skill(root: Path, name: str, description: str) -> Path:
    skill_dir = root / name
    skill_dir.mkdir()
    skill_dir.joinpath("SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n",
        encoding="utf-8",
    )
    return skill_dir


def make_alignment_candidate(
    *,
    alignment_id: str = "align-0000001",
    source_skill_id: int = 1,
    source_skill_name: str = "producer",
    target_skill_id: int = 2,
    target_skill_name: str = "consumer",
    retrieval_score: float = 0.99,
) -> dict:
    return {
        "alignment_id": alignment_id,
        "source_skill_id": source_skill_id,
        "source_skill_name": source_skill_name,
        "source_post_scenario_id": 10 + source_skill_id,
        "source_post_scenario": "cleaned CSV dataset available",
        "target_skill_id": target_skill_id,
        "target_skill_name": target_skill_name,
        "target_pre_scenario_id": 20 + target_skill_id,
        "target_pre_scenario": "chart-ready dataset available",
        "retrieval_score": retrieval_score,
    }


class AnalyzeModeTests(unittest.TestCase):
    def test_client_uses_default_llm_base_url_when_unset(self):
        with mock.patch.dict("os.environ", {"BASE_URL": ""}, clear=False):
            client = SkillNetClient(api_key="test-key")

        self.assertEqual(client.base_url, "https://api.openai.com/v1")

    def test_client_orchestrate_passes_model_endpoint_and_timeout(self):
        client = SkillNetClient(api_key="test-key", base_url="https://llm.example/v1")

        with mock.patch("skillnet_ai.client.SkillOrchestrator") as orchestrator_cls:
            orchestrator = orchestrator_cls.return_value
            orchestrator.orchestrate.return_value = "handoff"

            result = client.orchestrate(
                "Find recent retrieval-augmented generation papers.",
                scene="sciatlas",
                model="chat-model",
                timeout=37,
            )

        orchestrator_cls.assert_called_once_with(
            api_key="test-key",
            base_url="https://llm.example/v1",
            model="chat-model",
            execution_timeout_seconds=37,
        )
        orchestrator.orchestrate.assert_called_once_with(
            "Find recent retrieval-augmented generation papers.",
            scene="sciatlas",
        )
        self.assertEqual(result, "handoff")

    def test_client_orchestrate_requires_api_key(self):
        client = SkillNetClient(api_key="", base_url="https://llm.example/v1")

        with self.assertRaisesRegex(SkillNetError, "API_KEY"):
            client.orchestrate("Find recent retrieval-augmented generation papers.")

    def test_analyzer_module_keeps_basic_import_compatible(self):
        from skillnet_ai.analyzer import ScenarioSkillGraphAnalyzer, SkillRelationshipAnalyzer
        from skillnet_ai.analyzer import SkillRelationshipAnalyzer as BasicAnalyzer

        self.assertIs(SkillRelationshipAnalyzer, BasicAnalyzer)
        self.assertTrue(callable(ScenarioSkillGraphAnalyzer))

    def test_client_analyze_defaults_to_basic_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp)
            write_skill(skills_dir, "alpha", "Use when alpha data is available.")
            write_skill(skills_dir, "beta", "Use when beta output is required.")

            client = SkillNetClient(api_key="test-key", base_url="https://llm.example/v1")

            with mock.patch("skillnet_ai.client.SkillRelationshipAnalyzer") as analyzer_cls:
                analyzer = analyzer_cls.return_value
                analyzer.analyze_local_skills.return_value = [
                    {
                        "source": "alpha",
                        "target": "beta",
                        "type": "compose_with",
                        "reason": "alpha output can feed beta",
                    }
                ]

                result = client.analyze(skills_dir, model="chat-model")

            analyzer_cls.assert_called_once_with(
                api_key="test-key",
                base_url="https://llm.example/v1",
                model="chat-model",
            )
            analyzer.analyze_local_skills.assert_called_once_with(
                skills_dir=str(skills_dir),
                save_to_file=True,
            )
            self.assertEqual(result[0]["type"], "compose_with")

    def test_client_scenario_mode_requires_explicit_embedding_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            client = SkillNetClient(api_key="test-key", base_url="https://llm.example/v1")

            with mock.patch.dict(
                "os.environ",
                {
                    "EMBEDDING_API_KEY": "",
                    "EMBEDDING_BASE_URL": "",
                    "EMBEDDING_MODEL": "",
                },
                clear=False,
            ):
                with self.assertRaisesRegex(SkillNetError, "EMBEDDING_API_KEY"):
                    client.analyze(
                        tmp,
                        mode="scenario",
                        embedding_api_key=None,
                        embedding_base_url="https://embedding.example/v1",
                        embedding_model="embedding-model",
                    )

    def test_scenario_mode_reports_missing_graph_extra(self):
        from skillnet_ai.analyzer import GraphDependencyError

        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp)
            write_skill(skills_dir, "alpha", "Produces a text summary.")
            write_skill(skills_dir, "beta", "Consumes a text summary.")
            client = SkillNetClient(api_key="test-key", base_url="https://llm.example/v1")

            with mock.patch(
                "skillnet_ai.analyzer.require_graph_dependencies",
                side_effect=GraphDependencyError('Install them with `pip install "skillnet-ai[graph]"`.'),
            ):
                with self.assertRaisesRegex(SkillNetError, r"skillnet-ai\[graph\]"):
                    client.analyze(
                        skills_dir,
                        mode="scenario",
                        embedding_api_key="embedding-key",
                        embedding_base_url="https://embedding.example/v1",
                        embedding_model="embedding-model",
                    )

    def test_scenario_pipeline_writes_artifacts_and_relationships(self):
        from skillnet_ai.analyzer import ScenarioSkillGraphAnalyzer

        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            write_skill(skills_dir, "producer", "Creates a cleaned CSV dataset from raw spreadsheet data.")
            write_skill(skills_dir, "consumer", "Builds a chart from a cleaned CSV dataset.")
            output_dir = Path(tmp) / "graph"

            fake_rows = [
                {
                    "skill_id": 1,
                    "skill_name": "producer",
                    "skill_path": str(skills_dir / "producer" / "SKILL.md"),
                    "local_path": str(skills_dir / "producer"),
                    "pre_scenarios": ["raw spreadsheet data available"],
                    "post_scenarios": ["cleaned CSV dataset available"],
                },
                {
                    "skill_id": 2,
                    "skill_name": "consumer",
                    "skill_path": str(skills_dir / "consumer" / "SKILL.md"),
                    "local_path": str(skills_dir / "consumer"),
                    "pre_scenarios": ["cleaned CSV dataset available"],
                    "post_scenarios": ["chart generated from dataset"],
                },
            ]

            analyzer = ScenarioSkillGraphAnalyzer(
                api_key="test-key",
                base_url="https://llm.example/v1",
                model="chat-model",
                embedding_api_key="embedding-key",
                embedding_base_url="https://embedding.example/v1",
                embedding_model="embedding-model",
                max_workers=2,
                top_k=5,
            )
            analyzer._extract_all_skill_scenarios = mock.Mock(return_value=fake_rows)
            analyzer._verify_alignment = mock.Mock(
                return_value={
                    "compatible": True,
                    "alignment_type": "artifact_handoff",
                    "confidence": 5,
                    "reason": "The cleaned CSV from producer is the required input for consumer.",
                }
            )
            analyzer._review_redundancy_job = mock.Mock(
                side_effect=lambda job: {
                    **job,
                    "keep_edge": True,
                    "redundant": False,
                    "overlap_score": 1,
                    "redundancy_type": "none",
                    "reason": "The target performs a distinct downstream step.",
                }
            )

            fake_dedup = {
                "meta": {},
                "scenarios": [
                    {"scenario_id": 1, "canonical_scenario": "raw spreadsheet data available"},
                    {"scenario_id": 2, "canonical_scenario": "cleaned CSV dataset available"},
                    {"scenario_id": 3, "canonical_scenario": "chart generated from dataset"},
                ],
                "skill_scenarios": [
                    {
                        "skill_id": 1,
                        "skill_name": "producer",
                        "pre_scenario_ids": [1],
                        "post_scenario_ids": [2],
                        "pre_scenarios": ["raw spreadsheet data available"],
                        "post_scenarios": ["cleaned CSV dataset available"],
                    },
                    {
                        "skill_id": 2,
                        "skill_name": "consumer",
                        "pre_scenario_ids": [2],
                        "post_scenario_ids": [3],
                        "pre_scenarios": ["cleaned CSV dataset available"],
                        "post_scenarios": ["chart generated from dataset"],
                    },
                ],
            }
            fake_candidate = {
                "alignment_id": "align-0000001",
                "source_skill_id": 1,
                "source_skill_name": "producer",
                "source_post_scenario_id": 2,
                "source_post_scenario": "cleaned CSV dataset available",
                "target_skill_id": 2,
                "target_skill_name": "consumer",
                "target_pre_scenario_id": 2,
                "target_pre_scenario": "cleaned CSV dataset available",
                "retrieval_score": 0.99,
            }

            with mock.patch.object(analyzer.embedding_client, "embed_texts", return_value=[[1.0, 0.0]]), \
                mock.patch("skillnet_ai.analyzer.require_graph_dependencies"), \
                mock.patch("skillnet_ai.analyzer.deduplicate_scenarios", return_value=fake_dedup), \
                mock.patch("skillnet_ai.analyzer.build_alignment_candidates", return_value=[fake_candidate]):
                result = analyzer.analyze_local_skills(
                    str(skills_dir),
                    output_dir=output_dir,
                    force=True,
                )

            self.assertTrue((output_dir / "skill_scenarios.json").exists())
            self.assertTrue((output_dir / "scenario_dedup.json").exists())
            self.assertTrue((output_dir / "scenario_alignment.json").exists())
            self.assertTrue((output_dir / "scenario_alignment_keep.json").exists())
            self.assertTrue((output_dir / "skill_edge_redundancy_reviews.json").exists())
            self.assertTrue((output_dir / "scenario_alignment_nonredundant_keep.json").exists())
            self.assertTrue((output_dir / "scenario_skill_graph.json").exists())
            self.assertTrue((output_dir / "relationships.json").exists())

            self.assertEqual(result["meta"]["mode"], "scenario")
            self.assertEqual(result["relationships"][0]["source"], "producer")
            self.assertEqual(result["relationships"][0]["target"], "consumer")
            self.assertEqual(result["relationships"][0]["type"], "compose_with")

            relationships = json.loads((output_dir / "relationships.json").read_text(encoding="utf-8"))
            self.assertEqual(relationships, result["relationships"])

    def test_scenario_analyzer_passes_timeout_to_openai_client(self):
        from skillnet_ai.analyzer import ScenarioSkillGraphAnalyzer

        with mock.patch("skillnet_ai.analyzer.OpenAI") as openai_cls:
            ScenarioSkillGraphAnalyzer(
                api_key="test-key",
                base_url="https://llm.example/v1",
                model="chat-model",
                embedding_api_key="embedding-key",
                embedding_base_url="https://embedding.example/v1",
                embedding_model="embedding-model",
                timeout=37,
            )

        openai_cls.assert_called_once_with(
            api_key="test-key",
            base_url="https://llm.example/v1",
            timeout=37,
        )

    def test_scenario_progress_callback_reports_pipeline_stages(self):
        from skillnet_ai.analyzer import ScenarioSkillGraphAnalyzer

        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            write_skill(skills_dir, "producer", "Creates a cleaned CSV dataset from raw spreadsheet data.")
            write_skill(skills_dir, "consumer", "Builds a chart from a cleaned CSV dataset.")
            output_dir = Path(tmp) / "graph"
            progress_messages = []

            analyzer = ScenarioSkillGraphAnalyzer(
                api_key="test-key",
                base_url="https://llm.example/v1",
                model="chat-model",
                embedding_api_key="embedding-key",
                embedding_base_url="https://embedding.example/v1",
                embedding_model="embedding-model",
                progress_callback=progress_messages.append,
            )
            analyzer._extract_all_skill_scenarios = mock.Mock(
                return_value=[
                    {
                        "skill_id": 1,
                        "skill_name": "producer",
                        "skill_path": str(skills_dir / "producer" / "SKILL.md"),
                        "local_path": str(skills_dir / "producer"),
                        "pre_scenarios": ["raw spreadsheet data available"],
                        "post_scenarios": ["cleaned CSV dataset available"],
                    },
                    {
                        "skill_id": 2,
                        "skill_name": "consumer",
                        "skill_path": str(skills_dir / "consumer" / "SKILL.md"),
                        "local_path": str(skills_dir / "consumer"),
                        "pre_scenarios": ["cleaned CSV dataset available"],
                        "post_scenarios": ["chart generated from dataset"],
                    },
                ]
            )
            analyzer._verify_alignment = mock.Mock(
                return_value={
                    "compatible": True,
                    "alignment_type": "artifact_handoff",
                    "confidence": 5,
                    "reason": "The cleaned CSV from producer is the required input for consumer.",
                }
            )
            analyzer._review_redundancy_job = mock.Mock(
                side_effect=lambda job: {
                    **job,
                    "keep_edge": True,
                    "redundant": False,
                    "overlap_score": 1,
                    "redundancy_type": "none",
                    "reason": "The target performs a distinct downstream step.",
                }
            )
            fake_dedup = {
                "meta": {},
                "scenarios": [
                    {"scenario_id": 1, "canonical_scenario": "raw spreadsheet data available"},
                    {"scenario_id": 2, "canonical_scenario": "cleaned CSV dataset available"},
                    {"scenario_id": 3, "canonical_scenario": "chart generated from dataset"},
                ],
                "skill_scenarios": [
                    {
                        "skill_id": 1,
                        "skill_name": "producer",
                        "pre_scenario_ids": [1],
                        "post_scenario_ids": [2],
                        "pre_scenarios": ["raw spreadsheet data available"],
                        "post_scenarios": ["cleaned CSV dataset available"],
                    },
                    {
                        "skill_id": 2,
                        "skill_name": "consumer",
                        "pre_scenario_ids": [2],
                        "post_scenario_ids": [3],
                        "pre_scenarios": ["cleaned CSV dataset available"],
                        "post_scenarios": ["chart generated from dataset"],
                    },
                ],
            }
            fake_candidate = {
                "alignment_id": "align-0000001",
                "source_skill_id": 1,
                "source_skill_name": "producer",
                "source_post_scenario_id": 2,
                "source_post_scenario": "cleaned CSV dataset available",
                "target_skill_id": 2,
                "target_skill_name": "consumer",
                "target_pre_scenario_id": 2,
                "target_pre_scenario": "cleaned CSV dataset available",
                "retrieval_score": 0.99,
            }

            with mock.patch.object(analyzer.embedding_client, "embed_texts", return_value=[[1.0, 0.0]]), \
                mock.patch("skillnet_ai.analyzer.require_graph_dependencies"), \
                mock.patch("skillnet_ai.analyzer.deduplicate_scenarios", return_value=fake_dedup), \
                mock.patch("skillnet_ai.analyzer.build_alignment_candidates", return_value=[fake_candidate]):
                analyzer.analyze_local_skills(
                    str(skills_dir),
                    output_dir=output_dir,
                    force=True,
                )

            joined = "\n".join(progress_messages)
            self.assertIn("loaded 2 local skills", joined)
            self.assertIn("alignment retrieval complete: candidates=1", joined)
            self.assertIn("[1/1] alignment keep", joined)
            self.assertIn("[1/1] redundancy keep", joined)
            self.assertTrue((output_dir / "scenario_alignment.json").exists())

    def test_scenario_alignment_normalizes_string_false_as_false(self):
        from skillnet_ai.analyzer import ScenarioSkillGraphAnalyzer

        analyzer = ScenarioSkillGraphAnalyzer(
            api_key="test-key",
            base_url="https://llm.example/v1",
            model="chat-model",
            embedding_api_key="embedding-key",
            embedding_base_url="https://embedding.example/v1",
            embedding_model="embedding-model",
        )
        candidate = {
            "alignment_id": "align-0000001",
            "source_skill_id": 1,
            "source_skill_name": "producer",
            "source_post_scenario_id": 10,
            "source_post_scenario": "cleaned CSV dataset available",
            "target_skill_id": 2,
            "target_skill_name": "consumer",
            "target_pre_scenario_id": 20,
            "target_pre_scenario": "chart-ready dataset available",
            "retrieval_score": 0.91,
        }

        row = analyzer._normalize_alignment_result(
            candidate,
            {
                "compatible": "false",
                "alignment_type": "artifact_handoff",
                "confidence": 5,
                "reason": "The model used a string boolean.",
            },
        )

        self.assertIs(row["compatible"], False)
        self.assertEqual(row["alignment_type"], "artifact_handoff")

    def test_scenario_alignment_rejects_invalid_compatible_value(self):
        from skillnet_ai.analyzer import ScenarioSkillGraphAnalyzer

        analyzer = ScenarioSkillGraphAnalyzer(
            api_key="test-key",
            base_url="https://llm.example/v1",
            model="chat-model",
            embedding_api_key="embedding-key",
            embedding_base_url="https://embedding.example/v1",
            embedding_model="embedding-model",
        )
        candidate = {
            "alignment_id": "align-0000001",
            "source_skill_id": 1,
            "source_skill_name": "producer",
            "source_post_scenario_id": 10,
            "source_post_scenario": "cleaned CSV dataset available",
            "target_skill_id": 2,
            "target_skill_name": "consumer",
            "target_pre_scenario_id": 20,
            "target_pre_scenario": "chart-ready dataset available",
            "retrieval_score": 0.91,
        }

        with self.assertRaisesRegex(ValueError, "Expected a JSON boolean"):
            analyzer._normalize_alignment_result(
                candidate,
                {
                    "compatible": "yes",
                    "alignment_type": "artifact_handoff",
                    "confidence": 5,
                    "reason": "Invalid boolean string.",
                },
            )

    def test_scenario_alignment_error_rows_are_counted_as_failures(self):
        from skillnet_ai.analyzer import ScenarioSkillGraphAnalyzer

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            analyzer = ScenarioSkillGraphAnalyzer(
                api_key="test-key",
                base_url="https://llm.example/v1",
                model="chat-model",
                embedding_api_key="embedding-key",
                embedding_base_url="https://embedding.example/v1",
                embedding_model="embedding-model",
            )
            candidate = make_alignment_candidate()
            analyzer._verify_alignment = mock.Mock(
                return_value={
                    "compatible": False,
                    "alignment_type": "incompatible",
                    "confidence": 1,
                    "reason": "",
                    "error": "RuntimeError: model unavailable",
                }
            )

            rows = analyzer._verify_alignment_candidates(
                [candidate],
                dedup={"scenarios": [], "skill_scenarios": []},
                output_path=output_dir,
                save_to_file=True,
            )

            self.assertEqual(rows[0]["error"], "RuntimeError: model unavailable")
            self.assertEqual(rows[0]["alignment_id"], candidate["alignment_id"])

            payload = json.loads((output_dir / "scenario_alignment.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["meta"]["failed_count"], 1)
            self.assertEqual(payload["alignments"][0]["error"], "RuntimeError: model unavailable")

    def test_scenario_extraction_reuses_existing_successful_rows(self):
        from skillnet_ai.analyzer import ScenarioSkillGraphAnalyzer

        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            write_skill(skills_dir, "producer", "Creates a cleaned CSV dataset.")
            write_skill(skills_dir, "consumer", "Builds a chart from a cleaned CSV dataset.")
            output_dir = Path(tmp) / "graph"
            output_dir.mkdir()

            analyzer = ScenarioSkillGraphAnalyzer(
                api_key="test-key",
                base_url="https://llm.example/v1",
                model="chat-model",
                embedding_api_key="embedding-key",
                embedding_base_url="https://embedding.example/v1",
                embedding_model="embedding-model",
            )
            skill_rows = analyzer._load_skill_rows(skills_dir)
            existing_rows = [
                {
                    **skill_rows[0],
                    "pre_scenarios": ["raw spreadsheet data available"],
                    "post_scenarios": ["cleaned CSV dataset available"],
                },
                {
                    **skill_rows[1],
                    "pre_scenarios": ["chart-ready dataset available"],
                    "post_scenarios": ["chart generated from dataset"],
                    "error": "RuntimeError: previous failure",
                },
            ]
            analyzer._extract_skill_scenarios = mock.Mock(
                return_value={
                    **skill_rows[1],
                    "pre_scenarios": ["cleaned CSV dataset available"],
                    "post_scenarios": ["chart generated from dataset"],
                }
            )

            rows = analyzer._extract_all_skill_scenarios(
                skill_rows,
                existing_rows=existing_rows,
                output_path=output_dir,
                save_to_file=True,
            )

            analyzer._extract_skill_scenarios.assert_called_once_with(skill_rows[1])
            self.assertEqual([row["skill_name"] for row in rows], [row["skill_name"] for row in skill_rows])

            payload = json.loads((output_dir / "skill_scenarios.json").read_text(encoding="utf-8"))
            self.assertEqual(
                [row["skill_name"] for row in payload["skills"]],
                [row["skill_name"] for row in skill_rows],
            )
            self.assertNotIn("error", payload["skills"][1])

    def test_scenario_alignment_reuses_existing_successful_rows(self):
        from skillnet_ai.analyzer import ScenarioSkillGraphAnalyzer

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            analyzer = ScenarioSkillGraphAnalyzer(
                api_key="test-key",
                base_url="https://llm.example/v1",
                model="chat-model",
                embedding_api_key="embedding-key",
                embedding_base_url="https://embedding.example/v1",
                embedding_model="embedding-model",
            )
            candidates = [
                make_alignment_candidate(alignment_id="align-0000001", source_skill_id=1, target_skill_id=2),
                make_alignment_candidate(alignment_id="align-0000002", source_skill_id=2, target_skill_id=1),
            ]
            existing_rows = [
                {
                    **candidates[0],
                    "compatible": True,
                    "alignment_type": "artifact_handoff",
                    "confidence": 5,
                    "reason": "Cached valid handoff.",
                },
                {
                    **candidates[1],
                    "compatible": False,
                    "alignment_type": "incompatible",
                    "confidence": 1,
                    "reason": "",
                    "error": "RuntimeError: previous failure",
                },
            ]
            analyzer._verify_alignment = mock.Mock(
                return_value={
                    "compatible": True,
                    "alignment_type": "data_state_handoff",
                    "confidence": 4,
                    "reason": "Recomputed valid handoff.",
                }
            )

            rows = analyzer._verify_alignment_candidates(
                candidates,
                dedup={"scenarios": [], "skill_scenarios": []},
                output_path=output_dir,
                save_to_file=True,
                existing_rows=existing_rows,
            )

            analyzer._verify_alignment.assert_called_once_with(candidates[1])
            self.assertEqual(rows[0]["reason"], "Cached valid handoff.")
            self.assertEqual(rows[1]["reason"], "Recomputed valid handoff.")

            payload = json.loads((output_dir / "scenario_alignment.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["meta"]["evaluated_count"], 2)
            self.assertEqual(payload["meta"]["failed_count"], 0)

    def test_scenario_alignment_does_not_reuse_changed_candidate(self):
        from skillnet_ai.analyzer import ScenarioSkillGraphAnalyzer

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            analyzer = ScenarioSkillGraphAnalyzer(
                api_key="test-key",
                base_url="https://llm.example/v1",
                model="chat-model",
                embedding_api_key="embedding-key",
                embedding_base_url="https://embedding.example/v1",
                embedding_model="embedding-model",
            )
            candidate = make_alignment_candidate(
                alignment_id="align-0000001",
                source_skill_name="new-producer",
            )
            existing_rows = [
                {
                    **make_alignment_candidate(
                        alignment_id="align-0000001",
                        source_skill_name="old-producer",
                    ),
                    "compatible": True,
                    "alignment_type": "artifact_handoff",
                    "confidence": 5,
                    "reason": "Stale row.",
                }
            ]
            analyzer._verify_alignment = mock.Mock(
                return_value={
                    "compatible": False,
                    "alignment_type": "incompatible",
                    "confidence": 1,
                    "reason": "Recomputed for changed candidate.",
                }
            )

            rows = analyzer._verify_alignment_candidates(
                [candidate],
                dedup={"scenarios": [], "skill_scenarios": []},
                output_path=output_dir,
                save_to_file=True,
                existing_rows=existing_rows,
            )

            analyzer._verify_alignment.assert_called_once_with(candidate)
            self.assertEqual(rows[0]["source_skill_name"], "new-producer")
            self.assertEqual(rows[0]["reason"], "Recomputed for changed candidate.")

    def test_scenario_redundancy_reuses_existing_successful_reviews(self):
        from skillnet_ai.analyzer import ScenarioSkillGraphAnalyzer

        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            write_skill(skills_dir, "producer", "Creates a cleaned CSV dataset.")
            write_skill(skills_dir, "consumer", "Builds a chart from a cleaned CSV dataset.")
            output_dir = Path(tmp) / "graph"

            analyzer = ScenarioSkillGraphAnalyzer(
                api_key="test-key",
                base_url="https://llm.example/v1",
                model="chat-model",
                embedding_api_key="embedding-key",
                embedding_base_url="https://embedding.example/v1",
                embedding_model="embedding-model",
            )
            skill_rows = analyzer._load_skill_rows(skills_dir)
            alignments = [
                {
                    **make_alignment_candidate(
                        alignment_id="align-0000001",
                        source_skill_id=1,
                        source_skill_name="producer",
                        target_skill_id=2,
                        target_skill_name="consumer",
                    ),
                    "compatible": True,
                    "alignment_type": "artifact_handoff",
                    "confidence": 5,
                    "reason": "Producer output feeds consumer.",
                },
                {
                    **make_alignment_candidate(
                        alignment_id="align-0000002",
                        source_skill_id=2,
                        source_skill_name="consumer",
                        target_skill_id=1,
                        target_skill_name="producer",
                    ),
                    "compatible": True,
                    "alignment_type": "data_state_handoff",
                    "confidence": 4,
                    "reason": "Consumer output can feed producer.",
                },
            ]
            existing_reviews = [
                {
                    "pair_id": "1->2",
                    "source_skill_id": 1,
                    "source_skill_name": "producer",
                    "target_skill_id": 2,
                    "target_skill_name": "consumer",
                    "keep_edge": True,
                    "redundant": False,
                    "overlap_score": 1,
                    "redundancy_type": "none",
                    "reason": "Cached review.",
                }
            ]
            analyzer._review_redundancy_job = mock.Mock(
                side_effect=lambda job: {
                    **job,
                    "keep_edge": True,
                    "redundant": False,
                    "overlap_score": 2,
                    "redundancy_type": "none",
                    "reason": "Recomputed review.",
                }
            )

            reviews, kept_alignments, dropped_alignments = analyzer._review_edge_redundancy(
                skill_rows,
                alignments,
                output_path=output_dir,
                save_to_file=True,
                existing_reviews=existing_reviews,
            )

            analyzer._review_redundancy_job.assert_called_once()
            self.assertEqual([row["pair_id"] for row in reviews], ["1->2", "2->1"])
            self.assertEqual(len(kept_alignments), 2)
            self.assertEqual(dropped_alignments, [])

            payload = json.loads(
                (output_dir / "skill_edge_redundancy_reviews.json").read_text(encoding="utf-8")
            )
            self.assertEqual(payload["meta"]["pair_count"], 2)
            self.assertEqual(payload["meta"]["failed_pair_count"], 0)

    def test_scenario_redundancy_normalizes_string_booleans(self):
        from skillnet_ai.analyzer import ScenarioSkillGraphAnalyzer

        analyzer = ScenarioSkillGraphAnalyzer(
            api_key="test-key",
            base_url="https://llm.example/v1",
            model="chat-model",
            embedding_api_key="embedding-key",
            embedding_base_url="https://embedding.example/v1",
            embedding_model="embedding-model",
        )
        job = {
            "pair_id": "1->2",
            "source_skill_id": 1,
            "source_skill_name": "producer",
            "source_skill_path": "/tmp/source/SKILL.md",
            "target_skill_id": 2,
            "target_skill_name": "consumer",
            "target_skill_path": "/tmp/target/SKILL.md",
            "alignment_count": 1,
            "scenario_connections": [],
        }

        row = analyzer._normalize_redundancy_review(
            job,
            {
                "keep_edge": "true",
                "redundant": "false",
                "overlap_score": 2,
                "redundancy_type": "none",
                "reason": "The model used string booleans.",
            },
        )

        self.assertIs(row["keep_edge"], True)
        self.assertIs(row["redundant"], False)

    def test_scenario_redundancy_does_not_reuse_changed_pair(self):
        from skillnet_ai.analyzer import ScenarioSkillGraphAnalyzer

        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            write_skill(skills_dir, "producer", "Creates a cleaned CSV dataset.")
            write_skill(skills_dir, "consumer", "Builds a chart from a cleaned CSV dataset.")
            output_dir = Path(tmp) / "graph"

            analyzer = ScenarioSkillGraphAnalyzer(
                api_key="test-key",
                base_url="https://llm.example/v1",
                model="chat-model",
                embedding_api_key="embedding-key",
                embedding_base_url="https://embedding.example/v1",
                embedding_model="embedding-model",
            )
            skill_rows = analyzer._load_skill_rows(skills_dir)
            alignments = [
                {
                    **make_alignment_candidate(
                        alignment_id="align-0000001",
                        source_skill_id=1,
                        source_skill_name=skill_rows[0]["skill_name"],
                        target_skill_id=2,
                        target_skill_name=skill_rows[1]["skill_name"],
                    ),
                    "compatible": True,
                    "alignment_type": "artifact_handoff",
                    "confidence": 5,
                    "reason": "Producer output feeds consumer.",
                }
            ]
            existing_reviews = [
                {
                    "pair_id": "1->2",
                    "source_skill_id": 1,
                    "source_skill_name": "stale-source",
                    "target_skill_id": 2,
                    "target_skill_name": skill_rows[1]["skill_name"],
                    "keep_edge": True,
                    "redundant": False,
                    "overlap_score": 1,
                    "redundancy_type": "none",
                    "reason": "Stale review.",
                }
            ]
            analyzer._review_redundancy_job = mock.Mock(
                side_effect=lambda job: {
                    **job,
                    "keep_edge": False,
                    "redundant": True,
                    "overlap_score": 5,
                    "redundancy_type": "near_duplicate",
                    "reason": "Recomputed review.",
                }
            )

            reviews, kept_alignments, dropped_alignments = analyzer._review_edge_redundancy(
                skill_rows,
                alignments,
                output_path=output_dir,
                save_to_file=True,
                existing_reviews=existing_reviews,
            )

            analyzer._review_redundancy_job.assert_called_once()
            self.assertEqual(reviews[0]["reason"], "Recomputed review.")
            self.assertEqual(kept_alignments, [])
            self.assertEqual(len(dropped_alignments), 1)

    def test_scenario_fails_when_all_extraction_fails(self):
        from skillnet_ai.analyzer import ScenarioSkillGraphAnalyzer

        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            write_skill(skills_dir, "alpha", "Creates a normalized report.")
            write_skill(skills_dir, "beta", "Consumes a normalized report.")

            analyzer = ScenarioSkillGraphAnalyzer(
                api_key="test-key",
                base_url="https://llm.example/v1",
                model="chat-model",
                embedding_api_key="embedding-key",
                embedding_base_url="https://embedding.example/v1",
                embedding_model="embedding-model",
            )
            analyzer._extract_all_skill_scenarios = mock.Mock(
                return_value=[
                    {
                        "skill_id": 1,
                        "skill_name": "alpha",
                        "skill_path": str(skills_dir / "alpha" / "SKILL.md"),
                        "local_path": str(skills_dir / "alpha"),
                        "pre_scenarios": ["Applicable task state requiring this skill"],
                        "post_scenarios": ["Task state after applying this skill"],
                        "error": "RuntimeError: unavailable",
                    },
                    {
                        "skill_id": 2,
                        "skill_name": "beta",
                        "skill_path": str(skills_dir / "beta" / "SKILL.md"),
                        "local_path": str(skills_dir / "beta"),
                        "pre_scenarios": ["Applicable task state requiring this skill"],
                        "post_scenarios": ["Task state after applying this skill"],
                        "error": "RuntimeError: unavailable",
                    },
                ]
            )

            with mock.patch("skillnet_ai.analyzer.require_graph_dependencies"):
                with self.assertRaisesRegex(RuntimeError, "Scenario extraction failed for all skills"):
                    analyzer.analyze_local_skills(str(skills_dir), save_to_file=False)

    def test_scenario_no_save_does_not_write_output_dir(self):
        from skillnet_ai.analyzer import ScenarioSkillGraphAnalyzer

        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            write_skill(skills_dir, "producer", "Creates a cleaned CSV dataset from raw spreadsheet data.")
            write_skill(skills_dir, "consumer", "Builds a chart from a cleaned CSV dataset.")
            output_dir = Path(tmp) / "graph"

            analyzer = ScenarioSkillGraphAnalyzer(
                api_key="test-key",
                base_url="https://llm.example/v1",
                model="chat-model",
                embedding_api_key="embedding-key",
                embedding_base_url="https://embedding.example/v1",
                embedding_model="embedding-model",
            )
            analyzer._extract_all_skill_scenarios = mock.Mock(
                return_value=[
                    {
                        "skill_id": 1,
                        "skill_name": "producer",
                        "skill_path": str(skills_dir / "producer" / "SKILL.md"),
                        "local_path": str(skills_dir / "producer"),
                        "pre_scenarios": ["raw spreadsheet data available"],
                        "post_scenarios": ["cleaned CSV dataset available"],
                    },
                    {
                        "skill_id": 2,
                        "skill_name": "consumer",
                        "skill_path": str(skills_dir / "consumer" / "SKILL.md"),
                        "local_path": str(skills_dir / "consumer"),
                        "pre_scenarios": ["cleaned CSV dataset available"],
                        "post_scenarios": ["chart generated from dataset"],
                    },
                ]
            )
            analyzer._verify_alignment = mock.Mock(
                return_value={
                    "compatible": True,
                    "alignment_type": "artifact_handoff",
                    "confidence": 5,
                    "reason": "The cleaned CSV from producer is the required input for consumer.",
                }
            )
            analyzer._review_redundancy_job = mock.Mock(
                side_effect=lambda job: {
                    **job,
                    "keep_edge": True,
                    "redundant": False,
                    "overlap_score": 1,
                    "redundancy_type": "none",
                    "reason": "The target performs a distinct downstream step.",
                }
            )
            fake_dedup = {
                "meta": {},
                "scenarios": [
                    {"scenario_id": 1, "canonical_scenario": "raw spreadsheet data available"},
                    {"scenario_id": 2, "canonical_scenario": "cleaned CSV dataset available"},
                    {"scenario_id": 3, "canonical_scenario": "chart generated from dataset"},
                ],
                "skill_scenarios": [
                    {
                        "skill_id": 1,
                        "skill_name": "producer",
                        "pre_scenario_ids": [1],
                        "post_scenario_ids": [2],
                        "pre_scenarios": ["raw spreadsheet data available"],
                        "post_scenarios": ["cleaned CSV dataset available"],
                    },
                    {
                        "skill_id": 2,
                        "skill_name": "consumer",
                        "pre_scenario_ids": [2],
                        "post_scenario_ids": [3],
                        "pre_scenarios": ["cleaned CSV dataset available"],
                        "post_scenarios": ["chart generated from dataset"],
                    },
                ],
            }
            fake_candidate = {
                "alignment_id": "align-0000001",
                "source_skill_id": 1,
                "source_skill_name": "producer",
                "source_post_scenario_id": 2,
                "source_post_scenario": "cleaned CSV dataset available",
                "target_skill_id": 2,
                "target_skill_name": "consumer",
                "target_pre_scenario_id": 2,
                "target_pre_scenario": "cleaned CSV dataset available",
                "retrieval_score": 0.99,
            }

            with mock.patch.object(analyzer.embedding_client, "embed_texts", return_value=[[1.0, 0.0]]), \
                mock.patch("skillnet_ai.analyzer.require_graph_dependencies"), \
                mock.patch("skillnet_ai.analyzer.deduplicate_scenarios", return_value=fake_dedup), \
                mock.patch("skillnet_ai.analyzer.build_alignment_candidates", return_value=[fake_candidate]):
                result = analyzer.analyze_local_skills(
                    str(skills_dir),
                    output_dir=output_dir,
                    force=True,
                    save_to_file=False,
                )

            self.assertFalse(output_dir.exists())
            self.assertEqual(result["relationships"][0]["source"], "producer")


if __name__ == "__main__":
    unittest.main()
