---
type: Skill Card
title: venue-templates
description: Select this skill when the task involves a known target venue or funding agency and needs template retrieval, author/project customization, or compliance checking for manuscripts, conference papers, posters, or grant submissions. Best fit inputs are a submission draft plus venue/agency metadata and local template resources; expected outputs are a venue requirements profile, customized LaTeX template, and format validation report. Do not route here for general writing, content editing without venue constraints, or tasks lacking a target venue or submission format.
skill_id: skill:venue-templates
selectable: True
source: ../sources/venue-templates.md
tags: [skill, venue_requirements_profile, customized_latex_template, format_validation_report, read, write, edit, bash]
---

# Skill Card

Skill: venue-templates

## Purpose

Select this skill when the task involves a known target venue or funding agency and needs template retrieval, author/project customization, or compliance checking for manuscripts, conference papers, posters, or grant submissions. Best fit inputs are a submission draft plus venue/agency metadata and local template resources; expected outputs are a venue requirements profile, customized LaTeX template, and format validation report. Do not route here for general writing, content editing without venue constraints, or tasks lacking a target venue or submission format.

## Use When

- Use when a task must identify a target journal, conference, poster format, or funding agency, retrieve the matching template and requirements, customize author/project details, or verify submission compliance.
- Typical flow is: identify the target venue or agency, load the matching template and requirements, customize author/project details, then validate the draft against submission rules and regenerate as needed. Use validation after customization to catch formatting and compliance issues before handoff. This skill supports template-driven preparation and compliance checking, not substantive research or argument development.

## Do Not Use When

- Template or requirements may be stale if venue rules have changed, so official sources should be checked.
- The selected template may fail to compile because of formatting or package issues.
- A needed venue template may be absent or the specification may be wrong, preventing correct retrieval or setup.
- The document can miss page limits, fonts, margins, citation style, figure resolution, or anonymization requirements and fail validation or submission.

## Inputs

- target_venue_or_agency: A specific publication venue, conference, poster format, or funding agency must be identified to select the correct template and requirements.
- source_document_or_submission_draft: A manuscript, poster draft, or proposal draft must exist to be customized and checked against venue specifications.
- author_project_metadata: Title, authors, affiliations, email, or project details are needed for template customization.
- local_template_and_requirements_resources: The repository resources for references, assets, and helper scripts must be available to query, retrieve, customize, and validate templates.

## Outputs

- venue_requirements_profile: Venue-specific formatting requirements such as page limits, font, margins, citation style, figure rules, and anonymization constraints.
- customized_latex_template: A venue-tailored LaTeX template populated with title, authors, affiliations, and project details.
- format_validation_report: A compliance check result or report showing whether the document meets venue requirements.

## Tools And Dependencies

- Read: Read repository resources and requirement files.
- Write: Write customized template files or reports.
- Edit: Edit template files manually when not using helper scripts.
- Bash: Run helper scripts and compilation/validation commands from the repository.
- query_template.py: Search and retrieve templates by venue name, type, or keywords.
- customize_template.py: Customize templates with author and project information.
- validate_format.py: Check document compliance with venue requirements and generate validation output.
- pdflatex: Compile LaTeX sources into a document for review.
- bibtex: Process bibliography during LaTeX compilation.
- latexmk: Automate LaTeX compilation into PDF.

## Composition Notes

- compose_with: [[skills/cards/peer-review]]
- compose_with: [[skills/cards/sciatlas-literature-review]]
- compose_with: [[skills/cards/pdf]]
- member_of: [[communities/0002-paper-citation-network|Academic Paper Source-to-Venue Prep]]

## Failure Modes

- outdated_or_incorrect_guidelines
- template_compilation_error
- missing_template_or_incorrect_specification
- venue_compliance_failure

## Read Full Source

Open [full SKILL.md](../sources/venue-templates.md) when the card is insufficient to decide routing boundaries or execution requirements.
