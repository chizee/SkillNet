---
type: Skill Card
title: sciatlas-idea-grounding
description: Select this skill when the user provides a research idea and needs similar work, related-work support, differentiation evidence, motivation support, or literature-grounded refinement. It requires a research idea description plus SciAtlas API token and executable availability, and it is bounded to SciAtlas search-papers rather than general web or multi-source literature search. Typical outputs include a prior-art matrix, closest prior work summary, differentiation statement, novelty risk assessment, next search query, and sanitized search commands.
skill_id: skill:sciatlas-idea-grounding
selectable: True
source: ../sources/sciatlas-idea-grounding.md
tags: [skill, prior_art_matrix, grounded_positioning_memo, closest_prior_work_summary, differentiation_statement, sciatlas_search_papers, sciatlas_executable_presence_check, pip_install_sciatlas_package, sciatlas_environment_configuration]
---

# Skill Card

Skill: sciatlas-idea-grounding

## Purpose

Select this skill when the user provides a research idea and needs similar work, related-work support, differentiation evidence, motivation support, or literature-grounded refinement. It requires a research idea description plus SciAtlas API token and executable availability, and it is bounded to SciAtlas search-papers rather than general web or multi-source literature search. Typical outputs include a prior-art matrix, closest prior work summary, differentiation statement, novelty risk assessment, next search query, and sanitized search commands.

## Use When

- Use this skill when a user brings a research idea and wants similar work, related-work support, differentiation evidence, motivation support, or literature-grounded refinement using SciAtlas search-papers.
- Use after the idea is stated and before downstream drafting or recommendation steps that depend on grounded prior art. First verify SciAtlas executable availability and environment configuration, then search papers, then synthesize closest prior work and differentiation evidence into a grounded positioning memo and novelty risk assessment. If the needed inputs or SciAtlas access are missing, this skill should be used to surface the gap rather than claim literature-backed conclusions.

## Do Not Use When

- The skill cannot retrieve papers until the sciatlas executable and API key setup are completed.
- If the idea lacks enough detail, the skill can only ask one short clarification question before searching.
- A first search may be too sparse, requiring a second pass around the problem instead of the mechanism.
- Novelty claims must be downgraded when the search evidence is insufficient.
- Using any SciAtlas command other than search-papers violates the skill boundary.

## Inputs

- research_idea_description: A user-supplied research idea or concise idea statement to ground against prior work.
- sciatlas_api_token: A valid SciAtlas API token needed for authenticated search-papers access.
- sciatlas_executable_available: The sciatlas command-line executable must be present or installable before retrieval can run.

## Outputs

- prior_art_matrix: A structured matrix comparing each retrieved paper against the idea by overlap, difference, and threat level.
- grounded_positioning_memo: A literature-grounded memo that positions the idea against prior work and states differentiation and novelty risk.
- closest_prior_work_summary: A concise summary of the nearest prior work found by search.
- differentiation_statement: A statement explaining how the idea differs from the closest prior art.
- novelty_risk_assessment: An assessment of novelty risks and how to refine the idea to avoid the closest prior art.
- next_search_query: A follow-up SciAtlas search-papers query to test the weakest point in the idea.
- sanitized_search_commands: The search command(s) used, with the token omitted.

## Tools And Dependencies

- sciatlas_search_papers: SciAtlas retrieval command used for prior-art search and follow-up searches.
- sciatlas_executable_presence_check: Command check for whether the sciatlas executable is installed.
- pip_install_sciatlas_package: Installation path for the SciAtlas CLI package when the executable is missing.
- sciatlas_environment_configuration: Environment-variable setup for SCIATLAS_API_BASE_URL and SCIATLAS_API_KEY.

## Composition Notes

- compose_with: [[skills/cards/sciatlas-literature-review]]
- member_of: [[communities/0000-sciatlas-idea-data|Literature-grounded research idea lifecycle]]

## Failure Modes

- missing_sciatlas_setup
- idea_too_vague_to_search
- sparse_search_results
- unsupported_novelty_claims
- disallowed_downstream_commands

## Read Full Source

Open [full SKILL.md](../sources/sciatlas-idea-grounding.md) when the card is insufficient to decide routing boundaries or execution requirements.
