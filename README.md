# evidence-toolchain

`evidence-toolchain` is an independent document-evidence processing engine.

It observes messy evidence documents, chooses an extraction strategy, runs document tools, and emits a neutral `EvidenceReport` that downstream systems can consume.

The core idea is simple:

```text
Evidence document
-> observe document condition
-> plan tool usage
-> run extraction capabilities
-> consolidate extracted fields
-> emit EvidenceReport with provenance and issues
```

This repository is intentionally not tied to any single validator, LCA platform, ESG compiler, or downstream product.

## What this project should do

- Inspect evidence documents before choosing tools.
- Route documents to suitable capabilities such as document parsing, OCR, table extraction, vision extraction, handwriting extraction, barcode/QR reading, or manual review.
- Extract candidate fields with page, bounding box, confidence, source span, and tool provenance where possible.
- Preserve failure modes as structured issues instead of hiding them behind a best-effort answer.
- Produce neutral outputs that can be used by many consumers.

## What this project should not do

- It should not be the final validation authority.
- It should not decide whether a business claim is true, compliant, or publishable.
- It should not issue governance decisions, commit receipts, audit ledgers, or policy verdicts.
- It should not make the core package depend on a specific downstream project.

A downstream system may decide that extracted evidence supports, contradicts, or fails to support a declared input. This project only prepares the evidence side of that judgment.

## Initial documentation

- [Documentation index](docs/index.md)
- [Architecture](docs/architecture.md)
- [Evidence routing](docs/evidence-routing.md)
- [Capability registry](docs/capability-registry.md)
- [Failure modes](docs/failure-modes.md)
- [Adapter boundary](docs/adapter-boundary.md)

## North star

The project should become a reusable evidence-document front end:

```text
receipts / invoices / utility bills / scans / handwritten logs / meter photos
-> evidence-toolchain
-> EvidenceReport
-> downstream validator, audit UI, review workflow, or domain compiler
```

The safest design stance is:

```text
Tools extract.
Reports preserve.
Adapters translate.
Downstream systems judge.
```
