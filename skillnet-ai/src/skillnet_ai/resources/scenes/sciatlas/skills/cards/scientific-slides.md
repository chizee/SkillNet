---
type: Skill Card
title: scientific-slides
description: Select this skill when the task is to prepare or refine a scientific talk deck, such as for a conference, seminar, thesis defense, grant talk, or journal club. It fits when the inputs include talk context, source material, figures, and citation sources, and the desired outputs are a presentation plan, slide visuals, PowerPoint/Beamer-style slides, or a presentation PDF. It is not a general writing or document-layout skill; it is specifically for slide-based research presentations and depends on the OpenRouter API key plus supporting source artifacts.
skill_id: skill:scientific-slides
selectable: True
source: ../sources/scientific-slides.md
tags: [skill, presentation_plan, slide_image_set, presentation_pdf, visual_validation_artifacts, read, write, edit, bash]
---

# Skill Card

Skill: scientific-slides

## Purpose

Select this skill when the task is to prepare or refine a scientific talk deck, such as for a conference, seminar, thesis defense, grant talk, or journal club. It fits when the inputs include talk context, source material, figures, and citation sources, and the desired outputs are a presentation plan, slide visuals, PowerPoint/Beamer-style slides, or a presentation PDF. It is not a general writing or document-layout skill; it is specifically for slide-based research presentations and depends on the OpenRouter API key plus supporting source artifacts.

## Use When

- Use when a downstream agent needs to prepare or refine a conference, seminar, defense, grant, journal club, or other scientific talk with slide planning, AI-generated slide visuals, citations, PDF assembly, and readability checks.
- Best used after the talk context, source materials, figures, and citations are assembled. The typical flow is to create a presentation plan, generate or refine slide visuals, assemble the deck into PDF or presentation form, and then run visual/readability validation before handoff. Use it when downstream execution needs both composition and verification artifacts.

## Do Not Use When

- Slides become dry or forgettable when they rely on walls of text, lack graphics, or use generic defaults instead of strong visuals.
- The presentation loses scientific credibility if citations, background literature, or comparison studies are missing.
- Slides can become invalid if text overflows, elements overlap, or layouts are cluttered/misaligned.
- Slides fail when fonts are too small or contrast is insufficient for audience readability.
- Presentation delivery can fail if pacing is too slow, time checkpoints are missed, or conclusions get skipped.

## Inputs

- talk_context: Presentation type, duration, audience, venue, and post-talk context needed to shape structure and pacing.
- source_material_and_figures: Research content, existing figures, diagrams, logos, or user-provided files that will be incorporated into slides.
- citation_sources: Relevant papers or citation list to establish scientific context and support claims on slides.
- openrouter_api_key: OpenRouter API key or OPENROUTER_API_KEY environment variable required for Nano Banana Pro generation.

## Outputs

- presentation_plan: A slide-by-slide plan with titles, key points, and visual elements.
- slide_image_set: Per-slide PNG images or visual assets generated for the presentation.
- presentation_pdf: A combined PDF presentation assembled from generated slide images.
- visual_validation_artifacts: Rendered slide-review images or thumbnails plus issue notes used for visual inspection and iteration.

## Tools And Dependencies

- Read: File reading access for the skill's local documentation and assets.
- Write: Writes generated slide files, PDFs, and review artifacts to the workspace.
- Edit: Edits existing presentation sources or generated assets during iteration.
- Bash: Runs local scripts and shell commands for generation, conversion, and validation.
- generate_slide_image.py: AI slide/visual generation script used for full slides or visual-only assets.
- slides_to_pdf.py: Combines slide images into a single PDF presentation.
- validate_presentation.py: Validates slide count, timing, file size, dimensions, and compilation success.
- pdf_to_images.py: Converts a presentation PDF into images for visual inspection.
- thumbnail.py: Creates thumbnail grids for PPTX visual review.

## Composition Notes

- member_of: [[communities/0000-sciatlas-idea-data|Literature-grounded research idea lifecycle]]

## Failure Modes

- text_heavy_or_visual_poor_slides
- missing_research_context
- layout_overflow_or_overlap
- low_readability_or_contrast
- timing_overrun_or_skipped_conclusion

## Read Full Source

Open [full SKILL.md](../sources/scientific-slides.md) when the card is insufficient to decide routing boundaries or execution requirements.
