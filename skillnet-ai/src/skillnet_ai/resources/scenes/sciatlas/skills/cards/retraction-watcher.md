---
type: Skill Card
title: retraction-watcher
description: Select this skill when the input is a manuscript bibliography, raw citation list, or reference dataset that needs retraction-status verification before submission or reuse. It requires citation_input plus internet access, Python 3.10+ runtime, and installed dependencies, and it produces a retraction_watch_report and citation_verification_result_set. Best fit for citation screening and reproducible integrity reporting; do not route if offline execution or non-citation document review is needed.
skill_id: skill:retraction-watcher
selectable: True
source: ../sources/retraction-watcher.md
tags: [skill, retraction_watch_report, citation_verification_result_set, scripts/main.py, python--m-py_compile-scripts/main.py, python-scripts/main.py---help, retraction-watch-database]
---

# Skill Card

Skill: retraction-watcher

## Purpose

Select this skill when the input is a manuscript bibliography, raw citation list, or reference dataset that needs retraction-status verification before submission or reuse. It requires citation_input plus internet access, Python 3.10+ runtime, and installed dependencies, and it produces a retraction_watch_report and citation_verification_result_set. Best fit for citation screening and reproducible integrity reporting; do not route if offline execution or non-citation document review is needed.

## Use When

- Use when a manuscript, bibliography, or raw citation set must be verified for retractions, corrections, or expressions of concern before submission or reuse, especially when reproducible citation integrity reporting is needed.
- Use after citations are assembled and before final manuscript submission or downstream reuse so the report can be checked against the source reference set. The citation_verification_result_set can be used as validation output for manual review or automated filtering of flagged references. No strong workflow guidance.

## Do Not Use When

- The task falls outside the documented retraction-checking workflow and should be stopped rather than broadened by guessing.
- Essential citation input or other required context is missing, preventing safe completion.
- Internet or external API access is unavailable, blocking retraction database checks.
- Very recent retractions may not yet appear in the indexed sources, causing false negatives.
- Title-only matching can misidentify similar papers or minor title variants as the same work.
- The packaged Python workflow may fail to parse or execute, requiring fallback handling.

## Inputs

- citation_input: A manuscript, paper, bibliography, PDF, text file, raw references, URL, or clipboard text containing citations to scan.
- internet_access: Network access to query retraction databases and APIs.
- python_runtime_3_10_plus: A Python 3.10+ runtime for the packaged workflow.
- installed_python_dependencies: Python dependencies from requirements.txt must be installed before running the packaged script.

## Outputs

- retraction_watch_report: A structured report with document and reference counts, check date, status categories, retraction reasons/dates, and recommended actions.
- citation_verification_result_set: Per-citation verification results that preserve reference numbering and separate assumptions, deliverables, risks, and unresolved items.

## Tools And Dependencies

- scripts/main.py: Primary packaged implementation surface for the retraction scan workflow.
- python -m py_compile scripts/main.py: Validation command used to verify the packaged script entry point parses before deeper execution.
- python scripts/main.py --help: CLI inspection command for the packaged workflow.
- Retraction Watch Database: Primary database source for retraction data.
- Crossref API: External API used for retraction metadata checks.
- PubMed API / E-utilities: PubMed-based lookup used for retraction notices and publication type filters.
- Open Retractions: Aggregated retraction data source used during checking.
- pip install -r requirements.txt: Dependency installation step required for the packaged Python workflow.

## Composition Notes

- member_of: [[communities/0004-bib-verify-peer|Scholarly Integrity Verification]]

## Failure Modes

- out_of_scope_request
- missing_critical_input
- database_lookup_unavailable
- recent_retraction_not_indexed
- ambiguous_title_matching_false_positive
- script_entrypoint_failure

## Read Full Source

Open [full SKILL.md](../sources/retraction-watcher.md) when the card is insufficient to decide routing boundaries or execution requirements.
