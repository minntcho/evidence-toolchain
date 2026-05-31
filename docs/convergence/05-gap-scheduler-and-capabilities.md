# GapScheduler and Capabilities

이 문서는 Evidence Convergence Kernel MVP의 gap scheduling과 capability activation contract를 정의합니다.

핵심 원칙은 다음과 같습니다.

```text
Candidate의 다음 행동은 LLM planner가 아니라 CandidateGap과 CapabilitySpec이 결정한다.
```

즉 MVP loop는 다음 구조를 따릅니다.

```text
Candidate state
-> CandidateGap 계산
-> GapScheduler가 eligible capabilities 선택
-> Capability가 MaskPatch 제안
-> PatchValidator가 검증
-> Candidate state 갱신
```

## Scheduler의 책임

GapScheduler는 다음을 합니다.

```text
candidate의 gap을 계산한다.
capability registry에서 해당 gap을 처리할 수 있는 capability를 찾는다.
capability input_required_mask가 충족되었는지 확인한다.
낮은 cost와 deterministic capability를 우선한다.
선택 결과를 runner에 넘긴다.
```

GapScheduler는 다음을 하지 않습니다.

```text
candidate state를 직접 변경하지 않는다.
MaskPatch를 직접 만들지 않는다.
LLM에게 전체 상태를 맡기지 않는다.
claim alignment를 판단하지 않는다.
downstream verdict를 만들지 않는다.
```

## CandidateGap

`CandidateGap`은 candidate가 다음 loop에서 무엇을 필요로 하는지 구조화합니다.

```python
@dataclass(frozen=True)
class CandidateGap:
    missing_mask: int
    unassigned_mask: int
    unnormalized_mask: int
    unaligned_mask: int
    ambiguous_mask: int
    issue_mask: int

    @property
    def active_mask(self) -> int:
        return (
            self.missing_mask
            | self.unassigned_mask
            | self.unnormalized_mask
            | self.unaligned_mask
            | self.ambiguous_mask
        )
```

## Gap kinds

MVP gap kinds are:

```text
missing
unassigned
unnormalized
unaligned
ambiguous
issue
```

같은 slot bit라도 gap kind가 다르면 처리할 capability가 다릅니다.

예:

```text
QUANTITY missing:
  아직 quantity 후보 자체가 없음.
  candidate seeder, reader/probe, future LLM/VLM extraction이 필요할 수 있음.

QUANTITY unassigned:
  value는 있지만 quantity slot으로 배정되지 않음.
  slot assigner가 필요함.

QUANTITY unnormalized:
  quantity slot으로 배정되었지만 comparison-ready value가 없음.
  normalizer가 필요함.

QUANTITY unaligned:
  normalized value가 있지만 claim과 비교되지 않음.
  aligner가 필요함.

QUANTITY ambiguous:
  quantity인지 amount인지, current value인지 quote인지 모호함.
  disambiguation, review, future LLM patch producer가 필요할 수 있음.
```

## Gap calculation

MVP gap calculation은 schema와 candidate mask를 사용합니다.

```python
missing_mask = schema.required_mask & ~candidate.present_mask

unassigned_mask = (
    candidate.present_mask
    & schema.required_mask
    & ~candidate.assigned_mask
)

unnormalized_mask = (
    candidate.assigned_mask
    & schema.comparable_mask
    & ~candidate.normalized_mask
)

unaligned_mask = (
    candidate.assigned_mask
    & schema.alignment_required_mask
    & ~candidate.aligned_mask
)

ambiguous_mask = candidate.ambiguous_mask
issue_mask = candidate.issue_mask
```

The implementation may refine this formula for directly comparable slots, but the contract must keep gap kinds distinct.

## CapabilitySpec

Each capability declares what it can handle and what it may change.

```python
@dataclass(frozen=True)
class CapabilitySpec:
    name: str
    kind: str
    cost: int

    handles_mask: int
    handles_gap_kinds: frozenset[str]
    input_required_mask: int

    may_set_present_mask: int = 0
    may_set_assigned_mask: int = 0
    may_set_normalized_mask: int = 0
    may_set_aligned_mask: int = 0

    may_set_ambiguous_mask: int = 0
    may_clear_ambiguous_mask: int = 0

    may_set_issue_mask: int = 0
    may_clear_issue_mask: int = 0
```

### name

Stable capability identifier.

Example:

```text
simple_slot_assigner
deterministic_normalizer
simple_aligner
simple_conflict_detector
```

### kind

MVP kinds:

```text
deterministic
llm
manual
```

MVP should ship deterministic capabilities first. Future LLM capabilities must still return MaskPatch and pass PatchValidator.

### cost

Small integer used for scheduling order.

Lower cost runs first.

### handles_mask

Slot bits the capability can help with.

### handles_gap_kinds

Which gap kinds the capability can handle.

Example:

```text
simple_slot_assigner:
  handles_gap_kinds = {"missing", "unassigned", "ambiguous"}

deterministic_normalizer:
  handles_gap_kinds = {"unnormalized"}

simple_aligner:
  handles_gap_kinds = {"unaligned"}
```

### input_required_mask

Slots that must already be present or assigned before the capability can run.

The exact interpretation depends on the capability, but MVP should keep it simple:

```text
input_required_mask must be covered by candidate.present_mask or candidate.assigned_mask, according to capability kind.
```

For deterministic normalizer, input should generally require assigned slots.

For aligner, input should generally require normalized or directly comparable slots.

## Eligibility rule

A capability is eligible when it handles at least one active gap and its input requirements are met.

Pseudo-code:

```python
def is_eligible(candidate, gap, schema, capability):
    handles_slot = capability.handles_mask & gap.active_mask
    handles_issue = "issue" in capability.handles_gap_kinds and gap.issue_mask
    handles_kind = any_gap_kind_matches(gap, capability.handles_gap_kinds)

    if not (handles_slot or handles_issue) or not handles_kind:
        return False

    if not input_requirements_met(candidate, schema, capability):
        return False

    return True
```

MVP implementation can simplify this, but it must not reduce scheduler to only `cap.handles_mask & gap.active_mask` forever. Gap kind matters.

## Scheduling order

MVP scheduler should prefer:

```text
1. deterministic capabilities
2. lower cost
3. capabilities with more specific gap kind match
4. capabilities that do not require model/manual intervention
```

Example ordering:

```text
simple_slot_assigner
-> deterministic_normalizer
-> simple_aligner
-> simple_conflict_detector
-> future LLM patch producer
-> manual review request
```

This order keeps LLM out of the controller path.

## MVP capability set

MVP uses a small capability set.

```text
simple_candidate_seeder
simple_slot_assigner
deterministic_normalizer
simple_aligner
simple_conflict_detector
```

Reader capabilities are not part of convergence kernel MVP. Existing ingestion/readers produce `EvidenceInventory` before convergence begins.

## simple_candidate_seeder

Seeder creates initial `EvidenceCandidate` records from `EvidenceInventory` and `DeclaredClaim`.

It may use:

```text
EvidenceUnit.unit_type
EvidenceUnit.text
EvidenceUnit.value
EvidenceUnit.locator
EvidenceUnit.metadata
DeclaredClaim.fields
EvidenceSchema
```

MVP can start with simple row/cell heuristics:

```text
one table row -> one candidate
one text span with usage pattern -> one candidate
```

Seeder does not align claim and does not finalize convergence.

## simple_slot_assigner

Slot assigner maps observed values to schema slots.

It may set:

```text
present_mask
assigned_mask
ambiguous_mask
payload_updates
source_ref_updates
```

It must not set:

```text
normalized_mask
aligned_mask
```

## deterministic_normalizer

Normalizer turns assigned slot payloads into comparison-ready values.

It may set:

```text
normalized_mask
normalized_payload_updates
```

It must not set:

```text
aligned_mask
claim_alignment_status
evidence_convergence_status
```

MVP normalizer should cover only clear values:

```text
quantity: Wh/kWh/MWh/GWh -> kWh
period: YYYY-MM or explicit date range
identifier/activity/unit direct canonicalization where safe
```

## simple_aligner

Aligner compares normalized or directly comparable candidate slot values against the claim.

It may set:

```text
aligned_mask
alignment_updates
issue_mask for direct contradiction
```

It must not decide downstream policy sufficiency.

Examples:

```text
6.4 MWh normalized to 6400 kWh equals claim 6400 kWh
-> supported_after_unit_normalization

6800 kWh differs from claim 6400 kWh
-> contradicted
```

## simple_conflict_detector

Conflict detector is board-level, not candidate-level.

MVP conflict rule:

```text
If two active candidates for the same claim align the same required slot to different values,
raise needs_review_due_to_candidate_conflict.
```

MVP does not resolve source precedence.

Conflict detector may emit:

```text
ReviewTrigger
board issue
```

It should not silently retire candidates.

## Future LLM capability

Future LLM capability can be added as patch producer.

It must receive bounded input:

```text
target_candidate_id
target_gap_kind
target_slots_mask
small context pack
allowed schema
current known payload
```

It must return `MaskPatch`, not free-form state mutation.

LLM must not own scheduling.

```text
Bad:
LLM chooses next pipeline step.

Good:
GapScheduler chooses LLM capability because a specific gap remains.
LLM proposes a patch for that target gap only.
PatchValidator decides whether it applies.
```

## Manual review capability

MVP does not implement manual review workflow.

However, scheduler can produce review triggers when:

```text
no eligible capability remains
candidate conflict exists
blocking issue remains
max steps exhausted with active gap
```

A future manual review adapter can return MaskPatch or external review result, but it must use the same PatchValidator boundary.

## Scheduler output

Scheduler should return an ordered list, not a single hidden decision.

```python
@dataclass(frozen=True)
class ScheduledCapability:
    capability_name: str
    target_candidate_id: str
    target_gap_kind: str
    target_mask: int
    reason: str
```

MVP runner may execute only the first scheduled capability per step.

Recording the schedule reason is important for traceability.

## Trace events

Scheduler should be visible in convergence trace.

Minimum events:

```text
gap_computed
capability_selected
no_eligible_capability
```

Example:

```json
{
  "event_type": "capability_selected",
  "candidate_id": "cand_001",
  "capability_name": "deterministic_normalizer",
  "target_gap_kind": "unnormalized",
  "target_slots": ["quantity", "unit"],
  "reason": "quantity and unit assigned but not normalized"
}
```

## Stop conditions related to scheduler

Scheduler can stop the loop when:

```text
candidate has no active gap
no eligible capability remains
same scheduled capability repeats without progress
max steps exhausted
review trigger emitted
```

The runner owns stop handling, but scheduler must expose enough reason to explain why no capability was selected.

## Non-goals

GapScheduler does not implement:

```text
support set optimization
defeater resolution
source precedence
BundleGraph traversal
OCR/VLM planning
LLM autonomous planning
manual review workflow
```

Those may later plug into the same capability registry as additional patch producers or board-level detectors.

## Summary

```text
CandidateGap says what is missing.
CapabilitySpec says what can handle it.
GapScheduler chooses the next bounded action.
Capability proposes a MaskPatch.
PatchValidator enforces trust.
```
