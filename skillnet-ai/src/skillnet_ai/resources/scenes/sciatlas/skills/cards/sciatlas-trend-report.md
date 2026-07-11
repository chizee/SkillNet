---
type: Skill Card
title: sciatlas-trend-report
description: Select this skill when the request is about topic history, field evolution, recent trends, representative papers over time, or emerging directions, and the answer should be grounded in SciAtlas search-papers results. It needs a research_topic plus access setup (SciAtlas API key or registration path, installable environment, and a recent time range or a defaulting policy). It produces a timeline trend report, timeline ledger, phase analysis, and next search queries; use it for literature exploration rather than general web research or non-timeline summaries.
skill_id: skill:sciatlas-trend-report
selectable: True
source: ../sources/sciatlas-trend-report.md
tags: [skill, timeline_trend_report, timeline_ledger, phase_analysis, next_search_queries, sciatlas_search_papers, command_line_existence_check, python_pip_install, environment_variable_configuration]
---

# Skill Card

Skill: sciatlas-trend-report

## Purpose

Select this skill when the request is about topic history, field evolution, recent trends, representative papers over time, or emerging directions, and the answer should be grounded in SciAtlas search-papers results. It needs a research_topic plus access setup (SciAtlas API key or registration path, installable environment, and a recent time range or a defaulting policy). It produces a timeline trend report, timeline ledger, phase analysis, and next search queries; use it for literature exploration rather than general web research or non-timeline summaries.

## Use When

- Use when a user asks for topic history, field evolution, recent trends, representative papers over time, or emerging directions and the answer should be grounded in SciAtlas search-papers results.
- Provide the topic and time window first, then use the generated timeline ledger and phase analysis to drive follow-on paper review or additional searches. The next search queries are the main handoff artifact for deeper exploration or refinement, while the report itself is the coverage view. No strong workflow guidance.

## Do Not Use When

- Fails or becomes invalid if any SciAtlas command other than search-papers is used.
- Cannot run retrieval if the API key is absent and registration/configuration has not been completed.
- Emerging trends should not be claimed from a single weak paper or unsupported framing change.
- Trend phase segmentation can become unreliable if the result set does not show clear natural breaks.

## Inputs

- research_topic: A topic or field query to investigate for trend analysis.
- sciatlas_access_or_installable_environment: A runtime where the SciAtlas CLI can be found or installed and configured.
- sciatlas_api_key_or_registration_path: An API key or access path for SciAtlas registration and authentication.
- recent_time_range_or_policy_for_defaulting: A desired time range when the user wants recency-bounded analysis; otherwise the skill can default to the last five complete years for recent-trend requests.

## Outputs

- timeline_trend_report: A trend report containing the search commands used, a timeline table, phased trend analysis, representative papers, emerging directions, weak signals, and next searches.
- timeline_ledger: A paper-by-paper ledger with year, contribution, theme, phase label, and evidence phrase.
- phase_analysis: Phase-level synthesis of dominant problems, methods, evaluation patterns, and what changed across time.
- next_search_queries: Follow-up search-papers queries for open questions or weaker signals.

## Tools And Dependencies

- sciatlas_search_papers: The only allowed SciAtlas retrieval command for evidence gathering.
- command_line_existence_check: Checks whether the sciatlas executable is available before retrieval.
- python_pip_install: Installs SciAtlas when the executable is missing.
- environment_variable_configuration: Sets SciAtlas base URL and API key for local execution.

## Composition Notes

- compose_with: [[skills/cards/sciatlas-literature-review]]
- compose_with: [[skills/cards/sciatlas-quick-paper-search]]
- member_of: [[communities/0001-sciatlas-table-paper|Paper Evidence Synthesis]]

## Failure Modes

- unsupported_downstream_command
- missing_or_unconfigured_api_access
- insufficient_evidence_for_emerging_signal
- no_natural_phase_breaks

## Read Full Source

Open [full SKILL.md](../sources/sciatlas-trend-report.md) when the card is insufficient to decide routing boundaries or execution requirements.
