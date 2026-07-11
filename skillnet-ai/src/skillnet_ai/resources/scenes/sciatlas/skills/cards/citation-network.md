---
type: Skill Card
title: citation-network
description: Select this skill when the task has source/target citation pairs and the goal is literature review, trend detection, community discovery, bridge-paper identification, or exportable network visualization. It requires an initialized run directory, matching_config_json, and a Python 3.10+ runtime with dependencies. Best fit when the expected outputs are a directed citation graph, metrics JSON, GEXF, or HTML visualization rather than narrative synthesis.
skill_id: skill:citation-network
selectable: True
source: ../sources/citation-network.md
tags: [skill, citation_network_gexf, network_metrics_json, citation_network_html, directed_citation_graph, python_scripts_init_run_py, python_scripts_build_citation_network_py, pandas, networkx]
---

# Skill Card

Skill: citation-network

## Purpose

Select this skill when the task has source/target citation pairs and the goal is literature review, trend detection, community discovery, bridge-paper identification, or exportable network visualization. It requires an initialized run directory, matching_config_json, and a Python 3.10+ runtime with dependencies. Best fit when the expected outputs are a directed citation graph, metrics JSON, GEXF, or HTML visualization rather than narrative synthesis.

## Use When

- Use when you have citation-pair data and need to build a directed network to identify influential papers, clusters, bridging works, or exportable visualization files for review and analysis.
- Initialize the run directory and matching config before building the network, then use the generated metrics and HTML/GEXF outputs to inspect influence, clusters, and hotspots. This skill is best used as the graph-building/visualization step for citation analysis; downstream review or interpretation can use its exported artifacts. No strong workflow guidance.

## Do Not Use When

- CSV text may display incorrectly unless UTF-8/UTF-8-SIG or a configured input encoding is used.
- Records with the same identifier collapse to the same node, which can merge distinct papers if identifiers are not unique.
- If the CSV header names do not match configured `source`/`target` columns, the build can yield empty or missing output.

## Inputs

- citation_pairs_csv: A CSV containing at minimum `source` and `target` columns representing who cites whom.
- initialized_run_directory: A per-run workspace under `outputs/runs/<timestamp>/` created before execution.
- matching_config_json: A `config.json` in the run directory with input filename and column names aligned to the CSV, including optional input encoding if needed.
- python_3_10_plus_runtime_with_dependencies: A Python 3.10+ environment with `pandas` and `networkx`, and optionally `pyvis` for HTML visualization.

## Outputs

- citation_network_gexf: A Gephi-importable directed graph file for the citation network.
- network_metrics_json: A JSON file containing basic network statistics such as node and edge counts and density.
- citation_network_html: An interactive browser-viewable HTML visualization of the citation network.
- directed_citation_graph: A directed citation network data structure derived from the source-target pairs.

## Tools And Dependencies

- python_scripts_init_run_py: Initializes a new run directory for an isolated execution.
- python_scripts_build_citation_network_py: Builds the citation network and triggers HTML generation.
- pandas: Python data-processing dependency used by the pipeline.
- networkx: Python graph library used by the pipeline.
- pyvis: Optional library for HTML visualization.

## Composition Notes

- depends_on: [[skills/cards/networkx]] confidence=0.99
- member_of: [[communities/0002-paper-citation-network|Academic Paper Source-to-Venue Prep]]

## Failure Modes

- garbled_characters_from_input_encoding
- duplicate_nodes_from_identifier_collisions
- empty_or_missing_outputs_due_to_column_mismatch

## Read Full Source

Open [full SKILL.md](../sources/citation-network.md) when the card is insufficient to decide routing boundaries or execution requirements.
