# Evidence Convergence Kernel MVP Scope

이 문서는 Evidence Convergence Kernel의 MVP 범위를 고정합니다.

MVP는 full bundle reasoning engine이 아닙니다. MVP는 복잡한 evidence reasoning을 나중에 안전하게 붙일 수 있도록, candidate가 검증된 mask patch를 통해 수렴하는 최소 kernel만 정의합니다.

## MVP 정의

```text
MVP = Mask-gated candidate loop kernel
```

MVP가 답하려는 질문은 하나입니다.

```text
claim-relevant candidate가 검증된 mask patch를 통해
aligned, contradicted, insufficient, review 중 하나로 수렴할 수 있는가?
```

## 입력

MVP 입력은 기존 ingestion output을 재사용합니다.

```text
EvidenceInventory
DeclaredClaim
EvidenceSchemaRegistry
Capability registry
```

새 `EvidenceObservation` 모델을 만들지 않습니다.

```text
MVP observation = EvidenceUnit
MVP observation store = EvidenceInventory
```

## 출력

MVP 출력은 `ConvergenceReport`입니다.

최소 report shape는 다음 정보를 포함해야 합니다.

```text
claim_id
claim_alignment_status
evidence_convergence_status
selected_support_set
candidates
unresolved_gaps
review_triggers
partial_failures
downstream_verdict
```

`downstream_verdict`는 core가 만들지 않습니다. MVP report에서는 `null` 또는 absent여야 합니다.

## MVP가 하는 일

MVP는 다음 일만 합니다.

```text
EvidenceInventory를 입력으로 받는다.
DeclaredClaim을 입력으로 받는다.
claim별 EvidenceCandidate를 만든다.
CandidateGap을 계산한다.
GapScheduler가 capability를 고른다.
Capability가 MaskPatch를 제안한다.
PatchValidator가 capability permission과 lattice invariant를 검증한다.
검증된 patch만 candidate state에 적용한다.
SimpleNormalizer가 normalized_mask를 채운다.
SimpleAligner가 aligned_mask를 채운다.
SimpleConflictDetector가 명시적 후보 충돌을 review trigger로 올린다.
ConvergenceFinalizer가 ConvergenceReport를 낸다.
```

## MVP가 하지 않는 일

MVP는 다음을 하지 않습니다.

```text
EvidenceBundleGraph full relation model
RelevanceEnvelope
SupportSetOptimizer
DefeaterResolver
SourcePrecedencePolicy
PartialFailureClassifier full taxonomy
OCR loop
VLM loop
email/archive/Office full expansion
LLM planner
manual review workflow
downstream policy verdict
```

이 항목들은 future extension point입니다.

## MVP core objects

MVP core는 다음 객체로 시작합니다.

```text
SlotDef
EvidenceSchema
EvidenceCandidate
CandidateGap
CapabilitySpec
MaskPatch
PatchValidator
ConvergenceBoard
ConvergenceEvent
ConvergenceReport
```

## Candidate state model

Candidate state는 bitmask로 표현합니다.

```text
present_mask
assigned_mask
normalized_mask
aligned_mask
ambiguous_mask
issue_mask
```

Candidate slot은 기본적으로 다음 방향으로만 전진합니다.

```text
unknown
-> present
-> assigned
-> normalized
-> aligned
```

MVP invariant:

```text
assigned_mask   ⊆ present_mask
normalized_mask ⊆ assigned_mask
aligned_mask    ⊆ normalized_mask 또는 directly_comparable_mask
```

`directly_comparable_mask`는 `EvidenceSchema`가 명시적으로 직접 비교 가능하다고 선언한 slot만 포함합니다. MVP 기본 schema는 모든 alignment를 normalizer 경유로 처리할 수 있으므로 이 mask를 `0`으로 시작해도 됩니다.

## Provenance policy

MVP는 `PROVENANCE`를 독립 slot bit로 두지 않습니다.

각 slot의 provenance는 `source_refs_by_slot`에서 계산합니다.

```text
provenance_present_mask = slots with non-empty source refs
```

Schema는 어떤 slot에 provenance가 필요한지 `provenance_required_mask`로 선언할 수 있습니다.

## Capability permission model

MVP capability는 자기가 어떤 patch를 만들 수 있는지 명시해야 합니다.

```text
may_set_present_mask
may_set_assigned_mask
may_set_normalized_mask
may_set_aligned_mask
may_set_issue_mask
may_clear_issue_mask
```

PatchValidator는 producer 종류가 아니라 `CapabilitySpec` 권한을 기준으로 patch를 검증합니다.

예시:

```text
simple_slot_assigner:
  may_set_present_mask = SITE | PERIOD | ACTIVITY | QUANTITY | UNIT
  may_set_assigned_mask = SITE | PERIOD | ACTIVITY | QUANTITY | UNIT
  may_set_normalized_mask = 0
  may_set_aligned_mask = 0

deterministic_normalizer:
  may_set_normalized_mask = PERIOD | QUANTITY | UNIT
  may_set_aligned_mask = 0

simple_aligner:
  may_set_aligned_mask = SITE | PERIOD | ACTIVITY | QUANTITY | UNIT
```

## MVP capability set

MVP는 다음 작은 capability set으로 충분합니다.

```text
simple_candidate_seeder
simple_slot_assigner
deterministic_normalizer
simple_aligner
simple_conflict_detector
```

Reader는 convergence 내부 capability가 아닙니다. 기존 ingestion/readers가 만든 `EvidenceInventory`를 입력으로 받습니다.

## Runner boundary

MVP runner는 다음 entrypoint로 시작합니다.

```text
run_convergence_cycle(
  inventory: EvidenceInventory,
  claims: tuple[DeclaredClaim, ...],
  schema_registry: EvidenceSchemaRegistry,
  capabilities: tuple[PatchProducer, ...],
  max_steps: int,
) -> ConvergenceRun
```

Runner는 다음 일을 반복합니다.

```text
seed candidates
compute candidate gap
select eligible capability
run capability
receive MaskPatch
validate patch
apply patch
record event
repeat until stop condition
finalize report
```

## Stop conditions

MVP loop는 다음 조건에서 멈춥니다.

```text
candidate aligned
candidate contradicted
candidate missing required slots and no eligible capability remains
candidate conflict detected
max steps exhausted
no patch applied in a loop
patch validator rejects all proposed patches
```

## MVP status vocabulary

MVP는 alignment status와 convergence status를 분리합니다.

```text
claim_alignment_status:
  supported_direct
  supported_after_unit_normalization
  contradicted
  insufficient
  not_evaluated
```

```text
evidence_convergence_status:
  evidence_converged
  insufficient_missing_required_slots
  contradicted_by_selected_candidate
  needs_review_due_to_candidate_conflict
  insufficient_due_to_blocking_failure
  needs_review_unresolved_gap
```

이 분리가 필요한 이유는 selected candidate는 claim과 align되더라도 board-level conflict 때문에 convergence pass가 아닐 수 있기 때문입니다.

예시:

```json
{
  "claim_alignment_status": "supported_after_unit_normalization",
  "evidence_convergence_status": "needs_review_due_to_candidate_conflict",
  "downstream_verdict": null
}
```

## MVP selected support policy

MVP는 full support set optimizer를 구현하지 않습니다.

```text
MVP selected_support_set length = 1
```

즉 가장 좋은 단일 candidate를 selected support candidate로 둡니다.

Report field는 future expansion을 위해 배열 형태를 유지합니다.

```json
{
  "selected_support_set": ["cand_001"]
}
```

나중에 aggregation, derivation, cross-document support를 추가하면 여러 candidate를 넣을 수 있습니다.

## MVP conflict policy

MVP는 `DefeaterResolver`를 구현하지 않습니다.

대신 단순 conflict trigger만 둡니다.

```text
같은 claim의 같은 required slot에 대해
서로 다른 aligned value를 가진 active candidate가 있으면
needs_review_due_to_candidate_conflict
```

MVP는 source precedence, correction wins, quote loses, supersession을 자동 해결하지 않습니다.

## MVP partial failure policy

MVP는 full partial failure taxonomy를 구현하지 않습니다.

초기 treatment는 다음 정도로 제한합니다.

```text
blocking_failure
nonblocking_failure
unknown_failure
```

세부 분류는 future extension으로 둡니다.

```text
benign_failure
covered_failure
latent_defeater_risk
unresolved_relevant_failure
undefeated_defeater
```

## MVP vertical slices

### Slice 1: clean support

```text
input:
  CSV/XLSX row with OCH-01, 2025-03, electricity, 6.4 MWh
claim:
  OCH-01, 2025-03, electricity, 6400 kWh
expected:
  claim_alignment_status = supported_after_unit_normalization
  evidence_convergence_status = evidence_converged
```

### Slice 2: nonblocking issue

```text
input:
  valid support file
  unrelated unsupported/profile-only attachment
expected:
  evidence_converged
  issue preserved as nonblocking
```

### Slice 3: candidate conflict

```text
input:
  candidate A = 6400 kWh
  candidate B = 6800 kWh
  same claim-relevant context
expected:
  evidence_convergence_status = needs_review_due_to_candidate_conflict
```

### Slice 4: bad patch rejected

```text
input:
  fake schema assigner tries to set aligned_mask
expected:
  patch_rejected event
  aligned_mask unchanged
  convergence not passed from invalid patch
```

This fourth slice is a trust-boundary test and belongs in the first implementation batch.

## Implementation namespace

MVP code should live under:

```text
src/evidence_toolchain/convergence/
```

This avoids collisions with existing top-level modules such as `capabilities.py`, `runtime.py`, and `reports.py`.

## Initial documentation boundary

This scope document only introduces the intended contract.

```text
docs/convergence/00-north-star.md
docs/convergence/01-mvp-scope.md
docs/index.md update
```

No runtime code, tests, schema objects, or imports are changed by this document.
