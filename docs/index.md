# Documentation Index

This directory defines the first architecture contract for `evidence-toolchain`.

The repository is an independent evidence document processing engine. Its job is not to validate business claims directly. Its job is to turn messy evidence documents into structured, provenance-carrying reports that other systems can inspect.

## Read first

1. [Architecture](architecture.md)
2. [Evidence Routing](evidence-routing.md)
3. [Capability Registry](capability-registry.md)
4. [Failure Modes](failure-modes.md)
5. [Adapter Boundary](adapter-boundary.md)

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
