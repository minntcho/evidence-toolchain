# 증거 라우팅

Evidence routing은 이 저장소가 존재하는 핵심 이유입니다.

System은 parser 하나로 충분하다고 가정하면 안 됩니다. Evidence document는 clean PDF, scanned bill, receipt photo, screenshot, spreadsheet, form, handwritten log, mixed document일 수 있습니다.

Router는 주어진 document에 어떤 capability를 시도할지 결정합니다.

## 라우팅 원칙

```text
먼저 관찰한다.
그 다음 tool을 계획한다.
세 번째로 추출한다.
항상 uncertainty를 report한다.
```

이 원칙은 Docling-first 또는 OCR-first architecture가 숨은 bottleneck이 되는 일을 막습니다.

## 입력

Routing은 다음을 사용할 수 있습니다.

- file metadata
- media type
- page count
- image dimension
- text layer availability
- OCR probe result
- visual inspection result
- caller-requested target field
- previously known document source
- document quality signal

## 출력

Router는 `EvidenceToolPlan`을 emit합니다.

Plan은 다음을 포함해야 합니다.

- observed document class
- selected capability
- 각 selected capability의 reason
- fallback capability
- expected output
- blocking condition
- review trigger

예시:

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

## 라우팅 예시

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

## Router 구현

이 저장소는 여러 router implementation을 지원해야 합니다.

### Rule router

File metadata와 cheap probe에 기반한 deterministic router입니다.

적합한 경우:

- reproducible test
- baseline behavior
- offline execution
- controlled enterprise environment

### Model router

Classifier, LLM, VLM으로 document condition을 inspect하고 tool plan을 propose하는 router입니다.

적합한 경우:

- messy evidence
- unknown document format
- mixed scan과 screenshot
- early exploration

### Hybrid router

Model-assisted observation을 가진 deterministic skeleton입니다.

장기적으로 가장 안전한 default일 가능성이 큽니다.

```text
rules determine allowed capabilities
model observes document condition
rules compile observation into a bounded tool plan
```

## Router 제약

Router는 tool을 선택할 수 있습니다. 최종 validation judgment를 내리면 안 됩니다.

허용:

```text
This document needs OCR and table extraction.
The amount field is ambiguous.
Manual review should be requested.
```

금지:

```text
The declared business value is finally valid.
This claim is approved for reporting.
This evidence is sufficient under every policy.
```

## 실패 인식 라우팅

Tool failure는 숨겨지면 안 됩니다.

Capability가 실패하면 system은 failure를 보존하고 fallback을 시도할지 결정해야 합니다.

예시:

```text
docling_parse failed to recover table structure
-> try OCR/table extractor fallback
-> if results still conflict, emit ambiguous_table_structure issue
```

이 방식은 모든 document를 자동으로 solve할 수 있는 척하지 않으면서 system을 robust하게 만듭니다.
