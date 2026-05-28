# Synthetic E2E Runner Contract

This document defines the v0 program boundary for the synthetic artifact factory.
The goal is not broader carrier coverage. The goal is one executable line from
scenario authoring to runtime report.

```bash
evidence-synthetic run scenarios/erp_export_basic.yaml --out generated
```

## V0 Scope

V0 supports only these carriers:

```text
csv
xlsx
```

The following carriers and capabilities are deferred even if some local proof
code already exists:

```text
pdf
scanned_pdf
eml
image
OCR
VLM
```

## Command Boundary

`evidence-synthetic build` creates deterministic artifacts and synthetic
metadata.

`evidence-synthetic verify` checks generated artifact contracts without running
evidence-toolchain readers.

`evidence-synthetic run` performs build, verify, runtime reader execution, and
predicate comparison.

## Build Output

The build command writes this shape:

```text
generated/<case_id>/
  input/
    <artifact files>

  expected/
    expected_predicates.json

  _synthetic/
    scenario_spec.yaml
    scenario_ir.json
    bundle_plan.json
    tool_plan.json
    manifest.json
    carrier_trace.json
    verification_report.json
```

The expected predicate file is addressed as
`expected/expected_predicates.json`.

`verification_report.json` is generation-side evidence. It may read `_synthetic/`
because it verifies the factory output.

## Runtime Boundary

The runtime command creates a separate sandbox:

```text
runtime_tmp/input
```

The reader runtime sees input/ only. It must not read `_synthetic/`, latent
oracle files, render plans, or carrier traces.

`run` reaches the evidence-toolchain reader through a separate runtime bridge;
the synthetic artifact factory package remains generation and verification code.

The runtime command writes:

```text
generated/<case_id>/
  _synthetic/
    runtime_report.json
```

## Expected Predicates

V0 predicates are intentionally small:

```json
{
  "predicates": [
    {
      "id": "artifact_ingested",
      "artifact_id": "export",
      "expected": true
    },
    {
      "id": "minimum_observation_count",
      "artifact_id": "export",
      "min_count": 1
    }
  ]
}
```

They prove that the artifact was created, routed through a reader, and produced
at least one observation. They do not encode claim resolution, conflict handling,
manual review semantics, or downstream policy sufficiency.

## Runtime Report

The runtime report records reader and predicate outcomes:

```json
{
  "case_id": "erp_export_basic",
  "status": "passed",
  "artifacts": [
    {
      "artifact_id": "export",
      "path": "input/export.csv",
      "carrier": "csv",
      "reader": "delimited_table_reader",
      "reader_status": "ingested",
      "observation_count": 3,
      "issue_count": 0
    }
  ],
  "predicates": [
    {
      "id": "artifact_ingested",
      "artifact_id": "export",
      "status": "passed",
      "message": "export was ingested by delimited_table_reader."
    },
    {
      "id": "minimum_observation_count",
      "artifact_id": "export",
      "status": "passed",
      "actual": 3,
      "expected_min": 1,
      "message": "export produced 3 observations; expected at least 1."
    }
  ],
  "links": {
    "manifest": "_synthetic/manifest.json",
    "carrier_trace": "_synthetic/carrier_trace.json",
    "verification_report": "_synthetic/verification_report.json"
  }
}
```

## Phase 1 Close Condition

Phase 1 closes when csv and xlsx can run through:

```text
Scenario YAML
-> ScenarioSpec validation
-> ToolPlan compilation
-> artifact build
-> artifact verification
-> runtime reader over input/ only
-> expected predicate comparison
-> runtime_report.json
```
