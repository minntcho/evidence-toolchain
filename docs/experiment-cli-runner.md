# Experiment CLI runner

The `run-experiment` command is a local demo runner for the experiment harness.
It connects the current deterministic path without adding provider or
orchestration authority:

```text
ExperimentManifest
-> AttachmentBundle
-> EvidenceInventory
-> run_resolution_cycle
-> ExperimentRunTrace
-> optional ExpectedBehaviorReport
```

## What It Does

The command reads an `ExperimentManifest`, resolves relative attachment paths
from the manifest directory, ingests the attachments, runs the deterministic
resolution cycle, and writes an `ExperimentRunTrace` JSON artifact.

If an expected behavior file is supplied, the same trace is compared with
`ExperimentExpectedBehavior` and an `ExpectedBehaviorReport` is written.

Example:

```powershell
evidence-toolchain run-experiment .\experiment.json `
  --trace-out .\out\trace.json `
  --expected .\expected.json `
  --expected-report-out .\out\expected-report.json
```

The command exits with `0` when no expected behavior is supplied or when the
expected behavior passes. It exits with `1` when expected behavior comparison
fails after still writing the trace and comparison report.

## What It Does Not Do

The CLI runner does not call real provider tools, does not select external
framework orchestration, and does not decide downstream policy sufficiency.
It is a fast local harness for proving that manifest, ingestion, resolution,
trace, and oracle contracts can be wired together before real adapters are
attached.
