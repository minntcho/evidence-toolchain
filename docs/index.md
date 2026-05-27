# 문서 색인

이 디렉터리는 `evidence-toolchain`의 첫 번째 architecture contract를 정의합니다.

이 저장소는 독립적인 evidence document processing engine입니다. 이 저장소의 일은 business claim을 직접 validate하는 것이 아닙니다. 이 저장소의 일은 지저분한 evidence document를 다른 시스템이 검사할 수 있는 structured, provenance-carrying report로 바꾸는 것입니다.

## 먼저 읽기

1. [목적과 경계](purpose-and-boundaries.md)
2. [아키텍처](architecture.md)
3. [X-Y 증거 연결 아키텍처](evidence-linking-architecture.md)
4. [증거 라우팅](evidence-routing.md)
5. [오케스트레이션 경계](orchestration-boundary.md)
6. [Capability 레지스트리](capability-registry.md)
7. [실패 모드](failure-modes.md)
8. [Adapter 경계](adapter-boundary.md)
9. [첨부 정규화](ingestion-normalization.md)
10. [합성 증거 테스트킷](synthetic-evidence.md)
11. [계약 문서](contracts/README.md)
12. [테스트 전략](testing/README.md)

## 프로젝트 입장

`evidence-toolchain`은 Downstream consumer가 바뀌어도 계속 유용해야 합니다.

가능한 consumer 예시는 다음과 같습니다.

- ESG 또는 LCA validation system
- audit review dashboard
- internal document QA tool
- supplier evidence intake portal
- batch extraction pipeline
- domain-specific compiler 또는 validator

따라서 core package는 downstream-specific authority term을 피해야 합니다. core package는 observation, plan, extraction result, field, provenance, confidence, issue 같은 중립적인 evidence output을 내야 합니다.

## Core 흐름

```text
EvidenceDocument
-> EvidenceObservation
-> EvidenceToolPlan
-> EvidenceCapability calls
-> EvidenceExtractionResult
-> EvidenceReport
```

## 설계 경계

이 저장소는 다음 질문에 답할 수 있습니다.

```text
이 문서는 어떤 종류의 문서인가?
어떤 extraction strategy를 시도해야 하는가?
어떤 field가 발견되었는가?
각 value는 어디에서 왔는가?
extraction은 얼마나 신뢰할 수 있는가?
어떤 issue 또는 failure mode가 관찰되었는가?
```

이 저장소는 다음 질문에 답해서는 안 됩니다.

```text
declared business input이 최종적으로 valid한가?
이 value를 commit할 수 있는가?
이 evidence가 특정 governance policy 아래에서 충분한가?
public report를 publish해야 하는가?
```

이 결정들은 Downstream system의 책임입니다.

## 테스트킷 경계

이 저장소는 개발과 테스트를 위한 합성 증거 테스트킷을 포함합니다. testkit은 가짜 utility bill, receipt, meter log, degraded document, expected behavior manifest를 생성할 수 있습니다. testkit은 core runtime의 일부가 아닙니다.

허용:

```text
tests -> synthetic generator -> generated files
tests -> evidence_toolchain
CLI/dev tool -> synthetic generator -> generated files
```

금지:

```text
evidence_toolchain core -> synthetic generator
```

Synthetic fixture는 routing, extraction, failure-mode behavior를 실험하는 표면입니다. Synthetic fixture는 Downstream validation judgment를 authorize하지 않습니다.
