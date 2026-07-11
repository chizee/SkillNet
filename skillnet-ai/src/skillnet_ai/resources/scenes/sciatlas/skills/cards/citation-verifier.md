---
type: Skill Card
title: citation-verifier
description: Select this skill when the input is a known citation artifact such as a DOI, URL, arXiv ID, PubMed ID, citation string, or paper title and the task is to verify or normalize it. It is suitable for quick citation checking and enrichment, producing a structured citation card or hydrated paper record. Do not route here for topic discovery, broad literature search, or citation-graph exploration.
skill_id: skill:citation-verifier
selectable: True
source: ../sources/citation-verifier.md
tags: [skill, structured_citation_card, hydrated_paper_record, verify_citation, fetch]
---

# Skill Card

Skill: citation-verifier

## Purpose

Select this skill when the input is a known citation artifact such as a DOI, URL, arXiv ID, PubMed ID, citation string, or paper title and the task is to verify or normalize it. It is suitable for quick citation checking and enrichment, producing a structured citation card or hydrated paper record. Do not route here for topic discovery, broad literature search, or citation-graph exploration.

## Use When

- Use for a known citation or identifier that needs quick validation and normalization, not for topic discovery, broad literature search, or citation-graph exploration.
- Use the normalized citation output before downstream citation-dependent processing, and prefer the hydrated paper record when later steps need structured metadata. The skill is oriented to single-item validation and enrichment, not broader research discovery.

## Do Not Use When

- The citation cannot be verified cleanly or the match is ambiguous; the skill should report the issue and suggest a more complete title or different identifier.
- The request is for literature search or citation-graph exploration rather than checking a known reference, so this skill should not be selected.

## Inputs

- raw_citation_input: A single user-provided reference in the form of a DOI, URL, arXiv ID, PubMed ID, citation string, or partial title.

## Outputs

- structured_citation_card: A clean structured card containing title, authors, year, venue, DOI, identifiers, and verification status.
- hydrated_paper_record: A resolved paper record enriched with abstract, citation count, and venue details after successful verification.

## Tools And Dependencies

- verify_citation: Resolves and validates the raw citation input first, including DOI strings, arXiv IDs, PubMed IDs, URLs, and free-text citation strings.
- fetch: Retrieves the full paper record after successful verification.

## Composition Notes

- member_of: [[communities/0003-citation-verifier-docx|Scholarly Manuscript Artifact Handling]]

## Failure Modes

- verification_failed_or_ambiguous
- wrong_scope_topic_discovery_or_graph_exploration

## Read Full Source

Open [full SKILL.md](../sources/citation-verifier.md) when the card is insufficient to decide routing boundaries or execution requirements.
