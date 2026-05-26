# Extracted Field 계약

`ExtractedField`는 evidence material에서 발견된 candidate value입니다.

이 값은 candidate evidence이지 final truth가 아닙니다.

## 포함할 수 있는 것

Extracted field는 다음을 담을 수 있습니다.

- field name
- value
- unit
- normalized value
- page 또는 image reference
- bounding box
- text span
- table cell reference
- source capability
- confidence
- issue reference

같은 requested field에 대해 여러 candidate가 있을 수 있습니다.

## 해서는 안 되는 일

Extracted field는 Downstream input이 finally valid하다고 판단하면 안 됩니다.

Competing candidate, confidence, provenance, issue를 보존하지 않은 채 한 value를 골라 ambiguity를 숨기면 안 됩니다.

## Provenance 규칙

Capability가 provenance를 제공할 수 있다면 모든 extracted field는 어디에서 왔는지 보존해야 합니다. Provenance를 recover할 수 없다면, value가 fully grounded된 척하지 말고 issue를 담아야 합니다.
