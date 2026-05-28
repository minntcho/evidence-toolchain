# 실험 manifest

`ExperimentManifest`는 evidence experiment를 다시 실행할 수 있게 만드는 입력 계약입니다.
이 계약은 실제 도구를 호출하기 전에 무엇을 읽고, 어떤 declared claim을 대조하고, 어떤
budget과 capability policy로 investigation을 돌릴지 고정합니다.

## 포함할 수 있는 것

```text
schema_version
experiment_id
bundle_id
attachments
claims
budget
allowed_capabilities
metadata
```

`ExperimentAttachmentSpec`은 manifest 파일 기준 상대 경로나 절대 경로를 보존합니다.
실행 시에는 `AttachmentBundle`과 `RawAttachment`로 낮출 수 있습니다.

`claims`는 `DeclaredClaim` 목록입니다. 이 값은 증거에서 추출된 truth가 아니라, 증거 묶음이
지지하거나 반박해야 하는 입력 X입니다.

`budget`은 `InvestigationBudget` shape를 따릅니다. 기본 controller나 future provider adapter가
무제한 반복하지 않도록 max iteration, model call, new unit, new atom budget을 명시할 수 있습니다.

`allowed_capabilities`는 실험에서 허용된 tool/capability 이름 목록입니다. 이 필드는 capability
selection policy를 기록하기 위한 것이며, 특정 capability가 claim을 support한다고 말하지 않습니다.

## 해서야 하는 일

실험 manifest는 다음 질문에 답해야 합니다.

```text
어떤 파일 묶음을 읽는가?
어떤 declared claim을 검사 대상으로 삼는가?
얼마나 많은 조사 반복과 모델 호출을 허용하는가?
어떤 capability 또는 adapter를 실험에 열어 두는가?
```

이 contract가 있으면 generator가 만든 case, 손으로 만든 fixture, 실제 첨부 묶음을 같은 방식으로
runner에 전달할 수 있습니다.

## 해서는 안 되는 일

`ExperimentManifest`는 ExpectedBehavior oracle은 다음 slice에서 다룹니다.

이 manifest는 다음을 포함하면 안 됩니다.

```text
최종 support/contradict 기대값
Downstream judgment를 encode하지 않는다
policy sufficiency 또는 publication decision
receipt 또는 audit ledger authority
```

즉 manifest는 입력을 고정합니다. trace는 실행 결과를 보존하고, oracle은 테스트 기대값을
분리해서 다룹니다.
