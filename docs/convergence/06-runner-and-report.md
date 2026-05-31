# Runner and Report

이 문서는 Evidence Convergence Kernel MVP의 runner, loop, trace, report contract를 정의합니다.

이 문서는 runtime code를 추가하지 않고, 다음 구현에서 `run_convergence_cycle`이 따라야 할 contract를 고정합니다.

## Runner purpose

`run_convergence_cycle`은 기존 `run_resolution_cycle`을 대체하지 않습니다.

```text
run_resolution_cycle:
  existing NeedSpec / EvidenceAtom / ResolutionGraph reference path

run_convergence_cycle:
  new CandidateMaskState / MaskPatch / ConvergenceReport MVP path
```

Convergence runner는 claim-relevant candidates가 validated patches를 통해 alignment, contradiction, insufficiency, review 중 하나로 수렴하도록 orchestration합니다.

## Entry point shape

MVP entrypoint는 다음 shape를 목표로 합니다.

```python
def run_convergence_cycle(
    *,
    inventory: EvidenceInventory,
    claims: tuple[DeclaredClaim, ...],
    schema_registry: EvidenceSchemaRegistry,
    capabilities: tuple[PatchProducer, ...],
    run_id: str | None = None,
    max_steps: int = 10,
) -> ConvergenceRun:
    ...
```

MVP implementation may provide defaults, but the contract should remain explicit.

## Inputs

### EvidenceInventory

Existing ingestion output. It contains attachments, artifacts, units, routing decisions, safety decisions, and issues.

Convergence runner does not read files directly.

```text
Readers produce EvidenceInventory.
Convergence consumes EvidenceInventory.
```

### DeclaredClaim

Caller-side X input to compare against evidence candidates.

Convergence runner does not treat `DeclaredClaim` as extracted truth or downstream approval.

### EvidenceSchemaRegistry

Schema registry maps claim type or configured target to an `EvidenceSchema`.

MVP may support a single schema:

```text
utility_usage_record.v1
```

### PatchProducer capabilities

Capabilities propose `MaskPatch` records. They do not mutate candidate state directly.

## ConvergenceRun

Runner output should be a replay-friendly object.

```python
@dataclass(frozen=True)
class ConvergenceRun:
    run_id: str
    inventory: EvidenceInventory
    claims: tuple[DeclaredClaim, ...]
    schema_ids: tuple[str, ...]
    final_board: ConvergenceBoard
    report: ConvergenceReport
    stop_reason: str

    def to_dict(self) -> dict[str, object]: ...
```

The exact fields may evolve, but run output must remain serializable and trace-friendly.

## ConvergenceBoard

`ConvergenceBoard` is the runner state snapshot.

MVP board shape:

```python
@dataclass(frozen=True)
class ConvergenceBoard:
    board_id: str
    run_id: str
    inventory: EvidenceInventory
    claims: tuple[DeclaredClaim, ...]
    candidates: tuple[EvidenceCandidate, ...]
    events: tuple[ConvergenceEvent, ...] = ()
    review_triggers: tuple[ReviewTrigger, ...] = ()
    partial_failures: tuple[PartialFailure, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)
```

Board is not a BundleGraph. It only tracks convergence candidates, events, and report-facing records.

## Runner loop

The MVP loop is:

```text
1. seed candidates
2. compute CandidateGap
3. ask GapScheduler for eligible capabilities
4. run one bounded capability
5. receive MaskPatch
6. validate patch
7. apply valid patch to candidate state
8. record event
9. repeat
10. run simple conflict detection
11. finalize ConvergenceReport
```

Pseudo-code:

```python
board = seed_board(inventory, claims, schema_registry)

for step in range(max_steps):
    scheduled = scheduler.schedule(board, capabilities)
    if not scheduled:
        board = record_no_eligible_capability(board)
        break

    action = scheduled[0]
    patches = action.capability.run(board, action)

    applied_any = False
    for patch in patches:
        validation = validator.validate(board, patch, action.capability.spec)
        if not validation.passed:
            board = record_patch_rejected(board, patch, validation)
            continue
        board = apply_patch(board, patch)
        board = record_patch_applied(board, patch)
        applied_any = True

    if stop_condition(board, applied_any):
        break

board = detect_simple_conflicts(board)
report = finalize(board)
return ConvergenceRun(...)
```

## Step execution policy

MVP runner should execute at most one scheduled capability per candidate step unless a later implementation explicitly supports batching.

This keeps trace simple:

```text
gap -> selected capability -> patch -> validation -> state update
```

Batching can be added later.

## Stop conditions

MVP stop conditions:

```text
all selected candidates finalized
no active gap remains
no eligible capability remains
same scheduled capability repeats without progress
max_steps exhausted
patch validator rejects all proposed patches in a step
simple conflict trigger emitted
blocking failure recorded
```

Stop reason should be explicit.

Example stop reasons:

```text
evidence_converged
candidate_contradicted
candidate_insufficient
candidate_conflict_detected
no_eligible_capability
max_steps_exhausted
no_progress_detected
all_patches_rejected
```

## ConvergenceEvent

MVP runner must record event trace.

```python
@dataclass(frozen=True)
class ConvergenceEvent:
    run_id: str
    sequence: int
    event_type: str
    payload: dict[str, object]
```

Minimum event types:

```text
candidate_seeded
gap_computed
capability_selected
patch_proposed
patch_applied
patch_rejected
review_triggered
candidate_selected
finalized
stopped
```

Trace is required because convergence is patch-based. The report should not hide why state changed.

## Candidate selection in MVP

MVP does not implement a full support set optimizer.

```text
selected_support_set length = 1
```

The selected candidate should be the best candidate according to simple deterministic criteria.

Suggested priority:

```text
1. higher aligned required slot count
2. higher normalized required slot count
3. higher assigned required slot count
4. fewer active gaps
5. fewer issues
6. lower ambiguity
```

The final report keeps an array field to preserve future compatibility.

```json
{
  "selected_support_set": ["cand_001"]
}
```

## Simple conflict detection

After patch loop, MVP should run a simple board-level conflict detector.

Rule:

```text
If two active candidates for the same claim align the same required slot to different values,
raise needs_review_due_to_candidate_conflict.
```

MVP does not resolve precedence.

Do not silently retire the conflicting candidate.

## Partial failures in MVP

MVP only records coarse partial failure treatments.

```text
blocking_failure
nonblocking_failure
unknown_failure
```

Full taxonomy is out of scope.

Future treatments:

```text
benign_failure
covered_failure
latent_defeater_risk
unresolved_relevant_failure
undefeated_defeater
```

## ConvergenceReport

Report is the public-ish output of the MVP convergence cycle.

```python
@dataclass(frozen=True)
class ConvergenceReport:
    run_id: str
    bundle_id: str
    claim_reports: tuple[ClaimConvergenceReport, ...]
    metadata: dict[str, object] = field(default_factory=dict)
```

Claim-level report:

```python
@dataclass(frozen=True)
class ClaimConvergenceReport:
    claim_id: str
    target_schema_id: str
    claim_alignment_status: str
    evidence_convergence_status: str
    selected_support_set: tuple[str, ...]
    candidate_ids: tuple[str, ...]
    unresolved_gaps: tuple[str, ...]
    review_triggers: tuple[ReviewTrigger, ...]
    partial_failures: tuple[PartialFailure, ...]
    downstream_verdict: None = None
    metadata: dict[str, object] = field(default_factory=dict)
```

`downstream_verdict` must remain `None` in core output.

## Status vocabularies

MVP separates alignment status from convergence status.

### claim_alignment_status

```text
supported_direct
supported_after_unit_normalization
contradicted
insufficient
not_evaluated
```

This status describes how selected candidate evidence aligns with the declared claim.

### evidence_convergence_status

```text
evidence_converged
insufficient_missing_required_slots
contradicted_by_selected_candidate
needs_review_due_to_candidate_conflict
insufficient_due_to_blocking_failure
needs_review_unresolved_gap
```

This status describes the kernel's evidence readiness state.

It is not downstream approval.

## Status examples

### Clean support

```json
{
  "claim_alignment_status": "supported_after_unit_normalization",
  "evidence_convergence_status": "evidence_converged",
  "selected_support_set": ["cand_001"],
  "downstream_verdict": null
}
```

### Support exists but conflict remains

```json
{
  "claim_alignment_status": "supported_after_unit_normalization",
  "evidence_convergence_status": "needs_review_due_to_candidate_conflict",
  "selected_support_set": ["cand_001"],
  "review_triggers": [
    {
      "code": "candidate_conflict",
      "severity": "review"
    }
  ],
  "downstream_verdict": null
}
```

### Missing required slots

```json
{
  "claim_alignment_status": "insufficient",
  "evidence_convergence_status": "insufficient_missing_required_slots",
  "selected_support_set": [],
  "unresolved_gaps": ["site", "activity"],
  "downstream_verdict": null
}
```

### Bad patch rejected

```json
{
  "claim_alignment_status": "not_evaluated",
  "evidence_convergence_status": "needs_review_unresolved_gap",
  "review_triggers": [
    {
      "code": "patch_rejected",
      "severity": "review",
      "metadata": {
        "reason": "capability_may_not_set_aligned_mask"
      }
    }
  ],
  "downstream_verdict": null
}
```

## JSON serialization

ConvergenceRun and ConvergenceReport must provide `to_dict()` or equivalent JSON-compatible payloads.

This mirrors the existing experiment trace approach.

A convergence run should be suitable for:

```text
local debugging
synthetic e2e report
adapter acceptance smoke
future expected behavior oracle
```

## Relationship to ExperimentRunTrace

MVP may later embed `ConvergenceRun` in `ExperimentRunTrace.run` because `ExperimentRunTrace` accepts a generic run object as long as it can be serialized.

No change to the existing experiment trace contract is required for this runner/report contract.

## Optional EvidenceResolutionGraph projection

Projection is not part of the initial runtime contract, but report shape should not block it.

Future mapping example:

```text
evidence_converged + supported_after_unit_normalization
-> ClaimResolution.status = supported_after_unit_normalization

insufficient_missing_required_slots
-> ClaimResolution.status = insufficient

needs_review_due_to_candidate_conflict
-> ClaimResolution.status = needs_review
```

Candidate IDs can be carried in graph metadata until a richer atom projection is defined.

## Runner non-goals

MVP runner does not implement:

```text
full support set optimization
source precedence
supersession lifecycle
BundleGraph traversal
LLM autonomous planning
OCR/VLM/email/archive expansion
manual review workflow
downstream policy verdict
```

## First implementation slices

Runner and report should be tested against these first slices:

```text
1. clean support
2. nonblocking issue
3. candidate conflict
4. bad patch rejected
```

The fourth slice is required because it proves `PatchValidator` is the trust boundary.

## Summary

```text
run_convergence_cycle consumes EvidenceInventory.
It seeds candidates.
It advances candidates through scheduled patch producers.
It validates every patch.
It records trace events.
It emits ConvergenceReport.
It does not decide downstream approval.
```
