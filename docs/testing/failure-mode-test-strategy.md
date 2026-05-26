# Failure Mode Test Strategy

Failure-mode tests prove that the toolchain preserves uncertainty instead of
turning weak evidence into confident-looking answers.

## Strong assertions

Strong assertions should check that known failure conditions emit structured
issues:

- rotated documents emit `rotated_document`
- handwriting emits `low_trust_handwritten_evidence`
- ambiguous tables emit `ambiguous_table_structure`
- unclear units emit `possible_unit_confusion`
- unreadable or unsupported documents emit blocking issues

Strong assertions should also check that automated fallback or review paths stay
visible when uncertainty remains.

## Weak assertions

Weak assertions should avoid freezing:

- exact OCR confidence numbers
- exact natural-language issue wording
- exact order of non-blocking issues when order does not affect behavior
- one extraction backend's private error codes

## Must not

Failure-mode tests must not convert evidence issues into Downstream rejection
policy.

Allowed:

```text
issue includes low_trust_handwritten_evidence
fallback includes manual_review_request
```

Not allowed:

```text
input is finally rejected
claim is invalid
publication is denied
```
