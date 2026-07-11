---
type: Skill Card
title: networkx
description: Select this skill when the task involves graph or network data structures, pairwise relationships, graph algorithms, community detection, graph serialization, or network visualizations. Trigger especially on requests to build a graph from data, compute shortest paths or centrality, analyze connectivity/clustering, or produce graph artifacts. Requires an available NetworkX installation and source graph data; best fit when the input can be represented as a graph and the desired output is a graph object, analysis result, partition, serialized file, or visualization.
skill_id: skill:networkx
selectable: True
source: ../sources/networkx.md
tags: [skill, graph_object, graph_analysis_results, community_partition, serialized_graph_file, networkx, matplotlib_pyplot, pandas, numpy]
---

# Skill Card

Skill: networkx

## Purpose

Select this skill when the task involves graph or network data structures, pairwise relationships, graph algorithms, community detection, graph serialization, or network visualizations. Trigger especially on requests to build a graph from data, compute shortest paths or centrality, analyze connectivity/clustering, or produce graph artifacts. Requires an available NetworkX installation and source graph data; best fit when the input can be represented as a graph and the desired output is a graph object, analysis result, partition, serialized file, or visualization.

## Use When

- Select this skill for tasks that build graphs from data, compute paths/centrality/community/connectivity metrics, generate synthetic networks, read/write graph formats, or produce network visualizations.
- Validate that graph_source_or_data is available and the environment has NetworkX before execution. Use it to construct or load the graph first, then run the requested graph analysis, partitioning, serialization, or visualization, returning the corresponding graph object or artifacts. No strong workflow guidance.

## Do Not Use When

- The skill cannot execute if NetworkX is not installed in the Python environment.
- Floating-point graph data can make algorithm outputs approximate and affect minimum/maximum computations.
- Large networks may exceed memory or require more efficient representations and approximate methods.
- Random graph generation and force-directed layouts can vary unless seeds are fixed.
- Some operations are graph-type specific, so using the wrong algorithm for directed versus undirected graphs can invalidate results.

## Inputs

- networkx_installed: NetworkX must be available in the Python environment before graph operations can run.
- graph_source_or_data: An existing graph, edge list, matrix, DataFrame, or other network data source to create or load from.

## Outputs

- graph_object: An in-memory NetworkX graph built from scratch or loaded from input data.
- graph_analysis_results: Computed graph outputs such as metrics, shortest paths, connectivity checks, and community assignments.
- community_partition: A partition of nodes into detected communities.
- serialized_graph_file: Persisted graph representation such as edge list, GraphML, or GML output.
- network_visualization_artifact: Saved or displayed network figure output such as PNG, PDF, or on-screen plot.

## Tools And Dependencies

- networkx: Python network analysis library used for graph creation, algorithms, generators, I/O, and visualization support.
- matplotlib_pyplot: Plotting interface used to draw graphs, show figures, and save publication-quality visualizations.
- pandas: Tabular data library used to build edge-list DataFrames and export computed metrics to CSV.
- numpy: Array library used for adjacency-matrix conversion and array-based graph interchange.

## Composition Notes

- required_by: [[skills/cards/citation-network]] confidence=0.99
- member_of: [[communities/0000-sciatlas-idea-data|Literature-grounded research idea lifecycle]]

## Failure Modes

- networkx_not_available
- approximate_numeric_results
- memory_pressure_on_large_graphs
- non_reproducible_random_outputs
- graph_type_algorithm_mismatch

## Read Full Source

Open [full SKILL.md](../sources/networkx.md) when the card is insufficient to decide routing boundaries or execution requirements.
