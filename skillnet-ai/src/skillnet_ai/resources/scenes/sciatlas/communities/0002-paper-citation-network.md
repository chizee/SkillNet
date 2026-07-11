---
type: Community
title: Academic Paper Source-to-Venue Prep
description: A community for paper-source preparation tasks centered on arXiv/source LaTeX ingestion, citation-graph construction, venue template fitting, format conversion, and submission compliance checks.
community_id: community:0002-paper-citation-network
tags: [community]
---

# Academic Paper Source-to-Venue Prep

## Capability Cluster Summary

A community for paper-source preparation tasks centered on arXiv/source LaTeX ingestion, citation-graph construction, venue template fitting, format conversion, and submission compliance checks.

## Representative Skills

- [[skills/cards/read-arxiv-paper]]
- [[skills/cards/latex-paper-conversion]]
- [[skills/cards/venue-templates]]
- [[skills/cards/citation-network]]

## Member Skills

- [[skills/cards/citation-network]]
- [[skills/cards/latex-paper-conversion]]
- [[skills/cards/read-arxiv-paper]]
- [[skills/cards/venue-templates]]

## Common Task Patterns

- arXiv URL -> read source tree + summary
- citation pairs CSV -> build citation network
- LaTeX paper -> port to target template
- submission draft -> venue template + compliance check

## Common Contract Terms

- requires: citation_pairs_csv, initialized_run_directory, matching_config_json, python_3_10_plus_runtime_with_dependencies, source_latex_file, target_template_directory, latex_build_toolchain, arxiv_paper_url
- produces: citation_network_gexf, network_metrics_json, citation_network_html, directed_citation_graph, converted_tex_file, cached_source_archive, unpacked_source_tree, summary_markdown
- uses_tools: pdflatex, bibtex, python_scripts_init_run_py, python_scripts_build_citation_network_py, pandas, networkx, pyvis, python

## Important Skill Relations

- None
