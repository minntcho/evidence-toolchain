# SSOT and Strategy Boundary

이 문서는 기존 resolution path와 Evidence Convergence Kernel이 공존하는 동안
Single Source of Truth를 어디에 둘지 정의합니다.

핵심 문장은 다음과 같습니다.

```text
SSOT is the evidence case snapshot.
Strategies produce views.
Views do not mutate the snapshot.
```

한국어로는 다음과 같습니다.

```text
SSOT는 증빙 케이스 스냅샷이다.
전략은 그 스냅샷을 해석한 view를 만든다.
view는 snapshot을 변경하지 않는다.
```

## Why This Boundary Exists

기존 flow와 convergence flow는 같은 `EvidenceInventory`를 소비하지만 같은
결과물을 만들지 않습니다.

```text
Resolution strategy:
  EvidenceInventory
  -> EvidenceAtom
  -> NeedSpec
  -> NormalizationResult
  -> EvidenceResolutionGraph

Convergence strategy:
  EvidenceInventory
  -> EvidenceCandidate
  -> CandidateGap
  -> MaskPatch loop
  -> ConvergenceReport
```

이 둘을 "두 개의 진실"로 두면 안 됩니다. 둘은 고정된 evidence case
snapshot을 서로 다른 전략으로 해석한 materialized view입니다.

## Evidence Case Snapshot

Evidence case snapshot은 재현 가능한 입력과 관찰 결과를 고정합니다.

MVP에서 snapshot을 구성하는 durable material은 다음과 같습니다.

```text
ExperimentManifest or caller input metadata
AttachmentBundle
RawAttachment identity and sha256
EvidenceInventory
EvidenceUnit
RouteDecision
SafetyDecision
EvidenceIssue
DeclaredClaim
schema or contract binding
```

이 snapshot은 "무엇이 들어왔고 무엇이 관찰되었는가"를 보존합니다.

Reader 또는 ingestion이 개선되어 관찰 결과가 바뀌면 기존 snapshot을
덮어쓰지 않고 새 snapshot으로 다뤄야 합니다.

```text
same raw evidence root
-> inventory_snapshot_v1
-> inventory_snapshot_v2
```

## What Is Not SSOT

다음 객체들은 SSOT가 아닙니다.

```text
EvidenceAtom
EvidenceCandidate
MaskPatch
CandidateBoard
NormalizationResult
EvidenceResolutionGraph
ConvergenceReport
selected_support_set
review_triggers
partial_failures
downstream verdict
```

EvidenceResolutionGraph와 ConvergenceReport는 strategy-specific materialized view다.

즉 둘은 snapshot 자체가 아니라 snapshot에 대한 해석 결과입니다.

## Strategy-Specific Views

Strategy는 snapshot을 변경하지 않고 view를 만듭니다.

```text
EvidenceCaseSnapshot
  -> ResolutionGraphStrategy
       -> EvidenceResolutionGraph

EvidenceCaseSnapshot
  -> ConvergenceKernelStrategy
       -> ConvergenceReport
```

같은 snapshot에 대해 두 view가 서로 다른 status를 낼 수 있습니다.

```text
ResolutionGraphStrategy:
  supported_after_unit_normalization

ConvergenceKernelStrategy:
  needs_review_due_to_candidate_conflict
```

이 차이는 자동으로 하나의 verdict로 병합하면 안 됩니다. Resolution graph는
atom/need/normalization relation을 보여주는 view이고, Convergence report는
candidate convergence readiness와 남은 review signal을 보여주는 view입니다.

## Strategy Metadata

Strategy run은 최소한 다음 metadata를 남겨야 합니다.

```json
{
  "case_snapshot_id": "case_snapshot:...",
  "strategy_id": "convergence_mvp",
  "strategy_version": "0.1.0",
  "run_id": "run_001",
  "view_kind": "ConvergenceReport"
}
```

`EvidenceCaseSnapshot` is the code-level SSOT wrapper.

`EvidenceInventory` remains the observation store. The snapshot does not
replace inventory, readers, route decisions, safety decisions, or raw evidence
units. It names the fixed evidence case that strategy-specific views read.

Strategy outputs reference `case_snapshot_id`.

## Projection Boundary

Projection은 명시적 adapter다.

For example, a future adapter may project:

```text
ConvergenceReport -> EvidenceResolutionGraph
```

That projection must not run implicitly inside `run_convergence_cycle`.

Projection is lossy. Candidate masks, patch events, review triggers, and
partial failures cannot always be represented faithfully in a resolution graph.

Therefore projection must be explicit, named, and documented as a view adapter.

## Downstream Authority Boundary

downstream verdict는 core authority가 아니다.

The core package may emit evidence state, resolution graph views, convergence
views, trace records, review triggers, and partial failures.

It must not decide:

```text
the business claim is finally valid
the value can be committed
the evidence is sufficient for a downstream policy
the public report can be published
```

Those decisions belong to the downstream system or adapter.

## Implementation Rule

New reasoning must follow this rule:

```text
Do not mutate the evidence case snapshot.
Produce a new strategy-specific view.
Record which snapshot and strategy produced the view.
```

This keeps one SSOT while allowing resolution, convergence, and future
defeater-aware strategies to coexist without creating competing truths.
