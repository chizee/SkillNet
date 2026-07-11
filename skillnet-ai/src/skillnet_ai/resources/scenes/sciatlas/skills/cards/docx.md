---
type: Skill Card
title: docx
description: Select when the task targets Word documents or asks for a professional deliverable as .docx, especially for .docx creation/editing, formatting, find-and-replace, image insertion, tracked changes/comments, or reorganizing content from an existing Word file. Do not route for PDFs, spreadsheets, Google Docs, or non-document coding tasks.
skill_id: skill:docx
selectable: True
source: ../sources/docx.md
tags: [skill, docx, markdown, python]
---

# Skill Card

Skill: docx

## Purpose

Select when the task targets Word documents or asks for a professional deliverable as .docx, especially for .docx creation/editing, formatting, find-and-replace, image insertion, tracked changes/comments, or reorganizing content from an existing Word file. Do not route for PDFs, spreadsheets, Google Docs, or non-document coding tasks.

## Use When

- Use this skill whenever the user wants to create, read, edit, or manipulate Word documents (.docx files). Triggers include: any mention of "Word doc", "word document", ".docx", or requests to produce professional documents with formatting like tables of contents, headings, page numbers, or letterheads. Also use when extracting or reorganizing content from .docx files, inserting or replacing images in documents, performing find-and-replace in Word files, working with tracked changes or comments, or converting content into a polished Word document. If the user asks for a "report", "memo", "letter", "template", or similar deliverable as a Word or .docx file, use this skill. Do NOT use for PDFs, spreadsheets, Google Docs, or general coding tasks unrelated to document generation.
- Use as the document-format handling step when source content must be turned into or modified within a Word deliverable, with support for preserving editing features such as tracked changes and comments. No strong workflow guidance.

## Do Not Use When

- When the task requires unrelated inputs, outputs, tools, or execution responsibilities.

## Inputs

- docx
- pdf

## Outputs

- docx
- markdown

## Tools And Dependencies

- python

## Composition Notes

- member_of: [[communities/0003-citation-verifier-docx|Scholarly Manuscript Artifact Handling]]

## Failure Modes

- None

## Read Full Source

Open [full SKILL.md](../sources/docx.md) when the card is insufficient to decide routing boundaries or execution requirements.
