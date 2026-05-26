# 아키텍처

`evidence-toolchain`은 document-evidence front end입니다.

이 프로젝트는 독립적으로 실행될 수 있어야 합니다. file 또는 document artifact를 받으면, 문서를 검사하고, extraction strategy를 고르고, tool을 실행하고, structured report를 반환해야 합니다.

특정 Downstream validator의 존재를 요구해서는 안 됩니다.

## 아키텍처 목표

Core architecture는 네 가지 관심사를 분리합니다.

```text
Observation
Planning
Extraction
Reporting
```

이 분리는 tool limitation을 명시적으로 드러냅니다. Docling 같은 document parser는 born-digital PDF와 structured table에는 유용할 수 있지만 모든 evidence document에 충분하지 않습니다. 어떤 증거는 scanned, photographed, handwritten, cropped, rotated, table-heavy, low-resolution, 또는 semantically ambiguous할 수 있습니다.

따라서 system은 모든 문서를 하나의 parser에 밀어 넣지 않고 document condition에 따라 tool을 선택해야 합니다.

## 주요 파이프라인

```text
EvidenceDocument
  -> observe_document
  -> build_tool_plan
  -> execute_capabilities
  -> consolidate_results
  -> emit_evidence_report
```

### 1. EvidenceDocument

입력 material을 감싸는 중립적인 wrapper입니다.

포함해야 하는 정보:

- document id
- file name
- media type
- file hash
- 가능한 경우 upload/source metadata
- 알려진 경우 page/image count
- caller가 요청한 optional declared target field

Downstream judgment를 담아서는 안 됩니다.

### 2. EvidenceObservation

문서 상태에 대한 first-pass description입니다.

예시:

- born-digital PDF
- scanned PDF
- receipt photo
- invoice image
- utility bill
- spreadsheet export
- handwritten meter log
- meter photo
- mixed text and table document
- unreadable 또는 low-quality image

Observation은 simple rule, metadata inspection, OCR probe, visual model, LLM/VLM router로 만들어질 수 있습니다.

### 3. EvidenceToolPlan

Capability의 계획된 실행 순서입니다.

Plan은 tool이 선택된 이유를 기록합니다. fallback을 포함할 수 있습니다.

예시:

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

Capability는 하나의 extraction 또는 analysis task를 수행하는 tool-like unit입니다.

예시:

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

Registry는 각 capability의 input requirement, output shape, known strength, known limitation, failure mode를 설명해야 합니다.

### 5. EvidenceExtractionResult

Capability에서 나온 raw 또는 semi-structured output입니다.

보존해야 하는 정보:

- 가능한 경우 tool name과 version
- input document id
- page 또는 image reference
- text span
- table 또는 cell
- bounding box
- confidence score
- warning
- error

### 6. EvidenceReport

통합된 중립 output입니다.

포함해야 하는 정보:

- document identity
- observation
- selected plan
- tool call과 result summary
- extracted field
- 각 field의 provenance
- confidence와 issue metadata
- unresolved ambiguity
- extraction이 충분하지 않을 때의 recommended next action

최종 Downstream validation judgment를 포함해서는 안 됩니다.

## 독립성 규칙

Core module은 Downstream validator를 import하면 안 됩니다.

Dependency direction은 다음 중 하나여야 합니다.

```text
downstream app -> evidence-toolchain
```

또는:

```text
external orchestrator
  -> evidence-toolchain
  -> downstream validator
```

반대 방향은 존재해서는 안 됩니다.

```text
evidence-toolchain -> downstream validator
```

Adapter는 core package 밖에 둘 수 있습니다. Adapter는 `EvidenceReport`를 다른 system의 claim, hazard, review format으로 번역할 수 있지만, adapter가 core model을 정의해서는 안 됩니다.

## 신뢰 태도

Extraction은 validation이 아닙니다.

이 프로젝트는 evidence를 더 쉽게 inspect, compare, review하게 만듭니다. uncertainty를 polished natural-language answer 뒤에 숨겨서는 안 됩니다.

유용한 output은 추출된 value만이 아닙니다. 그 value가 어디에서 왔는지, 어떤 tool이 만들었는지, 무엇이 실패했는지, 무엇이 아직 uncertain한지까지 포함해야 유용합니다.
