# 계약 문서

계약 문서는 동작을 정의하지 Downstream 정책을 정의하지 않는다.

이 문서들은 code가 evolve하더라도 `evidence-toolchain`이 보존해야 하는 현재 core contract를 설명합니다. 의도적으로 domain-neutral하게 작성하며, 각 object가 무엇을 담을 수 있는지, 무엇을 판단할 수 있는지, 무엇을 판단해서는 안 되는지를 이름 붙입니다.

## 읽는 순서

1. [Evidence Document](evidence-document.md)
2. [Declared Input](declared-input.md)
3. [Extracted Field](extracted-field.md)
4. [Evidence Check](evidence-check.md)
5. [Evidence Report](evidence-report.md)

위 개별 문서는 초기 document/report compatibility contract입니다.
현재 public-ish contract surface는 더 넓어졌고, 다음 object들이 core architecture에서
안정적으로 이름을 갖습니다.

```text
AttachmentBundle
RawAttachment
RouteDecision
SafetyDecision
EvidenceArtifact
EvidenceUnit
EvidenceInventory
EvidenceAtom
AtomizerResult
DeclaredClaim
Need
NeedSpec
ExperimentAttachmentSpec
ExperimentManifest
ExperimentRunTrace
ExperimentExpectedBehavior
ExpectedClaimResolution
ExpectedBehaviorReport
NormalizationResult
EvidenceResolutionGraph
ResolutionEdge
ClaimResolution
ResolutionGapPlan
ResolutionGapPlanner
EvidenceUnitRetrievalResult
CandidateUnitRetriever
SimpleUnitClusterAtomizer
EvidenceResolutionRun
run_resolution_cycle
ResolverPort
InvestigationState
InvestigationTask
InvestigationTaskResult
```

이 목록은 downstream policy를 정의하지 않습니다. 어디까지가 core evidence state인지,
어디부터가 Downstream 판단인지 구분하기 위한 현재 contract surface입니다.

## 계약 규칙

Core contract는 evidence-processing state를 설명할 수 있습니다.

- document identity
- requested 또는 declared input
- extracted candidate field
- provenance
- confidence
- issue
- review trigger
- resolver evidence relation state
- support, contradiction, missing, uncertainty state inside an evidence relation graph

Core contract는 Downstream authority를 encode하면 안 됩니다.

- final domain approval
- legal 또는 compliance sufficiency
- publication approval
- commit 또는 receipt authority
- audit ledger decision

Downstream consumer는 adapter를 통해 이 contract를 자기 policy 또는 workflow language로 번역할 수 있습니다.
