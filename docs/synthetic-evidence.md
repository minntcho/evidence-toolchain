# Synthetic Evidence Testkit

The synthetic evidence testkit creates development fixtures for the core
document-evidence pipeline.

It exists because this project needs repeatable messy evidence cases:

- clean utility bills
- scanned or rotated bills
- fuel receipts with quantity/price ambiguity
- handwritten meter logs
- future blurred, cropped, low-resolution, or table-risk cases

The testkit is not part of the runtime extraction engine. It is an experiment
surface for tests and developer tooling.

## Boundary

Allowed dependency direction:

```text
tests -> synthetic generator -> generated files
tests -> evidence_toolchain
CLI/dev tool -> synthetic generator -> generated files
```

Forbidden dependency direction:

```text
evidence_toolchain core -> synthetic generator
```

The core package must stay reusable for real evidence documents. Synthetic cases
help test it, but they do not define runtime authority.

## Manifest contract

Each case starts as a manifest under `synthetic/manifests/`.

The manifest separates truth from expected behavior:

```json
{
  "case_id": "utility_bill_basic",
  "document_kind": "utility_bill",
  "ground_truth": {
    "amount": 6.4,
    "unit": "MWh"
  },
  "expected_behavior": {
    "plan_includes": [
      "docling_parse",
      "table_structure_extract",
      "utility_bill_extract"
    ],
    "fallbacks_include": [],
    "issues_include": []
  }
}
```

This separation matters. Some synthetic cases may have known ground truth while
still requiring manual review. For example, a handwritten meter log can contain a
known usage value in the synthetic world, but the expected behavior should still
include a review path.

## Generation

Generate default cases:

```bash
python tools/generate_evidence_cases.py
```

Generate selected cases:

```bash
python tools/generate_evidence_cases.py utility_bill_basic handwritten_meter_log
```

By default, generated case bundles are written to:

```text
tests/fixtures/generated/<case_id>/
+-- evidence.txt
`-- expected.json
```

That directory is ignored by git. Manifests and generator code are the committed
source of truth.

## Current cases

- `utility_bill_basic`
- `scanned_utility_bill_rotated`
- `handwritten_meter_log`
- `receipt_quantity_vs_price`

The default CLI command generates the first three cases so the baseline test run
stays small.
