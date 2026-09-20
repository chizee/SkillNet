import json
from pathlib import Path
from unittest.mock import Mock

import httpx
import openai
import pytest

from skillnet_ai.downloader import SkillDownloader
from skillnet_ai.errors import error_details
from skillnet_ai.llm import chat_completion

URL = "https://github.com/example/repo/tree/main/demo"
CONTENT = b"---\nname: demo\ndescription: Process CSV data.\n---\n# Demo\n"


def downloader(monkeypatch, fail=None):
    instance = SkillDownloader(max_retries=1)
    monkeypatch.setattr(instance, "_get_file_tree", lambda *a: [
        {"path": "demo/SKILL.md", "download_url": "https://raw.githubusercontent.com/example/repo/main/demo/SKILL.md"},
        {"path": "demo/scripts/run.py", "download_url": "https://raw.githubusercontent.com/example/repo/main/demo/scripts/run.py"},
    ])
    def get(url, **kwargs):
        if fail and url.endswith(fail):
            return Mock(status_code=503)
        return Mock(status_code=200, content=CONTENT if url.endswith("SKILL.md") else b"print('hello')")
    monkeypatch.setattr(instance.session, "get", get)
    return instance


def test_complete_download_and_collision_policy(monkeypatch, tmp_path):
    instance = downloader(monkeypatch)
    path = Path(instance.download(URL, str(tmp_path / "中文 空格"), require_skill=True))
    assert (path / "SKILL.md").read_bytes() == CONTENT
    assert (path / "scripts/run.py").exists()
    with pytest.raises(FileExistsError):
        instance.download(URL, str(path.parent))
    (path / "old-only.txt").write_text("old")
    instance.download(URL, str(path.parent), overwrite=True, require_skill=True)
    assert not (path / "old-only.txt").exists()


def test_partial_download_preserves_old_installation(monkeypatch, tmp_path):
    old = tmp_path / "demo"
    old.mkdir()
    (old / "SKILL.md").write_text("old version")
    with pytest.raises(RuntimeError, match="incomplete"):
        downloader(monkeypatch, fail="run.py").download(URL, str(tmp_path), overwrite=True)
    assert (old / "SKILL.md").read_text() == "old version"
    assert list(tmp_path.iterdir()) == [old]


def test_failed_publish_restores_old_directory(monkeypatch, tmp_path):
    old = tmp_path / "demo"
    old.mkdir()
    (old / "SKILL.md").write_text("old version")
    original = Path.rename
    def fail_publish(self, target):
        if self.name == "demo" and self.parent.name.startswith(".skillnet-download-"):
            raise OSError("simulated publish failure")
        return original(self, target)
    monkeypatch.setattr(Path, "rename", fail_publish)
    with pytest.raises(OSError, match="publish failure"):
        downloader(monkeypatch).download(URL, str(tmp_path), overwrite=True)
    assert (old / "SKILL.md").read_text() == "old version"


def test_invalid_package_never_installs(monkeypatch, tmp_path):
    instance = downloader(monkeypatch)
    monkeypatch.setattr(instance.session, "get", lambda *a, **k: Mock(status_code=200, content=b"no metadata"))
    with pytest.raises(ValueError, match="invalid"):
        instance.download(URL, str(tmp_path), require_skill=True)
    assert not (tmp_path / "demo").exists()


def test_failed_restore_does_not_delete_backup(monkeypatch, tmp_path):
    old = tmp_path / "demo"
    old.mkdir()
    (old / "SKILL.md").write_text("old version")
    original = Path.rename
    def fail_after_backup(self, target):
        if Path(target) == old:
            raise OSError("simulated blocked destination")
        return original(self, target)
    monkeypatch.setattr(Path, "rename", fail_after_backup)
    with pytest.raises(RuntimeError, match="previous files are preserved"):
        downloader(monkeypatch).download(URL, str(tmp_path), overwrite=True)
    backups = list(tmp_path.glob(".demo.backup-*"))
    assert len(backups) == 1
    assert (backups[0] / "SKILL.md").read_text() == "old version"


@pytest.mark.parametrize("url", [
    "https://evil.test/example/repo/tree/main/demo", "https://github.com@evil.test/x/repo/tree/main/demo",
    "http://github.com/example/repo/tree/main/demo", URL + "/%2E%2E/outside",
    URL + "/..%5Coutside", URL + "/C:outside", URL + "/CON", URL + "/invalid.",
])
def test_invalid_urls_rejected_before_network(tmp_path, url):
    with pytest.raises(ValueError):
        SkillDownloader().download(url, str(tmp_path))
    assert not list(tmp_path.iterdir())


def test_blob_skill_link_downloads_whole_package(monkeypatch, tmp_path):
    instance = downloader(monkeypatch)
    parsed = instance._parse_github_url("https://github.com/example/repo/blob/main/demo/SKILL.md")
    assert parsed[3:] == ("demo", "demo")
    assert instance._parse_github_url("https://github.com/example/repo/tree/feature%2Fcsv/demo")[2] == "feature/csv"


def test_escape_in_file_tree_never_writes_outside(monkeypatch, tmp_path):
    instance = downloader(monkeypatch)
    monkeypatch.setattr(instance, "_get_file_tree", lambda *a: [{"path": "demo/../../outside.txt"}])
    with pytest.raises(ValueError):
        instance.download(URL, str(tmp_path))
    assert not (tmp_path / "demo").exists()


def test_no_token_on_raw_or_mirror(monkeypatch):
    instance = SkillDownloader(api_token="private-test-token", mirror_url="https://mirror.test")
    get = Mock(return_value=Mock(status_code=200))
    monkeypatch.setattr(instance.session, "get", get)
    for url in ["https://api.github.com/repos/a/b", "https://raw.githubusercontent.com/a/b/main/file", "https://mirror.test/file"]:
        instance._request_with_retry(url)
    assert get.call_args_list[0].kwargs["headers"]["Authorization"] == "Bearer private-test-token"
    assert all("Authorization" not in call.kwargs["headers"] for call in get.call_args_list[1:])
    assert "Authorization" not in instance.session.headers
    assert instance._build_mirror_url("https://raw.githubusercontent.com/a/b/main/file") is None


def test_creator_fetches_authenticated_content_through_github_api(monkeypatch):
    from skillnet_ai.creator import _GitHubFetcher
    fetcher = _GitHubFetcher(api_token="private-test-token")
    get = Mock(return_value=Mock(status_code=200, text="file content"))
    monkeypatch.setattr(fetcher.session, "get", get)
    assert fetcher.fetch_file_content("a", "b", "code.py") == "file content"
    assert get.call_args.args[0].startswith("https://api.github.com/")
    assert get.call_args.kwargs["headers"]["Accept"] == "application/vnd.github.raw+json"
    assert "Authorization" not in fetcher.session.headers
    assert fetcher.fetch_readme("a", "b") == "file content"
    assert "/contents/README.md" in get.call_args.args[0]


def test_unavailable_repository_does_not_call_model(monkeypatch, tmp_path):
    from skillnet_ai.creator import SkillCreator, _GitHubFetcher
    from skillnet_ai.downloader import GitHubAPIError
    monkeypatch.setattr(_GitHubFetcher, "_request_with_retry", lambda *a, **k: Mock(status_code=404))
    creator = SkillCreator(api_key="test")
    create = Mock()
    monkeypatch.setattr(creator, "_get_llm_response", create)
    with pytest.raises(GitHubAPIError):
        creator.create_from_github("https://github.com/example/missing", str(tmp_path))
    create.assert_not_called()


def test_mirror_is_fallback_not_first_choice(monkeypatch, tmp_path):
    instance = downloader(monkeypatch)
    instance.mirror_url = "https://mirror.test"
    get = Mock(side_effect=[Mock(status_code=503), Mock(status_code=200, content=CONTENT)])
    monkeypatch.setattr(instance.session, "get", get)
    file = {"path": "demo/SKILL.md", "download_url": "https://raw.githubusercontent.com/a/b/main/demo/SKILL.md"}
    assert instance._download_single_file("a", "b", "main", "demo", file, "demo", str(tmp_path))
    assert get.call_args_list[0].args[0].startswith("https://raw.githubusercontent.com/")
    assert get.call_args_list[1].args[0].startswith("https://mirror.test/")


def compatible_client(responses):
    calls = []
    def handler(request):
        calls.append(json.loads(request.content))
        status, body = responses.pop(0)
        return httpx.Response(status, json=body)
    client = openai.OpenAI(api_key="test", base_url="https://provider.test/v1", max_retries=0,
                           http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    return client, calls


SUCCESS = {"id": "test", "object": "chat.completion", "created": 1, "model": "test",
           "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": "{}"}}]}


def test_only_explicitly_unsupported_parameters_are_removed():
    client, calls = compatible_client([
        (400, {"error": {"message": "response_format is not supported"}}),
        (400, {"error": {"message": "temperature is unsupported"}}), (200, SUCCESS)])
    chat_completion(client, model="test", messages=[], json_mode="auto", temperature=0.3)
    assert len(calls) == 3
    assert "response_format" in calls[0] and "temperature" in calls[0]
    assert "response_format" not in calls[1] and "temperature" in calls[1]
    assert "temperature" not in calls[2]


def test_unsupported_parameter_can_be_named_in_error_param_field():
    client, calls = compatible_client([
        (400, {"error": {"param": "response_format", "code": "unsupported_parameter", "message": "Not allowed"}}),
        (200, SUCCESS)])
    chat_completion(client, model="test", messages=[], json_mode="auto")
    assert len(calls) == 2
    assert "response_format" not in calls[1]


@pytest.mark.parametrize("mode,status,body", [
    ("on", 400, {"error": {"message": "response_format is unsupported"}}),
    ("auto", 401, {"error": {"message": "invalid key"}}),
    ("auto", 429, {"error": {"code": "insufficient_quota", "message": "no quota"}}),
    ("auto", 400, {"error": {"message": "model not available"}}),
])
def test_terminal_errors_do_not_retry_or_switch_provider(mode, status, body):
    client, calls = compatible_client([(status, body)])
    with pytest.raises(openai.APIStatusError):
        chat_completion(client, model="test", messages=[], json_mode=mode)
    assert len(calls) == 1


def test_quota_error_is_distinct_and_does_not_echo_provider_body():
    client, calls = compatible_client([(429, {"error": {"code": "insufficient_quota", "message": "secret provider details"}})])
    with pytest.raises(openai.APIStatusError) as captured:
        chat_completion(client, model="test", messages=[])
    result = error_details(captured.value)
    assert result["code"] == "quota_exceeded"
    assert "secret provider details" not in str(result)
