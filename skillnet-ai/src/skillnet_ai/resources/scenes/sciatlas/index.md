# SkillNet SciAtlas Scene Wiki

> Agent-readable skill knowledge bundle. Use skill cards for orchestration. Open full sources when exact boundaries, prerequisites, or execution details matter.

## Corpus
- skills: 28
- communities: 5
- workflows: 1

## Skill Cards
- [academic-writing-refiner](skills/cards/academic-writing-refiner.md)
  summary: Select this skill when the input is draft academic text to polish, proofread, or lightly edit research writing, especially LaTeX content or venue-specific material such as abstracts, introductions, related work, methods, experiments...
  source: [full SKILL.md](skills/sources/academic-writing-refiner.md)
- [bib-verify](skills/cards/bib-verify.md)
  summary: Select this skill when the task is to audit a .bib file or paper bibliography for hallucinated, fabricated, missing, or inaccurate citations. It requires a BibTeX file path and an execution environment with the listed runtime...
  source: [full SKILL.md](skills/sources/bib-verify.md)
- [citation-network](skills/cards/citation-network.md)
  summary: Select this skill when the task has source/target citation pairs and the goal is literature review, trend detection, community discovery, bridge-paper identification, or exportable network visualization. It requires an initialized run...
  source: [full SKILL.md](skills/sources/citation-network.md)
- [citation-verifier](skills/cards/citation-verifier.md)
  summary: Select this skill when the input is a known citation artifact such as a DOI, URL, arXiv ID, PubMed ID, citation string, or paper title and the task is to verify or normalize it. It is suitable for quick citation checking and enrichment...
  source: [full SKILL.md](skills/sources/citation-verifier.md)
- [data-analysis](skills/cards/data-analysis.md)
  summary: Select this when the task centers on uploaded .xlsx/.xls or CSV files and needs structured data exploration, file-structure inventory, filtering, aggregation, joins, statistics, queryable tables, or exported analytical outputs. Requires...
  source: [full SKILL.md](skills/sources/data-analysis.md)
- [docx](skills/cards/docx.md)
  summary: Select when the task targets Word documents or asks for a professional deliverable as .docx, especially for .docx creation/editing, formatting, find-and-replace, image insertion, tracked changes/comments, or reorganizing content from an...
  source: [full SKILL.md](skills/sources/docx.md)
- [glmocr-table](skills/cards/glmocr-table.md)
  summary: Select this skill when the task is to recognize or extract tabular content from an image, scanned document, spreadsheet capture, or PDF and return structured editable table output. It requires a source file or URL, a ZhiPu API key, and...
  source: [full SKILL.md](skills/sources/glmocr-table.md)
- [latex-paper-conversion](skills/cards/latex-paper-conversion.md)
  summary: Select this skill when the task is to port an existing LaTeX paper between publication formats such as Springer, IPOL, MDPI, IEEE, or Nature, especially when the work involves source LaTeX input, a target template directory, and...
  source: [full SKILL.md](skills/sources/latex-paper-conversion.md)
- [networkx](skills/cards/networkx.md)
  summary: Select this skill when the task involves graph or network data structures, pairwise relationships, graph algorithms, community detection, graph serialization, or network visualizations. Trigger especially on requests to build a graph...
  source: [full SKILL.md](skills/sources/networkx.md)
- [paper-compile](skills/cards/paper-compile.md)
  summary: Select this skill when the task is to build, fix, or validate a LaTeX paper PDF, especially for requests like compile paper, build PDF, 生成PDF, or when investigating compilation failures. It expects a LaTeX source tree and a LaTeX...
  source: [full SKILL.md](skills/sources/paper-compile.md)
- [pdf](skills/cards/pdf.md)
  summary: Select this skill when the task involves one or more PDF files and needs reading, transformation, assembly, or analysis rather than simple manual review. Trigger it for bulk text extraction, table extraction, creating new PDFs...
  source: [full SKILL.md](skills/sources/pdf.md)
- [peer-review](skills/cards/peer-review.md)
  summary: Select this entity when the downstream task is to peer-review a manuscript, preprint, review/meta-analysis, methods paper, or grant proposal from a provided target_submission and return a structured_peer_review_report. Use it for...
  source: [full SKILL.md](skills/sources/peer-review.md)
- [pptx-posters](skills/cards/pptx-posters.md)
  summary: Select only for explicit PowerPoint/PPTX poster requests or HTML posters intended for PowerPoint editing; requires an HTML poster template asset and is not the default for standard research posters or LaTeX poster requests, which should...
  source: [full SKILL.md](skills/sources/pptx-posters.md)
- [pyzotero](skills/cards/pyzotero.md)
  summary: Select this skill when the task needs code-driven interaction with a Zotero user or group library, especially for reference retrieval, library maintenance, attachment upload, citation export, or searching library contents. It requires...
  source: [full SKILL.md](skills/sources/pyzotero.md)
- [read-arxiv-paper](skills/cards/read-arxiv-paper.md)
  summary: Select this skill when the input includes an arXiv paper URL and the objective is to inspect the paper from source rather than a PDF. It requires an arxiv_paper_url and a writable local workspace, uses HTTP fetch plus tar.gz extraction...
  source: [full SKILL.md](skills/sources/read-arxiv-paper.md)
- [retraction-watcher](skills/cards/retraction-watcher.md)
  summary: Select this skill when the input is a manuscript bibliography, raw citation list, or reference dataset that needs retraction-status verification before submission or reuse. It requires citation_input plus internet access, Python 3.10+...
  source: [full SKILL.md](skills/sources/retraction-watcher.md)
- [sciatlas-idea-evaluate](skills/cards/sciatlas-idea-evaluate.md)
  summary: Select this skill when the task is to assess whether a research idea is worth pursuing and you have a clear research_idea_statement, plus access to SciAtlas search-papers via an executable and API/registration token. It is appropriate...
  source: [full SKILL.md](skills/sources/sciatlas-idea-evaluate.md)
- [sciatlas-idea-generate](skills/cards/sciatlas-idea-generate.md)
  summary: Select this skill when the user wants new research directions, brainstormed hypotheses, cross-topic combinations, or project ideas grounded in retrieved papers. It requires a topic or field plus SciAtlas access details, and it outputs...
  source: [full SKILL.md](skills/sources/sciatlas-idea-generate.md)
- [sciatlas-idea-grounding](skills/cards/sciatlas-idea-grounding.md)
  summary: Select this skill when the user provides a research idea and needs similar work, related-work support, differentiation evidence, motivation support, or literature-grounded refinement. It requires a research idea description plus...
  source: [full SKILL.md](skills/sources/sciatlas-idea-grounding.md)
- [sciatlas-literature-review](skills/cards/sciatlas-literature-review.md)
  summary: Select when the user needs a literature review, related-work section, survey outline, paper map, or topic overview grounded in SciAtlas search-papers evidence. Best fit when inputs include a topic scope or need for clarification and the...
  source: [full SKILL.md](skills/sources/sciatlas-literature-review.md)
- [sciatlas-quick-paper-search](skills/cards/sciatlas-quick-paper-search.md)
  summary: Select this skill when the user needs a first-pass literature check, retrieval smoke test, quick paper shortlist, or help choosing the next SciAtlas skill. It requires paper_search_topic and is bounded to SciAtlas search-papers only; it...
  source: [full SKILL.md](skills/sources/sciatlas-quick-paper-search.md)
- [sciatlas-researcher-review](skills/cards/sciatlas-researcher-review.md)
  summary: Select this skill when the request is about a specific researcher’s background, representative papers, topic evolution, or an author-centered literature overview, and the answer must be grounded only in retrieved SciAtlas paper...
  source: [full SKILL.md](skills/sources/sciatlas-researcher-review.md)
- [sciatlas-trend-report](skills/cards/sciatlas-trend-report.md)
  summary: Select this skill when the request is about topic history, field evolution, recent trends, representative papers over time, or emerging directions, and the answer should be grounded in SciAtlas search-papers results. It needs a...
  source: [full SKILL.md](skills/sources/sciatlas-trend-report.md)
- [scientific-figure-making](skills/cards/scientific-figure-making.md)
  summary: Select this skill when the task is to produce bar, trend, scatter, heatmap, or multi-panel figures for papers, slides, or reports that must match repository aesthetics and export cleanly to print/vector formats. It expects a...
  source: [full SKILL.md](skills/sources/scientific-figure-making.md)
- [scientific-slides](skills/cards/scientific-slides.md)
  summary: Select this skill when the task is to prepare or refine a scientific talk deck, such as for a conference, seminar, thesis defense, grant talk, or journal club. It fits when the inputs include talk context, source material, figures, and...
  source: [full SKILL.md](skills/sources/scientific-slides.md)
- [table-extractor](skills/cards/table-extractor.md)
  summary: Select this skill when the input is a PDF document and the task requires table extraction, page or region selection for tables, handling merged or borderless tables, combining tables across pages, or exporting extracted tables into...
  source: [full SKILL.md](skills/sources/table-extractor.md)
- [venue-templates](skills/cards/venue-templates.md)
  summary: Select this skill when the task involves a known target venue or funding agency and needs template retrieval, author/project customization, or compliance checking for manuscripts, conference papers, posters, or grant submissions. Best...
  source: [full SKILL.md](skills/sources/venue-templates.md)
- [zotero-vectorize](skills/cards/zotero-vectorize.md)
  summary: Select this skill for tasks that need Zotero path discovery, database snapshotting, metadata/full-text vector generation, incremental update detection or application, and vector store verification on Windows, macOS, or Linux. It is a...
  source: [full SKILL.md](skills/sources/zotero-vectorize.md)

## Communities
- [Academic Paper Source-to-Venue Prep](communities/0002-paper-citation-network.md): A community for paper-source preparation tasks centered on arXiv/source LaTeX ingestion, citation-graph construction, venue template fitting, format conversion, and submission compliance checks.
- [Literature-grounded research idea lifecycle](communities/0000-sciatlas-idea-data.md): Community for literature-grounded research idea work using SciAtlas search-papers to generate, ground, and assess research ideas or build a literature-based researcher profile.
- [Paper Evidence Synthesis](communities/0001-sciatlas-table-paper.md): Community for paper-evidence work that searches scholarly sources, extracts tables or layouts from paper artifacts, synthesizes literature into manuscript-ready text, and compiles LaTeX outputs.
- [Scholarly Integrity Verification](communities/0004-bib-verify-peer.md): Community for validating scholarly submissions and citation artifacts, including BibTeX/reference checks against external indexes, retraction/correction screening, and structured manuscript or grant peer review.
- [Scholarly Manuscript Artifact Handling](communities/0003-citation-verifier-docx.md): Community for scholarly manuscript artifact handling, centered on citation verification/normalization and DOCX/PDF document transformation for paper or report assembly.

## Workflows
- [skill:paper-compile -> skill:peer-review](workflows/paper-compile-skill-peer-review-artifact-compatibility.md): artifact_compatibility via target_submission_document.

## Full Skill Sources
- [academic-writing-refiner](skills/sources/academic-writing-refiner.md)
- [bib-verify](skills/sources/bib-verify.md)
- [citation-network](skills/sources/citation-network.md)
- [citation-verifier](skills/sources/citation-verifier.md)
- [data-analysis](skills/sources/data-analysis.md)
- [docx](skills/sources/docx.md)
- [glmocr-table](skills/sources/glmocr-table.md)
- [latex-paper-conversion](skills/sources/latex-paper-conversion.md)
- [networkx](skills/sources/networkx.md)
- [paper-compile](skills/sources/paper-compile.md)
- [pdf](skills/sources/pdf.md)
- [peer-review](skills/sources/peer-review.md)
- [pptx-posters](skills/sources/pptx-posters.md)
- [pyzotero](skills/sources/pyzotero.md)
- [read-arxiv-paper](skills/sources/read-arxiv-paper.md)
- [retraction-watcher](skills/sources/retraction-watcher.md)
- [sciatlas-idea-evaluate](skills/sources/sciatlas-idea-evaluate.md)
- [sciatlas-idea-generate](skills/sources/sciatlas-idea-generate.md)
- [sciatlas-idea-grounding](skills/sources/sciatlas-idea-grounding.md)
- [sciatlas-literature-review](skills/sources/sciatlas-literature-review.md)
- [sciatlas-quick-paper-search](skills/sources/sciatlas-quick-paper-search.md)
- [sciatlas-researcher-review](skills/sources/sciatlas-researcher-review.md)
- [sciatlas-trend-report](skills/sources/sciatlas-trend-report.md)
- [scientific-figure-making](skills/sources/scientific-figure-making.md)
- [scientific-slides](skills/sources/scientific-slides.md)
- [table-extractor](skills/sources/table-extractor.md)
- [venue-templates](skills/sources/venue-templates.md)
- [zotero-vectorize](skills/sources/zotero-vectorize.md)
