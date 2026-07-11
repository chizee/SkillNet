---
type: Skill Card
title: table-extractor
description: Select this skill when the input is a PDF document and the task requires table extraction, page or region selection for tables, handling merged or borderless tables, combining tables across pages, or exporting extracted tables into structured outputs such as dataframes or files. It is PDF-specific and depends on PDF extraction runtime support plus Office MCP access; it is not a general document understanding or OCR skill.
skill_id: skill:table-extractor
selectable: True
source: ../sources/table-extractor.md
tags: [skill, extracted_table_dataframes, table_export_files, table_parsing_report, extract_tables_from_pdf, camelot.read_pdf, camelot.plot, pandas]
---

# Skill Card

Skill: table-extractor

## Purpose

Select this skill when the input is a PDF document and the task requires table extraction, page or region selection for tables, handling merged or borderless tables, combining tables across pages, or exporting extracted tables into structured outputs such as dataframes or files. It is PDF-specific and depends on PDF extraction runtime support plus Office MCP access; it is not a general document understanding or OCR skill.

## Use When

- Use when a request needs table extraction from a PDF—especially for choosing pages or table areas, handling borderless or merged-cell tables, combining multi-page tables, or exporting extracted tables to structured formats.
- No strong workflow guidance.

## Do Not Use When

- Encrypted PDFs are not supported.
- Image-based PDFs need OCR preprocessing before table extraction.
- Very complex merged cells may require parameter tuning for accurate extraction.
- Rotated tables require preprocessing before extraction.
- Large PDFs may need page-by-page processing instead of one-pass extraction.

## Inputs

- pdf_document: A PDF containing tables to extract.
- camelot_pdf_extraction_runtime: Camelot PDF-extraction support must be available, including its installation dependencies.
- office_mcp_server: The office-mcp server providing the table extraction tool must be available.

## Outputs

- extracted_table_dataframes: One or more pandas DataFrames containing extracted table contents.
- table_export_files: Exported table files such as CSV, Excel, JSON, or HTML artifacts.
- table_parsing_report: Per-table quality and metadata such as accuracy, whitespace, order, shape, and parsing report.

## Tools And Dependencies

- extract_tables_from_pdf: MCP tool for extracting tables from PDFs.
- camelot.read_pdf: Primary PDF table extraction API used for bordered and borderless tables and page selection.
- camelot.plot: Visual debugging and inspection of detected table areas, text, and lines.
- pandas: Used to hold, combine, and compare extracted table data.

## Composition Notes

- member_of: [[communities/0001-sciatlas-table-paper|Paper Evidence Synthesis]]

## Failure Modes

- encrypted_pdf_unsupported
- image_based_pdf_requires_ocr
- complex_merged_cells_need_tuning
- rotated_tables_require_preprocessing
- large_pdfs_need_page_by_page_processing

## Read Full Source

Open [full SKILL.md](../sources/table-extractor.md) when the card is insufficient to decide routing boundaries or execution requirements.
