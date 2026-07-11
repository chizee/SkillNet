---
type: Skill Card
title: glmocr-table
description: Select this skill when the task is to recognize or extract tabular content from an image, scanned document, spreadsheet capture, or PDF and return structured editable table output. It requires a source file or URL, a ZhiPu API key, and a Python runtime. Best fit when the target output is extracted_table_markdown with optional layout_analysis_details; do not use it for non-tabular OCR or general document summarization.
skill_id: skill:glmocr-table
selectable: True
source: ../sources/glmocr-table.md
tags: [skill, extracted_table_markdown, layout_analysis_details, python_scripts_glm_ocr_cli_py, glm_ocr_layout_parsing_api]
---

# Skill Card

Skill: glmocr-table

## Purpose

Select this skill when the task is to recognize or extract tabular content from an image, scanned document, spreadsheet capture, or PDF and return structured editable table output. It requires a source file or URL, a ZhiPu API key, and a Python runtime. Best fit when the target output is extracted_table_markdown with optional layout_analysis_details; do not use it for non-tabular OCR or general document summarization.

## Use When

- Use when the task is to extract or recognize tables from an image, scanned document, or PDF and return them in editable Markdown or similar structured form, especially for complex tables, merged cells, or multi-page documents.
- Use the source file or URL and credentials first, then run table OCR/layout parsing to produce Markdown plus layout details. Treat merged cells and multi-page tables as supported cases and validate the extracted structure against the source layout before handoff. Downstream agents should consume the generated Markdown and layout analysis rather than re-deriving table structure from raw images.

## Do Not Use When

- Extraction cannot start when ZHIPU_API_KEY is not configured.
- Invalid or expired credentials can produce 401/403 authentication errors.
- Quota exhaustion can return 429 and require waiting before retrying.
- A missing local file path prevents table extraction.
- If the API fails, the skill stops rather than attempting any manual or alternative table parsing.

## Inputs

- zhipu_api_key: A configured ZhiPu API key for accessing the GLM-OCR API.
- python_runtime: A Python interpreter available to run the CLI script.
- table_source_file_or_url: A local image/PDF path or a remote URL pointing to the table source.

## Outputs

- extracted_table_markdown: Markdown text for the extracted table content.
- layout_analysis_details: Layout parsing details about detected table structure and related elements.

## Tools And Dependencies

- python_scripts_glm_ocr_cli_py: CLI script invoked to run the GLM-OCR table extraction workflow.
- glm_ocr_layout_parsing_api: Fixed ZhiPu layout parsing API endpoint used for table recognition.

## Composition Notes

- member_of: [[communities/0001-sciatlas-table-paper|Paper Evidence Synthesis]]

## Failure Modes

- api_key_missing
- authentication_failed
- rate_limited
- local_source_missing
- no_non_api_fallback

## Read Full Source

Open [full SKILL.md](../sources/glmocr-table.md) when the card is insufficient to decide routing boundaries or execution requirements.
