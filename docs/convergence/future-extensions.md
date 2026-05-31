# Evidence Convergence Future Extensions

이 문서는 Evidence Convergence Kernel MVP 밖으로 의도적으로 미룬 확장 항목을 기록합니다.

목적은 두 가지입니다.

```text
1. MVP가 커지는 것을 막는다.
2. 장기 아키텍처에서 필요한 확장 지점을 잃지 않는다.
```

MVP는 `Mask-gated candidate loop kernel`만 구현합니다. 아래 항목들은 MVP가 아니라 future extension입니다.

## Extension principle

Future extension은 core loop를 우회하면 안 됩니다.

```text
Good:
  extension observes gap or board state
  extension proposes MaskPatch or review trigger
  PatchValidator validates state changes

Bad:
  extension directly mutates candidate state
  extension bypasses PatchValidator
  extension emits downstream verdict
```

## EvidenceBundleGraph

### Why it matters

Real evidence arrives as a bundle, not as isolated files.

Examples:

```text
correction email attaches spreadsheet
spreadsheet hidden sheet corrects summary sheet
email quote contains old value
PDF statement is superseded by later correction
```

A flat inventory loses some document-to-document relationships.

### Why out of MVP

MVP can prove candidate mask convergence with existing `EvidenceInventory` and `EvidenceUnit`.

Full graph modeling would add document roles, zones, relations, and lifecycle semantics before the kernel itself is proven.

### Future integration point

```text
EvidenceBundleGraph
-> CandidateSeeder hints
-> GapScheduler context
-> DefeaterResolver input
```

It should remain additive.

## RelevanceEnvelope

### Why it matters

Partial failure and candidate conflict cannot be judged safely without claim relevance.

Example:

```text
unreadable fuel receipt may be benign for electricity usage claim
unreadable correction email may hide a relevant defeater
```

### Why out of MVP

MVP only needs coarse failure treatment:

```text
blocking_failure
nonblocking_failure
unknown_failure
```

Strict/broad relevance envelopes can be added after basic convergence behavior exists.

### Future integration point

```text
DeclaredClaim
-> RelevanceEnvelope
-> CandidateSeeder filtering
-> PartialFailureClassifier
-> DefeaterResolver
```

## SupportSetSelector

### Why it matters

Long-term convergence should not require every candidate to match.

It should ask:

```text
Can we construct a sufficient support set?
Are there undefeated relevant defeaters?
Are unresolved relevant failures still present?
```

### Why out of MVP

MVP uses a single selected support candidate.

```text
selected_support_set length = 1
```

This keeps the first implementation small.

### Future integration point

```text
CandidateBoard
-> SupportSetSelector
-> selected_support_set
-> ConvergenceFinalizer
```

The report shape already uses an array so future multi-candidate support can fit.

## DefeaterResolver

### Why it matters

Support candidate existence is not enough when a related contradiction remains.

Examples:

```text
selected candidate says 6400 kWh
correction email says 6800 kWh
source precedence unresolved
```

### Why out of MVP

MVP only raises simple review triggers for direct candidate conflicts.

It does not resolve:

```text
correction wins
quote loses
latest document wins
hidden sheet overrides summary
official statement beats internal spreadsheet
```

### Future integration point

```text
CandidateBoard
+ EvidenceBundleGraph
+ SourcePrecedencePolicy
-> DefeaterResolver
-> defeated/undefeated defeater records
```

DefeaterResolver must not emit downstream approval.

## SourcePrecedencePolicy

### Why it matters

Source precedence is domain-sensitive.

Examples:

```text
supplier correction notice may defeat old statement
signed PDF may defeat internal spreadsheet
manual override may require review
```

### Why out of MVP

Hard-coding precedence in MVP would make the core domain-specific too early.

### Future integration point

Precedence should be injected as policy/config/adapter.

```text
SourcePrecedencePolicy
-> DefeaterResolver
-> ConvergenceFinalizer
```

Core should record unresolved precedence when no policy is provided.

## PartialFailureClassifier

### Why it matters

Partial failures are not all equal.

Long-term treatment categories:

```text
benign_failure
covered_failure
local_candidate_failure
unresolved_relevant_failure
latent_defeater_risk
undefeated_defeater
```

### Why out of MVP

MVP only distinguishes coarse failure treatment.

```text
blocking_failure
nonblocking_failure
unknown_failure
```

This prevents the first implementation from becoming a full evidence governance engine.

### Future integration point

```text
EvidenceInventory.issues
+ RelevanceEnvelope
+ CandidateBoard
+ SupportSetSelector
-> PartialFailureClassifier
```

## LLM Schema Assigner

### Why it matters

Messy evidence often requires semantic schema assignment.

Examples:

```text
Which date is service period?
Is 6.4 a quantity or a rate?
Is this row current or quoted old value?
```

### Why out of initial MVP

The first code slice should prove deterministic patch flow before model-backed patch producers are introduced.

### Future integration point

LLM schema assigner must be a `PatchProducer`.

```text
CandidateGap
-> GapScheduler selects LLM capability
-> bounded context pack
-> LLM returns MaskPatch
-> PatchValidator validates
```

LLM must not become the loop controller.

## VLM/OCR loop

### Why it matters

Scanned PDFs, meter photos, screenshots, and low-quality images need OCR/VLM.

### Why out of MVP

MVP can use CSV/XLSX/plain text fixtures to prove convergence kernel behavior.

OCR/VLM adds provider cost, quality variability, and artifact handling before core convergence is proven.

### Future integration point

```text
EvidenceBundleGraph / EvidenceInventory
-> visual/OCR capability
-> EvidenceUnit or MaskPatch
-> PatchValidator
```

VLM/OCR outputs must preserve source locators and confidence.

## Email/archive/Office expansion

### Why it matters

Real evidence may arrive as:

```text
email with attachments
zip archive
Office document
forwarded thread
quoted old values
```

### Why out of MVP

Carrier expansion is orthogonal to candidate mask convergence.

### Future integration point

These should extend ingestion and possibly BundleGraph before candidate seeding.

```text
AttachmentBundle
-> ArtifactExpander
-> EvidenceInventory / EvidenceBundleGraph
-> Convergence Kernel
```

## Manual review workflow

### Why it matters

Some gaps and conflicts require human decision.

### Why out of MVP

MVP can emit review triggers without implementing queue assignment, UI, review decision, or audit workflow.

### Future integration point

```text
ConvergenceReport.review_triggers
-> review adapter
-> manual MaskPatch or downstream workflow
```

Manual review result should still return through explicit patch/review records.

## Multi-claim board reasoning

### Why it matters

One evidence candidate can relate to multiple claims.

Example:

```text
same spreadsheet row supports both electricity usage and cost context
```

### Why out of MVP

MVP can handle one claim or independent claim loops first.

### Future integration point

```text
CandidateBoard
-> claim_id partitioning
-> shared candidate refs
-> board-level conflict/reuse rules
```

## Aggregation and derivation support

### Why it matters

Claims may be supported by sums or derived values.

Examples:

```text
sum of monthly line items
meter end - meter start
unit conversion plus aggregation
```

### Why out of MVP

MVP selected support set length is one.

Aggregation/derivation requires explicit formula provenance and support set selection.

### Future integration point

```text
SupportSetSelector
+ DerivationRecord
+ AggregationSolver
-> derived support candidate
```

## EvidenceResolutionGraph projection

### Why it matters

Existing expected behavior and resolution contracts use `EvidenceResolutionGraph`.

Projection can bridge convergence reports into that shape.

### Why out of MVP docs PR

Projection is useful but should not block the convergence kernel MVP.

### Future integration point

```text
ConvergenceReport
-> EvidenceResolutionGraph projection
```

Candidate IDs can initially live in metadata. Richer atom projection can come later.

## Expected behavior oracle for convergence

### Why it matters

The current expected behavior oracle targets `EvidenceResolutionGraph`.

Convergence may need expected checks for:

```text
claim_alignment_status
evidence_convergence_status
selected_support_set
review_triggers
patch_rejections
unresolved_gaps
```

### Why out of MVP docs PR

First implementation can test reports directly.

### Future integration point

```text
ExperimentExpectedConvergence
+ ConvergenceRun
-> ExpectedConvergenceReport
```

This should be additive.

## Parking lot summary

MVP keeps these out:

```text
BundleGraph
RelevanceEnvelope
SupportSetSelector
DefeaterResolver
SourcePrecedencePolicy
PartialFailureClassifier full taxonomy
LLM planner
VLM/OCR loop
email/archive/Office expansion
manual review workflow
multi-claim board reasoning
aggregation/derivation support
```

They can be added later because the MVP kernel exposes stable extension points:

```text
EvidenceInventory input
CandidateBoard state
CandidateGap
CapabilitySpec
MaskPatch
PatchValidator
ConvergenceReport
```

## Guardrail

Future extension must not break this core rule:

```text
Extensions may propose patches or report triggers.
They must not bypass PatchValidator or emit downstream verdicts from core.
```
