# Evidence Convergence Core Concepts

이 문서는 Evidence Convergence Kernel MVP의 핵심 용어를 정의합니다.

이 문서의 목표는 runtime code를 만들지 않고, 이후 구현에서 용어가 섞이지 않도록 core contract vocabulary를 고정하는 것입니다.

## 위치

Convergence Kernel은 기존 X-Y resolution architecture를 대체하지 않습니다.

```text
기존 path:
EvidenceInventory
-> EvidenceAtom
-> NeedSpec
-> NormalizationResult
-> EvidenceResolutionGraph

convergence MVP path:
EvidenceInventory
-> EvidenceCandidate
-> MaskPatch loop
-> ConvergenceReport
```

두 path는 병렬입니다. 나중에 필요하면 `ConvergenceReport -> EvidenceResolutionGraph` projection을 추가할 수 있습니다.

## EvidenceUnit

`EvidenceUnit`은 reader가 만든 raw observation입니다.

Convergence MVP는 새 `EvidenceObservation` 모델을 만들지 않습니다.

```text
MVP observation = EvidenceUnit
MVP observation store = EvidenceInventory
```

`EvidenceUnit`은 다음을 표현합니다.

```text
CSV cell
XLSX cell
plain text span
PDF text span
word box
metadata unit
```

`EvidenceUnit`은 semantic slot assignment가 아닙니다. 예를 들어 `"6.4"`라는 table cell은 아직 `quantity`도 아니고 `amount`도 아닙니다. 그것은 reader가 본 raw observation일 뿐입니다.

## EvidenceInventory

`EvidenceInventory`는 bundle-level ingestion output입니다.

Convergence Kernel은 MVP에서 `EvidenceInventory`를 입력으로 받습니다.

```text
EvidenceInventory
  attachments
  artifacts
  units
  route_decisions
  safety_decisions
  issues
```

MVP는 BundleGraph를 만들지 않습니다. 파일 간 relation, source precedence, supersession, email quote relation은 future extension으로 둡니다.

## EvidenceAtom

`EvidenceAtom`은 기존 X-Y resolution flow의 semantic evidence candidate입니다.

Convergence Kernel MVP는 `EvidenceAtom`을 중심 모델로 쓰지 않습니다. 대신 claim-relevant `EvidenceCandidate`를 중심에 둡니다.

다만 `EvidenceAtom`은 compatibility path로 계속 유효합니다.

```text
EvidenceAtom:
  기존 atom/resolution flow에서 사용

EvidenceCandidate:
  convergence kernel에서 claim-relevant slot mask state를 관리
```

나중에 필요하면 candidate slot을 EvidenceAtom으로 flatten하거나, ConvergenceReport를 EvidenceResolutionGraph로 projection할 수 있습니다.

## DeclaredClaim

`DeclaredClaim`은 evidence bundle이 지지하거나 반박해야 하는 caller-side X input입니다.

Convergence Kernel은 claim을 downstream approval로 해석하지 않습니다.

```text
DeclaredClaim = 비교 대상 입력
EvidenceCandidate = claim과 align될 수 있는 evidence-side candidate
ConvergenceReport = evidence readiness result
Downstream = policy/audit/publish/receipt authority
```

## EvidenceCandidate

`EvidenceCandidate`는 convergence kernel의 중심 객체입니다.

Candidate는 raw observation 하나가 아닙니다. Candidate는 claim과 관련 있을 수 있는 schema-shaped evidence possibility입니다.

예시:

```text
candidate: utility_usage_record.v1
claim_id: x_001
slots:
  site
  period
  activity
  quantity
  unit
```

Candidate는 slot별 payload와 source refs를 가질 수 있습니다.

```text
payload_by_slot:
  site -> OCH-01
  period -> 2025-03
  activity -> electricity
  quantity -> 6.4
  unit -> MWh

source_refs_by_slot:
  quantity -> xlsx:Summary!D2
  unit -> xlsx:Summary!D1
```

Candidate는 pass/fail 자체가 아닙니다. Candidate는 mask patch를 통해 수렴하는 state holder입니다.

## Slot

Slot은 schema 안의 claim-relevant field입니다.

MVP의 first schema는 `utility_usage_record.v1`이며, 최소 slot은 다음과 같습니다.

```text
site
period
activity
quantity
unit
```

Slot은 bit로 표현됩니다.

```text
SITE      = 1 << 0
PERIOD    = 1 << 1
ACTIVITY  = 1 << 2
QUANTITY  = 1 << 3
UNIT      = 1 << 4
```

Slot은 다음 metadata를 가질 수 있습니다.

```text
slot_id
bit
value_kind
required
comparable
directly_comparable
alignment_required
provenance_required
```

## EvidenceSchema

`EvidenceSchema`는 candidate가 어떤 slots를 가져야 하는지 정의합니다.

MVP schema는 bitmask를 계산할 수 있어야 합니다.

```text
required_mask
comparable_mask
directly_comparable_mask
alignment_required_mask
provenance_required_mask
```

Schema는 full JSON schema가 아닙니다. MVP에서는 slot bit contract만 정의합니다.

## CandidateMaskState

Candidate state는 여러 mask로 표현됩니다.

```text
present_mask
assigned_mask
normalized_mask
aligned_mask
ambiguous_mask
issue_mask
```

각 mask의 의미는 다음과 같습니다.

```text
present_mask:
  해당 slot에 들어갈 수 있는 value/source가 관찰됨

assigned_mask:
  해당 value/source가 schema slot에 배정됨

normalized_mask:
  해당 slot이 비교 가능한 normalized material로 변환됨

aligned_mask:
  해당 slot이 claim과 비교되어 align됨

ambiguous_mask:
  해당 slot 해석이 모호함

issue_mask:
  candidate에 남은 issue가 있음
```

## CandidateGap

`CandidateGap`은 candidate가 다음 loop에서 무엇을 필요로 하는지 나타냅니다.

단일 int가 아니라 gap kind별 mask로 표현합니다.

```text
missing_mask
unassigned_mask
unnormalized_mask
unaligned_mask
ambiguous_mask
issue_mask
```

같은 bit라도 gap kind가 다르면 필요한 capability가 다릅니다.

```text
QUANTITY missing       -> reader/probe/seeder 문제
QUANTITY unassigned    -> slot assigner 문제
QUANTITY unnormalized  -> normalizer 문제
QUANTITY unaligned     -> aligner 문제
QUANTITY ambiguous     -> disambiguation/review 문제
```

## MaskPatch

`MaskPatch`는 capability가 제안하는 candidate state update입니다.

Capability는 candidate를 직접 변경하지 않습니다.

```text
Capability -> MaskPatch -> PatchValidator -> Candidate state update
```

Patch는 다음을 포함할 수 있습니다.

```text
set_present_mask
set_assigned_mask
set_normalized_mask
set_aligned_mask
set_ambiguous_mask
clear_ambiguous_mask
set_issue_mask
clear_issue_mask
payload_updates
source_ref_updates
notes
```

## CapabilitySpec

`CapabilitySpec`은 capability가 어떤 gap을 처리하고 어떤 patch를 만들 수 있는지 선언합니다.

```text
name
kind
cost
handles_mask
handles_gap_kinds
input_required_mask
may_set_present_mask
may_set_assigned_mask
may_set_normalized_mask
may_set_aligned_mask
may_set_issue_mask
may_clear_issue_mask
```

MVP는 producer type special case보다 permission model을 선호합니다.

```text
나쁜 기준:
LLM이라서 aligned_mask 설정 금지

좋은 기준:
이 CapabilitySpec에 may_set_aligned_mask 권한이 없으므로 금지
```

## PatchValidator

`PatchValidator`는 convergence kernel의 trust boundary입니다.

Validator는 다음을 검사합니다.

```text
schema 밖 bit를 건드리지 않았는가?
capability permission 밖 mask를 set/clear하지 않았는가?
payload update에 source refs가 있는가?
assigned_mask가 present_mask 없이 설정되지 않았는가?
normalized_mask가 assigned_mask 없이 설정되지 않았는가?
aligned_mask가 normalized/directly comparable 없이 설정되지 않았는가?
```

## GapScheduler

`GapScheduler`는 candidate gap과 capability registry를 보고 다음 capability를 고릅니다.

```text
CandidateGap
+ CapabilitySpec registry
-> eligible capabilities
```

Scheduler는 LLM planner가 아닙니다. Scheduler는 mask와 capability contract를 기준으로 deterministic하게 동작해야 합니다.

## ConvergenceBoard

`ConvergenceBoard`는 claim별 candidates와 patch/event trace를 관리합니다.

MVP board는 다음을 가질 수 있습니다.

```text
inventory
claims
candidates
events
review_triggers
partial_failures
```

Board는 full BundleGraph가 아닙니다.

## ConvergenceReport

`ConvergenceReport`는 MVP output입니다.

Report는 alignment status와 convergence status를 분리합니다.

```text
claim_alignment_status:
  selected candidate가 claim과 어떻게 align되는가

evidence_convergence_status:
  gap, conflict, issue까지 포함해 convergence state가 무엇인가
```

`ConvergenceReport`는 downstream verdict가 아닙니다.

## Core separation summary

```text
Reader observes EvidenceUnit.
CandidateSeeder creates EvidenceCandidate.
Capability proposes MaskPatch.
PatchValidator applies only valid patches.
Normalizer normalizes.
Aligner aligns.
Finalizer reports convergence.
Downstream decides.
```
