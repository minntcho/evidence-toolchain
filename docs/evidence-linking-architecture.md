# X-Y 증거 연결 아키텍처

증빙 처리는 문서 파싱이 아니라 X-Y evidence linking 문제입니다.

사용자가 제출한 입력 항목은 문서에서 찾아야 할 단어가 아니라 검증 대상 claim입니다.
문서 묶음 안에서 발견되는 값, 라벨, 날짜, 표 행, 계량기 수치, 공급자명 같은 단서는
그 claim을 지지하거나 반박하거나 아직 판단할 수 없게 만드는 evidence candidate입니다.

따라서 이 저장소의 장기 구조는 다음 문제를 풉니다.

```text
Declared X claim
+ AttachmentBundle
-> EvidenceInventory
-> EvidenceAtom / Y 후보
-> EvidenceResolutionGraph
```

핵심은 `X`를 문서에서 직접 검색하지 않는 것입니다. `X`를 먼저 `NeedSpec`으로 내리고,
문서에서 관찰된 원시 단서를 `EvidenceUnit`으로 보존한 뒤, 의미 후보인 `EvidenceAtom`으로 올리고,
마지막 resolver가 X와 atom 사이의 관계를 판단합니다.

정규화는 이 사이의 별도 계층입니다.

```text
EvidenceAtom / Need
-> NormalizationAdapter
-> NormalizationResult
-> Resolver
```

정규화는 support/contradict 판단이 아니다.
정규화는 값, 단위, 기간, 날짜, 금액, 식별자를 비교 가능한 재료로 바꿀 뿐입니다.

## 책임 경계

### X

`X`는 사용자가 기입했거나 Downstream system이 검사하려는 declared claim입니다.

예시는 다음과 같습니다.

```json
{
  "x_id": "x_001",
  "site": "OCH-01",
  "period": "2025-03",
  "activity": "electricity",
  "amount": 6400,
  "unit": "kWh"
}
```

이 값은 추출 결과가 아닙니다. 이 값은 evidence bundle이 지지하거나 반박해야 하는 대상입니다.

### NeedSpec

`NeedSpec`은 X를 문서 탐색 가능한 단서 요구사항으로 낮춘 것입니다.

`6400 kWh`라는 문자열만 찾으면 안 됩니다. 문서에는 `6.4 MWh`, `전력 사용량`,
`2025년 3월 사용분`, `오창 1공장`처럼 다른 표현으로 나타날 수 있습니다.

`NeedSpec`은 다음 질문을 분리합니다.

```text
activity identity가 맞는가?
usage amount가 단위 변환 후 맞는가?
service period가 맞는가?
site identity가 맞는가?
supplier 또는 source가 보조 context를 제공하는가?
청구금액, 납부기한, 전월사용량 같은 disqualifier가 아닌가?
```

`NeedSpec`은 아직 구현된 contract가 아닙니다. 하지만 다음 resolver 계층이 따라야 할
입력 언어로 예약합니다.

### EvidenceUnit

`EvidenceUnit`은 reader가 본 raw observation입니다.

예시는 text span, word box, table, table cell, image metadata, PDF page metadata입니다.
Reader는 EvidenceUnit까지만 만든다.

```text
"사용량 6.4 MWh" text span
"6.4" word box
"MWh" word box
spreadsheet C2 table_cell
image width/height metadata
```

`EvidenceUnit`은 의미 후보가 아닙니다. 어디에서 무엇을 봤는지와 provenance를 잃지 않기 위한
원시 관찰 단위입니다.

### EvidenceAtom

`EvidenceAtom`은 `EvidenceUnit`에서 해석된 semantic evidence candidate입니다.
Atomizer는 EvidenceAtom 후보만 만든다.

예시는 다음과 같습니다.

```json
{
  "atom_id": "atom_001",
  "atom_type": "usage_amount",
  "text": "사용량 6.4 MWh",
  "label": "사용량",
  "value": 6.4,
  "unit": "MWh",
  "source_unit_ids": ["unit_pdf_page_1_text"],
  "source_artifact_ids": ["artifact_pdf_page_1"],
  "producer": "regex_atomizer",
  "confidence": null
}
```

Atom은 "이 단서가 usage amount처럼 보인다"를 말할 수 있습니다. 하지만
"이 atom이 x_001을 지지한다"는 판단은 하지 않습니다.

`normalized`가 있더라도 best-effort helper입니다. 단위 호환성, tolerance, hard gate,
support 여부는 resolver가 다시 판단해야 합니다.

### NormalizationResult

`NormalizationResult`는 atom, need, claim을 resolver가 비교 가능한 형태로 낮춘 결과입니다.

v0 normalized value contract는 다음 shape를 포함합니다.

```text
NormalizedQuantity
NormalizedPeriod
NormalizedDate
NormalizedCurrency
NormalizedIdentifier
```

`NormalizedQuantity`는 value, unit, dimension, source value/unit을 보존합니다.
`NormalizedPeriod`는 start date, end date, granularity를 보존합니다.
`NormalizedDate`는 date와 bill date, payment due date 같은 optional role을 보존합니다.
`NormalizedCurrency`는 currency amount를 usage quantity와 분리해서 보존합니다.
`NormalizedIdentifier`는 site, supplier, meter id 같은 식별자 후보를 보존합니다.

`NormalizationAdapter`는 tool 또는 deterministic normalizer가 구현해야 하는 interface입니다.
`normalize_atom_value`는 EvidenceAtom 후보를 normalized comparison material로 낮추고,
`normalize_claim_need`는 NeedSpec의 개별 need를 normalized comparison material로 낮춥니다.

`DeterministicNormalizer`는 v0 pure-python baseline adapter입니다.
명확한 `usage_amount`, `currency_amount`, `service_period`, `date` atom과
`usage_amount`, `service_period` need를 `NormalizationResult`로 낮춥니다.
DeterministicNormalizer는 optional/reference adapter입니다.
core flow는 normalizer를 자동 호출하지 않는다.

즉 ingestion, reader, atomizer, NeedSpec, ResolutionGraph contract는
`DeterministicNormalizer`를 직접 실행하지 않습니다. NormalizationAdapter는 orchestrator,
resolver, 또는 별도 tool adapter가 명시적으로 선택해서 호출해야 합니다.

지원 범위는 작게 유지합니다.

```text
energy: Wh, kWh, MWh, GWh -> kWh
volume: L, m3, m³ -> L
mass: kg, t, tonne -> kg
currency: KRW, USD, EUR, 원
period: YYYY-MM 또는 YYYY-MM-DD ~ YYYY-MM-DD
date role: 납부기한, 청구일, 발행일 같은 명확한 label
```

DeterministicNormalizer는 resolver가 아니다.
예를 들어 `6.4 MWh`를 `6400 kWh`로 낮출 수는 있지만,
그 값이 특정 X claim을 support한다고 판단하지 않습니다.

정규화 계층은 다음을 하지 않습니다.

```text
이 atom이 X를 support한다고 판단하지 않는다.
currency_amount를 usage_amount로 승격하지 않는다.
site alias가 정책상 충분한지 판단하지 않는다.
period overlap이 X를 만족한다고 확정하지 않는다.
```

site/supplier alias와 ambiguous period는 deterministic scope 밖입니다.
이 영역은 catalog, policy, LLM/VLM 보조 normalizer, 또는 manual review와 결합될 수 있지만,
그 경우에도 output은 `NormalizationAdapter` contract를 따라야 합니다.

### EvidenceResolutionGraph

`EvidenceResolutionGraph`는 X claim과 EvidenceAtom/Y 후보 사이의 관계 그래프입니다.
Resolver만 support/contradict를 판단한다.

가능한 edge는 다음과 같습니다.

```text
supports
supports_after_unit_normalization
supports_by_aggregation
supports_by_derivation
contradicts
contextualizes
rejected_for_need
needs_review
```

그래프는 하나의 X를 하나의 Y에 매칭하는 단순 구조가 아닙니다.

```text
X 하나를 Y 하나가 직접 지지할 수 있다.
X 하나를 Y 여러 개가 합산해서 지지할 수 있다.
Y 하나가 여러 X의 context가 될 수 있다.
Y가 X를 반박할 수 있다.
Y가 애매해서 review queue로 갈 수 있다.
```

## 라우팅 계층

File routing은 증빙 의미를 판단하지 않는다.

파일 라우팅은 물리 첨부를 안전하게 열 수 있는지, 어떤 reader가 적절한지, 어떤 artifact로
낮출지를 결정합니다.

```text
AttachmentBundle
-> RawAttachment
-> SafetyPolicy
-> FileKindRouter
-> EvidenceArtifact
-> File-specific Reader
-> EvidenceUnit
-> EvidenceInventory
```

Semantic routing은 그 다음입니다.

```text
EvidenceInventory
-> Atomizer
-> EvidenceAtom / Y 후보
-> Resolver
-> EvidenceResolutionGraph
```

이 경계를 섞으면 안 됩니다.

```text
PDF reader가 "전기 사용량 support"를 만들면 안 된다.
Image profile reader가 "계량기 사진이 X를 증명한다"를 말하면 안 된다.
Spreadsheet reader가 "이 행은 최종 검증 통과"를 말하면 안 된다.
```

Reader는 관찰하고, atomizer는 의미 후보를 만들고, resolver는 관계를 판단합니다.

## LLM/VLM 위치

LLM/VLM은 authority가 아니라 adapter입니다.
구체적인 조사 루프 경계는 [조사 루프 경계](investigation-loop-boundary.md)에 따릅니다.

LLM이나 VLM은 다음 일을 도울 수 있습니다.

```text
페이지 또는 영역에서 missing clue를 찾는다.
이미지 crop에서 text 또는 meter reading 후보를 읽는다.
table row가 어떤 의미 후보인지 제안한다.
NeedSpec에 맞는 follow-up extraction task를 제안한다.
```

하지만 LLM/VLM 호출 결과가 곧 최종 support 판정은 아닙니다.
LLM/VLM output도 `EvidenceUnit` 또는 `EvidenceAtom`으로 내려와 provenance, producer,
confidence, issue를 보존해야 합니다. 그 다음 resolver가 같은 hard gate와 graph rule로 판단합니다.

LLM/VLM normalizer도 NormalizationAdapter contract를 따라야 합니다.
LLM/VLM이 모호한 날짜, alias, 단위 표현을 보정하더라도 결과는 `NormalizationResult`로
기록되어야 하며, resolver edge를 직접 만들면 안 됩니다.

## Resolver 판단 방식

Resolver는 hard gate와 soft score를 분리해야 합니다.

Hard gate 예시는 다음과 같습니다.

```text
activity type이 호환되는가?
period가 service period 기준으로 맞는가?
unit dimension이 맞는가?
값이 단위 변환 후 tolerance 안에 들어오는가?
currency amount를 usage amount로 착각하지 않았는가?
청구일, 납부기한, 전월사용량을 사용기간 또는 당월 사용량으로 착각하지 않았는가?
```

Soft score 예시는 다음과 같습니다.

```text
같은 page 또는 같은 table row에 있는가?
label이 값 근처에 있는가?
site alias가 맞는가?
supplier document class가 적절한가?
OCR/VLM confidence가 낮지 않은가?
```

최종 상태는 다음처럼 확장될 수 있습니다.

```text
SUPPORTED_DIRECT
SUPPORTED_AFTER_UNIT_NORMALIZATION
SUPPORTED_BY_AGGREGATION
SUPPORTED_BY_DERIVATION
CONTRADICTED
PARTIAL_SUPPORT
AMBIGUOUS
INSUFFICIENT
NEEDS_REVIEW
```

## 현재 구현된 것

현재 repository는 ingestion normalization, atom candidate contract,
X claim을 NeedSpec으로 낮추는 baseline contract, 그리고 X-Y graph record contract를
갖고 있습니다.

```text
NormalizationAdapter
NormalizationResult
NormalizedQuantity
NormalizedPeriod
NormalizedDate
NormalizedCurrency
NormalizedIdentifier
DeterministicNormalizer
DeclaredClaim
Need
NeedSpec
NeedType
ResolutionRelation
ResolutionStatus
ResolutionEdge
ClaimResolution
EvidenceResolutionGraph
HardGateResolver
EvidenceResolutionRun
SimpleUnitClusterAtomizer
run_resolution_cycle
AttachmentBundle
RawAttachment
RouteDecision
SafetyDecision
EvidenceArtifact
EvidenceUnit
EvidenceInventory
EvidenceAtom
AtomizerResult
```

지원되는 reader와 helper는 다음 범위입니다.

```text
UnsupportedReader
PlainTextReader
DelimitedTableReader
PdfProfileReader
PdfPlumberExtractReader
ImageProfileReader
SpreadsheetReader
merge_evidence_inventories
ingest_bundle
SimpleTextAtomizer
derive_need_spec
```

이 구현들은 아직 X-Y support graph를 만들지 않습니다. 특히 `SimpleTextAtomizer`는
`usage_amount`, `currency_amount`, `service_period`, `date` 같은 명확한 text/table-cell
후보만 올리는 deterministic baseline입니다.

`DeclaredClaim`은 사용자가 기입했거나 Downstream system이 검사하려는 X claim을
보존합니다. `derive_need_spec`은 `activity`, `amount`, `unit`, `period`, `site`,
`supplier` 같은 공통 field를 `activity_identity`, `usage_amount`, `service_period`,
`site_identity`, `supplier_identity` need로 낮춥니다. 이 함수는 검색 요구사항을 만들 뿐
EvidenceAtom retrieval이나 support 판정은 수행하지 않습니다.

`ResolutionEdge`는 `x_id`, `atom_id`, `need_id`, `relation`, `basis`, `confidence`,
`issues`를 보존하는 graph edge record입니다. `ClaimResolution`은 하나의 X claim에 대한
status, edge ids, supporting/rejected atom ids, missing need ids를 보존합니다.
`EvidenceResolutionGraph`는 bundle 안의 claim ids, atom ids, edge, resolution을 묶습니다.
`ResolutionRelation`과 `ResolutionStatus`는 v0 string vocabulary입니다.

`HardGateResolver`는 명시적으로 제공된 `NeedSpec`, `EvidenceAtom`, `NormalizationResult`를
소비해 `usage_amount`, `service_period`, currency reject, missing required need에 대한
v0 hard-gate edge와 claim resolution을 만듭니다. 이 resolver는 normalizer를 자동 호출하지
않으며, aggregation, derivation, soft score, alias 판단은 수행하지 않습니다.

`run_resolution_cycle`은 이 부품들을 provider 없이 실제 순서로 연결하는 deterministic
reference controller입니다. 이 경로는 `NeedSpec` 생성, need normalization, 초기 missing
graph, gap planning, candidate unit retrieval, unit-cluster atomization, atom normalization,
draft graph refresh를 한 번에 실연합니다. 그래도 support/contradict edge는
`HardGateResolver`가 만들고, reader/atomizer/normalizer/runner는 resolver authority가
아닙니다.

정규화 계약도 마찬가지입니다. 현재 구현은 `NormalizationResult`와 normalized value shape,
`NormalizationAdapter` interface, 그리고 명확한 atom/need만 처리하는
`DeterministicNormalizer` v0를 제공합니다. 이 adapter는 비교 재료만 만들고
resolver edge를 생성하지 않습니다. DeterministicNormalizer는 optional/reference adapter이며,
기본 ingestion/atomization/resolution contract가 자동 호출하는 runtime step이 아닙니다.

## 아직 구현하지 않은 것

다음은 architecture target이지만 아직 구현된 runtime contract가 아닙니다.

```text
soft score resolver
aggregation support solver
derivation support solver
support set selection
site/supplier alias normalizer
ambiguous period normalizer
provider/model-backed normalization orchestration
LLM/VLM atomizer adapter
OCR/VLM interrogation loop
archive recursive expansion
Office/email full reader
manual review queue output
```

다음 구현 PR은 이 문서의 경계를 따라 작게 나뉘어야 합니다.

```text
EvidenceInventory -> NeedSpec 없는 simple resolver로 가지 않는다.
먼저 X model과 NeedSpec을 정의한다.
그 다음 atom retrieval과 ResolutionGraph edge contract를 연다.
그 다음 hard gate resolver를 작게 붙이고, soft score, support set solving, review queue를 붙인다.
```

## 설계 원칙

```text
File routing normalizes physical attachments into EvidenceInventory.
Semantic routing converts EvidenceInventory into EvidenceAtoms.
Resolution links declared X claims to EvidenceAtoms.
```

한국어로는 다음과 같습니다.

```text
파일 라우팅은 물리 첨부를 공통 inventory로 낮춘다.
의미 라우팅은 inventory를 증거 후보 atom으로 바꾼다.
resolution은 입력 X와 atom Y를 연결한다.
```

이 원칙 때문에 PDF, 이미지, XLSX, CSV, 나중의 archive, Office, email reader는
서로 다른 구현을 가져도 후속 X-Y matching 계층에는 같은 언어로 들어올 수 있습니다.
