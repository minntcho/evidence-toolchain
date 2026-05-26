# Documentation Index

This directory defines the first architecture contract for `evidence-toolchain`.

The repository is an independent evidence document processing engine. Its job is not to validate business claims directly. Its job is to turn messy evidence documents into structured, provenance-carrying reports that other systems can inspect.

## Read first

1. [Purpose and Boundaries](purpose-and-boundaries.md)
2. [Architecture](architecture.md)
3. [Evidence Routing](evidence-routing.md)
4. [Capability Registry](capability-registry.md)
5. [Failure Modes](failure-modes.md)
6. [Adapter Boundary](adapter-boundary.md)
7. [Synthetic Evidence Testkit](synthetic-evidence.md)
8. [Contract Documents](contracts/README.md)
9. [Testing Strategy](testing/README.md)

## Project stance

`evidence-toolchain` should stay useful even when the downstream consumer changes.

Examples of possible consumers:

- ESG or LCA validation systems
- audit review dashboards
- internal document QA tools
- supplier evidence intake portals
- batch extraction pipelines
- domain-specific compilers or validators

The core package should therefore avoid downstream-specific authority terms. It should emit neutral evidence outputs such as observations, plans, extraction results, fields, provenance, confidence, and issues.

## Core flow

```text
EvidenceDocument
-> EvidenceObservation
-> EvidenceToolPlan
-> EvidenceCapability calls
-> EvidenceExtractionResult
-> EvidenceReport
```

## Design boundary

The repository may answer:

```text
What kind of document is this?
What extraction strategy should be attempted?
What fields were found?
Where did each value come from?
How reliable was the extraction?
What issues or failure modes were observed?
```

The repository should not answer:

```text
Is the declared business input finally valid?
Can this value be committed?
Is this evidence sufficient under a specific governance policy?
Should a public report be published?
```

Those decisions belong to downstream systems.

## Testkit boundary

The repository includes a synthetic evidence testkit for development and tests.
The testkit may generate fake utility bills, receipts, meter logs, degraded
documents, and expected behavior manifests. It is not part of the core runtime.

Allowed:

```text
tests -> synthetic generator -> generated files
tests -> evidence_toolchain
CLI/dev tool -> synthetic generator -> generated files
```

Not allowed:

```text
evidence_toolchain core -> synthetic generator
```

Synthetic fixtures are an experiment surface for routing, extraction, and
failure-mode behavior. They do not authorize downstream validation judgments.
