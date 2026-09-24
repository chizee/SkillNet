"""Build a read-only local dataset from this repository's SKILL.md files.

Edges are *literal document references*. They are never labelled as analyze output.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT_SKILLS = ROOT / "experiments" / "src" / "skills"
COLLECTION_LABELS = {"webshop": "WebShop", "scienceworld": "ScienceWorld", "alfworld": "ALFWorld"}
OUTPUT = Path(__file__).resolve().parents[1] / "src" / "demo.json"


def description(source: str) -> str:
    match = re.search(r"^description:\s*>-?\s*\n((?:[ \t]+.*\n)+)", source, re.M)
    if match:
        return " ".join(line.strip() for line in match.group(1).splitlines())
    match = re.search(r"^description:\s*(.+)$", source, re.M)
    return match.group(1).strip(" '\"") if match else ""


def main() -> None:
    directories = [
        (COLLECTION_LABELS.get(directory.name, directory.name.replace("_", " ").title()), directory)
        for directory in sorted(EXPERIMENT_SKILLS.iterdir()) if directory.is_dir()
    ]
    directories.append(("SkillNet", ROOT / "skills"))
    paths = [(collection, path) for collection, directory in directories for path in sorted(directory.glob("*/SKILL.md"))]
    ids_by_collection = {
        collection: {path.parent.name for current, path in paths if current == collection}
        for collection, _ in directories
    }
    skills = []
    references = []
    for collection, path in paths:
        source = path.read_text(encoding="utf-8-sig")
        skill_id = path.parent.name
        key = f"{collection}::{skill_id}"
        name = re.search(r"^name:\s*(.+)$", source, re.M)
        skills.append({
            "id": key,
            "skillId": skill_id,
            "name": name.group(1).strip(" '\"") if name else skill_id,
            "description": description(source),
            "collection": collection,
            "source": source,
            "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        })
        reference_ids = sorted((item for item in ids_by_collection[collection] if "-" in item), key=len, reverse=True)
        reference_pattern = re.compile(r"(?<![a-zA-Z0-9-])(?:" + "|".join(map(re.escape, reference_ids)) + r")(?![a-zA-Z0-9-])") if reference_ids else None
        seen = set()
        for line_number, line in enumerate(source.splitlines(), 1):
            for target in reference_pattern.findall(line) if reference_pattern else ():
                if target in ids_by_collection[collection] and target != skill_id and target not in seen:
                    seen.add(target)
                    references.append({
                        "source": key,
                        "target": f"{collection}::{target}",
                        "type": "source_reference",
                        "line": line_number,
                        "excerpt": line.strip(),
                    })
    OUTPUT.write_text(
        json.dumps({"skills": skills, "references": references}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(skills)} source skills and {len(references)} explicit references to {OUTPUT}")


if __name__ == "__main__":
    main()
