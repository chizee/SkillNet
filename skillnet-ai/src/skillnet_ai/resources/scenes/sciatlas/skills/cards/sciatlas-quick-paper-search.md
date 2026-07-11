---
type: Skill Card
title: sciatlas-quick-paper-search
description: Select this skill when the user needs a first-pass literature check, retrieval smoke test, quick paper shortlist, or help choosing the next SciAtlas skill. It requires paper_search_topic and is bounded to SciAtlas search-papers only; it outputs a paper_search_decision_aid, evidence_ledger, search_command_used, and next_action_recommendation. Use it for small, evidence-backed search results rather than deep literature synthesis or broad research workflows.
skill_id: skill:sciatlas-quick-paper-search
selectable: True
source: ../sources/sciatlas-quick-paper-search.md
tags: [skill, paper_search_decision_aid, evidence_ledger, search_command_used, next_action_recommendation, sciatlas_search_papers, cli_presence_check, python_pip_install_editable, python_pip_install_from_github]
---

# Skill Card

Skill: sciatlas-quick-paper-search

## Purpose

Select this skill when the user needs a first-pass literature check, retrieval smoke test, quick paper shortlist, or help choosing the next SciAtlas skill. It requires paper_search_topic and is bounded to SciAtlas search-papers only; it outputs a paper_search_decision_aid, evidence_ledger, search_command_used, and next_action_recommendation. Use it for small, evidence-backed search results rather than deep literature synthesis or broad research workflows.

## Use When

- Use when the user needs a quick first-pass literature check, retrieval smoke test, or a small evidence-backed paper shortlist and wants the next SciAtlas skill or follow-up query.
- Start with a paper_search_topic, run the SciAtlas paper search, then inspect the evidence ledger and search command used to confirm the retrieval. Use the returned decision aid and next action recommendation to decide whether the topic is covered well enough or whether a deeper SciAtlas skill or follow-up query is needed.

## Do Not Use When

- the SciAtlas executable is unavailable and must be installed before retrieval can run
- no SCIATLAS_API_KEY is configured, so the user must provide registration inputs or the returned token
- the requested topic is genuinely ambiguous and the skill must ask the user to clarify it
- a setup or retrieval step fails and the run cannot proceed until the blocker is fixed
- the report artifacts lack key metadata or the abstract is missing, making the evidence weak

## Inputs

- paper_search_topic: the research topic or question to search in natural English

## Outputs

- paper_search_decision_aid: a compact search result combining the command used, top paper evidence, synthesis, and next-step guidance
- evidence_ledger: ranked paper evidence with title, year, authors if available, match rationale, strongest clue, and URL/ID
- search_command_used: the SciAtlas search command used for the run with the token omitted
- next_action_recommendation: a routing suggestion for the next SciAtlas skill or follow-up search query

## Tools And Dependencies

- sciatlas_search_papers: SciAtlas retrieval command used for paper search runs
- cli_presence_check: checks whether the SciAtlas CLI executable exists before running retrieval
- python_pip_install_editable: local editable installation path when the repository is present
- python_pip_install_from_github: GitHub-based installation path when the repository is not present
- shell_environment_configuration: sets SCIATLAS_API_BASE_URL and SCIATLAS_API_KEY in the current shell before retrieval
- run_artifact_inspection: reads the generated run directory artifacts after search completes

## Composition Notes

- compose_with: [[skills/cards/sciatlas-idea-generate]]
- compose_with: [[skills/cards/sciatlas-idea-evaluate]]
- compose_with: [[skills/cards/sciatlas-trend-report]]
- member_of: [[communities/0001-sciatlas-table-paper|Paper Evidence Synthesis]]

## Failure Modes

- missing_sciatlas_cli
- missing_api_token_or_registration_needed
- ambiguous_topic_needs_clarification
- retrieval_blocked_or_step_failed
- weak_or_incomplete_evidence

## Read Full Source

Open [full SKILL.md](../sources/sciatlas-quick-paper-search.md) when the card is insufficient to decide routing boundaries or execution requirements.
