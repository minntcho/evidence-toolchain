# Failure mode

Failure mode는 first-class output입니다.

`evidence-toolchain`은 uncertain extraction을 confident-looking answer로 바꾸면 안 됩니다. Document, tool, result가 약하다면 그 약점을 structured issue로 보존해야 합니다.

## Failure mode가 중요한 이유

Evidence document는 지저분합니다.

- scanned bill
- blurry receipt photo
- handwritten log
- screenshot
- broken table
- ambiguous unit
- cropped image
- multiple candidate value
- mixed date concept
- unknown document source

유용한 evidence system은 무엇이 잘못되었는지, 다음에 무엇을 해야 하는지 설명해야 합니다.

## Issue category

### Document quality issue

예시:

```text
unreadable_document
low_resolution_image
cropped_document
rotated_document
glare_or_shadow
missing_pages
unsupported_media_type
```

### OCR and text issue

예시:

```text
ocr_low_confidence
possible_digit_confusion
possible_unit_confusion
missing_text_layer
text_layer_incomplete
```

흔한 confusion:

```text
0 vs O
1 vs l
m3 vs m³
kWh vs KWH
MWh vs mWh
comma vs decimal point
```

### Layout and table issue

예시:

```text
ambiguous_reading_order
ambiguous_table_structure
merged_cell_risk
multi_page_table_risk
header_association_unclear
line_item_association_unclear
```

### Field extraction issue

예시:

```text
field_not_found
multiple_candidate_values
field_label_ambiguous
value_unit_pair_unclear
quantity_vs_price_confusion
billing_period_vs_invoice_date_confusion
subtotal_vs_total_confusion
```

### Evidence trust issue

예시:

```text
low_trust_handwritten_evidence
source_unknown
missing_signature
missing_document_id
manual_edit_visible
screenshot_without_source
single_transaction_not_period_total
```

### Review issue

예시:

```text
manual_review_required
review_required_for_handwriting
review_required_for_conflicting_values
review_required_for_low_confidence_amount
review_required_for_missing_period
```

## Issue severity

초기 severity level:

```text
info
warning
blocking
```

### `info`

Issue는 visible해야 하지만 report가 useful한 것을 막지는 않습니다.

예시:

```text
needs_unit_normalization
```

### `warning`

Extraction은 여전히 usable할 수 있지만 Downstream consumer는 조심해서 다뤄야 합니다.

예시:

```text
multiple_candidate_values
```

### `blocking`

Report는 fallback 또는 review 없이 extraction-ready로 다뤄지면 안 됩니다.

예시:

```text
unreadable_document
field_not_found
```

## Failure handling pattern

System은 다음 pattern을 따라야 합니다.

```text
capture issue
try allowed fallback if available
preserve both original failure and fallback result
emit review request if uncertainty remains
```

예시:

```text
docling_parse reports ambiguous table structure
-> table_structure_extract fallback runs
-> two usage candidates remain
-> emit multiple_candidate_values warning
-> request manual review for target field
```

## Terminal failure

일부 failure는 automated extraction을 멈춰야 합니다.

예시:

```text
unsupported_media_type
file_corrupt
unreadable_document
no_visible_evidence_content
```

Terminal failure도 issue detail을 포함한 `EvidenceReport`를 emit해야 합니다. 설명 없는 empty extraction은 허용되지 않습니다.

## Non-goal

Failure mode는 Downstream policy verdict가 되면 안 됩니다.

허용:

```text
This field was not found.
This value has low OCR confidence.
This document appears handwritten and needs review.
```

금지:

```text
This business claim is invalid.
This reporting row must be rejected.
This evidence is legally sufficient.
```

Downstream system은 issue를 자기 policy, hazard, review, rejection semantic으로 map할 수 있습니다.
