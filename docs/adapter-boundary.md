# Adapter 경계

Core package는 독립적으로 유지되어야 합니다.

Adapter는 `EvidenceReport`를 Downstream system의 언어로 번역할 수 있습니다. 하지만 Downstream concept가 core model을 정의해서는 안 됩니다.

## 의존 방향

선호:

```text
consumer -> evidence-toolchain
```

허용:

```text
orchestrator
  -> evidence-toolchain
  -> downstream validator
```

피해야 할 방향:

```text
evidence-toolchain -> specific downstream validator
```

## Core 언어

Core term은 중립적으로 유지되어야 합니다.

Compatibility document workflow의 core language:

```text
EvidenceDocument
EvidenceObservation
EvidenceToolPlan
EvidenceCapability
ExtractedField
EvidenceIssue
EvidenceReport
```

현재 X-Y evidence linking workflow의 core language:

```text
AttachmentBundle
EvidenceInventory
EvidenceAtom
DeclaredClaim
NeedSpec
NormalizationResult
EvidenceResolutionGraph
ResolutionEdge
ClaimResolution
InvestigationState
InvestigationTask
InvestigationTaskResult
```

이 용어들은 document processing, extraction, evidence candidate, comparison material,
그리고 resolver가 만든 evidence relation record를 설명합니다.

### Core resolver 언어

현재 core는 `DeclaredClaim`을 가질 수 있습니다. 여기서 claim은 Downstream policy claim이
아니라, evidence bundle과 비교할 caller-side X input입니다.

현재 core resolver는 `EvidenceResolutionGraph`, `ResolutionEdge`, `ClaimResolution`으로
다음 같은 resolver의 evidence relation status를 기록할 수 있습니다.

```text
supports
supports_after_unit_normalization
contradicts
rejected_for_need
needs_review
insufficient
```

이 status는 document evidence가 declared X input과 어떤 관계인지 보존하는 record입니다.
이것은 final approval, publication, legal sufficiency, audit ledger commit 같은 최종 domain
authority verdict가 아닙니다.

## Downstream 언어

Downstream system은 더 강한 용어를 사용할 수 있습니다.

```text
domain claim approval
policy sufficiency threshold
hazard
obligation
review queue
policy decision
commit
receipt
audit ledger
regulatory filing
publication verdict
```

이 용어들은 repository가 나중에 clearly separate optional adapter package를 정의하지 않는 한
core package 밖에 속합니다.

## Adapter 예시

### Generic JSON adapter 예시

```text
EvidenceReport -> JSON
```

API, CLI, batch job, dashboard를 위한 adapter입니다.

### Review UI adapter 예시

```text
EvidenceReport -> review task
```

Human review queue를 위한 adapter입니다.

### Domain validator adapter 예시

```text
EvidenceResolutionGraph -> domain-specific declared-input comparison payload
```

LCA, ESG, ERP, audit system을 위한 adapter입니다.

### Compiler adapter 예시

```text
EvidenceReport -> compiler-specific evidence claim candidates
```

이 adapter는 허용되지만 optional이어야 합니다. Core package는 compiler를 import하면 안 됩니다.

## 경계 규칙

Core는 다음처럼 말할 수 있습니다.

```text
The document contains an extracted field candidate:
- name: electricity_usage
- value: 6.4
- unit: MWh
- page: 1
- bbox: ...
- confidence: 0.91
- issue: needs_unit_normalization
```

Core resolver는 다음처럼 evidence relation을 기록할 수도 있습니다.

```text
DeclaredClaim x_001 has a ResolutionEdge to atom_usage_001:
- relation: supports_after_unit_normalization
- basis: 6.4 MWh = 6400 kWh
- need_id: usage_amount
```

Downstream adapter는 이것을 다음처럼 번역할 수 있습니다.

```text
Evidence package for the electricity usage review workflow.
```

Downstream validator는 그 다음 declared input과 비교할 수 있습니다.

```text
6400 kWh == 6.4 MWh
```

Core resolver는 evidence relation status를 만들 수 있지만, Core는 최종 domain validation
status나 최종 domain authority verdict를 결정하면 안 됩니다. 예를 들어
"문서 증거가 X 사용량을 단위 정규화 후 지지한다"는 core record가 될 수 있습니다.
"이 사업장 신고값을 승인한다", "공시해도 된다", "감사 ledger에 commit한다"는
Downstream authority verdict입니다.

## 이 경계가 중요한 이유

Core가 너무 이른 시점에 한 Downstream system의 authority model을 배우면, reusable engine이 아니라 plugin이 됩니다.

이 저장소는 다음 용도에 유용해야 합니다.

- direct CLI extraction
- standalone API
- review dashboard
- LCA/ESG intake
- invoice processing
- internal audit tooling
- future compiler 또는 validator

Adapter를 core 밖에 두면 이 선택지가 보존됩니다.
