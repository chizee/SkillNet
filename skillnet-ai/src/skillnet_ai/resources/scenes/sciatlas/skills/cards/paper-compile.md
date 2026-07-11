---
type: Skill Card
title: paper-compile
description: Select this skill when the task is to build, fix, or validate a LaTeX paper PDF, especially for requests like compile paper, build PDF, 生成PDF, or when investigating compilation failures. It expects a LaTeX source tree and a LaTeX compilation toolchain, and it produces a submission_ready_pdf plus compile_log and compilation_report. Do not route it for general document editing, non-LaTeX PDFs, or tasks that do not involve paper compilation or compile verification.
skill_id: skill:paper-compile
selectable: True
source: ../sources/paper-compile.md
tags: [skill, submission_ready_pdf, compile_log, compilation_report, latexmk, pdflatex, bibtex, pdfinfo]
---

# Skill Card

Skill: paper-compile

## Purpose

Select this skill when the task is to build, fix, or validate a LaTeX paper PDF, especially for requests like compile paper, build PDF, 生成PDF, or when investigating compilation failures. It expects a LaTeX source tree and a LaTeX compilation toolchain, and it produces a submission_ready_pdf plus compile_log and compilation_report. Do not route it for general document editing, non-LaTeX PDFs, or tasks that do not involve paper compilation or compile verification.

## Use When

- Use this skill when a task asks to build or repair a LaTeX paper PDF, investigate compile failures, or confirm that a paper is submission-ready under venue constraints.
- Use the source tree and toolchain to compile first, then inspect the compile log for errors and warnings, repair issues, and rerun until the PDF is produced cleanly. Validate the output with PDF inspection tools such as pdfinfo, pdftotext, and pdffonts when confirming submission readiness or diagnosing build problems. The primary handoff artifact for downstream use is the compiled PDF with supporting logs and a compilation report.

## Do Not Use When

- Compilation cannot proceed because the required LaTeX toolchain is not installed or not discoverable.
- Expected source files, bibliography, section files, or figures are absent from `paper/`.
- The build fails and `compile.log` contains errors that require diagnosis and fixes.
- A LaTeX package referenced by `\usepackage` is not installed.
- References or citations remain undefined after compilation.
- Figure assets are missing or referenced with the wrong extension/path.
- BibTeX syntax problems prevent bibliography generation.
- The paper's main body exceeds the venue page limit measured to the end of the Conclusion section.
- The final PDF is not suitable for submission because fonts are not embedded, appendix/supplementary material is mixed into the main text, file size is too large, or `[VERIFY]` markers remain.
- Section files exist in `paper/sections/` but are no longer referenced by `main.tex`, which can cause stale-content confusion.

## Inputs

- latex_compilation_toolchain: LaTeX build tools must be available, including the compiler, build wrapper, and bibliography toolchain.
- paper_source_tree: The paper source directory and its expected main inputs should exist, especially `paper/main.tex` and supporting bibliography/section/figure assets.

## Outputs

- submission_ready_pdf: A compiled `main.pdf` paper output that has been checked after successful build.
- compile_log: A retained build log capturing compilation output and errors for diagnosis.
- compilation_report: A summary of build status, page count, fixes, and remaining warnings/checks.

## Tools And Dependencies

- latexmk: Build wrapper used for cleaning and full multi-pass PDF compilation.
- pdflatex: LaTeX engine used by the build process and checked as an installed prerequisite.
- bibtex: Bibliography tool checked as part of the compilation environment and used in the build chain.
- pdfinfo: Used to inspect the compiled PDF page count.
- pdftotext: Used to extract PDF text for page-boundary and section-limit verification.
- python3: Used with `pdftotext` output to locate conclusion and references page boundaries.
- grep: Used to detect undefined references, missing citations, and font-embedding issues via log/PDF checks.
- pdffonts: Used to verify that fonts are embedded in the final PDF.
- tlmgr: Used as a package-install remediation path for missing LaTeX packages.

## Composition Notes

- required_by: [[skills/cards/peer-review]] confidence=0.94
- member_of: [[communities/0001-sciatlas-table-paper|Paper Evidence Synthesis]]
- [[skills/cards/paper-compile]] -> [[skills/cards/peer-review]] (artifact_compatibility: `target_submission_document`)

## Failure Modes

- latex_toolchain_missing
- missing_source_or_assets
- compile_errors_in_log
- missing_package_dependency
- unresolved_references_or_citations
- missing_figures
- bibtex_or_bibliography_syntax_error
- page_limit_exceeded
- non_submission_ready_pdf
- orphaned_section_files

## Read Full Source

Open [full SKILL.md](../sources/paper-compile.md) when the card is insufficient to decide routing boundaries or execution requirements.
