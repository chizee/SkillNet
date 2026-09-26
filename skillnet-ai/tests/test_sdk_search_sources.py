"""Search source metadata is usable in Python, JSON and terminal output."""

import json
from unittest.mock import Mock

import pytest
import requests
from rich.console import Console
from typer.testing import CliRunner

from skillnet_ai.core.models import SkillModel
from skillnet_ai.interfaces import cli
from skillnet_ai.interfaces.client import SkillNetClient


@pytest.fixture
def search_response(monkeypatch):
    rows = [
        {
            "skill_name": "example",
            "repo_name": "owner/repo",
            "skill_dir": f"owner/repo/releases/{version}/example",
            "skill_url": f"https://github.com/owner/repo/tree/commit/releases/{version}/example",
            "stars": 10,
        }
        for version in ("v1", "v2")
    ]
    # Old servers omit the fields; local/non-GitHub records may return null.
    rows.extend(
        [{"skill_name": "legacy"}, {"skill_name": "local", "repo_name": None, "skill_dir": None}]
    )
    response = requests.Response()
    response.status_code = 200
    response._content = json.dumps({"success": True, "data": rows, "meta": {}}).encode()
    get = Mock(return_value=response)
    monkeypatch.setattr(requests.Session, "get", get)
    return rows, get


def test_sdk_and_cli_json_preserve_source_identity(search_response):
    rows, get = search_response
    result = SkillNetClient().search("example")
    assert [(r.repo_name, r.skill_dir) for r in result] == [
        (r.get("repo_name"), r.get("skill_dir")) for r in rows
    ]
    assert get.call_count == 1
    assert "repo_name" not in get.call_args.kwargs["params"]
    assert "skill_dir" not in get.call_args.kwargs["params"]
    output = CliRunner().invoke(cli.app, ["search", "example", "--json"])
    assert output.exit_code == 0, output.output
    data = json.loads(output.stdout)["data"]
    assert [(r["repo_name"], r["skill_dir"]) for r in data] == [
        (r.get("repo_name"), r.get("skill_dir")) for r in rows
    ]
    assert [r["skill_url"] for r in data] == [r.get("skill_url") for r in rows]


def test_cli_displays_sources_without_changing_download_urls(search_response, monkeypatch):
    monkeypatch.setattr(cli, "console", Console(width=180, force_terminal=False, highlight=False))
    output = CliRunner().invoke(cli.app, ["search", "example"])
    assert output.exit_code == 0, output.output
    assert "Source" in output.stdout
    assert "Repo Stars" in output.stdout
    assert "owner/repo" in output.stdout
    assert "releases/v1/example" in output.stdout
    assert "releases/v2/example" in output.stdout
    assert "legacy" in output.stdout and "local" in output.stdout


def test_cli_treats_source_metadata_as_literal_text(search_response, monkeypatch):
    rows, _ = search_response
    rows[0]["repo_name"] = "owner/[demo]"
    rows[0]["skill_dir"] = "owner/[demo]/[red]example[/red]"
    monkeypatch.setattr(SkillNetClient, "search", lambda *a, **k: [SkillModel(**rows[0])])
    monkeypatch.setattr(cli, "console", Console(width=180, force_terminal=False, highlight=False))
    output = CliRunner().invoke(cli.app, ["search", "example"])
    assert output.exit_code == 0, output.output
    assert "[demo]" in output.stdout
    assert "[red]example[/red]" in output.stdout


def test_cli_keeps_long_sources_readable_in_a_narrow_terminal(monkeypatch):
    repo = "danielmiessler/Personal_AI_Infrastructure"
    directory = "Releases/v4.0.2/.claude/skills/Security/PromptInjection"
    row = SkillModel(
        skill_name="PromptInjection",
        repo_name=repo,
        skill_dir=f"{repo}/{directory}",
        skill_description="Prompt injection testing.",
        skill_url=f"https://github.com/{repo}/tree/commit/{directory}",
    )
    monkeypatch.setattr(SkillNetClient, "search", lambda *a, **k: [row])
    monkeypatch.setattr(cli, "console", Console(width=80, force_terminal=False, highlight=False))
    output = CliRunner().invoke(cli.app, ["search", "prompt injection"])
    assert output.exit_code == 0, output.output
    # Reassemble the wrapped source cell; truncation would lose real characters.
    identity = "".join(
        line.split("│")[1].strip() for line in output.stdout.splitlines() if line.startswith("│")
    )
    assert repo in identity and directory in identity


@pytest.mark.parametrize("directory", ["owner/repo", "owner/repo/"])
def test_cli_displays_repository_root_as_dot(directory, monkeypatch):
    row = SkillModel(skill_name="example", repo_name="owner/repo", skill_dir=directory)
    monkeypatch.setattr(SkillNetClient, "search", lambda *a, **k: [row])
    monkeypatch.setattr(cli, "console", Console(width=140, force_terminal=False, highlight=False))
    output = CliRunner().invoke(cli.app, ["search", "example"])
    assert output.exit_code == 0, output.output
    cells = [
        line.split("│")[1].strip() for line in output.stdout.splitlines() if line.startswith("│")
    ]
    assert cells.count("owner/repo") == 1 and "." in cells
