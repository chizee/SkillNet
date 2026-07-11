---
type: Skill Card
title: latex-paper-conversion
description: Select this skill when the task is to port an existing LaTeX paper between publication formats such as Springer, IPOL, MDPI, IEEE, or Nature, especially when the work involves source LaTeX input, a target template directory, and build/compile debugging. Route only if the available artifacts include a source_latex_file and target_template_directory and the environment can provide a latex_build_toolchain. It produces a converted_tex_file and uses LaTeX-oriented tooling for extraction, regex-based edits, bibliography handling, and compilation checks. Do not select it for general writing, non-LaTeX document conversion, or tasks that do not require template-driven paper reformatting.
skill_id: skill:latex-paper-conversion
selectable: True
source: ../sources/latex-paper-conversion.md
tags: [skill, converted_tex_file, python, regular_expressions, pdflatex, bibtex]
---

# Skill Card

Skill: latex-paper-conversion

## Purpose

Select this skill when the task is to port an existing LaTeX paper between publication formats such as Springer, IPOL, MDPI, IEEE, or Nature, especially when the work involves source LaTeX input, a target template directory, and build/compile debugging. Route only if the available artifacts include a source_latex_file and target_template_directory and the environment can provide a latex_build_toolchain. It produces a converted_tex_file and uses LaTeX-oriented tooling for extraction, regex-based edits, bibliography handling, and compilation checks. Do not select it for general writing, non-LaTeX document conversion, or tasks that do not require template-driven paper reformatting.

## Use When

- Use when an existing LaTeX academic paper must be ported to a different journal or publisher format and the task includes automated extraction, template injection, formatting fixes, and compilation debugging.
- Use the source LaTeX and target template together, then perform extraction and template injection before formatting fixes and compilation debugging. Validate by building the paper with the LaTeX toolchain and iterating on errors until the converted_tex_file is produced. No strong workflow guidance.

## Do Not Use When

- conversion can stall when source and target layouts differ too much to map automatically
- the converted template may fail to compile because required packages or commands are absent in the target template
- tables and float placements may break when moving between single-column and double-column layouts
- graphics may fail to resolve after the file is moved into a new template directory

## Inputs

- source_latex_file: the existing .tex paper to be converted
- target_template_directory: the destination journal or publisher template directory
- latex_build_toolchain: a local LaTeX build environment capable of running the document build cycle

## Outputs

- converted_tex_file: a new LaTeX file assembled in the target template structure

## Tools And Dependencies

- python: used to create the conversion script that parses and rewrites the LaTeX source
- regular_expressions: used to extract core text blocks from the source LaTeX file
- pdflatex: used in the build cycle to compile the converted document
- bibtex: used in the build cycle to resolve bibliography compilation
- grep: used to inspect the build log for compilation errors and package issues
- rg: used to inspect the build log for compilation errors and package issues

## Composition Notes

- member_of: [[communities/0002-paper-citation-network|Academic Paper Source-to-Venue Prep]]

## Failure Modes

- template_structure_mismatch
- missing_latex_packages_or_undefined_commands
- table_or_float_layout_breakage
- broken_image_path_resolution

## Read Full Source

Open [full SKILL.md](../sources/latex-paper-conversion.md) when the card is insufficient to decide routing boundaries or execution requirements.
