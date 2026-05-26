# Evidence Document Contract

An `EvidenceDocument` is the neutral wrapper around source material before any
downstream judgment.

It describes what was received and what is known about that material. It does not
describe whether the material is sufficient under any policy.

## May

An evidence document may carry:

- document id
- file name
- media type
- file hash
- source metadata
- page or image count
- document text when available
- caller-provided target fields
- observed document-kind hints

## Must not

An evidence document must not carry final validation state.

It must not say that a claim is approved, that a declared value is committed, or
that a Downstream policy has been satisfied.

## Relationship To Observation

Observation is derived from the evidence document. The document stores input
identity and material facts; observation records condition, quality, and routing
signals discovered by the toolchain.
