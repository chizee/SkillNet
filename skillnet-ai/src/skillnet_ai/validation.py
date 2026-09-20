"""Offline Agent Skills structure checks; no model call or script execution."""
import re
import os
from pathlib import Path

import yaml

DIMENSIONS = ("safety", "completeness", "executability", "maintainability", "cost_awareness")


def parse_frontmatter(text: str) -> dict:
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise ValueError("SKILL.md must start with YAML frontmatter (---).")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError("Unclosed YAML frontmatter.") from exc
    try:
        metadata = yaml.safe_load("\n".join(lines[1:end]))
    except yaml.YAMLError as exc:
        raise ValueError("Invalid YAML frontmatter.") from exc
    if not isinstance(metadata, dict):
        raise ValueError("Frontmatter must be a YAML mapping.")
    return metadata


def validate_skill(skill_dir) -> dict:
    root = Path(os.path.abspath(Path(skill_dir).expanduser()))
    errors, warnings = [], []
    try:
        content = (root / "SKILL.md").read_text(encoding="utf-8")
        metadata = parse_frontmatter(content)
    except (OSError, UnicodeError, ValueError) as exc:
        return {"valid": False, "errors": [str(exc)], "warnings": []}
    name, description = metadata.get("name"), metadata.get("description")
    if (not isinstance(name, str) or not 1 <= len(name) <= 64
            or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name)):
        errors.append("name must be 1–64 lowercase letters/digits with single separating hyphens.")
    elif name != root.name:
        errors.append("name must match the skill directory name.")
    if not isinstance(description, str) or not description.strip() or len(description) > 1024:
        errors.append("description must be a nonempty string of at most 1024 characters.")
    elif len(description) > 500:
        warnings.append("dsh truncates catalog descriptions beyond 500 characters.")
    if "metadata" in metadata and (not isinstance(metadata["metadata"], dict)
            or any(not isinstance(k, str) or not isinstance(v, str)
                   for k, v in metadata["metadata"].items())):
        warnings.append("Portable metadata uses string keys and values; vendor metadata may be ignored.")
    if len(content.splitlines()) > 500:
        warnings.append("Consider moving conditional detail into references; SKILL.md exceeds 500 lines.")
    # scripts/ and references/ are optional, not validity requirements.
    return {"valid": not errors, "errors": errors, "warnings": warnings}


def validate_evaluation(report) -> dict:
    if not isinstance(report, dict):
        raise ValueError("Evaluation must be a JSON object.")
    if report.get("error"):
        raise ValueError("Evaluation provider returned an error report.")
    for dimension in DIMENSIONS:
        item = report.get(dimension)
        if (not isinstance(item, dict) or item.get("level") not in {"Good", "Average", "Poor"}
                or not isinstance(item.get("reason"), str) or not item["reason"].strip()):
            raise ValueError(f"Invalid evaluation dimension {dimension}: expected level and nonempty reason.")
    return report
