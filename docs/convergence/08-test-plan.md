# Evidence Convergence Kernel Test Plan

이 문서는 Evidence Convergence Kernel MVP의 초기 테스트 계획을 정의합니다.

이 문서는 테스트 코드를 추가하지 않고, 다음 implementation 작업들이 어떤 behavior를 증명해야 하는지 고정합니다.

## Test philosophy

MVP 테스트의 목표는 full bundle reasoning을 검증하는 것이 아닙니다.

목표는 다음 kernel invariant를 검증하는 것입니다.

```text
EvidenceInventory를 입력으로 받을 수 있다.
Candidate를 seed할 수 있다.
CandidateGap을 계산할 수 있다.
GapScheduler가 bounded capability를 고를 수 있다.
Capability가 MaskPatch만 제안한다.
PatchValidator가 invalid patch를 막는다.
Valid patch만 candidate state를 전진시킨다.
ConvergenceReport가 alignment/convergence status를 분리해서 낸다.
```

## Test layers

MVP test suite should be organized in layers.

```text
contract tests
unit tests
runner tests
report tests
optional projection tests
synthetic e2e tests
```

## Contract tests

Contract tests verify dataclass and invariant behavior.

Targets:

```text
SlotDef
EvidenceSchema
EvidenceCandidate
CandidateGap
MaskPatch
CapabilitySpec
PatchValidator
ConvergenceReport
```

Examples:

```text
schema masks are computed from SlotDef
provenance_present_mask is computed from source_refs_by_slot
CandidateGap separates missing/unassigned/unnormalized/unaligned
PatchValidator rejects out-of-schema bits
PatchValidator rejects capability permission violations
PatchValidator rejects lattice violations
```

## Unit tests

Unit tests verify small deterministic components.

Targets:

```text
simple_candidate_seeder
simple_slot_assigner
deterministic_normalizer
simple_aligner
simple_conflict_detector
GapScheduler
ConvergenceFinalizer
```

## Runner tests

Runner tests verify `run_convergence_cycle` behavior on small in-memory `EvidenceInventory` fixtures.

The first implementation should avoid filesystem-heavy tests where possible.

Use in-memory `EvidenceUnit` fixtures for contract tests, and reader-produced inventories for e2e tests.

## Report tests

Report tests verify JSON-compatible output.

Checks:

```text
ConvergenceRun.to_dict is JSON serializable
ConvergenceReport.to_dict is JSON serializable
claim_alignment_status is present
evidence_convergence_status is present
downstream_verdict is null/absent
selected_support_set is array-shaped even in MVP
patch events are visible in trace
```

Expected behavior tests may read convergence reports directly.

```text
ExperimentExpectedBehavior.claim_convergences
-> ExperimentRunTrace.run.report.claim_reports
-> ExpectedBehaviorReport checks
```

These checks compare convergence view fields such as
`claim_alignment_status`, `evidence_convergence_status`,
`selected_support_set`, `review_trigger_codes`, `partial_failure_codes`, and
`unresolved_gaps`. They do not project the convergence report into an
`EvidenceResolutionGraph`, and they do not compare `downstream_verdict`.

## MVP vertical slices

The first implementation batch should include four slices.

```text
Slice 1: clean support
Slice 2: nonblocking issue
Slice 3: candidate conflict
Slice 4: bad patch rejected
```

The fourth slice is required because it proves the trust boundary.

## File-backed fixture matrix

The current file-backed convergence fixtures live under `tests/fixtures/` and
drive `run-convergence` through `ExperimentExpectedBehavior.claim_convergences`.

```text
convergence_clean_support
  expected: evidence_converged

convergence_nonblocking_issue
  expected: evidence_converged
  expected partial_failure_codes: nonblocking_failure

convergence_candidate_conflict
  expected: needs_review_due_to_candidate_conflict
  expected review_trigger_codes: candidate_conflict
  expected unresolved_gaps: quantity
```

The bad patch rejected slice remains a runner-level fixture because it requires
injecting a fake `PatchProducer`. It should still be asserted through
`ExperimentExpectedBehavior.claim_convergences` so the trust-boundary behavior is
visible from the same expected-behavior surface.
## Slice 1: clean support

### Purpose

Prove that a candidate can converge through assignment, normalization, alignment, and finalization.

### Input

Claim:

```json
{
  "x_id": "x_usage_001",
  "fields": {
    "site": "OCH-01",
    "period": "2025-03",
    "activity": "electricity",
    "amount": 6400,
    "unit": "kWh"
  }
}
```

Evidence units:

```text
Site      | Period  | Activity    | Usage (MWh)
OCH-01    | 2025-03 | electricity | 6.4
```

### Expected candidate progression

After seeding/assignment:

```text
present_mask:
  SITE | PERIOD | ACTIVITY | QUANTITY | UNIT

assigned_mask:
  SITE | PERIOD | ACTIVITY | QUANTITY | UNIT
```

After normalization:

```text
normalized_mask:
  SITE | PERIOD | ACTIVITY | QUANTITY | UNIT

normalized quantity:
  6.4 MWh -> 6400 kWh
```

After alignment:

```text
aligned_mask:
  SITE | PERIOD | ACTIVITY | QUANTITY | UNIT
```

Expected report:

```text
claim_alignment_status = supported_after_unit_normalization
evidence_convergence_status = evidence_converged
selected_support_set = [candidate_id]
downstream_verdict = null
```

## Slice 2: nonblocking issue

### Purpose

Prove that a nonblocking attachment issue does not automatically fail convergence when a selected candidate covers required slots.

### Input

Evidence bundle contains:

```text
valid CSV/XLSX support source
unsupported or profile-only unrelated attachment
```

MVP does not need full relevance classification. It only needs to preserve the issue as nonblocking when the selected support candidate covers required slots and no conflict exists.

### Expected report

```text
claim_alignment_status = supported_after_unit_normalization or supported_direct
evidence_convergence_status = evidence_converged
partial_failures includes nonblocking_failure
review_triggers empty
```

### Guardrail

If the selected support candidate does not cover required slots, the same attachment issue may become blocking or unresolved. The test should not teach the runner to ignore all failures blindly.

## Slice 3: candidate conflict

### Purpose

Prove that support candidate existence is not enough when another active candidate conflicts.

### Input

Two candidates for the same claim context:

```text
Candidate A:
  site = OCH-01
  period = 2025-03
  activity = electricity
  quantity = 6400 kWh

Candidate B:
  site = OCH-01
  period = 2025-03
  activity = electricity
  quantity = 6800 kWh
```

MVP does not resolve source precedence.

### Expected report

```text
claim_alignment_status = supported_direct or supported_after_unit_normalization
  # selected candidate may support claim

evidence_convergence_status = needs_review_due_to_candidate_conflict
review_triggers includes candidate_conflict
```

### Guardrail

The conflict detector must not silently retire Candidate B.

## Slice 4: bad patch rejected

### Purpose

Prove that PatchValidator is the trust boundary.

### Input

A fake or future-like schema assigner proposes an unauthorized patch:

```json
{
  "candidate_id": "cand_001",
  "capability_name": "llm_schema_assigner",
  "set_aligned_mask": "QUANTITY",
  "alignment_updates": {
    "QUANTITY": "supports_after_unit_normalization"
  }
}
```

CapabilitySpec:

```text
may_set_present_mask = SITE | PERIOD | ACTIVITY | QUANTITY | UNIT
may_set_assigned_mask = SITE | PERIOD | ACTIVITY | QUANTITY | UNIT
may_set_normalized_mask = 0
may_set_aligned_mask = 0
```

### Expected event trace

```text
patch_proposed
patch_rejected
```

Rejection reason:

```text
capability_may_not_set_aligned_mask
```

Expected state:

```text
candidate.aligned_mask unchanged
claim_alignment_status != supported_after_unit_normalization from invalid patch
evidence_convergence_status != evidence_converged from invalid patch
```

This test belongs in the first implementation batch.

## Additional unit tests

### Schema mask computation

Input:

```text
SlotDef(site, SITE, required=True, comparable=True)
SlotDef(period, PERIOD, required=True, comparable=True)
SlotDef(note, NOTE, required=False, comparable=False)
```

Expected:

```text
required_mask = SITE | PERIOD
comparable_mask = SITE | PERIOD
schema_mask = SITE | PERIOD | NOTE
```

### Provenance invariant

Candidate has payload for SITE and QUANTITY but source ref only for QUANTITY.

Expected:

```text
provenance_present_mask = QUANTITY
provenance_ok = false if SITE provenance is required
```

### Lattice invariant

Patch tries:

```text
set_normalized_mask = QUANTITY
```

when QUANTITY is not assigned.

Expected:

```text
patch_rejected
reason = normalized_without_assigned
```

### Scheduler chooses deterministic first

Gap:

```text
unnormalized_mask = QUANTITY | UNIT
```

Capabilities:

```text
deterministic_normalizer cost=1 kind=deterministic
future_llm_normalizer cost=5 kind=llm
```

Expected:

```text
deterministic_normalizer selected first
```

### No eligible capability

Gap remains but no capability handles it.

Expected:

```text
no_eligible_capability event
needs_review_unresolved_gap or insufficient_missing_required_slots
```

## JSON serialization tests

Every run/report object must be JSON serializable.

Checks:

```python
json.dumps(run.to_dict(), ensure_ascii=False)
json.dumps(report.to_dict(), ensure_ascii=False)
```

## Future projection tests

Projection is not part of the first MVP implementation, but future tests should cover:

```text
ConvergenceReport evidence_converged -> EvidenceResolutionGraph supported status
needs_review_due_to_candidate_conflict -> EvidenceResolutionGraph needs_review status
insufficient_missing_required_slots -> EvidenceResolutionGraph insufficient status
contradicted_by_selected_candidate -> EvidenceResolutionGraph contradicted status
```

## Synthetic e2e tests

Once convergence runner exists, synthetic e2e can add:

```text
evidence-synthetic run scenario.yaml
-> reader runtime report
-> convergence report
```

The test must ensure runtime does not use `_synthetic` expected files as evidence.

## Test naming suggestion

Suggested files:

```text
tests/convergence/test_schema_masks.py
tests/convergence/test_candidate_gap.py
tests/convergence/test_patch_validator.py
tests/convergence/test_gap_scheduler.py
tests/convergence/test_convergence_runner.py
tests/convergence/test_convergence_report.py
```

## First implementation acceptance criteria

The first implementation batch after docs should be accepted only if:

```text
clean support passes
candidate conflict triggers review
bad patch is rejected
report is JSON serializable
downstream_verdict is null/absent
existing run_resolution_cycle tests still pass
```

## Non-goals for MVP tests

Do not test these in MVP:

```text
full BundleGraph relation reasoning
source precedence
correction email wins
quote zone loses
OCR/VLM extraction
manual review workflow
multi-candidate support set optimization
aggregation or derivation support
```

These belong to future extension test plans.
