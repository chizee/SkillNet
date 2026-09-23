"""Scenario Analysis Example - Using SkillNetClient.

Run from the repository root:
    python -m pip install -e "./skillnet-ai[graph]"
    python examples/analyze_example.py
    python examples/analyze_example.py ./my_skills --output-dir ./my_index

Configure API_KEY, BASE_URL, SKILLNET_MODEL and EMBEDDING_API_KEY,
EMBEDDING_BASE_URL, EMBEDDING_MODEL, or use saved SkillNet settings.
See skillnet-ai/README.md for model configuration.

Without a skills directory, create/update four illustrative SKILL.md files in
./demo_analysis_skills. Only their instructions are analyzed; no PDF or CSV is
processed. Model and embedding API calls may incur costs. Repeated analysis
reuses cached model results when their inputs are unchanged.
"""

import argparse
import json
from pathlib import Path

from skillnet_ai import SkillNetClient

# Concrete handoffs and two alternative implementations of the same capability.
DEMO_SKILLS = {
    "pdf-table-to-csv": """---
name: pdf-table-to-csv
description: Extract a transaction table from a text-based PDF into a UTF-8 CSV.
---
# PDF transaction table to CSV

Use when a text-based PDF contains one transaction table with a header row and
an amount column. All amounts must be decimal numbers in the same currency.

1. Open the PDF with Python and pdfplumber. Extract the table, retaining the
   column names, row order and cell values. Use empty strings for empty cells.
2. Write transactions.csv with csv.writer, UTF-8 encoding and a header row.
3. Return the CSV path for subsequent quality checks and amount calculations.

Preserve the original PDF. Report ambiguous table boundaries or headers and
stop rather than guessing. Scanned PDFs require OCR outside this skill.
This step preserves missing values and duplicate rows for later inspection;
it does not validate, deduplicate or calculate transaction statistics.
""",
    "csv-quality-checker": """---
name: csv-quality-checker
description: Check a transaction CSV and produce a read-only data quality report.
---
# CSV quality check

Input: a UTF-8 transaction CSV with a header row and an amount column.
Use Python standard-library csv, decimal and json modules.

1. Read the CSV and check row widths, missing cells and duplicate rows.
2. Check that each amount parses as a finite Decimal. Record invalid values.
3. Write quality-report.json with the CSV path, row count, issue counts and
   passed=true only when at least one data row exists and every check passes.
4. Return the report and unchanged CSV paths. A passing report allows amount
   summarizers to use this CSV; otherwise the user must resolve the issues.

Never fill, delete, deduplicate or overwrite source data. Report malformed CSV
or a missing amount column as a failed check. Do not compute transaction means.
""",
    "csv-amount-summary": """---
name: csv-amount-summary
description: Calculate transaction count, total and mean using Python's standard library.
---
# Transaction amount summary

Input: a UTF-8 CSV with an amount column and a passing quality-report.json
for that unchanged file. Amounts must be finite decimals in one currency.

1. Read the report with json; confirm its CSV path and passed=true status.
2. Read the CSV with csv.DictReader and parse amounts using decimal.Decimal.
3. Calculate count, total and arithmetic mean; return them in a JSON report,
   representing decimal results as strings. Round the mean to two decimal
   places with ROUND_HALF_UP.

Stop on a failed or missing quality report, empty CSV or invalid amount.
Keep inputs unchanged. Use only the Python standard library. This skill
accepts user-provided transaction CSVs and performs no currency conversion.
""",
    "csv-amount-summary-pandas": """---
name: csv-amount-summary-pandas
description: Calculate transaction count, total and mean in a pandas workflow.
---
# Transaction amount summary with pandas

Input: a UTF-8 CSV with an amount column and a passing quality-report.json
for that unchanged file. Amounts must be finite decimals in one currency.

1. Read the report with json; confirm its CSV path and passed=true status.
2. Load the CSV with pandas.read_csv(dtype=str, keep_default_na=False).
3. Convert amounts to decimal.Decimal and calculate count, total and mean.
   Return a JSON report with decimal results as strings; round the mean to
   two decimal places with ROUND_HALF_UP.

Requires pandas in addition to Python. Stop on a failed or missing quality
report, empty CSV or invalid amount. Keep inputs unchanged. This skill accepts
user-provided transaction CSVs and performs no currency conversion.
""",
}


def setup_demo_environment(skills_dir: Path) -> None:
    """Write the sample skill instructions, preserving existing analysis artifacts."""
    for name, source in DEMO_SKILLS.items():
        directory = skills_dir / name
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "SKILL.md").write_text(source, encoding="utf-8")
    print(f"📦 Prepared {len(DEMO_SKILLS)} demo skills in {skills_dir.resolve()}")


def main() -> None:
    """Analyze a local library and display scenario-specific relationships."""
    parser = argparse.ArgumentParser(description="Build and inspect a SkillNet analysis index.")
    parser.add_argument(
        "skills_dir",
        nargs="?",
        type=Path,
        help="Existing skill library; omit to create demo skills.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("./demo_skillnet_index"),
        help="Analysis index directory (default: ./demo_skillnet_index).",
    )
    args = parser.parse_args()

    skills_dir = args.skills_dir
    if skills_dir is None:
        skills_dir = Path("./demo_analysis_skills")
        setup_demo_environment(skills_dir)

    # Model and embedding configuration comes from the environment or saved settings.
    client = SkillNetClient()
    print("\n🔍 Extracting scenarios and analyzing skill relationships...")
    analysis = client.analyze(skills_dir=skills_dir, output_dir=args.output_dir)
    print(f"Skills analyzed: {analysis.skill_count}")
    print(f"Relations: {analysis.relation_counts}")
    print(f"Cache hits: {analysis.cache_hits}")
    print(f"Index: {analysis.index_dir}")

    # CURRENT identifies the last successfully published snapshot.
    snapshot_name = (analysis.index_dir / "CURRENT").read_text(encoding="utf-8").strip()
    snapshot = analysis.index_dir / snapshot_name
    graph = json.loads((snapshot / "graph.json").read_text(encoding="utf-8"))
    print("\ncompose_with: predecessor -> successor under the stated conditions.")
    print("similar_to: comparable capabilities; check constraints before substituting.")
    if not graph["relations"]:
        print("No supported relationships found.")
    for relation in graph["relations"]:
        arrow = "->" if relation["type"] == "compose_with" else "<->"
        print(f"\n{relation['source']} {arrow} {relation['target']} ({relation['type']})")
        for context in relation["contexts"]:
            print(f"  Scenario: {context['scenario']}")
            print(f"  Explanation: {context['explanation']}")
            for condition in context["conditions"]:
                print(f"  Condition: {condition}")

    print(f"\n📄 Full graph: {snapshot / 'graph.json'}")
    print(f"📚 Wiki: {snapshot / 'wiki'}")
    print("Reuse this index with examples/route_example.py --index-dir <index directory>.")


if __name__ == "__main__":
    main()
