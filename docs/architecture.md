# 아키텍처

`evidence-toolchain`은 지저분한 증빙 첨부를 도메인 중립적인 evidence state로 낮추고,
Downstream system이 입력 claim과 증거 후보를 비교할 수 있게 준비하는 toolchain입니다.

이 저장소는 최종 validation authority가 아닙니다. 문서를 읽고, 관찰을 보존하고,
의미 후보를 만들고, resolver가 X claim과 Y evidence atom 사이의 관계를 기록할 수 있게
합니다. 최종 정책 판단, 제출 승인, public report publish 여부는 Downstream system의
책임입니다.

## 현재 구현 기준의 큰 흐름

현재 구현 기준의 큰 흐름은 단일 문서 report generator보다 넓습니다.

```text
AttachmentBundle -> RawAttachment -> EvidenceArtifact -> EvidenceUnit -> EvidenceInventory
EvidenceInventory -> EvidenceAtom -> NeedSpec -> NormalizationResult -> EvidenceResolutionGraph
InvestigationState / InvestigationTask / InvestigationTaskResult
```

각 계층의 책임은 다음처럼 나뉩니다.

```text
파일 라우팅은 물리 첨부를 공통 EvidenceInventory로 낮춘다.
Reader는 EvidenceUnit까지만 만든다.
Atomizer는 EvidenceAtom 후보만 만든다.
NeedSpec은 declared X claim을 탐색 가능한 need로 낮춘다.
NormalizationResult는 비교 가능한 재료를 만든다.
Resolver만 support/contradict를 판단한다.
Resolution gap bridge는 resolver gap을 NeedLedgerEntry와 InvestigationTask로 번역한다.
CandidateUnitRetriever는 retrieve_candidate_units task를 EvidenceInventory 안의 EvidenceUnit 후보 선택으로 접지한다.
LocalInvestigationRunner는 주입된 CandidateUnitRetriever로 retrieve_candidate_units를 실행할 수 있다.
LocalInvestigationRunner는 주입된 NormalizationAdapter로 queued normalize_candidate를 실행할 수 있다.
LocalInvestigationRunner는 atomize_unit_cluster가 만든 atom id를 normalize_candidate follow-up task로 이어 줄 수 있다.
Investigation loop는 부족한 단서를 채우기 위한 task를 오케스트레이션한다.
LLM/VLM은 resolver authority가 아니다.
```

## 계층

### Ingestion

Ingestion 계층은 physical attachment를 안전하게 열고 공통 inventory로 낮춥니다.

```text
AttachmentBundle
-> RawAttachment
-> SafetyPolicy
-> FileKindRouter
-> EvidenceArtifact
-> file-specific reader
-> EvidenceUnit
-> EvidenceInventory
```

이 계층은 증빙 의미를 판단하지 않습니다. PDF, image, CSV, XLSX 같은 형식 차이를
흡수하고, route decision, safety decision, source locator, issue를 보존합니다.

### Atomization

Atomization 계층은 `EvidenceUnit`에서 semantic candidate인 `EvidenceAtom`을 만듭니다.

예를 들어 reader가 본 것은 `"사용량 6.4 MWh"` text span이고, atomizer가 만든 것은
`usage_amount` atom입니다. 이 atom은 "사용량 후보처럼 보인다"까지만 말합니다.
특정 X claim을 support한다고 판단하지 않습니다.

### NeedSpec

`DeclaredClaim`은 사용자가 기입했거나 Downstream system이 검사하려는 X claim입니다.
`NeedSpec`은 이 claim을 문서 탐색 가능한 need 목록으로 낮춥니다.

```text
activity_identity
usage_amount
service_period
site_identity
supplier_identity
```

X를 문서에서 직접 문자열 검색하지 않습니다. `6400 kWh`는 문서에서 `6.4 MWh`로
나타날 수 있고, `2025-03`은 `2025년 3월 사용분`으로 나타날 수 있습니다.

### Normalization

`NormalizationResult`는 atom 또는 need를 resolver가 비교 가능한 재료로 낮춥니다.

```text
NormalizedQuantity
NormalizedPeriod
NormalizedDate
NormalizedCurrency
NormalizedIdentifier
```

정규화는 support/contradict 판단이 아닙니다. `6.4 MWh`를 `6400 kWh`로 낮출 수는
있지만, 그 값이 특정 X claim을 지지한다고 판단하는 것은 resolver 책임입니다.

### Resolution

`EvidenceResolutionGraph`는 X claim과 EvidenceAtom/Y 후보 사이의 관계를 기록합니다.
`HardGateResolver`는 v0에서 명시적으로 제공된 `NeedSpec`, `EvidenceAtom`,
`NormalizationResult`를 소비해 `usage_amount`, `service_period`, currency reject,
missing required need에 대한 hard-gate edge와 claim resolution을 만듭니다.

이 resolver는 normalizer를 자동 호출하지 않으며, aggregation, derivation, soft score,
site/supplier alias 판단은 아직 수행하지 않습니다.

### Investigation

Investigation 계층은 부족한 단서를 채우기 위한 framework-neutral state와 task contract를
제공합니다.

```text
InvestigationState
InvestigationTask
InvestigationTaskResult
InvestigationBudget
NeedLedgerEntry
LLMPlannerPort
VLMObserverPort
LLMAtomizerPort
LLMNormalizerPort
LocalInvestigationRunner
```

`ResolutionGapPlanner`는 `EvidenceResolutionGraph`의 missing/contradict gap을
`NeedLedgerEntry`와 `InvestigationTask` agenda로 번역합니다. 이 bridge는 resolver를 다시
실행하지 않고, runner나 provider도 호출하지 않습니다.

`CandidateUnitRetriever`는 `retrieve_candidate_units` task와 `EvidenceInventory`,
`NeedSpec`을 받아 관련 있어 보이는 기존 `EvidenceUnit` id만 고릅니다. 이 결과는 다음
`atomize_unit_cluster` task의 `target_unit_ids`로 넘길 수 있습니다. 이 단계는
EvidenceAtom, NormalizationResult, ResolutionEdge를 만들지 않습니다.

`LocalInvestigationRunner`는 fake/model port를 호출할 수 있지만, provider SDK나 LangGraph를
core에 묶지 않습니다. 모델 output atom은 core vocabulary, `allowed_atom_types`,
provenance guardrail을 통과해야 state에 들어갑니다.
또한 `CandidateUnitRetriever`가 주입되면 `retrieve_candidate_units` task를 실행하고,
선택된 unit이 있을 때 follow-up `atomize_unit_cluster` task를 agenda 앞에 추가합니다.
`NormalizationAdapter`가 주입되면 agenda에 올라온 `normalize_candidate` task를 실행해
선택된 `EvidenceAtom` 후보를 `NormalizationResult`로 낮출 수 있습니다. 이 단계도
`ResolutionEdge`나 `ClaimResolution.status`를 만들지 않습니다.
또한 normalizer가 주입된 runner는 `atomize_unit_cluster`가 accepted atom을 만들었을 때
그 atom id를 대상으로 하는 follow-up `normalize_candidate` task를 agenda 앞에 추가할 수
있습니다. 이 bridge는 normalization task를 계획할 뿐이고, resolver를 실행하지 않습니다.

## Compatibility document workflow

기존 `EvidenceDocument -> EvidenceReport` 경로는 compatibility document workflow입니다.
이 경로는 단일 문서 관찰, planning, capability 실행, report emission을 실험하고 보존하는
표면입니다.

```text
EvidenceDocument
-> EvidenceObservation
-> EvidenceToolPlan
-> EvidenceCapability calls
-> EvidenceReport
```

이 경로도 여전히 유효하지만, 새 X-Y evidence linking 계층의 최종 authority는 아닙니다.
`EvidenceReport`는 관찰과 issue를 보존하는 output이고, X claim과 atom 사이의
support/contradict 판정은 `EvidenceResolutionGraph` 계층에서 다뤄야 합니다.

## 현재 구현된 것

현재 repository는 다음 contract와 baseline adapter를 제공합니다.

```text
AttachmentBundle
RawAttachment
RouteDecision
SafetyDecision
EvidenceArtifact
EvidenceUnit
EvidenceInventory
EvidenceAtom
AtomizerResult
SimpleTextAtomizer
DeclaredClaim
Need
NeedSpec
derive_need_spec
NormalizationAdapter
NormalizationResult
DeterministicNormalizer
ResolutionEdge
ClaimResolution
EvidenceResolutionGraph
HardGateResolver
ResolutionGapPlan
ResolutionGapPlanner
EvidenceUnitRetrievalResult
CandidateUnitRetriever
InvestigationState
InvestigationTask
InvestigationTaskResult
LLM/VLM model port protocols
Fake model adapters
LocalInvestigationRunner
```

Reader baseline은 plain text, CSV/TSV, PDF profile, PDF text/word extraction,
image profile, XLSX sheet/cell inventory를 지원합니다. Archive, Office, email full reader는
아직 본격 구현 범위 밖입니다.

## 아직 구현하지 않은 것

다음은 architecture target이지만 아직 닫힌 구현 축이 아닙니다.

```text
automatic end-to-end EvidenceInventory -> ResolutionGraph orchestration
soft score resolver
aggregation support solver
derivation support solver
support set selection
site/supplier alias normalizer
ambiguous period normalizer
real LLM/VLM provider adapter
LangGraph adapter
OCR/VLM interrogation loop
archive recursive expansion
Office/email full reader
manual review queue output
```

## 독립성 규칙

Core module은 Downstream validator를 import하면 안 됩니다.

허용되는 dependency direction은 다음과 같습니다.

```text
downstream app -> evidence-toolchain
```

또는:

```text
external orchestrator
  -> evidence-toolchain
  -> downstream validator
```

반대 방향은 금지합니다.

```text
evidence-toolchain -> downstream validator
```

Adapter는 core package 밖에 둘 수 있습니다. Adapter는 evidence-toolchain output을 다른
system의 claim, hazard, review format으로 번역할 수 있지만, adapter가 core model을
정의해서는 안 됩니다.

## 신뢰 태도

Extraction은 validation이 아닙니다. Normalization도 validation이 아닙니다. Model observation도
validation이 아닙니다.

이 프로젝트의 유용한 output은 값 하나가 아니라, 그 값이 어디에서 왔는지, 어떤 tool이
만들었는지, 무엇이 실패했는지, 무엇이 아직 uncertain한지까지 포함하는 evidence state입니다.
