import json
import os
import stat
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
from typer.testing import CliRunner

from skillnet_ai.cli import app
from skillnet_ai.client import SkillNetClient
from skillnet_ai.config import config_path, resolve_settings, save_config
from skillnet_ai.evaluator import EvaluatorConfig, LLMClient
from skillnet_ai.models import SkillModel
from skillnet_ai.validation import DIMENSIONS, validate_skill

runner = CliRunner()


def skill(root, name="demo", description="Use to process CSV data."):
    path = root / name
    path.mkdir(parents=True, exist_ok=True)
    (path / "SKILL.md").write_text(f"---\nname: {name}\ndescription: {description}\n---\n# Demo\n", encoding="utf-8")
    return path


def report(level="Good"):
    return {d: {"level": level, "reason": "Checked the supplied content."} for d in DIMENSIONS}


def test_configuration_precedence_and_runtime_model(monkeypatch):
    save_config({"api_key": "stored-key", "model": "stored-model", "base_url": "https://example.test/v1"})
    monkeypatch.setenv("API_KEY", "environment-key")
    assert resolve_settings().api_key == "environment-key"
    assert resolve_settings(api_key="explicit-key").api_key == "explicit-key"
    assert resolve_settings(api_key="").api_key == ""
    assert resolve_settings().model == "stored-model"
    monkeypatch.setenv("SKILLNET_MODEL", "late-model")
    client = SkillNetClient()
    assert client.model == "late-model"
    factory = Mock()
    factory.return_value.create_from_prompt.return_value = []
    monkeypatch.setattr("skillnet_ai.client.SkillCreator", factory)
    client.create(prompt="a skill")
    assert factory.call_args.kwargs["model"] == "late-model"


def test_configure_stdin_and_doctor_never_echo_key():
    key = "private-test-credential-9a7d"
    result = runner.invoke(app, ["configure", "--api-key-stdin", "--model", "example-model", "--json"], input=key+"\n")
    assert result.exit_code == 0, result.output
    assert key not in result.output
    assert json.loads(config_path().read_text())["api_key"] == key
    if os.name != "nt":
        assert stat.S_IMODE(config_path().stat().st_mode) == 0o600
    result = runner.invoke(app, ["doctor", "--json"])
    assert result.exit_code == 0
    assert key not in result.output
    settings = json.loads(result.stdout)["data"]["settings"]
    assert settings["api_key"] == {"value": True, "source": "config"}


def test_saved_config_is_reused_by_another_process():
    save_config({"model": "persistent-model"})
    process = subprocess.run([sys.executable, "-m", "skillnet_ai", "doctor", "--json"],
                             capture_output=True, text=True, check=True)
    assert json.loads(process.stdout)["data"]["settings"]["model"]["value"] == "persistent-model"


def test_configure_is_noninteractive_by_default():
    result = runner.invoke(app, ["configure", "--json"])
    assert result.exit_code == 1
    assert not config_path().exists()
    assert not json.loads(result.stdout)["ok"]


def test_configure_from_named_environment(monkeypatch):
    monkeypatch.setenv("MY_TEST_KEY", "named-test-credential")
    result = runner.invoke(app, ["configure", "--api-key-env", "MY_TEST_KEY", "--json"])
    assert result.exit_code == 0
    assert "named-test-credential" not in result.output
    assert resolve_settings().api_key == "named-test-credential"


def test_invalid_config_is_actionable_without_dumping_contents():
    config_path().write_text('{"api_key": "secret"', encoding="utf-8")
    result = runner.invoke(app, ["doctor", "--json"])
    assert result.exit_code == 1
    assert "secret" not in result.output
    assert "Cannot read SkillNet config" in json.loads(result.stdout)["error"]["message"]


def test_search_json_has_intact_urls_without_key(monkeypatch):
    url = "https://github.com/example/long-repository-name/tree/main/skills/a-long-skill-name"
    def search(self, *args, **kwargs):
        assert self.api_key is None
        print("progress from dependency")
        return [SkillModel(skill_name="example", skill_url=url)]
    monkeypatch.setattr(SkillNetClient, "search", search)
    result = runner.invoke(app, ["search", "csv", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["data"][0]["skill_url"] == url
    assert "progress from dependency" in result.stderr


def test_empty_search_is_success(monkeypatch):
    monkeypatch.setattr(SkillNetClient, "search", lambda *a, **k: [])
    result = runner.invoke(app, ["search", "absent", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.stdout) == {"ok": True, "data": [], "error": None}


def test_create_defaults_to_no_evaluation_and_explicit_mode_evaluates(monkeypatch, tmp_path):
    path = skill(tmp_path / "中文 空格")
    monkeypatch.setattr(SkillNetClient, "create", lambda *a, **k: [str(path)])
    evaluate = Mock(return_value=report("Poor"))
    monkeypatch.setattr(SkillNetClient, "evaluate", evaluate)
    result = runner.invoke(app, ["create", "--prompt", "CSV helper", "--json"])
    assert result.exit_code == 0, result.output
    evaluate.assert_not_called()
    result = runner.invoke(app, ["create", "--prompt", "CSV helper", "--evaluate", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["data"]["evaluations"][str(path)]["report"]["safety"]["level"] == "Poor"


@pytest.mark.parametrize("mode", ["empty", "invalid", "evaluation-failed"])
def test_create_failures_preserve_paths_and_report_failure(monkeypatch, tmp_path, mode):
    path = skill(tmp_path)
    if mode == "invalid":
        (path / "SKILL.md").unlink()
    monkeypatch.setattr(SkillNetClient, "create", lambda *a, **k: [] if mode == "empty" else [str(path)])
    monkeypatch.setattr(SkillNetClient, "evaluate", Mock(side_effect=RuntimeError("endpoint unavailable")))
    result = runner.invoke(app, ["create", "--prompt", "CSV helper", "--evaluate", "--json"])
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert not payload["ok"]
    assert payload["data"]["paths"] == ([] if mode == "empty" else [str(path)])


@pytest.mark.parametrize("source", ["prompt", "github", "office", "trajectory"])
def test_all_create_sources_reach_sdk(monkeypatch, tmp_path, source):
    path = skill(tmp_path)
    create = Mock(return_value=[str(path)])
    monkeypatch.setattr(SkillNetClient, "create", create)
    source_file = tmp_path / "输入 文件.txt"
    source_file.write_text("Reusable workflow", encoding="utf-8")
    args = {"prompt": ["--prompt", "Reusable workflow"], "github": ["--github", "https://github.com/example/repo"],
            "office": ["--office", str(source_file)], "trajectory": [str(source_file)]}[source]
    result = runner.invoke(app, ["create", *args, "--json"])
    assert result.exit_code == 0, result.output
    field = {"prompt": "prompt", "github": "github_url", "office": "office_file", "trajectory": "trajectory_content"}[source]
    assert field in create.call_args.kwargs


def test_validate_yaml_and_optional_directories(tmp_path):
    path = skill(tmp_path, name="a", description=">\n  Process tables:\n  preserve headers.")
    assert validate_skill(path)["valid"]
    path = skill(tmp_path, name="bad--name")
    assert not validate_skill(path)["valid"]


def test_evaluation_json_repair_still_validates_schema():
    llm = LLMClient(EvaluatorConfig(api_key="test", base_url="https://example.test/v1", model="test"))
    response = Mock()
    llm.client.chat.completions.create = Mock(return_value=response)
    response.choices = [Mock(finish_reason="stop", message=Mock(content="```json\n" + json.dumps(report()) + "\n```"))]
    assert llm.evaluate("Evaluate JSON") == report()
    response.choices[0].message.content = '{"safety": {"level": "Good", "reason": "ok"}}'
    with pytest.raises(ValueError, match="completeness"):
        llm.evaluate("Evaluate JSON")


def test_sdk_clients_disable_hidden_transport_retries(monkeypatch):
    from skillnet_ai.creator import SkillCreator
    for module in ("skillnet_ai.creator.OpenAI", "skillnet_ai.evaluator.OpenAI"):
        factory = Mock()
        monkeypatch.setattr(module, factory)
        if "creator" in module:
            SkillCreator(api_key="test")
        else:
            LLMClient(EvaluatorConfig(api_key="test", base_url="https://example.test/v1", model="test"))
        assert factory.call_args.kwargs["max_retries"] == 0


def test_version_works_without_subcommand():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0, result.output


def test_real_sdk_create_evaluate_chain(monkeypatch, tmp_path):
    import httpx
    import openai
    calls = []
    generated = '## FILE: demo/SKILL.md\n```markdown\n---\nname: demo\ndescription: Check CSV headers.\n---\n# Demo\n\n```text\nexample.csv\n```\n\nKeep this instruction after the example.\n```'

    def transport(request):
        calls.append(json.loads(request.content))
        content = generated if len(calls) == 1 else json.dumps(report())
        return httpx.Response(200, json={"id": "test", "object": "chat.completion", "created": 1,
            "model": "test", "choices": [{"index": 0, "finish_reason": "stop",
                                           "message": {"role": "assistant", "content": content}}]})

    client = openai.OpenAI(api_key="test", base_url="https://model.test/v1", max_retries=0,
                          http_client=httpx.Client(transport=httpx.MockTransport(transport)))
    monkeypatch.setattr("skillnet_ai.creator.OpenAI", lambda **kw: client)
    monkeypatch.setattr("skillnet_ai.evaluator.OpenAI", lambda **kw: client)
    monkeypatch.setenv("API_KEY", "test")
    result = runner.invoke(app, ["create", "--prompt", "CSV checker", "--output-dir", str(tmp_path), "--evaluate", "--json"])
    assert result.exit_code == 0, result.output
    assert len(calls) == 2
    assert "Keep this instruction" in (tmp_path / "demo/SKILL.md").read_text()
    payload = json.loads(result.stdout)
    assert payload["data"]["evaluations"][str(tmp_path / "demo")]["ok"]


def test_trajectory_partial_failure_retains_actual_paths(monkeypatch, tmp_path):
    from skillnet_ai.creator import SkillCreator
    monkeypatch.setenv("API_KEY", "test")
    output = '## FILE: actual/SKILL.md\n```markdown\n---\nname: actual\ndescription: Useful skill.\n---\n# Skill\n```'
    responses = Mock(side_effect=[json.dumps([{"name": "proposed"}, {"name": "second"}]),
                                 output, RuntimeError("endpoint failed")])
    monkeypatch.setattr(SkillCreator, "_get_llm_response", responses)
    trace = tmp_path / "trace.txt"
    trace.write_text("Trace input")
    result = runner.invoke(app, ["create", str(trace), "--output-dir", str(tmp_path / "out"), "--json"])
    assert result.exit_code == 1
    assert json.loads(result.stdout)["data"]["paths"] == [str(tmp_path / "out/actual")]
    assert (tmp_path / "out/actual/SKILL.md").exists()


def test_search_service_error_is_not_empty_success(monkeypatch):
    from skillnet_ai.searcher import SkillNetSearcher
    response = Mock()
    response.json.return_value = {"success": False, "data": [], "meta": {}}
    searcher = SkillNetSearcher()
    monkeypatch.setattr(searcher.session, "get", lambda *a, **k: response)
    with pytest.raises(RuntimeError, match="success=False"):
        searcher.search("csv")
