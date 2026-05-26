# 실패 모드 테스트 전략

Failure-mode test는 toolchain이 약한 evidence를 confident-looking answer로 바꾸지 않고 uncertainty를 보존한다는 점을 증명합니다.

## 강하게 assert할 것

Strong assertion은 known failure condition이 structured issue를 emitted하는지 확인해야 합니다.

- rotated document는 `rotated_document`를 emitted한다
- handwriting은 `low_trust_handwritten_evidence`를 emitted한다
- ambiguous table은 `ambiguous_table_structure`를 emitted한다
- unclear unit은 `possible_unit_confusion`을 emitted한다
- unreadable 또는 unsupported document는 blocking issue를 emitted한다

Strong assertion은 uncertainty가 남아 있을 때 automated fallback 또는 review path가 visible하게 유지되는지도 확인해야 합니다.

## freeze하지 말아야 할 것

Weak assertion은 다음을 freeze하지 말아야 합니다.

- exact OCR confidence number
- exact natural-language issue wording
- order가 behavior에 영향을 주지 않을 때 non-blocking issue의 exact order
- 특정 extraction backend의 private error code

## 해서는 안 되는 일

Failure-mode test는 evidence issue를 Downstream rejection policy로 바꾸면 안 됩니다.

허용:

```text
issue includes low_trust_handwritten_evidence
fallback includes manual_review_request
```

금지:

```text
input is finally rejected
claim is invalid
publication is denied
```
