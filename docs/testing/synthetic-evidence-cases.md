# Synthetic Evidence Cases

Synthetic evidence cases create repeatable test worlds for development.

They are useful because real evidence documents are messy, private, and hard to
share. Synthetic cases let the repository test routing, extraction contracts,
failure modes, and review triggers without tying the core to one domain.

## Case Anatomy

Each case should separate:

- `ground_truth`: the value in the synthetic world
- `expected_behavior`: what the toolchain should observe, plan, extract, issue,
  or send to review
- generated document: the materialized evidence input
- expected manifest: the materialized comparison target for tests

This separation matters because known synthetic truth does not always mean the
toolchain should automatically trust the document.

## Strong assertions

Strong assertions should check:

- manifest-driven generation
- stable case ids
- generated document existence
- generated expected manifest existence
- `ground_truth` and `expected_behavior` separation
- expected capabilities for baseline cases
- expected issues for degraded cases

## Weak assertions

Weak assertions should avoid freezing:

- exact line wrapping in generated documents
- synthetic business names
- fixture file extensions before real renderers exist
- final downstream schema names
- visual degradation implementation details

## Must not

Synthetic cases must not become core runtime authority.

The core package must not import the synthetic generator. Synthetic manifests may
define test worlds, but Downstream systems own real policy, commit, receipt, and
publication decisions.
