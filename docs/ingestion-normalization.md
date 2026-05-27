# 첨부 정규화

`evidence-toolchain`은 PDF reader 하나에 의존하는 시스템이 아닙니다.
실제 제출물은 PDF, 이미지, spreadsheet, CSV, Office 문서, email, archive처럼
여러 physical attachment 형식으로 들어올 수 있습니다.

파일 라우팅은 물리 첨부를 공통 inventory로 낮춘다.
의미 라우팅은 inventory를 증거 후보 atom으로 바꾼다.
resolution은 입력 X와 atom Y를 연결한다.

## 계층

첨부 ingestion 계층은 다음 책임을 가집니다.

```text
AttachmentBundle
-> RawAttachment
-> SafetyPolicy
-> FileKindRouter
-> ArtifactExpander
-> EvidenceArtifact
-> File-specific Reader
-> EvidenceUnit
-> EvidenceInventory
```

그 다음 계층은 `EvidenceInventory`를 읽고 semantic candidate를 만듭니다.

```text
EvidenceInventory
-> EvidenceAtom / Y 후보
-> X-Y ResolutionGraph
```

## 계약

### `AttachmentBundle`

함께 제출된 raw attachment 묶음입니다.
Bundle은 아직 증빙 의미를 판단하지 않습니다.

### `RawAttachment`

라우팅 전 원본 첨부 파일의 안정적인 identity record입니다.
확장자, 파일명, byte size, sha256, declared/detected media type 같은 값을 보존합니다.

### `RouteDecision`

`FileKindRouter`가 선택한 route와 그 근거를 보존합니다.
확장자, magic bytes, MIME, open probe가 충돌할 수 있으므로 `matched_by`,
`rejected_by`, `issues`를 남겨야 합니다.

FileKindRouter는 route와 근거를 함께 남긴다.
예를 들어 `.pdf` 확장자와 `%PDF` magic signature가 함께 확인되면 `pdf`
route를 선택할 수 있지만, 확장자와 signature가 충돌하면 `unknown` route와
`file_signature_mismatch` issue를 남겨야 합니다.

### `SafetyDecision`

reader 실행 전에 적용된 safety check 결과입니다.
SafetyPolicy는 reader보다 먼저 적용되어야 한다.

### `EvidenceArtifact`

출처/물리 단위입니다.
예시는 file, PDF page, image, spreadsheet sheet, archive member, email body입니다.

### `EvidenceUnit`

reader가 관찰한 원시 단위입니다.
예시는 text span, word box, table, table cell, image region, metadata입니다.

EvidenceUnit은 semantic matching target이 아니다.
EvidenceUnit은 "어디에서 무엇을 봤는지"를 보존합니다.
X-Y matching 대상은 `EvidenceAtom`입니다.

### `EvidenceInventory`

Attachment, artifact, unit, route decision, safety decision, issue를 묶는
bundle-level ingestion output입니다.

`merge_evidence_inventories`는 single-attachment inventory들을 입력 순서대로
하나의 bundle-level inventory로 합칩니다.
이 merge는 semantic routing이 아니다.
Attachment, artifact, unit, route decision, safety decision, issue를 결합할 뿐
EvidenceAtom이나 X-Y graph edge를 만들지 않습니다.

`ingest_bundle`은 `AttachmentBundle`의 각 `RawAttachment`에 같은 router와
safety policy를 적용한 뒤 결과 inventory를 merge합니다.
Bundle ingestion은 reader orchestration의 얇은 계층이며, archive expansion이나
semantic evidence classification을 수행하지 않습니다.

### `EvidenceAtom`

EvidenceAtom은 `EvidenceUnit`에서 해석된 semantic evidence candidate입니다.
LLM, VLM, deterministic atomizer, resolver가 함께 소비할 수 있는 공통 언어이며,
X-Y matching 대상이 되는 Y 후보입니다.

EvidenceAtom은 support/contradict 판정이 아니다.
Atom은 "이 단서가 usage_amount, service_period, site_identity 같은 의미 후보일 수 있다"를
표현할 뿐이며, 특정 X를 지지하거나 반박하는지는 후속 ResolutionGraph가 판단합니다.

v0 atom type vocabulary는 사람이 읽을 수 있는 string으로 고정합니다.

```text
document_type
activity_identity
usage_amount
service_period
site_identity
supplier_identity
meter_reading
meter_delta
line_item
currency_amount
date
identifier
table_row
note
unknown
```

`producer`는 atom을 만든 주체를 보존합니다.
예시는 `regex_atomizer`, `table_atomizer`, `llm_atomizer`, `vlm_atomizer`입니다.
`source_unit_ids`와 `source_artifact_ids`는 반드시 보존해야 합니다.

`normalized`는 best-effort helper field다.
단위 변환 또는 정규화 결과를 담을 수 있지만 final matching authority가 아니며,
최종 compatibility, tolerance, support 여부는 resolver 계층이 판단해야 합니다.

### `AtomizerResult`

AtomizerResult는 하나의 `EvidenceInventory` 또는 bundle에서 생성된
EvidenceAtom 후보 묶음입니다.
AtomizerResult는 EvidenceReport도 아니고 ResolutionGraph도 아닙니다.
Support edge, contradiction edge, `x_id` 연결은 이 계층에 들어오면 안 됩니다.

### `SimpleTextAtomizer`

SimpleTextAtomizer는 deterministic baseline atomizer입니다.
`text_span`과 `table_cell` EvidenceUnit에서 명확한 숫자, 단위, 날짜 패턴만
EvidenceAtom 후보로 올립니다.

초기 범위는 좁게 유지합니다.

```text
usage_amount
currency_amount
service_period
date
```

SimpleTextAtomizer는 LLM/VLM adapter가 아니다.
복잡한 row grouping, table semantics, OCR repair, unit conversion authority,
support/contradict 판정은 수행하지 않습니다.
특히 `currency_amount`는 usage support로 바로 쓰기 위한 값이 아니라,
나중에 resolver가 "금액 후보라서 사용량 support로 쓰면 안 된다"라고 설명할 수 있게
provenance가 있는 semantic candidate로 보존하는 값입니다.

### `UnsupportedReader`

지원하지 않는 attachment를 억지로 읽지 않고 `unsupported_attachment` artifact와
`unsupported_media_type` issue로 보존합니다.
UnsupportedReader는 semantic extraction을 수행하지 않으며 `EvidenceUnit`을 만들지 않습니다.

### `PlainTextReader`

PlainTextReader는 `.txt`, `.md`, `.log` 같은 plain text attachment를 file
artifact와 line-level `text_span` EvidenceUnit으로 낮춥니다.
Plain text는 원천성이 약할 수 있으므로 `plain_text_low_provenance` issue를 보존합니다.

### `DelimitedTableReader`

DelimitedTableReader는 `.csv`, `.tsv` attachment를 file artifact, `table`
EvidenceUnit, `table_cell` EvidenceUnit으로 낮춥니다.
Header, row, column locator는 provenance로 남기지만, reader는 EvidenceAtom을 만들지 않는다.

### `PdfProfileReader`

PdfProfileReader는 PDF attachment를 file artifact, page-level `pdf_page` artifact,
그리고 PDF profile metadata EvidenceUnit으로 낮춥니다.
PDF profile은 text extraction이 아니다.
Page count, encrypted 여부, rough text-layer marker 같은 cheap signal만 보존하며,
text span, table, field extraction은 별도 reader/capability가 담당해야 합니다.

### `PdfPlumberExtractReader`

PdfPlumberExtractReader는 born-digital PDF의 text와 word bbox를
`text_span` EvidenceUnit, `word_box` EvidenceUnit으로 낮춥니다.
이 reader는 `pdfplumber` adapter이며 PDF profile reader를 대체하지 않습니다.
기본 `ingest_attachment` PDF route는 cheap profile을 만들고, text/word extraction은
후속 interrogation loop나 capability가 필요할 때 별도로 호출해야 합니다.

PdfPlumberExtractReader는 EvidenceAtom을 만들지 않는다.
`사용량 6.4 MWh` 같은 text span과 `6.4` 같은 word box를 관찰 단위로 보존할 뿐,
usage_amount, unit, period 같은 semantic 후보 판단은 후속 atomizer 계층이 담당합니다.

### `ImageProfileReader`

ImageProfileReader는 image attachment를 image artifact와 image profile metadata
EvidenceUnit으로 낮춥니다.
Image profile은 OCR 또는 VLM extraction이 아니다.
Width, height, format, mode, EXIF orientation placeholder, aspect ratio 같은
cheap signal만 보존하며, text OCR, meter reading, receipt extraction, handwriting
해석은 별도 capability가 담당해야 합니다.

### `SpreadsheetReader`

SpreadsheetReader는 `.xlsx` workbook을 workbook artifact, sheet artifact,
`table` EvidenceUnit, `table_cell` EvidenceUnit으로 낮춥니다.
Sheet name, used range, row/column/cell locator, cached cell value, formula 존재 여부,
hidden sheet signal을 provenance로 남기지만, reader는 EvidenceAtom을 만들지 않는다.

Spreadsheet reader는 수식을 실행하지 않는다.
Formula cell은 cached value와 formula text를 raw observation으로 보존할 뿐이며,
usage_amount, service_period, site_identity 같은 semantic 후보 생성은 후속
atomizer 계층이 담당해야 합니다.

## 해야 하는 일

- 물리 attachment를 공통 inventory로 정규화한다.
- route와 safety decision의 근거를 보존한다.
- reader output을 `EvidenceUnit`으로 보존한다.
- source locator와 lineage를 잃지 않는다.
- semantic matching 전에 file format 차이를 최대한 흡수한다.

## 해서는 안 되는 일

- reader가 직접 final validation judgment를 만들면 안 됩니다.
- `EvidenceUnit`을 `EvidenceAtom` 또는 X-Y graph edge처럼 사용하면 안 됩니다.
- file extension만 믿고 route를 확정하면 안 됩니다.
- archive, email, Office reader가 external resource나 macro를 실행하면 안 됩니다.
- unsupported binary를 억지로 LLM/VLM에 보내면 안 됩니다.
