---
type: Community
title: Paper Evidence Synthesis
description: Community for paper-evidence work that searches scholarly sources, extracts tables or layouts from paper artifacts, synthesizes literature into manuscript-ready text, and compiles LaTeX outputs.
community_id: community:0001-sciatlas-table-paper
tags: [community]
---

# Paper Evidence Synthesis

## Capability Cluster Summary

Community for paper-evidence work that searches scholarly sources, extracts tables or layouts from paper artifacts, synthesizes literature into manuscript-ready text, and compiles LaTeX outputs.

## Representative Skills

- [[skills/cards/sciatlas-quick-paper-search]]
- [[skills/cards/sciatlas-literature-review]]
- [[skills/cards/sciatlas-trend-report]]
- [[skills/cards/glmocr-table]]
- [[skills/cards/paper-compile]]

## Member Skills

- [[skills/cards/academic-writing-refiner]]
- [[skills/cards/glmocr-table]]
- [[skills/cards/paper-compile]]
- [[skills/cards/sciatlas-literature-review]]
- [[skills/cards/sciatlas-quick-paper-search]]
- [[skills/cards/sciatlas-trend-report]]
- [[skills/cards/table-extractor]]

## Common Task Patterns

- quick paper check or retrieval smoke test
- literature review / related-work synthesis from search-papers
- trend or timeline report from paper evidence
- extract tables from PDFs or images into Markdown or structured data
- compile LaTeX paper PDF or fix build errors
- refine manuscript sections or camera-ready prose

## Common Contract Terms

- requires: draft_academic_text, working_context_if_available, zhipu_api_key, python_runtime, table_source_file_or_url, latex_compilation_toolchain, paper_source_tree, topic_scope_or_clarification
- produces: refined_academic_text, marginal_notes, unresolved_issues_list, extracted_table_markdown, layout_analysis_details, submission_ready_pdf, compile_log, compilation_report
- uses_tools: sciatlas_search_papers, references/section-guide.md, references/word-choice.md, references/rebuttal-guide.md, python_scripts_glm_ocr_cli_py, glm_ocr_layout_parsing_api, latexmk, pdflatex

## Important Skill Relations

- compose_with: [[skills/cards/sciatlas-literature-review]] -> [[skills/cards/sciatlas-trend-report]]
- compose_with: [[skills/cards/sciatlas-quick-paper-search]] -> [[skills/cards/sciatlas-trend-report]]
