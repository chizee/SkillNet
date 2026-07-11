---
type: Skill Card
title: zotero-vectorize
description: Select this skill for tasks that need Zotero path discovery, database snapshotting, metadata/full-text vector generation, incremental update detection or application, and vector store verification on Windows, macOS, or Linux. It is a good fit when the goal is to create or refresh metadata_vectors.json, fulltext_vectors.json, or related vector-store reports; do not select it to modify Zotero itself. Requires read-only Zotero access and a vector store output directory.
skill_id: skill:zotero-vectorize
selectable: True
source: ../sources/zotero-vectorize.md
tags: [skill, metadata_vectors_json, fulltext_vectors_json, vector_store_metadata_json, zotero_db_snapshot, scripts/detect_zotero_paths.py, scripts/snapshot_zotero_db.py, scripts/build_metadata_vectors.py, scripts/build_fulltext_vectors.py]
---

# Skill Card

Skill: zotero-vectorize

## Purpose

Select this skill for tasks that need Zotero path discovery, database snapshotting, metadata/full-text vector generation, incremental update detection or application, and vector store verification on Windows, macOS, or Linux. It is a good fit when the goal is to create or refresh metadata_vectors.json, fulltext_vectors.json, or related vector-store reports; do not select it to modify Zotero itself. Requires read-only Zotero access and a vector store output directory.

## Use When

- Use when a task needs to locate Zotero paths, snapshot the database, create or refresh metadata/full-text embeddings, detect or apply confirmed incremental updates, or verify a local Zotero vector store on Windows, macOS, or Linux; do not select it to edit Zotero itself.
- Typical flow is to detect Zotero paths, snapshot the Zotero database, build metadata vectors, build full-text vectors, check for incremental changes, apply confirmed updates, and then verify vector counts and sizes. Use the verification step to confirm refresh integrity after initial build or incremental maintenance.

## Do Not Use When

- The workflow becomes invalid if it tries to modify the user's Zotero database or attachment storage.
- Database snapshot creation can fail when SQLite is locked.
- Detected Zotero data, database, or storage paths may be wrong and require user correction.
- Incremental store updates must not run until the user confirms the update.
- Full-text processing can fail when PDFs are missing or unreadable.
- PDF full-text extraction may be incomplete.
- Embedding/model setup can fail during model download or local model loading.

## Inputs

- read_only_zotero_access: Access to the user's Zotero data, database, and attachment storage as read-only input.
- vector_store_output_dir: A target store directory for writing vector files, metadata, backups, and verification outputs.

## Outputs

- metadata_vectors_json: Metadata embedding store for Zotero library items.
- fulltext_vectors_json: PDF full-text chunk embedding store for Zotero attachments.
- vector_store_metadata_json: Store metadata describing the current vector store state.
- zotero_db_snapshot: Safe SQLite snapshot of the Zotero database used before builds or updates.
- incremental_update_report: Comparison report showing vector-store coverage gaps and item counts before updating.
- verification_report: Post-build verification of counts, chunk totals, and file sizes for the vector store.

## Tools And Dependencies

- scripts/detect_zotero_paths.py: Resolve default or current Zotero paths.
- scripts/snapshot_zotero_db.py: Create a safe SQLite snapshot before reading or updating.
- scripts/build_metadata_vectors.py: Full rebuild of metadata vectors.
- scripts/build_fulltext_vectors.py: Full rebuild of PDF full-text vectors.
- scripts/check_incremental_updates.py: Compare Zotero against the current vector store to find missing items.
- scripts/apply_incremental_updates.py: Append missing items after user confirmation.
- scripts/verify_vector_store.py: Report counts, sizes, and store metadata after builds or updates.

## Composition Notes

- member_of: [[communities/0000-sciatlas-idea-data|Literature-grounded research idea lifecycle]]

## Failure Modes

- zotero_mutation_violation
- sqlite_snapshot_locked
- wrong_zotero_paths_detected
- unconfirmed_incremental_update
- missing_or_unreadable_pdfs
- incomplete_full_text_extraction
- model_download_or_loading_failure

## Read Full Source

Open [full SKILL.md](../sources/zotero-vectorize.md) when the card is insufficient to decide routing boundaries or execution requirements.
