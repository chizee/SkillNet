---
type: Skill Card
title: pptx-posters
description: Select only for explicit PowerPoint/PPTX poster requests or HTML posters intended for PowerPoint editing; requires an HTML poster template asset and is not the default for standard research posters or LaTeX poster requests, which should route to latex-posters.
skill_id: skill:pptx-posters
selectable: True
source: ../sources/pptx-posters.md
tags: [skill, poster_figure_assets, poster_html, poster_pdf, poster_pptx, bash_shell, scientific_schematics, nano_banana_pro, browser_print_function]
---

# Skill Card

Skill: pptx-posters

## Purpose

Select only for explicit PowerPoint/PPTX poster requests or HTML posters intended for PowerPoint editing; requires an HTML poster template asset and is not the default for standard research posters or LaTeX poster requests, which should route to latex-posters.

## Use When

- Select only when the user explicitly requests a PPTX/PowerPoint poster or an HTML-based poster meant for PowerPoint editing; route ordinary research posters and LaTeX poster requests to latex-posters instead.
- Use the HTML poster template asset to build poster_html and figure assets first, then export to poster_pdf or poster_pptx via browser print, LibreOffice headless conversion, or python_pptx when an editable PPTX is needed.

## Do Not Use When

- This skill should not be selected for ordinary research posters or LaTeX-based poster requests; those should route to latex-posters.
- Graphics can fail when they contain too many elements, too many steps, too much text, or insufficient white space, producing unreadable poster visuals.
- Export can fail quality checks if content is cut off, images do not display, colors render incorrectly, paper size is wrong, or resolution is too low.

## Inputs

- explicit_pptx_or_powerpoint_poster_request: The task must explicitly ask for PPTX/PowerPoint poster format.
- poster_html_template_asset: The HTML poster template asset must be available for copying and customization.

## Outputs

- poster_figure_assets: AI-generated poster visuals such as hero, methods, results, and conclusions images in the figures/ directory.
- poster_html: A customized HTML poster file assembled from the template with inserted images, text, and references.
- poster_pdf: A PDF export of the poster generated from the HTML poster in a browser or headless Chrome.
- poster_pptx: A PowerPoint version of the poster, either converted from PDF or created directly with python-pptx.

## Tools And Dependencies

- bash_shell: Shell execution for creating directories, running generators, copying templates, previewing files, and exporting artifacts.
- scientific_schematics: Used to generate poster diagrams and flowcharts.
- nano_banana_pro: Used to create stylized graphics and hero images.
- browser_print_function: Browser print workflow used to save the poster HTML as PDF.
- chrome_or_firefox_browser: Browser used to open poster.html for preview and print/export.
- libreoffice_headless_conversion: Headless LibreOffice conversion from PDF to PPTX.
- python_pptx: Python PPTX library used for direct PowerPoint slide generation.

## Composition Notes

- member_of: [[communities/0000-sciatlas-idea-data|Literature-grounded research idea lifecycle]]

## Failure Modes

- wrong_poster_format_route
- overcrowded_or_unreadable_graphics
- export_or_layout_defect

## Read Full Source

Open [full SKILL.md](../sources/pptx-posters.md) when the card is insufficient to decide routing boundaries or execution requirements.
