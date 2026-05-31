# ExpectedBehavior oracle

`ExperimentExpectedBehavior`는 `ExperimentRunTrace`를 테스트 기대값과 비교하기 위한
oracle input입니다. 이 oracle은 test expectation을 검증하는 도구이며, runtime authority가 아니다.

## 포함할 수 있는 것

```text
ExperimentExpectedBehavior
ExpectedClaimResolution
ExpectedClaimConvergence
ExpectedBehaviorCheck
ExpectedBehaviorReport
```

`ExpectedClaimResolution`은 claim 단위 기대값을 표현합니다.

```text
x_id
status
missing_need_ids
supporting_atom_types
rejected_atom_types
```

`evaluate_expected_behavior`는 `ExperimentRunTrace`의 final graph와 investigation atoms를
읽어 다음 check를 만들 수 있습니다.

```text
claim_status
missing_need_ids
supporting_atom_types
rejected_atom_types
```

결과는 `ExpectedBehaviorReport`입니다. report는 각 check의 expected/actual 값과 passed
여부를 보존합니다.

## 해서야 하는 일

ExpectedBehavior oracle은 다음 질문에 답해야 합니다.

```text
실험 trace가 fixture가 기대한 claim resolution status를 만들었는가?
필수 need가 여전히 missing인지 아닌지 기대와 맞는가?
supporting atom type과 rejected atom type이 기대와 맞는가?
```

이 비교는 generator fixture와 adapter 실험을 regression test로 만들기 위한 것입니다.

## 해서는 안 되는 일

ExpectedBehavior oracle은 다음을 해서는 안 됩니다.

```text
Downstream policy sufficiency를 판단하지 않는다.
public report publish 여부를 결정하지 않는다.
receipt 또는 audit authority가 되지 않는다.
runtime trace를 수정하지 않는다.
```

이 oracle은 테스트의 기대값 비교기입니다. 같은 trace라도 Downstream system은 다른 policy
아래에서 다른 review workflow를 선택할 수 있습니다.

## Convergence expected behavior

`ExpectedClaimConvergence` represents expected values for a convergence report
claim view.

```text
x_id
claim_alignment_status
evidence_convergence_status
selected_support_set
review_trigger_codes
partial_failure_codes
unresolved_gaps
```

For convergence traces, `evaluate_expected_behavior` reads
`run.report.claim_reports` and creates these checks.

```text
claim_alignment_status
evidence_convergence_status
selected_support_set
review_trigger_codes
partial_failure_codes
unresolved_gaps
```

`claim_resolutions` remains the expectation surface for the resolution graph.
`claim_convergences` is the expectation surface for the convergence report.
The oracle does not compare `downstream_verdict`.
