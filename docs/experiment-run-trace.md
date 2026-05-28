# 실행 trace

`ExperimentRunTrace`는 하나의 evidence experiment 실행 결과를 replay-friendly JSON artifact로
보존합니다. 입력을 정의하는 `ExperimentManifest`와 실제 실행 결과인 `EvidenceResolutionRun`을
함께 담되, 성공/실패 기대값을 판정하지는 않습니다.

## 포함할 수 있는 것

```text
schema_version
experiment_id
manifest
run
metadata
```

`manifest`는 실험 입력입니다. 어떤 attachment와 declared claim, budget, capability policy를
사용했는지 보존합니다.

`run`은 `EvidenceResolutionRun.to_dict()` payload입니다. 현재 deterministic reference cycle은
다음 주요 field를 남깁니다.

```text
initial_graph
gap_plan
investigation_state
final_graph
stop_reason
```

이 payload는 어디서 정보가 추가되었는지 확인하기 위한 실행 기록입니다. 예를 들어
`initial_graph`가 missing need를 드러내고, `gap_plan`이 task agenda를 만들고,
`investigation_state`가 completed task, produced atom, normalization을 보존하며,
`final_graph`가 resolver 재실행 결과를 남깁니다.

## 해서야 하는 일

실행 trace는 다음 질문에 답해야 합니다.

```text
이 실험은 어떤 manifest에서 시작했는가?
초기 resolver graph는 어떤 gap을 발견했는가?
어떤 investigation task가 실행되었는가?
어떤 EvidenceAtom과 NormalizationResult가 추가되었는가?
최종 draft graph는 어떤 상태인가?
```

이 정보는 generator와 실제 adapter를 붙였을 때 디버깅 표면이 됩니다.

## 해서는 안 되는 일

`ExperimentRunTrace`는 ExpectedBehavior oracle이 아니다.

이 trace는 다음을 해서는 안 됩니다.

```text
expected status와 실제 status를 비교하지 않는다.
Downstream verdict가 아니다.
policy sufficiency 또는 publishability를 결정하지 않는다.
trace 존재 자체를 validation success로 취급하지 않는다.
```

비교와 판정은 다음 slice의 expected behavior oracle 또는 Downstream adapter가 맡아야 합니다.
