# Architecture

`evidence-toolchain` is a document-evidence front end.

It should be able to run independently: given a file or document artifact, it should inspect the document, choose an extraction strategy, run tools, and return a structured report.

It should not require a specific downstream validator to exist.

## Architectural goal

The core architecture separates four concerns:

```text
Observation
Planning
Extraction
Reporting
```

This makes tool limitations explicit. A document parser such as Docling may be useful for born-digital PDFs and structured tables, but it is not enough for every evidence document. Some evidence will be scanned, photographed, handwritten, cropped, rotated, table-heavy, low-resolution, or semantically ambiguous.

The system must therefore choose tools based on document condition instead of forcing every document through one parser.

## Main pipeline

```text
EvidenceDocument
  -> observe_document
  -> build_tool_plan
  -> execute_capabilities
  -> consolidate_results
  -> emit_evidence_report
```

### 1. EvidenceDocument

A neutral wrapper around the input material.

It should carry:

- document id
- file name
- media type
- file hash
- upload/source metadata when available
- page/image count when known
- optional declared target fields requested by the caller

It should not carry downstream judgment.

### 2. EvidenceObservation

A first-pass description of the document condition.

Examples:

- born-digital PDF
- scanned PDF
- receipt photo
- invoice image
- utility bill
- spreadsheet export
- handwritten meter log
- meter photo
- mixed text and table document
- unreadable or low-quality image

Observation may be produced by simple rules, metadata inspection, OCR probes, visual models, or an LLM/VLM router.

### 3. EvidenceToolPlan

A planned sequence of capabilities.

The plan records why a tool was selected. It may include fallbacks.

Example:

```json
{
  "document_class": "utility_bill",
  "selected_capabilities": [
    {
      "name": "docling_parse",
      "reason": "born_digital_pdf_with_tables"
    },
    {
      "name": "table_extract",
      "reason": "usage_values_appear_in_table"
    }
  ],
  "fallbacks": ["ocr_extract", "manual_review"]
}
```

### 4. EvidenceCapability

A capability is a tool-like unit that performs one extraction or analysis task.

Examples:

- `docling_parse`
- `ocr_extract`
- `layout_kv_extract`
- `table_structure_extract`
- `receipt_extract`
- `invoice_extract`
- `utility_bill_extract`
- `meter_photo_read`
- `handwriting_read`
- `barcode_read`
- `manual_review_request`

The registry should describe each capability's input requirements, output shape, known strengths, known limitations, and failure modes.

### 5. EvidenceExtractionResult

Raw and semi-structured output from a capability.

It should preserve:

- tool name and version when available
- input document id
- page or image reference
- text spans
- tables or cells
- bounding boxes
- confidence scores
- warnings
- errors

### 6. EvidenceReport

The consolidated neutral output.

It should include:

- document identity
- observation
- selected plan
- tool calls and results summary
- extracted fields
- provenance for each field
- confidence and issue metadata
- unresolved ambiguities
- recommended next action when extraction is insufficient

It should not include final downstream validation judgment.

## Independence rule

Core modules must not import downstream validators.

The dependency direction should be:

```text
downstream app -> evidence-toolchain
```

or:

```text
external orchestrator
  -> evidence-toolchain
  -> downstream validator
```

The reverse direction should not exist:

```text
evidence-toolchain -> downstream validator
```

Adapters may live outside the core package. An adapter can translate `EvidenceReport` into another system's claim, hazard, or review format, but that adapter must not define the core model.

## Trust stance

Extraction is not validation.

The project should make evidence easier to inspect, compare, and review. It should not hide uncertainty behind a polished natural-language answer.

Useful output is not just the extracted value. Useful output includes where the value came from, what tool produced it, what failed, and what remains uncertain.
