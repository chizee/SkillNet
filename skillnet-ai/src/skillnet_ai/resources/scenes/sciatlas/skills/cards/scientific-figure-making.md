---
type: Skill Card
title: scientific-figure-making
description: Select this skill when the task is to produce bar, trend, scatter, heatmap, or multi-panel figures for papers, slides, or reports that must match repository aesthetics and export cleanly to print/vector formats. It expects a matplotlib/numpy environment plus the data and labels needed to plot. Do not route interactive dashboards, quick exploratory EDA, complex 3D/GIS visualization, or heavy infographic design to this skill.
skill_id: skill:scientific-figure-making
selectable: True
source: ../sources/scientific-figure-making.md
tags: [skill, publication_ready_figure, exported_figure_files, matplotlib, numpy, high_level_plot_helpers, finalize_export_helper]
---

# Skill Card

Skill: scientific-figure-making

## Purpose

Select this skill when the task is to produce bar, trend, scatter, heatmap, or multi-panel figures for papers, slides, or reports that must match repository aesthetics and export cleanly to print/vector formats. It expects a matplotlib/numpy environment plus the data and labels needed to plot. Do not route interactive dashboards, quick exploratory EDA, complex 3D/GIS visualization, or heavy infographic design to this skill.

## Use When

- Use when you need publication-ready bar, trend, scatter, heatmap, or multi-panel figures in a consistent house style with print/vector-safe export; avoid it for interactive dashboards, quick exploratory EDA, complex 3D/GIS visualization, or heavy infographic design.
- Prepare the plotting data and labels first, then use this skill to render the figure in the required house style and finish with export for publication-ready outputs. Validate that the chosen chart type fits the source data and that the output format is suitable for vector or print use. It produces a publication-ready figure and exported figure files.

## Do Not Use When

- TeX/usetex can fail if LaTeX is unavailable; the default mitigation is to keep TeX disabled.
- Fonts may render inconsistently on another machine if the fallback chain is not used.
- Legends can overlap plotted data when not placed in a dedicated legend panel.
- Bar charts can become crowded or too small without a wider figure or fewer categories per row.
- Plotting fails when category counts or trend lengths do not match the supplied data dimensions.

## Inputs

- matplotlib_numpy_environment: A Python environment with matplotlib and numpy available at the required versions.
- plotting_data_and_labels: Plottable categories, series, axes data, and labels for the target figure layout.

## Outputs

- publication_ready_figure: A scientifically styled matplotlib figure with global typography, minimal spines, and consistent house defaults applied.
- exported_figure_files: Figure exports saved in print- and vector-safe formats such as PNG, PDF, or SVG with tight bounding box and optional padding.

## Tools And Dependencies

- matplotlib: Python plotting library used to create and style the figures.
- numpy: Numerical array library required by the figure-making workflow.
- high_level_plot_helpers: House-style helpers for grouped bars, trend lines, heatmaps, scatter plots, and related figure types.
- finalize_export_helper: Shared export helper used to produce consistent, reproducible figure output.

## Composition Notes

- member_of: [[communities/0003-citation-verifier-docx|Scholarly Manuscript Artifact Handling]]

## Failure Modes

- latex_rendering_failure
- font_fallback_mismatch
- legend_overlap
- crowded_or_too_small_bars
- shape_length_mismatch

## Read Full Source

Open [full SKILL.md](../sources/scientific-figure-making.md) when the card is insufficient to decide routing boundaries or execution requirements.
