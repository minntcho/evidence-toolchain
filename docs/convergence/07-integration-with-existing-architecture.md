# Integration with Existing Architecture

이 문서는 Evidence Convergence Kernel이 기존 `evidence-toolchain` architecture와 어떻게 공존해야 하는지 정의합니다.

Convergence Kernel은 replacement가 아닙니다. 기존 ingestion, atomization, normalization, resolution, investigation contracts를 유지하면서 그 옆에 얇은 candidate/mask/patch loop를 추가합니다.

## Integration principle

```text
Do not replace the existing X-Y resolution path.
Add a convergence path beside it.
Bridge only where useful.
```

한국어로는:

```text
기존 X-Y resolution path를 대체하지 않는다.
그 옆에 convergence path를 추가한다.
필요한 지점에서만 bridge한다.
```

## Existing path

현재 architecture의 주요 흐름은 다음과 같습니다.

```text
AttachmentBundle
-> RawAttachment
-> SafetyPolicy
-> FileKindRouter
-> EvidenceArtifact
-> File-specific Reader
-> EvidenceUnit
-> EvidenceInventory
-> EvidenceAtom
-> NeedSpec
-> NormalizationResult
-> EvidenceResolutionGraph
```

또한 deterministic reference controller인 `run_resolution_cycle`은 다음 계층을 묶습니다.

```text
EvidenceInventory
+ DeclaredClaim
-> NeedSpec
-> initial EvidenceResolutionGraph
-> ResolutionGapPlanner
-> LocalInvestigationRunner
-> CandidateUnitRetriever
-> SimpleUnitClusterAtomizer
-> DeterministicNormalizer
-> HardGateResolver
-> final EvidenceResolutionGraph
```

이 흐름은 계속 유지합니다.

## New convergence path

Convergence MVP path는 다음과 같습니다.

```text
EvidenceInventory
+ DeclaredClaim
+ EvidenceSchemaRegistry
+ PatchProducer capabilities
-> ConvergenceBoard
-> CandidateGap
-> GapScheduler
-> MaskPatch
-> PatchValidator
-> ConvergenceReport
```

이 path는 `EvidenceAtom` 중심이 아니라 `EvidenceCandidate` 중심입니다.

## Side-by-side entrypoints

MVP는 기존 entrypoint를 건드리지 않습니다.

```text
run_resolution_cycle      # existing reference X-Y resolution path
run_convergence_cycle     # future convergence kernel MVP path
```

`run_convergence_cycle`은 `run_resolution_cycle`을 내부에서 호출하지 않아도 됩니다. 반대로 `run_resolution_cycle`도 convergence kernel을 알 필요가 없습니다.

두 entrypoint는 같은 ingestion output을 공유할 수 있습니다.

```text
EvidenceInventory
  -> run_resolution_cycle
  -> run_convergence_cycle
```

## Shared input: EvidenceInventory

Convergence Kernel은 새 observation store를 만들지 않습니다.

```text
MVP observation = EvidenceUnit
MVP observation store = EvidenceInventory
```

This is the primary integration point.

Reader implementations such as CSV, XLSX, PDF profile, PDF text, image profile, and plain text readers already produce `EvidenceInventory`. Convergence should consume that existing output.

## EvidenceUnit usage

`EvidenceUnit` remains raw observation.

Convergence capabilities may read:

```text
unit_id
artifact_id
unit_type
producer
text
value
bbox
locator
confidence
metadata
```

They must not reinterpret `EvidenceUnit` as final evidence.

Example:

```text
EvidenceUnit:
  unit_type = table_cell
  text = "6.4"
  locator = {"sheet": "Summary", "cell": "D2", "header": "Usage (MWh)"}

ConvergenceCandidate slot assignment:
  quantity = 6.4
  unit = MWh
  source_refs = xlsx:Summary!D2, xlsx:Summary!D1
```

The assignment happens inside convergence as a patch, not inside the reader.

## EvidenceAtom relationship

`EvidenceAtom` remains the semantic candidate object for the existing X-Y resolution path.

Convergence MVP does not make `EvidenceAtom` the central object.

```text
EvidenceAtom:
  field-level semantic candidate in existing resolution path

EvidenceCandidate:
  schema-shaped claim-relevant candidate in convergence path
```

Future bridge options:

```text
EvidenceCandidate -> flattened EvidenceAtom[]
ConvergenceReport -> EvidenceResolutionGraph
EvidenceResolutionGraph -> initial ConvergenceBoard hints
```

These bridges are optional and should not be required for MVP.

## NeedSpec relationship

`NeedSpec` remains part of the existing resolution path.

Convergence MVP may use `DeclaredClaim` fields directly with `EvidenceSchemaRegistry`.

Future integration may derive schema focus from `NeedSpec`, but the initial convergence integration does not require that.

Recommended boundary:

```text
NeedSpec:
  search/resolution need language

EvidenceSchema:
  convergence candidate slot language
```

They can be mapped later but should not be collapsed prematurely.

## Normalization relationship

Existing `DeterministicNormalizer` can inform convergence normalizer behavior, but convergence MVP should expose normalization through MaskPatch.

Existing path:

```text
EvidenceAtom / Need
-> NormalizationResult
```

Convergence path:

```text
EvidenceCandidate assigned slot
-> deterministic_normalizer PatchProducer
-> MaskPatch(set_normalized_mask, normalized_payload_updates)
```

The conceptual responsibility remains the same:

```text
Normalization makes comparison material.
It does not decide downstream policy.
```

## Resolution relationship

Existing `HardGateResolver` creates `EvidenceResolutionGraph` edges and claim resolutions.

Convergence MVP creates `ConvergenceReport`.

These are different outputs.

```text
EvidenceResolutionGraph:
  X claim to EvidenceAtom relation graph

ConvergenceReport:
  claim-level candidate convergence report
```

Future projection can map convergence outputs into resolution graph shape for compatibility.

## Optional projection to EvidenceResolutionGraph

Projection is useful because existing experiment expected behavior checks inspect `final_graph.resolutions`.

Initial projection can be simple.

```text
evidence_converged + supported_direct
-> ClaimResolution.status = supported_direct

evidence_converged + supported_after_unit_normalization
-> ClaimResolution.status = supported_after_unit_normalization

insufficient_missing_required_slots
-> ClaimResolution.status = insufficient

needs_review_due_to_candidate_conflict
-> ClaimResolution.status = needs_review

contradicted_by_selected_candidate
-> ClaimResolution.status = contradicted
```

Candidate IDs can be stored in metadata until richer atom projection exists.

Projection must not fabricate downstream approval.

## ExperimentRunTrace relationship

`ExperimentRunTrace` can already wrap a generic run object that exposes `to_dict()`.

Therefore convergence implementation should make `ConvergenceRun.to_dict()` JSON-compatible.

Potential future usage:

```text
ExperimentManifest
-> EvidenceInventory
-> run_convergence_cycle
-> ExperimentRunTrace(run=ConvergenceRun)
```

No existing experiment trace contract needs to change for the initial convergence integration.

## Adapter acceptance relationship

Existing adapter acceptance flows target reader and resolution adapters.

Convergence can later get its own acceptance helper.

Potential future helper:

```text
run_convergence_adapter_acceptance(
  inventory,
  claims,
  patch_producers,
  expected_convergence_behavior,
)
```

This should be additive. It must not break existing `run_basic_resolution_adapter_acceptance` or `run_reader_resolution_adapter_acceptance`.

## Synthetic e2e relationship

Existing synthetic e2e runner writes runtime reports for reader behavior.

Future convergence e2e can add a new report layer:

```text
evidence-synthetic run
-> build input artifacts
-> verify artifacts
-> runtime reader bridge
-> convergence run
-> _synthetic/convergence_report.json
```

The runtime must not read `_synthetic` oracle files as evidence.

## Package namespace

Convergence code should live under:

```text
src/evidence_toolchain/convergence/
```

Do not create top-level packages named `capabilities`, `runtime`, or `reports`, because top-level modules with these names already exist.

Suggested future layout:

```text
src/evidence_toolchain/convergence/
  __init__.py
  schemas.py
  candidates.py
  patches.py
  validator.py
  scheduler.py
  board.py
  capabilities.py
  runner.py
  reports.py
  projection.py
```

## Import boundary

Initial convergence implementation should import existing core contracts:

```text
EvidenceInventory
EvidenceUnit
DeclaredClaim
EvidenceIssue
```

It should not import synthetic artifact factory code.

It should not import downstream validators.

It should not require provider SDKs.

## Downstream boundary

ConvergenceReport is not a downstream verdict.

It must not answer:

```text
Can this value be committed?
Can this report be published?
Is this policy sufficient?
Should an audit receipt be issued?
```

It may answer:

```text
Did the selected candidate converge?
Which candidate was selected?
Which slots aligned?
Which gaps remain?
Which review triggers exist?
Which patches were rejected?
```

## Migration strategy

Implementation should happen in small additive slices:

```text
1. Add convergence package skeleton.
2. Add schema/candidate/mask/patch dataclasses.
3. Add PatchValidator invariants.
4. Add simple runner with fake capabilities.
5. Add CSV/XLSX based vertical slices.
6. Add optional projection later.
```

Do not move existing classes into convergence package during MVP.

## Non-goals

Integration batches must not introduce:

```text
large refactor of run_resolution_cycle
replacement of EvidenceAtom
replacement of NeedSpec
changes to reader contracts
changes to synthetic generator contracts
provider SDK dependency
Downstream policy adapter
```

## Summary

```text
Reuse EvidenceInventory.
Keep run_resolution_cycle.
Add run_convergence_cycle beside it.
Keep bridge optional.
Keep downstream authority out.
```
