"""Generated file paths must stay inside the user's output directory."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from skillnet_ai.creator import SkillCreator


@pytest.fixture(params=["_save_skill_files", "_save_github_skill_files"])
def save_files(request):
    # File parsing needs no credentials or network client.
    return getattr(SkillCreator.__new__(SkillCreator), request.param)


def file_block(path, content="replacement"):
    return f"## FILE: {path}\n```text\n{content}\n```\n"


@pytest.mark.parametrize(
    "unsafe_path",
    ["../outside.txt", "nested/../../outside.txt", "C:/outside.txt",
     "C:outside.txt", r"..\outside.txt", r"\\server\share\outside.txt", "."],
)
def test_rejects_unsafe_paths_before_writing_any_files(tmp_path, save_files, unsafe_path):
    output = tmp_path / "output"
    outside = tmp_path / "outside.txt"
    outside.write_text("original")
    response = file_block("safe/SKILL.md") + file_block(unsafe_path)

    with pytest.raises(ValueError):
        save_files(response, str(output))

    assert outside.read_text() == "original"
    assert not output.exists()


def test_rejects_absolute_paths(tmp_path, save_files):
    outside = tmp_path / "outside.txt"
    outside.write_text("original")
    with pytest.raises(ValueError):
        save_files(file_block(str(outside)), str(tmp_path / "output"))
    assert outside.read_text() == "original"


@pytest.mark.parametrize("directory_link", [False, True])
def test_rejects_symlinks_leading_outside_output(tmp_path, save_files, directory_link):
    output = tmp_path / "output"
    output.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    target = outside / "file.txt"
    target.write_text("original")
    link = output / "linked"
    link.symlink_to(outside if directory_link else target, target_is_directory=directory_link)
    generated = "linked/file.txt" if directory_link else "linked"

    with pytest.raises(ValueError):
        save_files(file_block(generated), str(output))
    assert target.read_text() == "original"


def test_writes_nested_files_and_allows_normal_updates(tmp_path, save_files):
    response = file_block("demo/SKILL.md", "技能说明") + file_block("demo/scripts/run.py", "print('ok')")
    paths = save_files(response, str(tmp_path))
    assert {Path(p).relative_to(tmp_path).as_posix() for p in paths} == {
        "demo/SKILL.md", "demo/scripts/run.py",
    }
    assert (tmp_path / "demo/SKILL.md").read_text() == "技能说明\n"
    save_files(file_block("demo/SKILL.md", "updated"), str(tmp_path))
    assert (tmp_path / "demo/SKILL.md").read_text() == "updated\n"


def test_prompt_creation_rejects_unsafe_model_response(tmp_path):
    creator = SkillCreator.__new__(SkillCreator)
    creator._get_llm_response = Mock(return_value=file_block("../outside.txt"))
    assert creator.create_from_prompt("Create a demo skill", str(tmp_path / "output")) == []
    assert not (tmp_path / "outside.txt").exists()


def test_prompt_creation_preserves_symlink_output_directory(tmp_path):
    actual = tmp_path / "actual"
    actual.mkdir()
    output = tmp_path / "output"
    output.symlink_to(actual, target_is_directory=True)
    creator = SkillCreator.__new__(SkillCreator)
    creator._get_llm_response = Mock(return_value=file_block("demo/SKILL.md", "valid"))
    assert creator.create_from_prompt("Create a demo skill", str(output)) == [str(output / "demo")]
    assert (actual / "demo/SKILL.md").read_text() == "valid\n"
