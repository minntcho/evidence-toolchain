# Failure Modes

Failure modes are first-class outputs.

`evidence-toolchain` should not turn uncertain extraction into confident-looking answers. When the document, tool, or result is weak, that weakness should be preserved as a structured issue.

## Why failure modes matter

Evidence documents are messy:

- scanned bills
- blurry receipt photos
- handwritten logs
- screenshots
- broken tables
- ambiguous units
- cropped images
- multiple candidate values
- mixed date concepts
- unknown document source

A useful evidence system must explain what went wrong and what should happen next.

## Issue categories

### Document quality issues

Examples:

```text
unreadable_document
low_resolution_image
cropped_document
rotated_document
glare_or_shadow
missing_pages
unsupported_media_type
```

### OCR and text issues

Examples:

```text
ocr_low_confidence
possible_digit_confusion
possible_unit_confusion
missing_text_layer
text_layer_incomplete
```

Common confusions:

```text
0 vs O
1 vs l
m3 vs m³
kWh vs KWH
MWh vs mWh
comma vs decimal point
```

### Layout and table issues

Examples:

```text
ambiguous_reading_order
ambiguous_table_structure
merged_cell_risk
multi_page_table_risk
header_association_unclear
line_item_association_unclear
```

### Field extraction issues

Examples:

```text
field_not_found
multiple_candidate_values
field_label_ambiguous
value_unit_pair_unclear
quantity_vs_price_confusion
billing_period_vs_invoice_date_confusion
subtotal_vs_total_confusion
```

### Evidence trust issues

Examples:

```text
low_trust_handwritten_evidence
source_unknown
missing_signature
missing_document_id
manual_edit_visible
screenshot_without_source
single_transaction_not_period_total
```

### Review issues

Examples:

```text
manual_review_required
review_required_for_handwriting
review_required_for_conflicting_values
review_required_for_low_confidence_amount
review_required_for_missing_period
```

## Issue severity

Initial severity levels:

```text
info
warning
blocking
```

### `info`

The issue should be visible but does not stop the report from being useful.

Example:

```text
needs_unit_normalization
```

### `warning`

The extraction may still be usable, but a downstream consumer should treat it carefully.

Example:

```text
multiple_candidate_values
```

### `blocking`

The report should not be treated as extraction-ready without fallback or review.

Example:

```text
unreadable_document
field_not_found
```

## Failure handling pattern

The system should follow this pattern:

```text
capture issue
try allowed fallback if available
preserve both original failure and fallback result
emit review request if uncertainty remains
```

Example:

```text
docling_parse reports ambiguous table structure
-> table_structure_extract fallback runs
-> two usage candidates remain
-> emit multiple_candidate_values warning
-> request manual review for target field
```

## Terminal failures

Some failures should stop automated extraction.

Examples:

```text
unsupported_media_type
file_corrupt
unreadable_document
no_visible_evidence_content
```

A terminal failure should still emit an `EvidenceReport` with issue details. Empty extraction without explanation is not acceptable.

## Non-goal

Failure modes should not become downstream policy verdicts.

Allowed:

```text
This field was not found.
This value has low OCR confidence.
This document appears handwritten and needs review.
```

Not allowed:

```text
This business claim is invalid.
This reporting row must be rejected.
This evidence is legally sufficient.
```

Downstream systems can map issues into their own policy, hazard, review, or rejection semantics.
