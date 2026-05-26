# Adapter Boundary

The core package should stay independent.

Adapters may translate `EvidenceReport` into a downstream system's language, but downstream concepts must not define the core model.

## Dependency direction

Preferred:

```text
consumer -> evidence-toolchain
```

Also acceptable:

```text
orchestrator
  -> evidence-toolchain
  -> downstream validator
```

Avoid:

```text
evidence-toolchain -> specific downstream validator
```

## Core language

Core terms should remain neutral:

```text
EvidenceDocument
EvidenceObservation
EvidenceToolPlan
EvidenceCapability
EvidenceExtractionResult
ExtractedField
EvidenceIssue
EvidenceReport
```

These terms describe document processing and extraction.

## Downstream language

Downstream systems may use stronger terms:

```text
claim
support
contradiction
hazard
obligation
review queue
policy decision
commit
receipt
audit ledger
```

Those terms belong outside the core package unless the repository later defines a clearly separate optional adapter package.

## Adapter examples

### Generic JSON adapter

```text
EvidenceReport -> JSON
```

For APIs, CLIs, batch jobs, and dashboards.

### Review UI adapter

```text
EvidenceReport -> review task
```

For human review queues.

### Domain validator adapter

```text
EvidenceReport -> domain-specific declared-input comparison payload
```

For LCA, ESG, ERP, or audit systems.

### Compiler adapter

```text
EvidenceReport -> compiler-specific evidence claim candidates
```

This kind of adapter is allowed, but it must remain optional. The core package should not import the compiler.

## Boundary rule

The core may say:

```text
The document contains an extracted field candidate:
- name: electricity_usage
- value: 6.4
- unit: MWh
- page: 1
- bbox: ...
- confidence: 0.91
- issue: needs_unit_normalization
```

A downstream adapter may translate that into:

```text
Evidence claim candidate for electricity usage.
```

A downstream validator may then compare it with declared input:

```text
6400 kWh == 6.4 MWh
```

But the core should not decide the final validation status.

## Why this matters

If the core learns one downstream system's authority model too early, it becomes a plugin instead of a reusable engine.

The repository should be useful for:

- direct CLI extraction
- standalone APIs
- review dashboards
- LCA/ESG intake
- invoice processing
- internal audit tooling
- future compilers or validators

Keeping adapters outside the core preserves that option.
