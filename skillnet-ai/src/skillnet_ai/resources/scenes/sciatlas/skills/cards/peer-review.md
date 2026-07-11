---
type: Skill Card
title: peer-review
description: Select this entity when the downstream task is to peer-review a manuscript, preprint, review/meta-analysis, methods paper, or grant proposal from a provided target_submission and return a structured_peer_review_report. Use it for critical assessment of methodology, study design, statistical soundness, reproducibility, ethics, figures, and reporting quality; it is not for drafting new content or general writing help.
skill_id: skill:peer-review
selectable: True
source: ../sources/peer-review.md
tags: [skill, structured_peer_review_report]
---

# Skill Card

Skill: peer-review

## Purpose

Select this entity when the downstream task is to peer-review a manuscript, preprint, review/meta-analysis, methods paper, or grant proposal from a provided target_submission and return a structured_peer_review_report. Use it for critical assessment of methodology, study design, statistical soundness, reproducibility, ethics, figures, and reporting quality; it is not for drafting new content or general writing help.

## Use When

- Use when a downstream agent must peer-review a scientific manuscript, preprint, review/meta-analysis, methods paper, or grant proposal and produce constructive, section-level critique covering rigor, statistics, reproducibility, ethics, figures, and reporting standards.
- Use after the target_submission is available; the expected output is a structured_peer_review_report with constructive section-level critique. Best used as an evaluation and validation step for scientific submissions, with attention to rigor, statistics, reproducibility, ethics, figures, and reporting standards.

## Do Not Use When

- The review is weakened when the submission lacks enough methodological, results, figure, or reporting detail to assess rigor and reproducibility.
- The work can be invalid if conclusions exceed the data, ignore contradictory evidence, or make causal/mechanistic claims without support.
- The review can miss major problems if statistical assumptions, correction, effect sizes, confidence intervals, or sample-size justification are absent or incorrect.
- The skill fails to fully assess research quality when data, code, materials, or reporting-guideline compliance are not available or are insufficient.
- The review must flag or may be compromised by missing ethics approvals, consent, conflicts of interest, plagiarism, fabrication, or falsification concerns.
- Visualization problems or image-manipulation signs can invalidate the assessment of results presentation and integrity.
- The review can fail if it becomes vague, overly harsh, or requests unnecessary work instead of specific, actionable, proportionate critique.

## Inputs

- target_submission: Scientific manuscript, grant proposal, or research application to be reviewed.

## Outputs

- structured_peer_review_report: Hierarchical review with an overall summary, major comments, minor comments, optional line-by-line comments, and questions for authors.

## Tools And Dependencies

- None

## Composition Notes

- compose_with: [[skills/cards/venue-templates]]
- depends_on: [[skills/cards/paper-compile]] confidence=0.94
- member_of: [[communities/0004-bib-verify-peer|Scholarly Integrity Verification]]
- [[skills/cards/paper-compile]] -> [[skills/cards/peer-review]] (artifact_compatibility: `target_submission_document`)

## Failure Modes

- incomplete_or_insufficient_submission
- unsupported_or_overstated_conclusions
- inadequate_statistical_rigor
- reproducibility_or_transparency_gap
- ethical_or_integrity_concern
- figure_or_data_presentation_integrity_issue
- non_constructive_or_unfocused_review

## Read Full Source

Open [full SKILL.md](../sources/peer-review.md) when the card is insufficient to decide routing boundaries or execution requirements.
