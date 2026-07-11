---
type: Skill Card
title: bib-verify
description: Select this skill when the task is to audit a .bib file or paper bibliography for hallucinated, fabricated, missing, or inaccurate citations. It requires a BibTeX file path and an execution environment with the listed runtime dependencies; it cross-checks each entry and reports verified, suspect, or not found outcomes with field-level mismatch details for title, authors, year, and DOI. Do not route for citation generation, general literature search, or manuscript editing unrelated to reference validation.
skill_id: skill:bib-verify
selectable: True
source: ../sources/bib-verify.md
tags: [skill, bib_verification_report_md, per_entry_verification_statuses, openjudge_paperreviewpipeline_bibtex_only, crossref, arxiv, dblp]
---

# Skill Card

Skill: bib-verify

## Purpose

Select this skill when the task is to audit a .bib file or paper bibliography for hallucinated, fabricated, missing, or inaccurate citations. It requires a BibTeX file path and an execution environment with the listed runtime dependencies; it cross-checks each entry and reports verified, suspect, or not found outcomes with field-level mismatch details for title, authors, year, and DOI. Do not route for citation generation, general literature search, or manuscript editing unrelated to reference validation.

## Use When

- Use when auditing a .bib file or paper bibliography for fabricated, hallucinated, or mis-cited references and you need per-entry verification status.
- Use as a validation pass after a bibliography or BibTeX export is available and before the references are trusted downstream. Its outputs are a markdown verification report and per-entry status list, which can be used to triage and correct individual entries based on mismatch details. It is best for coverage checks of existing references, not for creating new citations.

## Do Not Use When

- Standalone verification cannot proceed without the required .bib file path.
- CrossRef lookups may have reduced rate limits when no email is supplied.
- An entry can be reported as not_found when no match exists in any database.
- An entry can be reported as suspect when title or authors do not match a real paper, with detailed field mismatches exposed.

## Inputs

- bibtex_file_path: Path to the .bib file to verify.
- openjudge_runtime_dependencies: The OpenJudge BibTeX verification pipeline dependencies must be available to run the verifier.

## Outputs

- bib_verification_report_md: A Markdown report of the BibTeX verification run.
- per_entry_verification_statuses: Per-reference verification statuses with field-level mismatch details for suspect entries.

## Tools And Dependencies

- openjudge_paperreviewpipeline_bibtex_only: OpenJudge PaperReviewPipeline operating in BibTeX-only mode.
- crossref: CrossRef lookup for reference verification.
- arxiv: arXiv lookup for reference verification.
- dblp: DBLP lookup for reference verification.

## Composition Notes

- member_of: [[communities/0004-bib-verify-peer|Scholarly Integrity Verification]]

## Failure Modes

- missing_bibtex_file_path
- crossref_rate_limit_constraint
- no_database_match_not_found
- field_mismatch_suspect

## Read Full Source

Open [full SKILL.md](../sources/bib-verify.md) when the card is insufficient to decide routing boundaries or execution requirements.
