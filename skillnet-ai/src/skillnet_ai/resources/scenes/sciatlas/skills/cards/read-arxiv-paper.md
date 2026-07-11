---
type: Skill Card
title: read-arxiv-paper
description: Select this skill when the input includes an arXiv paper URL and the objective is to inspect the paper from source rather than a PDF. It requires an arxiv_paper_url and a writable local workspace, uses HTTP fetch plus tar.gz extraction and filesystem reads, and outputs a cached source archive, unpacked source tree, and summary markdown. Do not route it for non-arXiv sources or tasks that do not need local source-based reading and file output.
skill_id: skill:read-arxiv-paper
selectable: True
source: ../sources/read-arxiv-paper.md
tags: [skill, cached_source_archive, unpacked_source_tree, summary_markdown, http_fetch, tar_gz_extraction, filesystem_source_read, markdown_file_write]
---

# Skill Card

Skill: read-arxiv-paper

## Purpose

Select this skill when the input includes an arXiv paper URL and the objective is to inspect the paper from source rather than a PDF. It requires an arxiv_paper_url and a writable local workspace, uses HTTP fetch plus tar.gz extraction and filesystem reads, and outputs a cached source archive, unpacked source tree, and summary markdown. Do not route it for non-arXiv sources or tasks that do not need local source-based reading and file output.

## Use When

- Use when given an arXiv paper URL and the task is to read the paper from source rather than PDF, then produce a local summary file and related insights for nanochat.
- Use it after you have a valid arXiv URL and a writable workspace available. It can hand off extracted source material and a summary file to downstream consumers, but the payload does not provide evidence for broader composition or sequencing beyond source retrieval, unpacking, reading, and local summary writing.

## Do Not Use When

- If the URL is not normalized to the /src/ form, the skill will not target the TeX source as intended.
- The paper source may not have an obvious LaTeX entrypoint to start recursive reading from.
- Choosing a tag that already exists can overwrite an existing summary file.

## Inputs

- arxiv_paper_url: A URL identifying the arXiv paper to read and normalize into a source URL.
- writable_local_workspace: A local workspace with cache and knowledge directories available for downloading, unpacking, and writing the summary file.

## Outputs

- cached_source_archive: A local .tar.gz archive of the arXiv TeX source.
- unpacked_source_tree: The extracted TeX source directory for the paper.
- summary_markdown: A markdown summary file written under the local knowledge directory, including paper takeaways and possible nanochat connections.

## Tools And Dependencies

- http_fetch: Fetch the arXiv source URL to a local archive file.
- tar_gz_extraction: Unpack the downloaded source archive into a local directory.
- filesystem_source_read: Read the entrypoint and recurse through other relevant source files.
- markdown_file_write: Write the resulting summary to a local markdown file.

## Composition Notes

- member_of: [[communities/0002-paper-citation-network|Academic Paper Source-to-Venue Prep]]

## Failure Modes

- non_source_arxiv_url
- missing_or_unfindable_entrypoint
- summary_tag_overwrite_collision

## Read Full Source

Open [full SKILL.md](../sources/read-arxiv-paper.md) when the card is insufficient to decide routing boundaries or execution requirements.
