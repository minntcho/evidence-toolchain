# Purpose and Boundaries

`evidence-toolchain` is a domain-neutral evidence-input consistency engine.

Its job is to help a caller compare requested or declared inputs with what can
be observed and extracted from evidence documents. It preserves where values
came from, how confident the extraction is, what failed, and whether review is
needed.

It does not make final domain decisions.

## Stable Purpose

The purpose is stable even when downstream domains change:

```text
declared or requested input
+ evidence document
-> observation
-> extraction and routing
-> candidate evidence fields
-> consistency, provenance, issue, and review report
```

The repository should stay useful for many consumers: intake systems, review
queues, audit tools, domain validators, compilers, and other workflows that need
evidence reports.

Consumer examples are examples, not core identity.

## What The Core May Decide

The core may answer:

- what kind of evidence document was observed
- what extraction capabilities should be attempted
- what candidate fields were found
- where each candidate value came from
- whether requested values are supported, contradicted, missing, or uncertain
- what extraction issues or review triggers should be preserved

These answers are evidence-processing outputs. They are not final domain
approval.

## What The Core Must Not Decide

The core must not answer:

- whether a business, legal, compliance, scientific, or policy claim is finally
  approved
- whether a public report may be published
- whether a domain-specific value should be committed as authoritative state
- whether a downstream system should issue receipts, audit ledger entries, or
  governance decisions

Those decisions belong to downstream systems.

## Neutral Naming Rule

Core terms stay neutral.

Preferred core language:

```text
EvidenceDocument
DeclaredInput
RequestedField
ExtractedField
EvidenceObservation
EvidenceToolPlan
EvidenceIssue
EvidenceCheck
EvidenceReport
```

Downstream or consumer-specific language should stay outside the core package
unless it is clearly part of an optional adapter.

Examples of downstream language:

```text
claim
policy approval
commit
receipt
audit ledger
regulatory filing
domain verdict
```

## Adapter Boundary

Adapters may translate an `EvidenceReport` into a consumer's language, but the
consumer's authority model must not define the core model.

Allowed:

```text
consumer -> evidence-toolchain
external orchestrator -> evidence-toolchain -> downstream validator
```

Avoid:

```text
evidence-toolchain core -> specific downstream validator
evidence-toolchain core -> synthetic generator
evidence-toolchain core -> policy or publication authority
```

## North Star

The north star is:

```text
domain-neutral evidence-input consistency, provenance, uncertainty, and failure reporting
```

If a future feature strengthens that purpose without taking downstream authority,
it belongs near the core. If it turns one consumer's policy, product workflow, or
reporting decision into core behavior, it belongs in an adapter or downstream
system.
