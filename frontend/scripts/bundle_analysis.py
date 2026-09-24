"""Bundle a local analysis graph without machine paths or service endpoints.

Usage: python scripts/bundle_analysis.py COLLECTION PATH/TO/graph.json
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "public" / "data"
SKILLS_DIR = ROOT / "experiments" / "src" / "skills"
def main() -> None:
    if len(sys.argv) != 3 or not re.fullmatch(r"[a-z][a-z0-9_-]*", sys.argv[1]):
        raise SystemExit("usage: python scripts/bundle_analysis.py COLLECTION PATH/TO/graph.json")
    collection, graph_path = sys.argv[1:]
    skills_dir = SKILLS_DIR / collection
    if not skills_dir.is_dir():
        raise ValueError(f"Unknown collection: {collection}")
    output = OUTPUT_DIR / f"{collection}-analysis.json"
    snapshot = json.loads(Path(graph_path).read_text(encoding="utf-8"))
    if snapshot.get("schema_version") != 1:
        raise ValueError("Expected GraphSnapshot schema_version 1")

    skills = []
    for item in snapshot["skills"]:
        skill_id = item["skill_id"]
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", skill_id):
            raise ValueError(f"Invalid skill ID: {skill_id}")
        source_path = skills_dir / skill_id / "SKILL.md"
        if not source_path.is_file() or source_path.read_text(encoding="utf-8-sig").replace("\r\n", "\n") != item["source"].replace("\r\n", "\n"):
            raise ValueError(f"Snapshot source differs from the repository: {skill_id}")
        skills.append({
            "skill_id": skill_id,
            "name": item["name"],
            "path": str(source_path.relative_to(ROOT)).replace("\\", "/"),
            "source": item["source"],
            "profile": item["profile"],
        })

    relations = []
    for item in snapshot["relations"]:
        if item["type"] not in ("compose_with", "similar_to"):
            raise ValueError(f"Unsupported relation type: {item['type']}")
        relations.append({key: item[key] for key in ("source", "target", "type", "contexts")})

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({
        "schema_version": 1,
        "skills": skills,
        "relations": relations,
    }, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Wrote {len(skills)} skills and {len(relations)} relations to {output}")


if __name__ == "__main__":
    main()
