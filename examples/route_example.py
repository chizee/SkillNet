"""Skill Routing Example - Using SkillNetClient.

First run examples/analyze_example.py from the repository root. Install one of
the following extras for your chosen Explorer SDK:
    python -m pip install -e "./skillnet-ai[graph,claude]"
    python -m pip install -e "./skillnet-ai[graph,codex]"

Configure SKILLNET_EXPLORER_API_KEY, SKILLNET_EXPLORER_BASE_URL and
SKILLNET_EXPLORER_MODEL for the chosen SDK, independently of the analysis
model. Keep EMBEDDING_API_KEY, EMBEDDING_BASE_URL and EMBEDDING_MODEL configured;
the embedding endpoint and model must match the index. Saved settings also work.
See skillnet-ai/README.md for model configuration.

Run the two demo tasks with either backend:
    python examples/route_example.py --backend claude
    python examples/route_example.py --backend codex

Or route your own task against an existing index:
    python examples/route_example.py "Check my CSV for duplicates" --index-dir ./my_index --k 3

Without --backend, use SKILLNET_EXPLORER_BACKEND or saved settings (default: claude).
Without a query, make two route calls using the sample tasks below. These calls
use the embedding and Explorer APIs; they select skills without executing them.
"""

import argparse
from pathlib import Path
from time import perf_counter

from skillnet_ai import SkillNetClient

DEMO_TASKS = (
    "I have a text-based PDF containing one transaction table with an amount column "
    "in a single currency. Extract it to CSV, check missing values, duplicate rows "
    "and invalid amounts, then calculate the mean amount if the checks pass.",
    "I already have transactions.csv with an amount column in a single currency "
    "and a passing quality-report.json for that unchanged file. Calculate the "
    "mean amount using only the Python standard library.",
)


def main() -> None:
    """Select skills for complete and partially prepared tasks using one index."""
    parser = argparse.ArgumentParser(description="Route tasks through a SkillNet analysis index.")
    parser.add_argument("query", nargs="?", help="Task to route; omit to run both demo tasks.")
    parser.add_argument(
        "--index-dir",
        type=Path,
        default=Path("./demo_skillnet_index"),
        help="Existing analysis index (default: ./demo_skillnet_index).",
    )
    parser.add_argument("--backend", choices=("claude", "codex"), help="Explorer SDK override.")
    parser.add_argument("--k", type=int, default=5, help="Maximum skills per task (default: 5).")
    args = parser.parse_args()

    client = SkillNetClient()
    queries = DEMO_TASKS if args.query is None else (args.query,)
    print("Skills are returned as a set of choices, not an execution sequence.")
    print("The router may select fewer than k skills, including none.")
    for query in queries:
        print(f"\n🔍 Task: {query}")
        started = perf_counter()
        result = client.route(
            query=query,
            index_dir=args.index_dir,
            k=args.k,
            backend=args.backend,
        )
        print(f"Selected {len(result.skills)} skill(s) in {perf_counter() - started:.1f}s:")
        if not result.skills:
            print("  No suitable skills selected.")
        for skill in result.skills:
            print(f"\n  {skill.name} ({skill.skill_id})")
            print(f"  Path: {skill.path}")
            print(f"  Reason: {skill.reason}")
        if result.usage:
            print(f"\nUsage: {result.usage}")


if __name__ == "__main__":
    main()
