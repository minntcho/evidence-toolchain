# Router and Planner Test Strategy

Router and planner tests prove that the toolchain looks at evidence condition
before choosing capabilities.

The goal is not to freeze every implementation detail. The goal is to preserve
the observable behavior that makes the project an evidence-processing engine
rather than a single-parser wrapper.

## Strong assertions

Strong assertions should check that:

- born-digital documents can select structure-aware parsing
- scanned documents can select OCR
- receipt-like documents can select receipt extraction
- handwritten logs can select handwriting and review paths
- meter photos can select visual and meter-reading paths
- fallback capabilities remain visible when risk remains
- plans preserve the reason each selected capability was chosen

These assertions protect the observation -> planning -> extraction boundary.

## Weak assertions

Weak assertions should avoid freezing:

- private helper function names
- exact internal planner rule order
- whether a future planner is rule-based, model-assisted, or hybrid
- exact prompt or classifier implementation details
- downstream adapter shape

## Must not

Planner tests must not assert final Downstream approval.

A planner may decide that OCR, table extraction, or manual review is needed. It
must not decide that a domain claim is finally valid, committed, published, or
policy-approved.
