---
type: Skill Card
title: sciatlas-idea-evaluate
description: Select this skill when the task is to assess whether a research idea is worth pursuing and you have a clear research_idea_statement, plus access to SciAtlas search-papers via an executable and API/registration token. It is appropriate for literature-backed critique, closest-prior-art checking, and generating an evaluation artifact set such as an evaluation ledger, evaluation table, recommendation, revised idea statement, and next search query. Do not route it for general research tasks without an idea statement or without SciAtlas access; its scope is search-papers evaluation, not broad research execution.
skill_id: skill:sciatlas-idea-evaluate
selectable: True
source: ../sources/sciatlas-idea-evaluate.md
tags: [skill, evaluation_ledger, evaluation_table, closest_prior_art_risk, recommendation, sciatlas_search_papers, shell_command_probe, python_pip_install, shell_env_configuration]
---

# Skill Card

Skill: sciatlas-idea-evaluate

## Purpose

Select this skill when the task is to assess whether a research idea is worth pursuing and you have a clear research_idea_statement, plus access to SciAtlas search-papers via an executable and API/registration token. It is appropriate for literature-backed critique, closest-prior-art checking, and generating an evaluation artifact set such as an evaluation ledger, evaluation table, recommendation, revised idea statement, and next search query. Do not route it for general research tasks without an idea statement or without SciAtlas access; its scope is search-papers evaluation, not broad research execution.

## Use When

- Use when a user wants a literature-backed assessment of whether a proposed research idea is worth pursuing, especially when novelty, feasibility, soundness, and differentiation need to be checked against SciAtlas search-papers results.
- Start with the user’s idea statement, then use SciAtlas search-papers to compare against prior art and compile evidence for novelty, feasibility, soundness, and differentiation. The skill’s outputs support a handoff by providing a recommendation, revised idea statement, closest prior art risk, and the next search query, while setup may require probing the executable and configuring the shell environment or Python dependencies before searching. Use it when an evidence-grounded literature review is needed to decide whether to proceed, revise, or abandon the idea.

## Do Not Use When

- Invalid if the workflow tries to call any SciAtlas downstream command other than search-papers.
- Fails or cannot start if the sciatlas executable is absent and installation is not performed.
- Cannot proceed with retrieval if no SCIATLAS_API_KEY is available and registration/token setup is not completed.
- The evaluation becomes unknown or weak when search results do not support novelty, feasibility, soundness, or differentiation.
- Novelty may be overstated if the closest competing formulation is not searched and compared.

## Inputs

- research_idea_statement: A research idea to be converted into novelty, feasibility, soundness, and differentiation claims.
- sciatlas_executable_available: The sciatlas CLI must exist before retrieval can begin.
- sciatlas_api_access_or_registration_token: A SciAtlas API key/token or the ability to register and obtain one.

## Outputs

- evaluation_ledger: A structured ledger of evidence for and against novelty, feasibility, soundness, and missing evidence.
- evaluation_table: A scored comparison table for novelty, feasibility, soundness, and differentiation.
- closest_prior_art_risk: A risk statement about the closest competing prior work and how strongly it threatens the idea's novelty or differentiation.
- recommendation: A go, revise, or no-go decision based on the evidence review.
- revised_idea_statement: A sharpened or revised version of the idea after evidence review.
- next_search_papers_query: A follow-up SciAtlas search-papers query to refine the literature check.
- search_command_log: The search command or commands used, with token omitted.

## Tools And Dependencies

- sciatlas_search_papers: SciAtlas retrieval command used to gather literature evidence.
- shell_command_probe: Shell command used to verify the sciatlas executable exists.
- python_pip_install: Fallback installation command for adding the SciAtlas CLI when missing.
- shell_env_configuration: Shell environment variable setup for SciAtlas base URL and API key.

## Composition Notes

- compose_with: [[skills/cards/sciatlas-idea-generate]]
- compose_with: [[skills/cards/sciatlas-quick-paper-search]]
- member_of: [[communities/0000-sciatlas-idea-data|Literature-grounded research idea lifecycle]]

## Failure Modes

- unsupported_sciatlas_command_usage
- missing_sciatlas_installation_or_cli
- missing_api_key_or_registration_blocked
- insufficient_evidence_for_scored_dimensions
- weak_novelty_or_prior_art_stress_test

## Read Full Source

Open [full SKILL.md](../sources/sciatlas-idea-evaluate.md) when the card is insufficient to decide routing boundaries or execution requirements.
