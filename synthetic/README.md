# Synthetic Evidence Testkit

This directory creates synthetic evidence documents for development and tests.

It is intentionally outside the core extraction package. The generator may
materialize manifests into sample documents and expected behavior files, but the
core package must not import this testkit.

The manifest is the source of truth for each case:

- `ground_truth` describes the synthetic world value.
- `expected_behavior` describes what the toolchain should observe, plan, or flag.

These are separate because some documents have known truth while still requiring
manual review.
