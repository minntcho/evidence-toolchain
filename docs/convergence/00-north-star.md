# Evidence Convergence Kernel North Star

이 문서는 `evidence-toolchain`에 추가할 Evidence Convergence Kernel의 북극성입니다.

이 kernel은 기존 X-Y resolution architecture를 대체하지 않습니다. 기존 `EvidenceInventory`, `EvidenceUnit`, `EvidenceAtom`, `NeedSpec`, `NormalizationResult`, `EvidenceResolutionGraph`, `run_resolution_cycle` 흐름 옆에 놓이는 얇은 MVP layer입니다.

## 한 문장 정의

```text
Evidence Convergence Kernel은 전체 증빙 다발 reasoning을 해결하지 않는다.
claim-relevant candidate가 검증된 mask patch를 통해 aligned, contradicted, insufficient, review 중 하나로 수렴하도록 보장한다.
```

영문 정의:

```text
The Evidence Convergence Kernel does not solve full bundle reasoning.
It guarantees that claim-relevant candidates advance through validated mask patches until they are aligned, contradicted, insufficient, or escalated for review.
```

## 왜 이 layer가 필요한가

현재 architecture는 dirty attachment를 `EvidenceInventory`로 낮추고, raw observation을 `EvidenceUnit`으로 보존하고, semantic candidate를 `EvidenceAtom`으로 만들고, normalized comparison material을 `NormalizationResult`로 만든 뒤 resolver가 `EvidenceResolutionGraph`를 갱신하는 흐름을 갖습니다.

이 흐름은 계속 유효합니다. 다만 messy evidence bundle에서는 중요한 질문이 하나 더 생깁니다.

```text
어떤 raw observation이나 atom 하나가 곧바로 claim을 지지하는가?
```

보다 더 중요한 질문은 다음입니다.

```text
claim과 관련 있을 수 있는 candidate가
필수 slot을 충분히 채웠는가?
그 slot들은 출처와 함께 배정되었는가?
비교 가능한 값은 정규화되었는가?
claim과 alignment 되었는가?
남은 gap이나 conflict는 review로 올려야 하는가?
```

Evidence Convergence Kernel은 이 질문을 작게 다룹니다.

## 핵심 원칙

### 1. 기존 ingestion output을 재사용한다

MVP는 새 `EvidenceObservation` 모델을 만들지 않습니다.

```text
MVP observation = EvidenceUnit
MVP observation store = EvidenceInventory
```

Reader가 만든 `EvidenceUnit`과 bundle-level `EvidenceInventory`를 convergence input으로 사용합니다.

### 2. 기존 resolution flow를 대체하지 않는다

`run_resolution_cycle`은 계속 `NeedSpec`, `ResolutionGapPlanner`, `LocalInvestigationRunner`, `DeterministicNormalizer`, `HardGateResolver`를 묶는 deterministic reference path입니다.

Convergence MVP는 별도 entrypoint로 시작합니다.

```text
run_resolution_cycle      # existing X-Y atom/resolution path
run_convergence_cycle     # new candidate/mask/patch convergence path
```

나중에 필요하면 `ConvergenceReport -> EvidenceResolutionGraph` projection을 제공할 수 있습니다.

### 3. Candidate state는 bitmask로 표현한다

복잡한 자연어 상태를 늘리지 않습니다.

```text
present_mask
assigned_mask
normalized_mask
aligned_mask
ambiguous_mask
issue_mask
```

Candidate가 claim alignment까지 갈 수 있는지 여부는 mask와 invariant로 계산합니다.

### 4. Candidate state는 단조 수렴 격자다

Candidate slot은 기본적으로 다음 방향으로만 전진합니다.

```text
unknown
-> present
-> assigned
-> normalized
-> aligned
```

핵심 invariant:

```text
assigned_mask   ⊆ present_mask
normalized_mask ⊆ assigned_mask
aligned_mask    ⊆ normalized_mask 또는 directly_comparable_mask
```

### 5. Capability는 상태를 직접 바꾸지 않는다

Capability는 candidate state를 직접 mutate하지 않습니다.

```text
Capability -> MaskPatch
MaskPatch -> PatchValidator
PatchValidator -> Candidate state update
```

LLM, deterministic probe, normalizer, aligner, manual adapter도 모두 같은 규칙을 따릅니다.

### 6. PatchValidator가 trust boundary다

PatchValidator는 다음을 강제합니다.

```text
schema 밖의 slot bit를 건드릴 수 없다.
권한 없는 capability는 mask를 set/clear할 수 없다.
payload update에는 source ref가 있어야 한다.
assigned는 present 없이 설정할 수 없다.
normalized는 assigned 없이 설정할 수 없다.
aligned는 normalized/directly comparable 없이 설정할 수 없다.
```

### 7. LLM은 controller가 아니라 patch producer다

LLM이 들어오더라도 loop controller가 되면 안 됩니다.

```text
나쁜 구조:
LLM이 현재 상태를 읽고 다음 pipeline을 결정한다.

좋은 구조:
GapScheduler가 gap mask로 capability를 고른다.
LLM은 허용된 target gap에 대해서만 MaskPatch를 제안한다.
PatchValidator가 적용 여부를 결정한다.
```

### 8. Normalization과 alignment는 분리한다

Normalizer는 비교 가능한 material을 만듭니다.
Aligner는 claim과 candidate slot을 비교합니다.

```text
normalizer:
  set_normalized_mask 가능
  set_aligned_mask 불가

aligner:
  set_aligned_mask 가능
  claim_alignment_status 생성 가능
```

### 9. Convergence pass는 downstream verdict가 아니다

Convergence status는 `evidence-toolchain` 내부의 evidence readiness status입니다.

```text
evidence_converged != domain approved
evidence_converged != publishable
evidence_converged != audit ledger commit
evidence_converged != policy sufficiency verdict
```

Downstream system이 최종 policy, audit, publish, receipt 판단을 맡습니다.

## MVP가 풀 문제

MVP의 목표는 하나입니다.

```text
claim-relevant candidate가 검증된 mask patch를 통해
claim alignment까지 수렴할 수 있는가?
```

MVP는 다음을 증명해야 합니다.

```text
EvidenceInventory를 입력으로 받는다.
DeclaredClaim을 입력으로 받는다.
Candidate를 만든다.
Candidate gap을 계산한다.
Capability가 MaskPatch를 낸다.
PatchValidator가 patch를 검증한다.
Candidate state를 갱신한다.
Normalizer와 Aligner가 각각 자기 권한 안에서 mask를 전진시킨다.
ConvergenceReport를 낸다.
```

## MVP가 풀지 않는 문제

MVP는 다음을 구현하지 않습니다.

```text
EvidenceBundleGraph full relation model
RelevanceEnvelope
SupportSetOptimizer
DefeaterResolver
SourcePrecedencePolicy
PartialFailureClassifier full taxonomy
OCR/VLM/email/archive full loop
LLM planner
manual review workflow
downstream policy verdict
```

이 항목들은 future extension point로 남깁니다.

## 설계 약속

```text
Readers observe.
Candidates converge.
Capabilities propose patches.
Validators enforce trust boundaries.
Normalizers normalize.
Aligners compare.
Finalizers report convergence.
Downstream systems decide.
```

## 첫 번째 구현 위치

MVP code는 기존 top-level module 이름과 충돌하지 않도록 새 namespace에 격리합니다.

```text
src/evidence_toolchain/convergence/
```

초기 public-ish entrypoint는 다음처럼 둡니다.

```text
run_convergence_cycle
```

기존 `run_resolution_cycle`은 유지합니다.

## 첫 문서 세트

PR1은 이 북극성 문서와 MVP scope 문서만 추가합니다.

다음 문서들은 이후 PR에서 추가합니다.

```text
02-core-concepts.md
03-candidate-mask-state.md
04-mask-patch-and-validator.md
05-gap-scheduler-and-capabilities.md
06-runner-and-report.md
07-integration-with-existing-architecture.md
08-test-plan.md
future-extensions.md
```
