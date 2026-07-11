---
type: Skill Card
title: sciatlas-literature-review
description: Select when the user needs a literature review, related-work section, survey outline, paper map, or topic overview grounded in SciAtlas search-papers evidence. Best fit when inputs include a topic scope or need for clarification and the environment can supply a SciAtlas API key and CLI access. Outputs are oriented to search logs, evidence tables, thematic review text, development timeline notes, gap-driven follow-up queries, and a reading path. Do not route if the task requires evidence outside SciAtlas search-papers or a non-literature-review deliverable.
skill_id: skill:sciatlas-literature-review
selectable: True
source: ../sources/sciatlas-literature-review.md
tags: [skill, search_command_log, evidence_table, thematic_literature_review, timeline_or_development_notes, sciatlas_search_papers, shell_executable_discovery, shell_package_installation, shell_env_configuration]
---

# Skill Card

Skill: sciatlas-literature-review

## Purpose

Select when the user needs a literature review, related-work section, survey outline, paper map, or topic overview grounded in SciAtlas search-papers evidence. Best fit when inputs include a topic scope or need for clarification and the environment can supply a SciAtlas API key and CLI access. Outputs are oriented to search logs, evidence tables, thematic review text, development timeline notes, gap-driven follow-up queries, and a reading path. Do not route if the task requires evidence outside SciAtlas search-papers or a non-literature-review deliverable.

## Use When

- Use when a user needs a literature review, related-work summary, survey outline, paper map, or topic overview that should be grounded in SciAtlas search-papers evidence.
- Start by clarifying topic scope, then ensure SciAtlas API and CLI setup before searching papers. Use retrieved search results to build an evidence table, then synthesize a thematic literature review or survey outline from that evidence. Timeline/development notes and gap-focused next-search queries are useful for extending coverage, and the reading path can support downstream follow-up. No strong workflow guidance.

## Do Not Use When

- The workflow cannot start until the sciatlas executable exists or is installed.
- Search-papers cannot proceed without a valid SCIATLAS_API_KEY credential.
- Completion can stall when the user must provide email, a verification code, or the returned token.
- Using any SciAtlas downstream command other than search-papers violates the skill contract.
- A first pass can be too narrow and require a broader coverage pass.
- The full API token must never be included in the final answer.

## Inputs

- topic_scope_or_clarification: The topic or necessary topic clarification that defines what literature should be searched and reviewed.
- sciatlas_api_key: A valid SciAtlas API credential for running search-papers.
- sciatlas_cli_environment: The sciatlas executable must be available in the shell environment or installable locally before search can run.

## Outputs

- search_command_log: The exact search-papers command(s) used, with the token omitted.
- evidence_table: A 6-10 paper evidence table with title, year, venue/source, problem, method, supporting evidence, and role in the review.
- thematic_literature_review: A structured literature review with headings that clusters and compares papers by theme.
- timeline_or_development_notes: A year-aware timeline or development view of the topic when publication years are available.
- gap_focused_next_search_queries: Gap analysis paired with follow-up search queries for broader coverage or refinement.
- reading_path: A recommended first-three-papers reading path with rationale.

## Tools And Dependencies

- sciatlas_search_papers: The only SciAtlas retrieval command allowed for gathering paper evidence and metadata.
- shell_executable_discovery: Checking for the sciatlas executable with shell command discovery before attempting retrieval.
- shell_package_installation: Installing SciAtlas from the local repo or GitHub subdirectory using pip when the executable is missing.
- shell_env_configuration: Setting SCIATLAS_API_BASE_URL and SCIATLAS_API_KEY in the shell/session environment.
- browser_registration_flow: Browser-based registration and token acquisition when the API key is missing.

## Composition Notes

- compose_with: [[skills/cards/sciatlas-trend-report]]
- compose_with: [[skills/cards/sciatlas-idea-grounding]]
- compose_with: [[skills/cards/venue-templates]]
- member_of: [[communities/0001-sciatlas-table-paper|Paper Evidence Synthesis]]

## Failure Modes

- missing_sciatlas_cli
- missing_sciatlas_api_key
- human_only_registration_value_required
- forbidden_non_search_papers_command
- insufficient_search_coverage
- token_leakage_in_response

## Read Full Source

Open [full SKILL.md](../sources/sciatlas-literature-review.md) when the card is insufficient to decide routing boundaries or execution requirements.
