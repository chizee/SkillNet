"""Regressions found while reviewing the cross-agent skill release."""
import json
import sys
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import Mock

import httpx
import openai
import pytest
from typer.testing import CliRunner

from skillnet_ai.cli import app
from skillnet_ai.config import config_path, save_config
from skillnet_ai.creator import SkillCreator, _GitHubFetcher
from skillnet_ai.downloader import SkillDownloader, GitHubAPIError
from skillnet_ai.errors import error_details
from skillnet_ai.evaluator import Skill, EvaluatorConfig, LLMClient
from skillnet_ai.validation import validate_skill


def test_evaluate_blob_skill_url_keeps_package_semantics(tmp_path):
    url = "https://github.com/example/repo/blob/main/demo/SKILL.md"
    downloader = Mock()
    downloader.download.return_value = str(tmp_path / "demo")
    skill, error = Skill.from_url(url, downloader, str(tmp_path))
    assert error is None
    assert downloader.download.call_args.args[0] == url
    assert skill.name == "demo"


def test_remote_loader_returns_error_tuple_when_download_raises(tmp_path):
    downloader = Mock()
    downloader.download.side_effect = GitHubAPIError(404, "Not found")
    skill, error = Skill.from_url("https://github.com/example/repo/tree/main/demo", downloader, str(tmp_path))
    assert skill is None and error
    downloader.download.assert_called_once()


@pytest.mark.parametrize("fence", ["```", "````"])
def test_generated_markdown_preserves_unlabelled_nested_fences(tmp_path, fence):
    content = "---\nname: demo\ndescription: Check CSV.\n---\n\n```\nexample.csv\n```\n\nRequired final instruction.\n"
    response = f"## FILE: demo/SKILL.md\n{fence}markdown\n{content}{fence}\n"
    creator = SkillCreator.__new__(SkillCreator)
    creator._save_github_skill_files(response, str(tmp_path))
    assert (tmp_path / "demo/SKILL.md").read_text() == content


@pytest.mark.parametrize("malformed", [
    "## FILE: demo/scripts/run.py\n```python\nprint('unfinished')\n",
    "## FILE: demo/scripts/run.py\nnot a fenced file\n",
])
def test_malformed_file_block_rejects_entire_generation_before_writes(tmp_path, malformed):
    creator = SkillCreator.__new__(SkillCreator)
    response = "## FILE: demo/SKILL.md\n```markdown\nvalid first file\n```\n" + malformed
    with pytest.raises(ValueError):
        creator._save_github_skill_files(response, str(tmp_path))
    assert not (tmp_path / "demo").exists()


@pytest.mark.parametrize("reason", ["length", "content_filter"])
def test_incomplete_model_response_is_not_written(reason):
    creator = SkillCreator.__new__(SkillCreator)
    creator.client = Mock()
    creator.model = "test"
    creator.client.chat.completions.create.return_value.choices = [
        Mock(finish_reason=reason, message=Mock(content="partially generated content"))]
    with pytest.raises(ValueError, match="complete"):
        creator._get_llm_response([])


@pytest.mark.parametrize("reason", ["length", "content_filter"])
def test_incomplete_evaluation_is_not_repaired_into_success(reason):
    evaluator = LLMClient(EvaluatorConfig(api_key="test", base_url="https://model.test/v1", model="test"))
    evaluator.client = Mock()
    evaluator.client.chat.completions.create.return_value.choices = [
        Mock(finish_reason=reason, message=Mock(content="{}"))]
    with pytest.raises(ValueError, match="complete evaluation"):
        evaluator.evaluate("Evaluate this skill.")


def test_validate_current_directory(monkeypatch, tmp_path):
    root = tmp_path / "demo"
    root.mkdir()
    (root / "SKILL.md").write_text("---\nname: demo\ndescription: Useful skill.\n---\n")
    monkeypatch.chdir(root)
    assert validate_skill(".")["valid"]


def test_interactive_configuration_can_replace_existing_key(monkeypatch):
    save_config({"api_key": "old-private-test-key"})
    monkeypatch.setattr("skillnet_ai.cli.sys", SimpleNamespace(
        stdin=SimpleNamespace(isatty=lambda: True), stderr=sys.stderr))
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    hidden_prompt = Mock(return_value="new-private-test-key")
    monkeypatch.setattr("skillnet_ai.cli.getpass.getpass", hidden_prompt)
    result = CliRunner().invoke(app, ["configure", "--interactive", "--json"])
    assert result.exit_code == 0, result.output
    hidden_prompt.assert_called_once()
    assert json.loads(config_path().read_text())["api_key"] == "new-private-test-key"
    assert "private-test-key" not in result.output


def test_interactive_blank_key_keeps_saved_key(monkeypatch):
    save_config({"api_key": "keep-private-test-key"})
    monkeypatch.setattr("skillnet_ai.cli.sys", SimpleNamespace(
        stdin=SimpleNamespace(isatty=lambda: True), stderr=sys.stderr))
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    monkeypatch.setattr("skillnet_ai.cli.getpass.getpass", lambda prompt: "")
    result = CliRunner().invoke(app, ["configure", "--interactive", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(config_path().read_text())["api_key"] == "keep-private-test-key"


def test_http_server_error_does_not_echo_provider_body():
    response = httpx.Response(500, request=httpx.Request("POST", "https://provider.test/v1/chat/completions"))
    exc = openai.InternalServerError("private provider response", response=response,
                                     body={"message": "private provider response"})
    error = error_details(exc)
    assert error["code"] == "service_unavailable"
    assert "private provider response" not in str(error)


@pytest.mark.parametrize("url", [
    "https://notgithub.com/owner/repo", "https://evil.test/github.com/owner/repo",
    "https://github.com/owner/repo/tree/main/../../outside",
])
def test_creator_rejects_non_github_or_unsafe_repository_urls(url):
    with pytest.raises(ValueError):
        _GitHubFetcher().parse_github_url(url)


def test_creator_honors_explicit_repository_ref():
    creator = SkillCreator.__new__(SkillCreator)
    creator._analyze_github_code_files = Mock(return_value={})
    fetcher = Mock()
    fetcher.fetch_repo_metadata.return_value = {"default_branch": "main"}
    fetcher.fetch_readme.return_value = "README"
    creator._fetch_github_repo_data(fetcher, "owner", "repo", "release", 5)
    assert fetcher.fetch_readme.call_args.args[2] == "release"


def test_saturated_github_listing_does_not_claim_complete_download(monkeypatch):
    downloader = SkillDownloader()
    response = Mock(status_code=200)
    response.json.return_value = [{"type": "file", "path": f"demo/{i}.txt"} for i in range(1000)]
    monkeypatch.setattr(downloader, "_request_with_retry", lambda *a, **kw: response)
    with pytest.raises(ValueError, match="limit"):
        downloader._get_file_tree("owner", "repo", "main", "demo")
