---
type: Skill Card
title: academic-writing-refiner
description: Select this skill when the input is draft academic text to polish, proofread, or lightly edit research writing, especially LaTeX content or venue-specific material such as abstracts, introductions, related work, methods, experiments, conclusions, camera-ready revisions, rebuttals, or paper revisions for major CS conferences and similar venues. It expects the text to refine and works better with surrounding context when available. Do not route non-academic writing or tasks that require generating new research content.
skill_id: skill:academic-writing-refiner
selectable: True
source: ../sources/academic-writing-refiner.md
tags: [skill, refined_academic_text, marginal_notes, unresolved_issues_list, references/section-guide.md, references/word-choice.md, references/rebuttal-guide.md]
---

# Skill Card

Skill: academic-writing-refiner

## Purpose

Select this skill when the input is draft academic text to polish, proofread, or lightly edit research writing, especially LaTeX content or venue-specific material such as abstracts, introductions, related work, methods, experiments, conclusions, camera-ready revisions, rebuttals, or paper revisions for major CS conferences and similar venues. It expects the text to refine and works better with surrounding context when available. Do not route non-academic writing or tasks that require generating new research content.

## Use When

- Use this skill when the user wants to improve, polish, proofread, or lightly edit academic or research writing for CS venues, including LaTeX sections, camera-ready revisions, rebuttals, or full-paper and section-by-section refinement.
- Use after a draft section or paper excerpt is available; it supports both full-paper refinement and section-by-section editing. Provide any available working context to improve consistency, and use its marginal notes and unresolved-issues output for follow-up review or downstream revision.

## Do Not Use When

- The section, venue, or stage may be ambiguous enough that the skill must ask for clarification rather than apply the wrong conventions.
- The skill can fail if it adds unsupported claims, results, or missing material instead of only refining existing text and flagging gaps.
- The skill can fail by altering citations, labels, equations, macros, formatting, or section structure that should remain unchanged in LaTeX inputs.
- The skill can fail if it introduces fancy vocabulary or excessive hedging instead of clear, concise academic prose.

## Inputs

- draft_academic_text: Academic or research writing text that the user wants refined.
- working_context_if_available: Any stated section, venue, or stage context that can guide section-specific conventions and tone.

## Outputs

- refined_academic_text: A polished version of the input text in the same format as the input (LaTeX if LaTeX, plain text otherwise).
- marginal_notes: Brief notes explaining substantive edits and why they were made.
- unresolved_issues_list: A separate list of issues the skill cannot fix, such as missing citations, unclear experimental details, or potential factual concerns.

## Tools And Dependencies

- references/section-guide.md: Reference guide for section-specific academic writing conventions.
- references/word-choice.md: Reference table for sentence-level substitutions, tightening, and transition choices.
- references/rebuttal-guide.md: Reference guide for rebuttal and reviewer-response writing.

## Composition Notes

- member_of: [[communities/0001-sciatlas-table-paper|Paper Evidence Synthesis]]

## Failure Modes

- context_ambiguity_requires_clarification
- content_invention_or_claim_fabrication
- latex_integrity_corruption
- overly_fancy_or_overhedged_prose

## Read Full Source

Open [full SKILL.md](../sources/academic-writing-refiner.md) when the card is insufficient to decide routing boundaries or execution requirements.
