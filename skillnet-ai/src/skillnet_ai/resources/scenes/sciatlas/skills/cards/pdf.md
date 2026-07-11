---
type: Skill Card
title: pdf
description: Select this skill when the task involves one or more PDF files and needs reading, transformation, assembly, or analysis rather than simple manual review. Trigger it for bulk text extraction, table extraction, creating new PDFs, merging/splitting/rotating/watermarking/encrypting documents, extracting images, or producing PDF metadata. Requires a source PDF, an output destination for write operations, and a password for encrypted PDFs; OCR support is needed for scanned or image-based PDFs. Use the separate forms guide for PDF form filling.
skill_id: skill:pdf
selectable: True
source: ../sources/pdf.md
tags: [skill, extracted_text_transcript, extracted_table_dataset, pdf_metadata_record, generated_pdf_document, pypdf, pdfplumber, reportlab, pdftotext]
---

# Skill Card

Skill: pdf

## Purpose

Select this skill when the task involves one or more PDF files and needs reading, transformation, assembly, or analysis rather than simple manual review. Trigger it for bulk text extraction, table extraction, creating new PDFs, merging/splitting/rotating/watermarking/encrypting documents, extracting images, or producing PDF metadata. Requires a source PDF, an output destination for write operations, and a password for encrypted PDFs; OCR support is needed for scanned or image-based PDFs. Use the separate forms guide for PDF form filling.

## Use When

- Select this skill when a task requires programmatic reading, generation, or transformation of one or more PDF files, especially for bulk text/table extraction or document assembly; use the separate forms guide for PDF form filling.
- Use extraction first when downstream work depends on PDF text or tables, and use OCR only when the PDF is image-based or text extraction is insufficient. If the PDF is encrypted, provide the password before processing. For document assembly or transformation, route through the appropriate output artifact type (generated, merged, split, rotated, watermarked, or encrypted PDF) based on the requested operation. No strong workflow guidance.

## Do Not Use When

- Text extraction on image-only PDFs is insufficient unless the document is first converted to images and OCRed.
- Decryption cannot succeed without the correct password.
- PDF form filling is out of scope for this guide and is delegated to forms.md.
- Table extraction may yield no usable tables, so downstream combination or export may have nothing to process.
- Plain text extraction can lose visual layout unless layout-preserving mode is chosen.

## Inputs

- source_pdf_document: A PDF file to inspect, extract from, or transform must already be available.
- output_write_destination: A writable file path or destination must exist for generated or modified PDFs and extracted artifacts.
- password_for_encrypted_pdf: A password is needed when decrypting password-protected PDFs.
- ocr_support_stack: OCR dependencies must be available when the input is a scanned or image-only PDF.

## Outputs

- extracted_text_transcript: Plain text extracted from PDF pages, including OCR text for scanned documents.
- extracted_table_dataset: Tabular data extracted from PDF pages, optionally combined into a spreadsheet.
- pdf_metadata_record: Document metadata such as title, author, subject, and creator.
- generated_pdf_document: A newly created PDF composed from drawn text or multi-page structured content.
- merged_pdf_document: A merged PDF assembled from multiple input PDFs.
- split_pdf_page_files: Individual one-page PDF files created from a multi-page input PDF.
- rotated_pdf_document: A PDF saved after page rotation.
- watermarked_pdf_document: A PDF with a watermark merged onto its pages.
- encrypted_pdf_document: A password-protected PDF written after encryption.
- extracted_image_files: Image files extracted from a PDF into an output prefix.

## Tools And Dependencies

- pypdf: Python PDF reader/writer library used for reading, merging, splitting, rotating, watermarking, and encrypting PDFs.
- pdfplumber: Python library used to extract page text and tables from PDFs.
- reportlab: Python library used to create PDFs and multi-page documents.
- pdftotext: Command-line tool used to extract text, optionally preserving layout or page ranges.
- qpdf: Command-line tool used for merging, splitting, rotating, and decrypting PDFs.
- pdftk: Command-line tool used for merging, splitting, and rotating PDFs.
- pdf2image: Python library used to convert scanned PDFs into images for OCR.
- pytesseract: OCR library used to extract text from PDF page images.
- pdfimages: Command-line tool used to extract embedded images from PDFs.
- pandas: DataFrame library used to combine extracted tables and export them to Excel.

## Composition Notes

- compose_with: [[skills/cards/venue-templates]]
- member_of: [[communities/0003-citation-verifier-docx|Scholarly Manuscript Artifact Handling]]

## Failure Modes

- scanned_pdf_needs_ocr
- encrypted_pdf_requires_password
- forms_handled_elsewhere
- table_extraction_can_be_empty
- layout_may_be_lost_without_layout_mode

## Read Full Source

Open [full SKILL.md](../sources/pdf.md) when the card is insufficient to decide routing boundaries or execution requirements.
