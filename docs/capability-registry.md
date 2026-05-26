# Capability registry

Capability registry는 router가 선택할 수 있는 extraction 및 inspection tool catalog입니다.

Capability는 단순한 function이 아닙니다. Known input, output, strength, limit, failure mode를 가진 declared unit of document-processing behavior입니다.

## Registry가 필요한 이유

Evidence document는 하나의 default parser로 처리하기에는 너무 다양합니다.

Registry는 system이 다음 질문을 하게 해 줍니다.

```text
What can we try on this document?
What does this tool require?
What does this tool produce?
What does this tool commonly get wrong?
When should this tool be followed by another tool?
```

## Capability record

Registry entry는 나중에 다음을 설명해야 합니다.

```text
name
purpose
input requirements
output shape
strengths
known limitations
failure modes
confidence semantics
fallback recommendations
review triggers
```

예시 shape:

```json
{
  "name": "docling_parse",
  "purpose": "Convert structured PDFs and office documents into document structure with text, tables, layout, and reading order.",
  "input_requirements": ["pdf_or_supported_office_document"],
  "outputs": ["pages", "text_spans", "tables", "cells", "layout_blocks"],
  "strengths": ["born_digital_pdf", "tables", "reading_order"],
  "limitations": ["bad_scans", "handwriting", "cropped_photos", "domain_field_judgment"],
  "fallbacks": ["ocr_extract", "table_structure_extract", "manual_review_request"]
}
```

## 초기 capability set

### `docling_parse`

Structured document conversion에 사용합니다.

좋은 candidate:

- born-digital PDF
- table이 있는 utility bill
- clear text layer가 있는 invoice
- office document
- table-heavy report

Known limit:

- image-only scan은 OCR이 먼저 필요할 수 있다
- handwriting에는 safe default가 아니다
- complex table은 specialized table extraction이 여전히 필요할 수 있다
- extracted structure는 final business judgment가 아니다

### `ocr_extract`

Image 또는 scan text extraction에 사용합니다.

좋은 candidate:

- scanned PDF
- receipt photo
- screenshot
- photographed invoice

Known limit:

- digit와 unit이 confused될 수 있다
- rotation, blur, glare, crop boundary가 extraction을 깨뜨릴 수 있다
- OCR text만으로는 table relationship을 자주 잃는다

### `layout_kv_extract`

Field label과 value가 서로 가까이 배치된 key-value extraction에 사용합니다.

좋은 candidate:

- form
- invoice
- receipt
- bill

Known limit:

- repeated label은 wrong match를 만들 수 있다
- nested table structure는 key-value pairing을 confuse할 수 있다
- field name은 domain-dependent하다

### `table_structure_extract`

Table reconstruction에 사용합니다.

좋은 candidate:

- usage table
- invoice line item
- meter reading log
- monthly activity table

Known limit:

- merged cell, multi-row header, footnote, page break는 risky하다
- table geometry가 맞아도 semantic field mapping은 틀릴 수 있다

### `receipt_extract`

Receipt-specific field에 사용합니다.

Potential field:

- transaction date
- merchant
- item description
- quantity
- unit
- amount
- total

Known limit:

- price와 physical quantity가 confused될 수 있다
- receipt 하나는 보통 transaction 하나를 의미하며 reporting-period total이 아닐 수 있다
- item name은 domain mapping이 필요할 수 있다

### `invoice_extract`

Invoice-specific field에 사용합니다.

Potential field:

- supplier
- invoice number
- billing period
- line item
- quantity
- unit
- amount
- currency

Known limit:

- invoice amount가 항상 activity amount는 아니다
- billing period와 invoice date가 다를 수 있다
- tax, fee, subtotal row가 activity row로 잘못 읽힐 수 있다

### `utility_bill_extract`

Electricity, gas, water, steam 같은 utility bill에 사용합니다.

Potential field:

- customer/site name
- service address
- billing period
- meter id
- usage amount
- usage unit
- supplier

Known limit:

- bill date와 service period가 다르다
- peak/off-peak row는 aggregation이 필요할 수 있다
- correction row와 estimate는 flag되어야 한다

### `meter_photo_read`

Physical meter image에 사용합니다.

Potential field:

- meter id
- visible reading
- visible한 경우 unit
- embedded 또는 externally provided timestamp

Known limit:

- single reading은 period usage amount가 아니다
- site-to-meter mapping은 다른 곳에서 필요하다
- glare, angle, display type이 value를 ambiguous하게 만들 수 있다

### `handwriting_read`

Handwritten log 또는 handwritten field에 사용합니다.

Potential field:

- date
- reading
- quantity
- name
- signature

Known limit:

- 보통 review를 trigger해야 한다
- value는 더 강한 provenance와 cross-checking이 필요하다
- overwritten 또는 corrected value는 explicit issue가 필요하다

### `barcode_read`

Barcode 또는 QR code에 사용합니다.

Potential field:

- document id
- supplier code
- invoice/payment lookup reference
- 가능한 경우 verification URL

Known limit:

- code content는 external lookup이 필요할 수 있다
- QR 존재만으로 business value correctness가 증명되지는 않는다

### `vision_extract`

Text extraction을 넘어 visual reasoning이 필요한 document state에 사용합니다.

좋은 candidate:

- screenshot
- photo
- mixed visual document
- poor layout recovery case

Known limit:

- provenance-rich extraction을 silently replace하면 안 된다
- natural language answer는 가능한 경우 visible span 또는 region에 다시 grounded되어야 한다

### `manual_review_request`

Automated extraction이 insufficient, ambiguous, high-risk일 때 사용합니다.

Review는 afterthought가 아니라 toolchain의 일부이기 때문에 이것도 capability입니다.

보존해야 하는 것:

- what needs review
- why review was requested
- which fields are uncertain
- which tool outputs caused the uncertainty

## Registry policy

새 capability를 추가할 때는 다음을 문서화해야 합니다.

1. 언제 사용하는가.
2. 언제 사용하지 않는가.
3. 어떤 output을 promise하는가.
4. 무엇을 guarantee할 수 없는가.
5. 어떤 issue를 emit할 수 있는가.
6. Failure 뒤에 어떤 fallback 또는 review path가 따라야 하는가.

문서화된 한계가 없는 capability는 default routing에 들어갈 준비가 된 것이 아닙니다.
