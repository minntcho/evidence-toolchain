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

## Core language

Core term은 중립적으로 유지되어야 합니다.

```text
EvidenceDocument
EvidenceObservation
EvidenceToolPlan
EvidenceCapability
EvidenceExtractionResult
ExtractedField
EvidenceIssue
EvidenceReport
```

이 용어들은 document processing과 extraction을 설명합니다.

## Downstream language

Downstream system은 더 강한 용어를 사용할 수 있습니다.

```text
claim
support
contradiction
hazard
obligation
review queue
policy decision
commit
receipt
audit ledger
```

이 용어들은 repository가 나중에 clearly separate optional adapter package를 정의하지 않는 한 core package 밖에 속합니다.

## Adapter 예시

### Generic JSON adapter

```text
EvidenceReport -> JSON
```

API, CLI, batch job, dashboard를 위한 adapter입니다.

### Review UI adapter

```text
EvidenceReport -> review task
```

Human review queue를 위한 adapter입니다.

### Domain validator adapter

```text
EvidenceReport -> domain-specific declared-input comparison payload
```

LCA, ESG, ERP, audit system을 위한 adapter입니다.

### Compiler adapter

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

Downstream adapter는 이것을 다음처럼 번역할 수 있습니다.

```text
Evidence claim candidate for electricity usage.
```

Downstream validator는 그 다음 declared input과 비교할 수 있습니다.

```text
6400 kWh == 6.4 MWh
```

하지만 Core는 최종 validation status를 결정하면 안 됩니다.

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
