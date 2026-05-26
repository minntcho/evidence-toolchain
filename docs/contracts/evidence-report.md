# Evidence Report 계약

`EvidenceReport`는 toolchain이 내는 통합된 중립 output입니다.

이 report는 여러 consumer에게 유용해야 하지만, 특정 consumer의 authority model이 되어서는 안 됩니다.

## 포함할 수 있는 것

Evidence report는 다음을 포함할 수 있습니다.

- document identity
- observation
- selected tool plan
- capability result summary
- extracted field
- evidence check
- provenance
- confidence
- issue
- unresolved ambiguity
- event timeline
- recommended next action

Recommended next action은 fallback capability를 시도하거나 case를 review로 보내는 일을 포함할 수 있습니다.

## 해서는 안 되는 일

Evidence report는 final Downstream validation judgment를 포함하면 안 됩니다.

Claim을 approve하거나, value를 commit하거나, receipt를 issue하거나, audit ledger decision을 쓰거나, report가 publicly published될 수 있다고 결정하면 안 됩니다.

## Adapter 사용

Adapter는 evidence report를 review task, domain validator payload, dashboard, compiler-specific candidate로 번역할 수 있습니다. 그 번역은 core report가 판단할 권한을 바꾸면 안 됩니다.
