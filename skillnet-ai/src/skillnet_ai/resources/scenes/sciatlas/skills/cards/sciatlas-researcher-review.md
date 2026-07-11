---
type: Skill Card
title: sciatlas-researcher-review
description: Select this skill when the request is about a specific researcher’s background, representative papers, topic evolution, or an author-centered literature overview, and the answer must be grounded only in retrieved SciAtlas paper evidence. It requires a researcher name plus SciAtlas executable access and credentials, and it is not a general biography or open-web research skill. Expected outputs are a researcher profile ledger, a literature-grounded researcher profile report, and follow-up search queries.
skill_id: skill:sciatlas-researcher-review
selectable: True
source: ../sources/sciatlas-researcher-review.md
tags: [skill, researcher_profile_ledger, literature_grounded_researcher_profile_report, followup_search_queries, sciatlas_search_papers, sciatlas_executable_discovery, python_pip_install_sciatlas, environment_variable_configuration]
---

# Skill Card

Skill: sciatlas-researcher-review

## Purpose

Select this skill when the request is about a specific researcher’s background, representative papers, topic evolution, or an author-centered literature overview, and the answer must be grounded only in retrieved SciAtlas paper evidence. It requires a researcher name plus SciAtlas executable access and credentials, and it is not a general biography or open-web research skill. Expected outputs are a researcher profile ledger, a literature-grounded researcher profile report, and follow-up search queries.

## Use When

- Use when a user asks for a researcher’s background, representative papers, topic evolution, or an author-centered literature overview and the profile must be grounded only in retrieved SciAtlas paper evidence.
- Best used after SciAtlas executable discovery and environment/API setup, because it depends on executable access and credentials before paper retrieval can happen. Use the produced follow-up search queries to extend coverage or refine the profile when the initial paper set is incomplete, and validate that all claims are supported by retrieved paper evidence rather than external memory.

## Do Not Use When

- Common or ambiguous names require a clarifying disambiguator before reliable searching.
- Retrieval cannot proceed if the sciatlas executable is absent until it is installed.
- SciAtlas retrieval is blocked when SCIATLAS_API_KEY is absent until the user registers and provides a token.
- Papers with unclear author evidence should be discarded or clearly marked as weak.
- The output is a literature-grounded profile, not a complete bibliography or authoritative CV, so overclaiming is invalid.

## Inputs

- researcher_name: The researcher identity or name to query in SciAtlas search-papers.
- sciatlas_executable: The sciatlas CLI must be available before retrieval can begin.
- sciatlas_api_key: A configured SciAtlas API key for authenticated retrieval.
- sciatlas_api_base_url: SciAtlas API base URL configured to the openkg endpoint.

## Outputs

- researcher_profile_ledger: A paper-level ledger with title, year, author-match status, topic, contribution, and evidence confidence.
- literature_grounded_researcher_profile_report: A confidence-noted literature-grounded profile with representative works, topic trajectory, recurring themes, and missing-evidence follow-ups.
- followup_search_queries: Next search-papers queries to resolve missing periods, ambiguity, or weak evidence.

## Tools And Dependencies

- sciatlas_search_papers: The only allowed SciAtlas retrieval command.
- sciatlas_executable_discovery: Check whether the sciatlas executable exists before retrieval.
- python_pip_install_sciatlas: Install SciAtlas with pip when the executable is missing.
- environment_variable_configuration: Set SciAtlas API base URL and API key in the shell environment.

## Composition Notes

- member_of: [[communities/0000-sciatlas-idea-data|Literature-grounded research idea lifecycle]]

## Failure Modes

- ambiguous_researcher_identity
- missing_sciatlas_installation
- missing_api_key
- uncertain_author_match
- non_authoritative_profile

## Read Full Source

Open [full SKILL.md](../sources/sciatlas-researcher-review.md) when the card is insufficient to decide routing boundaries or execution requirements.
