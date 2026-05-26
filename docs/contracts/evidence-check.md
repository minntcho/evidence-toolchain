# Evidence Check 계약

`EvidenceCheck`는 declared 또는 requested input과 extracted evidence candidate 사이의 comparison을 기록합니다.

이 contract는 이 프로젝트가 raw extraction 이상임을 보여줍니다. Evidence가 caller가 verify하려던 대상과 어떻게 관련되는지 설명합니다.

## 포함할 수 있는 것

Evidence check는 다음 상태를 말할 수 있습니다.

- supported
- contradicted
- missing
- uncertain
- review needed

Evidence check는 다음을 보존할 수 있습니다.

- declared input reference
- extracted field reference
- normalization note
- unit conversion note
- confidence
- issue reference
- review trigger reference

## 해서는 안 되는 일

Evidence check는 final domain decision을 내리면 안 됩니다.

Claim을 approve하거나, value를 commit하거나, receipt를 issue하거나, audit ledger entry를 쓰거나, publication readiness를 결정하면 안 됩니다. 이것들은 Downstream authority decision입니다.

## Review semantics 규칙

`review needed`는 evidence-processing state입니다. Toolchain이 automated means만으로 check를 충분히 안전하게 resolve하지 못했다는 뜻입니다. Downstream consumer가 반드시 input을 reject해야 한다는 뜻은 아닙니다.
