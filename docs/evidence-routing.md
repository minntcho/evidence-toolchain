# Evidence Routing

Evidence routing is the core reason this repository exists.

The system should not assume that one parser is enough. Evidence documents may be clean PDFs, scanned bills, receipt photos, screenshots, spreadsheets, forms, handwritten logs, or mixed documents.

The router decides which capabilities should be attempted for a given document.

## Routing principle

```text
Look first.
Plan tools second.
Extract third.
Report uncertainty always.
```

This prevents a Docling-first or OCR-first architecture from becoming a hidden bottleneck.

## Inputs

Routing can use:

- file metadata
- media type
- page count
- image dimensions
- text layer availability
- OCR probe results
- visual inspection results
- caller-requested target fields
- previously known document source
- document quality signals

## Output

The router emits an `EvidenceToolPlan`.

A plan should include:

- observed document class
- selected capabilities
- reason for each selected capability
- fallback capabilities
- expected outputs
- blocking conditions
- review triggers

Example:

```json
{
  "document_class": "receipt_photo",
  "quality": "medium",
  "selected_capabilities": [
    {
      "name": "ocr_extract",
      "reason": "photo_without_text_layer"
    },
    {
      "name": "receipt_extract",
      "reason": "receipt_like_layout"
    }
  ],
  "fallbacks": [
    {
      "name": "vision_extract",
      "reason": "ocr_may_fail_on_rotated_or_low_quality_image"
    },
    {
      "name": "manual_review_request",
      "reason": "receipt_total_or_quantity_may_be_ambiguous"
    }
  ]
}
```

## Routing examples

### Born-digital utility bill

```text
Observation:
- PDF has text layer
- tables are visible
- no handwriting

Plan:
- docling_parse
- table_structure_extract
- utility_bill_extract

Fallback:
- ocr_extract if text layer is incomplete
- manual_review_request if multiple candidate usage values conflict
```

### Scanned invoice

```text
Observation:
- image-only PDF
- invoice-like layout
- medium OCR risk

Plan:
- ocr_extract
- layout_kv_extract
- invoice_extract

Fallback:
- vision_extract
- manual_review_request
```

### Handwritten meter log

```text
Observation:
- handwriting present
- table-like rows
- meter readings may require subtraction

Plan:
- handwriting_read
- table_structure_extract
- meter_log_extract

Fallback:
- manual_review_request

Default issue:
- low_trust_handwritten_evidence
```

### Meter photo

```text
Observation:
- image of physical meter
- no document table
- target is likely meter reading, not invoice amount

Plan:
- vision_extract
- meter_photo_read

Fallback:
- manual_review_request

Default issue:
- site_meter_mapping_required
```

### Poor-quality screenshot

```text
Observation:
- low resolution
- cropped boundaries
- unclear source

Plan:
- ocr_extract
- vision_extract

Fallback:
- manual_review_request

Possible terminal issue:
- unreadable_document
```

## Router implementations

The repository should support multiple router implementations.

### Rule router

A deterministic router based on file metadata and cheap probes.

Good for:

- reproducible tests
- baseline behavior
- offline execution
- controlled enterprise environments

### Model router

A router that uses a classifier, LLM, or VLM to inspect document condition and propose tool plans.

Good for:

- messy evidence
- unknown document formats
- mixed scans and screenshots
- early exploration

### Hybrid router

A deterministic skeleton with model-assisted observation.

This is likely the safest default long term:

```text
rules determine allowed capabilities
model observes document condition
rules compile observation into a bounded tool plan
```

## Router constraints

The router may choose tools. It may not make final validation judgments.

Allowed:

```text
This document needs OCR and table extraction.
The amount field is ambiguous.
Manual review should be requested.
```

Not allowed:

```text
The declared business value is finally valid.
This claim is approved for reporting.
This evidence is sufficient under every policy.
```

## Failure-aware routing

Tool failure should not be hidden.

If a capability fails, the system should preserve the failure and decide whether to try a fallback.

Example:

```text
docling_parse failed to recover table structure
-> try OCR/table extractor fallback
-> if results still conflict, emit ambiguous_table_structure issue
```

This makes the system robust without pretending that every document can be solved automatically.
