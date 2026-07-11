---
type: Skill Card
title: sciatlas-idea-generate
description: Select this skill when the user wants new research directions, brainstormed hypotheses, cross-topic combinations, or project ideas grounded in retrieved papers. It requires a topic or field plus SciAtlas access details, and it outputs an idea_seed_set. Use it when SciAtlas search-papers is available or can be made available via executable check, installation, and environment configuration. Do not route here for general web search, direct literature review synthesis without idea generation, or tasks lacking a topic/field and required SciAtlas auth/base URL configuration.
skill_id: skill:sciatlas-idea-generate
selectable: True
source: ../sources/sciatlas-idea-generate.md
tags: [skill, idea_seed_set, sciatlas_search_papers, check_sciatlas_executable, install_sciatlas_editable, install_sciatlas_from_github]
---

# Skill Card

Skill: sciatlas-idea-generate

## Purpose

Select this skill when the user wants new research directions, brainstormed hypotheses, cross-topic combinations, or project ideas grounded in retrieved papers. It requires a topic or field plus SciAtlas access details, and it outputs an idea_seed_set. Use it when SciAtlas search-papers is available or can be made available via executable check, installation, and environment configuration. Do not route here for general web search, direct literature review synthesis without idea generation, or tasks lacking a topic/field and required SciAtlas auth/base URL configuration.

## Use When

- Use when the user wants new research directions, hypotheses, cross-topic combinations, or project ideas grounded in retrieved papers and can provide a topic/field plus any needed SciAtlas auth details.
- Use as an early-stage literature ideation step: verify SciAtlas availability and configuration, search papers for the provided topic, then synthesize idea_seed_set from the retrieved literature. Best when the goal is exploration rather than answering a fixed research question. If SciAtlas is not already usable, perform executable check and environment setup before paper retrieval.

## Do Not Use When

- cannot retrieve papers until the sciatlas executable is present or installed
- retrieval is blocked until SCIATLAS_API_KEY is configured or obtained through registration
- any SciAtlas command other than search-papers is outside the allowed retrieval scope
- the first retrieval pool may be too homogeneous and require a contrastive follow-up search
- idea seeds are rejected if they only apply a method to a domain without a mechanism and evaluation plan
- the full API token must not be disclosed while configuring or using the skill

## Inputs

- desired_topic_or_field: a topic, field, or clarification to steer literature retrieval and idea generation
- sciatlas_executable_available: the sciatlas CLI must exist before retrieval can run
- sciatlas_api_key: an API key or token for SciAtlas access when authentication is needed
- sciatlas_api_base_url_configured: SciAtlas API base URL must be set to the service endpoint used by the skill

## Outputs

- idea_seed_set: a set of 3-8 evidence-grounded research idea seeds, each with hypothesis, evidence trail, nontriviality, closest prior-art risk, minimal validation experiment, and a follow-up search query

## Tools And Dependencies

- sciatlas_search_papers: SciAtlas retrieval command used to gather literature for idea generation
- check_sciatlas_executable: command used to verify the sciatlas CLI exists before retrieval
- install_sciatlas_editable: local repository installation path for the SciAtlas CLI
- install_sciatlas_from_github: GitHub-based installation path for the SciAtlas CLI
- configure_sciatlas_env_vars: environment variable setup for SciAtlas base URL and API key

## Composition Notes

- compose_with: [[skills/cards/sciatlas-quick-paper-search]]
- compose_with: [[skills/cards/sciatlas-idea-evaluate]]
- member_of: [[communities/0000-sciatlas-idea-data|Literature-grounded research idea lifecycle]]

## Failure Modes

- missing_sciatlas_runtime
- missing_sciatlas_api_key
- unsupported_downstream_sciatlas_command
- homogeneous_search_pool
- trivial_or_ungrounded_idea
- credential_disclosure_risk

## Read Full Source

Open [full SKILL.md](../sources/sciatlas-idea-generate.md) when the card is insufficient to decide routing boundaries or execution requirements.
