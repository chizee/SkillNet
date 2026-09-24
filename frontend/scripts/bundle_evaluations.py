"""Copy completed SDK evaluation reports into the read-only frontend."""

from __future__ import annotations

import json
from pathlib import Path


FRONTEND = Path(__file__).resolve().parents[1]
SOURCE = FRONTEND / "data" / "evaluations"
OUTPUT = FRONTEND / "src" / "evaluations.json"
DIMENSIONS = ("safety", "completeness", "executability", "maintainability", "cost_awareness")


def main() -> None:
    records = {}
    for path in sorted(SOURCE.glob("*.json")):
        skill_id = path.stem
        result = json.loads(path.read_text(encoding="utf-8"))
        if result.get("status") != "ok":
            continue
        report = result["report"]
        for dimension in DIMENSIONS:
            if report[dimension]["level"] not in {"Good", "Average", "Poor"} or not report[dimension]["reason"]:
                raise ValueError(f"Invalid {dimension} report: {skill_id}")
        records[skill_id] = {
            "dimensions": {dimension: report[dimension] for dimension in DIMENSIONS},
            "injectionScan": {
                "clean": report["prompt_injection_scan"]["clean"],
                "complete": report["prompt_injection_scan"]["complete"],
                "count": report["prompt_injection_scan"]["count"],
            },
        }
    OUTPUT.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(records)} evaluation reports to {OUTPUT}")


if __name__ == "__main__":
    main()
