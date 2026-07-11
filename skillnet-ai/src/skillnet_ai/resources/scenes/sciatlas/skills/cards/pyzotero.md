---
type: Skill Card
title: pyzotero
description: Select this skill when the task needs code-driven interaction with a Zotero user or group library, especially for reference retrieval, library maintenance, attachment upload, citation export, or searching library contents. It requires Zotero access setup and a Python environment with pyzotero; use the read-only mode only for inspection when API credentials are unavailable. Suitable outputs include Zotero library records, modified library state, and citation exports.
skill_id: skill:pyzotero
selectable: True
source: ../sources/pyzotero.md
tags: [skill, zotero_library_records, modified_library_state, citation_export, pyzotero_python_client, zotero_web_api_v3, pyzotero_cli]
---

# Skill Card

Skill: pyzotero

## Purpose

Select this skill when the task needs code-driven interaction with a Zotero user or group library, especially for reference retrieval, library maintenance, attachment upload, citation export, or searching library contents. It requires Zotero access setup and a Python environment with pyzotero; use the read-only mode only for inspection when API credentials are unavailable. Suitable outputs include Zotero library records, modified library state, and citation exports.

## Use When

- Use when a task needs code-driven access to a Zotero user or group library for retrieval, reference maintenance, attachment upload, citation export, or research automation; use local read-only mode only for inspection without API credentials.
- Establish Zotero access and the pyzotero Python environment before any library operations. Use retrieval or search first for inspection tasks, and only proceed to create, update, delete, or upload attachments when modifying library state is intended and acceptable. If the downstream need is citation generation or research automation, this skill can provide the library data or exports those workflows consume.

## Do Not Use When

- The skill cannot access the target library if the required user ID, API key, or library type/local-mode setup is missing or incorrect.
- Write methods may fail by raising `ZoteroError` instead of returning success.
- Retrieval can be incomplete if default paging is used instead of `everything()` or pagination helpers.
- Local mode is explicitly read-only, so it does not support write workflows.

## Inputs

- zotero_access_setup: Configured target library access: a Zotero user/group library with library ID, library type, and API key, or local=True read-only access.
- pyzotero_python_environment: Python environment with the pyzotero package available to import and use.

## Outputs

- zotero_library_records: Retrieved item, collection, tag, group, and full-text data from the target library.
- modified_library_state: Created, updated, or deleted items, collections, tags, and attachments in the target Zotero library.
- citation_export: BibTeX, CSL-JSON, or bibliography export data generated from Zotero items.

## Tools And Dependencies

- pyzotero_python_client: Python client library used to access the Zotero API and manage library objects.
- zotero_web_api_v3: Remote Zotero API used for library retrieval and write operations.
- pyzotero_cli: Optional command-line interface support for pyzotero.

## Composition Notes

- member_of: [[communities/0000-sciatlas-idea-data|Literature-grounded research idea lifecycle]]

## Failure Modes

- missing_or_misconfigured_library_access
- write_operation_raises_zotero_error
- partial_results_from_default_pagination
- local_mode_is_read_only

## Read Full Source

Open [full SKILL.md](../sources/pyzotero.md) when the card is insufficient to decide routing boundaries or execution requirements.
