# 목적과 경계

`evidence-toolchain`은 도메인 중립적인 증거-입력 일관성 엔진입니다.

이 저장소의 일은 caller가 요청하거나 선언한 input을 evidence document에서 관찰하고 추출할 수 있는 내용과 비교할 수 있도록 돕는 것입니다. 값이 어디에서 왔는지, extraction confidence가 어느 정도인지, 무엇이 실패했는지, review가 필요한지를 보존합니다.

이 저장소는 최종 도메인 판단을 내리지 않는다.

## 안정적인 목적

목적은 Downstream domain이 바뀌어도 안정적으로 유지됩니다.

```text
declared or requested input
+ evidence document
-> observation
-> extraction and routing
-> candidate evidence fields
-> consistency, provenance, issue, and review report
```

이 저장소는 intake system, review queue, audit tool, domain validator, compiler, 그 밖에 evidence report가 필요한 workflow에서 유용해야 합니다.

소비자 예시는 예시일 뿐 코어 정체성이 아니다.

## Core가 판단할 수 있는 것

Core는 다음에 답할 수 있습니다.

- 어떤 종류의 evidence document가 관찰되었는가
- 어떤 extraction capability를 시도해야 하는가
- 어떤 candidate field가 발견되었는가
- 각 candidate value가 어디에서 왔는가
- requested value가 supported, contradicted, missing, uncertain 중 어디에 해당하는가
- 어떤 extraction issue 또는 review trigger를 보존해야 하는가

이 답들은 evidence-processing output입니다. 최종 domain approval이 아닙니다.

## Core가 판단해서는 안 되는 것

Core는 다음에 답해서는 안 됩니다.

- business, legal, compliance, scientific, policy claim이 최종적으로 approved인지
- public report를 publish할 수 있는지
- domain-specific value를 authoritative state로 commit해야 하는지
- Downstream system이 receipt, audit ledger entry, governance decision을 발행해야 하는지

이 결정들은 Downstream system의 책임입니다.

## 중립 명명 규칙

코어 용어는 중립적으로 유지한다.

선호하는 core language:

```text
EvidenceDocument
DeclaredInput
RequestedField
ExtractedField
EvidenceObservation
EvidenceToolPlan
EvidenceIssue
EvidenceCheck
EvidenceReport
```

Downstream 또는 consumer-specific language는 optional adapter의 일부라는 점이 분명하지 않다면 core package 밖에 머물러야 합니다.

Downstream language 예시:

```text
claim
policy approval
commit
receipt
audit ledger
regulatory filing
domain verdict
```

## Adapter 경계

Adapter는 `EvidenceReport`를 consumer의 언어로 번역할 수 있지만, consumer의 authority model이 core model을 정의해서는 안 됩니다.

허용:

```text
consumer -> evidence-toolchain
external orchestrator -> evidence-toolchain -> downstream validator
```

피해야 할 형태:

```text
evidence-toolchain core -> specific downstream validator
evidence-toolchain core -> synthetic generator
evidence-toolchain core -> policy or publication authority
```

## 방향성

방향성은 다음과 같습니다.

```text
domain-neutral evidence-input consistency, provenance, uncertainty, and failure reporting
```

미래 기능이 Downstream authority를 가져오지 않으면서 이 목적을 강화한다면 core 가까이에 둘 수 있습니다. 반대로 한 consumer의 policy, product workflow, reporting decision을 core behavior로 만든다면 adapter 또는 Downstream system에 속합니다.
