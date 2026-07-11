---
type: Skill Card
title: data-analysis
description: Select this when the task centers on uploaded .xlsx/.xls or CSV files and needs structured data exploration, file-structure inventory, filtering, aggregation, joins, statistics, queryable tables, or exported analytical outputs. Requires an uploaded data file, a defined analysis goal, and an output format preference. Best fit for tabular data work; not a general-purpose analysis skill for non-file tasks.
skill_id: skill:data-analysis
selectable: True
source: ../sources/data-analysis.md
tags: [skill, file_structure_inventory, query_result_table, statistical_summary_report, exported_result_file, analyze_py_script, duckdb, present_files]
---

# Skill Card

Skill: data-analysis

## Purpose

Select this when the task centers on uploaded .xlsx/.xls or CSV files and needs structured data exploration, file-structure inventory, filtering, aggregation, joins, statistics, queryable tables, or exported analytical outputs. Requires an uploaded data file, a defined analysis goal, and an output format preference. Best fit for tabular data work; not a general-purpose analysis skill for non-file tasks.

## Use When

- Select when a task involves user-uploaded Excel/CSV files and needs schema inspection, SQL-based exploration, summaries, joins or aggregations, or exportable analytical results.
- No strong workflow guidance.

## Do Not Use When

- Cannot run if the required Excel/CSV uploads are not available.
- Queries can fail if the user references a table or sheet name incorrectly, especially after sanitization or quoting rules apply.
- Export may not be valid if the requested output file is not CSV, JSON, or Markdown.
- Analysis can fail when the SQL query is invalid or incompatible with the inspected schema.

## Inputs

- uploaded_data_files: Path(s) to uploaded Excel/CSV files under the uploads directory.
- analysis_goal: What insights the user wants from the data analysis.
- output_format_preference: How results should be presented or exported.

## Outputs

- file_structure_inventory: Inspection details such as sheet or file names, column names, data types, row counts, and sample rows.
- query_result_table: Formatted SQL query results presented in conversation.
- statistical_summary_report: Per-column statistical summaries for numeric and string fields.
- exported_result_file: A CSV, JSON, or Markdown file containing exported analysis results.

## Tools And Dependencies

- analyze_py_script: Single Python analyzer script used to inspect, query, summarize, and export uploaded files.
- duckdb: In-process analytical SQL engine used for file analysis and query execution.
- present_files: Tool used to share exported files when results are large.

## Composition Notes

- member_of: [[communities/0000-sciatlas-idea-data|Literature-grounded research idea lifecycle]]

## Failure Modes

- missing_uploaded_data_files
- table_or_sheet_name_mismatch
- unsupported_export_extension
- sql_execution_failure

## Read Full Source

Open [full SKILL.md](../sources/data-analysis.md) when the card is insufficient to decide routing boundaries or execution requirements.
