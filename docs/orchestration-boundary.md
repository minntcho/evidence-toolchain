# Orchestration Boundary

`evidence-toolchain` should stay useful even when the workflow framework
changes.

The core package defines orchestration-neutral evidence semantics. It should
describe what happened to an evidence document, what remains pending, what tools
ran, what failed, and what report was emitted. It should not make LangGraph,
Prefect, Temporal, or any other runner DSL the source of core meaning.

The default design stance is:

```text
core = orchestration-neutral evidence semantics
local runner = reference execution path
framework adapters = optional execution wrappers
```

## Why this boundary exists

LLM/VLM-assisted routing may be the first semantic observation step, but it is
not the final validation authority. A framework may help run observation,
schema validation, retries, capability execution, fallback selection, and human
review handoff. It must still emit bounded evidence records.

Frameworks may orchestrate the workflow. They must not define the core evidence
schema, decide Downstream validity, or turn framework state into the public
contract.

## Core runtime records

The core runtime contract should be serializable and framework independent.

### `EvidenceRunState`

`EvidenceRunState` is the current snapshot of an evidence processing run.

It should eventually carry:

- `run_id`
- input `EvidenceDocument`
- optional preflight summary
- current `EvidenceObservation`
- current `EvidenceToolPlan`
- completed `EvidenceStep` records
- pending `EvidenceStep` records
- `EvidenceToolResult` records
- issues
- interrupts or review requests
- final `EvidenceReport` when emitted

The state should be serializable so it can be stored by a local test runner, a
checkpoint database, a framework saver, or a durable workflow engine without
changing core semantics.

### `EvidenceEvent`

`EvidenceEvent` is an append-only record of what happened during a run.

Initial event types should include:

- `document_received`
- `preflight_completed`
- `observation_created`
- `plan_created`
- `capability_started`
- `capability_completed`
- `capability_failed`
- `fallback_selected`
- `review_requested`
- `review_resumed`
- `report_emitted`

Events are useful for replay, debugging, audit review, and comparing runner
implementations. Event history may explain a run, but it must not become a
separate source of Downstream approval.

### `EvidenceStep`

`EvidenceStep` is a planned or executed unit of work.

Examples:

- run preflight probe
- create LLM/VLM observation
- execute `docling_parse`
- execute `ocr_extract`
- execute `table_structure_extract`
- request manual review
- emit report

Steps should reference capability names and routing reasons instead of embedding
framework node ids as core concepts.

### `EvidenceToolResult`

`EvidenceToolResult` is the framework-neutral output of a capability.

It should preserve:

- capability name
- capability version when available
- input document or page reference
- status
- extracted text, tables, fields, spans, or regions where available
- confidence metadata
- warnings
- errors
- produced artifacts

Tool results should be JSON-compatible so multiple runners can compare behavior
without depending on framework-specific result objects.

## Runtime ports

The core should define small neutral ports before adopting framework-specific
implementations.

### `CapabilityRunner`

Runs a capability against an `EvidenceRunState` and returns an
`EvidenceToolResult`.

Capabilities should be idempotent where possible. If a capability writes an
artifact, the artifact id or path should be stable enough for retry and resume.

### `CheckpointStore`

Stores and loads `EvidenceRunState`.

Local execution may store checkpoints in memory or files. LangGraph may use a
saver. Temporal may use workflow history. Prefect may use task state. The core
should only depend on the checkpoint contract.

### `EventSink`

Records append-only `EvidenceEvent` entries.

An event sink may write to memory, JSONL, a database, or an observability tool.
The event payload should remain framework-neutral.

### `ArtifactStore`

Stores generated artifacts such as page thumbnails, OCR text, structured
tables, or intermediate JSON outputs.

The core should reference stored artifacts by neutral ids or paths, not by
framework task handles.

### `ReviewQueue`

Represents human review interrupts and resume input.

Manual review is part of the evidence toolchain, but review input must be
recorded as neutral state and events so local and framework runners can resume
the same run contract.

### `RetryPolicy`

Describes retry limits, timeout behavior, and fallback eligibility.

Retry policy should be explicit enough that a local runner and a durable
workflow runner can make comparable decisions.

## Runner roles

### Local runner

The local runner is the reference implementation.

It should execute the same evidence semantics without requiring an orchestration
framework. Tests should prove that the local runner can process generated case
bundles and emit the expected events, state transitions, and report shape.

### Framework adapters

Framework adapters may implement the same runner contract with different
execution guarantees.

Examples:

- LangGraph adapter for graph-shaped agentic routing and repair loops
- Prefect adapter for batch-oriented extraction jobs
- Temporal adapter for durable long-running workflows

Adapters may add scheduling, persistence, parallelism, tracing, and worker
deployment behavior. They must emit the same core records.

## Framework portability

Framework replacement becomes cheaper when the workflow is expressed through
core records and ports instead of a framework DSL.

Hard parts will still remain:

- checkpoint behavior
- retry policy
- parallel capability execution
- human interrupt and resume semantics
- timeout handling
- cache and artifact store integration
- observability and tracing
- deployment and worker model

Those concerns should be isolated behind runtime ports. Switching frameworks
should be a runner adapter change, not an evidence semantics rewrite.

## Testing expectations

Tests may strongly assert:

- `EvidenceRunState` is serializable
- `EvidenceEvent` is append-only
- tool results are JSON-compatible
- local runner output matches expected generated case bundles
- framework adapters emit the same core event and report contracts

Tests should avoid freezing:

- framework node names
- framework checkpoint internals
- exact task scheduling order when the plan permits parallel execution
- vendor-specific tracing metadata
- deployment topology

## Must not

The core package must not make a framework DSL the authoritative workflow
definition.

Framework adapters must not redefine `EvidenceObservation`, `EvidenceToolPlan`,
`EvidenceToolResult`, or `EvidenceReport`.

LLM/VLM routing may propose observations and plans. It must not produce final
Downstream validation judgments. Final business, policy, audit, publication, or
commit decisions belong outside the core package.
