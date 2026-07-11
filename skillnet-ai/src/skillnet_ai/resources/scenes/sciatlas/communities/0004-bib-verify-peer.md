---
type: Community
title: Scholarly Integrity Verification
description: Community for validating scholarly submissions and citation artifacts, including BibTeX/reference checks against external indexes, retraction/correction screening, and structured manuscript or grant peer review.
community_id: community:0004-bib-verify-peer
tags: [community]
---

# Scholarly Integrity Verification

## Capability Cluster Summary

Community for validating scholarly submissions and citation artifacts, including BibTeX/reference checks against external indexes, retraction/correction screening, and structured manuscript or grant peer review.

## Representative Skills

- [[skills/cards/bib-verify]]
- [[skills/cards/retraction-watcher]]
- [[skills/cards/peer-review]]

## Member Skills

- [[skills/cards/bib-verify]]
- [[skills/cards/peer-review]]
- [[skills/cards/retraction-watcher]]

## Common Task Patterns

- audit .bib or reference list for fabricated citations
- screen references for retractions/corrections/expressions of concern
- peer-review manuscript, preprint, or grant for rigor and reporting quality
- verify citation integrity before submission or reuse

## Common Contract Terms

- requires: bibtex_file_path, openjudge_runtime_dependencies, target_submission, citation_input, internet_access, python_runtime_3_10_plus, installed_python_dependencies
- produces: bib_verification_report_md, per_entry_verification_statuses, structured_peer_review_report, retraction_watch_report, citation_verification_result_set
- uses_tools: openjudge_paperreviewpipeline_bibtex_only, crossref, arxiv, dblp, scripts/main.py, python -m py_compile scripts/main.py, python scripts/main.py --help, Retraction Watch Database

## Important Skill Relations

- None
