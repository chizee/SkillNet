import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills/skillnet"


def test_canonical_skill_fits_catalog_and_keeps_references():
    from skillnet_ai.validation import parse_frontmatter
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    metadata = parse_frontmatter(text)
    assert len(metadata["description"]) <= 500
    assert all(isinstance(v, str) for v in metadata["metadata"].values())
    import re
    for link in re.findall(r"\]\((references/[^)]+)\)", text):
        assert (SKILL / link).is_file(), link


def test_archive_is_complete_and_reproducible(tmp_path):
    spec = importlib.util.spec_from_file_location("package_skill", ROOT / "skillnet-ai/tools/package_skill.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    first = module.package_skill(SKILL, tmp_path / "first.zip")
    second = module.package_skill(SKILL, tmp_path / "second.zip")
    assert first.read_bytes() == second.read_bytes()
    with zipfile.ZipFile(first) as archive:
        names = archive.namelist()
        assert "skillnet/SKILL.md" in names
        assert "skillnet/scripts/_skillnet_cli.py" in names
        assert "skillnet/references/setup.md" in names
        assert not any("__pycache__" in n or n.endswith(".pyc") for n in names)


def test_legacy_validator_runs_from_unrelated_working_directory(tmp_path):
    result = subprocess.run([sys.executable, str(SKILL / "scripts/skillnet_validate.py"), str(SKILL), "--json"],
                            cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["ok"]


def test_legacy_creator_forwards_arguments_without_own_sdk_logic(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(SKILL / "scripts"))
    spec = importlib.util.spec_from_file_location("legacy_creator", SKILL / "scripts/skillnet_create.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    calls = []
    monkeypatch.setattr(module, "run_cli", lambda args: calls.append(args) or 0)
    monkeypatch.setattr(sys, "argv", ["create.py", "--prompt", "A user's CSV skill", "--json"])
    assert module.main() == 0
    assert calls[0][0] == "create" and "--evaluate" in calls[0]
    assert calls[0][calls[0].index("--prompt") + 1] == "A user's CSV skill"


def test_live_runner_without_credentials_reports_pending(tmp_path):
    env = dict(os.environ)
    env.pop("SKILLNET_TEST_UNUSED_KEY", None)
    output = tmp_path / "live"
    result = subprocess.run([sys.executable, str(ROOT / "skillnet-ai/acceptance/run_live.py"),
        "--provider-label", "test", "--base-url", "https://provider.test/v1", "--model", "test",
        "--api-key-env", "SKILLNET_TEST_UNUSED_KEY", "--output-dir", str(output)],
        capture_output=True, text=True, env=env)
    assert result.returncode == 2
    assert "PENDING" in result.stderr
    assert not output.exists()
