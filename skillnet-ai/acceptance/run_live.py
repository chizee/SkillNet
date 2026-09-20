"""Explicit, billable create+evaluate smoke test for a selected compatible endpoint."""
import argparse
from datetime import datetime, timezone
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import sys
import time

from skillnet_ai import SkillNetClient
from skillnet_ai.errors import error_details
from skillnet_ai.validation import validate_skill, validate_evaluation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider-label", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--api-key-env", required=True, help="Environment variable name, never the key itself.")
    parser.add_argument("--output-dir", type=Path, required=True, help="New directory for test artifacts.")
    args = parser.parse_args()
    if not os.environ.get(args.api_key_env):
        print("PENDING: the selected credential environment variable is absent.", file=sys.stderr)
        return 2
    if args.output_dir.exists():
        parser.error("Choose a new output directory; existing artifacts are preserved.")
    args.output_dir.mkdir(parents=True)
    result = {"timestamp": datetime.now(timezone.utc).isoformat(), "sdk_version": version("skillnet-ai"),
              "platform": platform.platform(), "provider": args.provider_label,
              "base_url": args.base_url, "model": args.model, "status": "failed",
              "paths": [], "validation": {}, "evaluations": {}, "task_execution": "pending"}
    start = time.monotonic()
    try:
        client = SkillNetClient(api_key=os.environ[args.api_key_env], base_url=args.base_url, model=args.model)
        result["paths"] = client.create(prompt=(
            "Create one reusable skill named csv-header-check. Given a CSV file and required column names, "
            "report missing columns without modifying the input. Include a Python standard-library CLI "
            "with --help, clear exit codes and two usage examples. Do not call external services."),
            output_dir=args.output_dir / "generated")
        if not result["paths"]:
            raise ValueError("No generated skill directories.")
        for path in result["paths"]:
            validation = validate_skill(path)
            result["validation"][path] = validation
            if not validation["valid"]:
                raise ValueError("Generated skill failed structural validation.")
            result["evaluations"][path] = validate_evaluation(client.evaluate(path))
        result["status"] = "passed"
    except Exception as exc:
        result["error"] = error_details(exc)
    result["seconds"] = round(time.monotonic() - start, 2)
    (args.output_dir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": result["status"], "report": str(args.output_dir / 'result.json'),
                      "task_execution": "pending"}))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
