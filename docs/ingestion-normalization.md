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

### `ImageProfileReader`

ImageProfileReader는 image attachment를 image artifact와 image profile metadata
EvidenceUnit으로 낮춥니다.
Image profile은 OCR 또는 VLM extraction이 아니다.
Width, height, format, mode, EXIF orientation placeholder, aspect ratio 같은
cheap signal만 보존하며, text OCR, meter reading, receipt extraction, handwriting
해석은 별도 capability가 담당해야 합니다.

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
