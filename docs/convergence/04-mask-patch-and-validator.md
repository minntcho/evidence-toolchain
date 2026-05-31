# MaskPatch and PatchValidator

이 문서는 Evidence Convergence Kernel MVP의 patch contract와 trust boundary를 정의합니다.

핵심 원칙:

```text
Capability는 candidate state를 직접 변경하지 않는다.
Capability는 MaskPatch만 제안한다.
PatchValidator만 patch를 적용할 수 있다.
```

## Why patch-based updates

Convergence Kernel에는 deterministic capability, LLM capability, future VLM/OCR/manual adapter가 함께 붙을 수 있습니다.

이들이 candidate state를 직접 변경하면 trust boundary가 무너집니다.

따라서 모든 capability output을 `MaskPatch`로 통일합니다.

```text
slot assigner -> MaskPatch
normalizer -> MaskPatch
aligner -> MaskPatch
conflict detector -> board issue / review trigger
future LLM -> MaskPatch
future VLM -> MaskPatch
future manual adapter -> MaskPatch
```

## MaskPatch shape

MVP patch는 candidate 하나에 대한 proposed update입니다.

```python
@dataclass(frozen=True)
class MaskPatch:
    candidate_id: str
    producer: str
    capability_name: str

    set_present_mask: int = 0
    set_assigned_mask: int = 0
    set_normalized_mask: int = 0
    set_aligned_mask: int = 0

    set_ambiguous_mask: int = 0
    clear_ambiguous_mask: int = 0

    set_issue_mask: int = 0
    clear_issue_mask: int = 0

    payload_updates: dict[int, object] = field(default_factory=dict)
    source_ref_updates: dict[int, tuple[str, ...]] = field(default_factory=dict)
    normalized_payload_updates: dict[int, object] = field(default_factory=dict)
    alignment_updates: dict[int, object] = field(default_factory=dict)

    notes: tuple[str, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)
```

Patch shape can grow later, but MVP should keep state mutation explicit.

## CapabilitySpec permission model

Validator must not hard-code producer names such as `llm_schema_assigner`.

It should check capability permissions.

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

This means:

```text
A capability can only set or clear the bits it is explicitly allowed to touch.
```

## Example permissions

### simple_slot_assigner

```text
may_set_present_mask:
  SITE | PERIOD | ACTIVITY | QUANTITY | UNIT

may_set_assigned_mask:
  SITE | PERIOD | ACTIVITY | QUANTITY | UNIT

may_set_normalized_mask:
  0

may_set_aligned_mask:
  0
```

### deterministic_normalizer

```text
may_set_normalized_mask:
  SITE | PERIOD | ACTIVITY | QUANTITY | UNIT

may_set_aligned_mask:
  0
```

### simple_aligner

```text
may_set_aligned_mask:
  SITE | PERIOD | ACTIVITY | QUANTITY | UNIT
```

### future LLM schema assigner

```text
may_set_present_mask:
  SITE | PERIOD | ACTIVITY | QUANTITY | UNIT

may_set_assigned_mask:
  SITE | PERIOD | ACTIVITY | QUANTITY | UNIT

may_set_normalized_mask:
  0

may_set_aligned_mask:
  0
```

The future LLM can propose slot assignment but cannot align the claim.

## PatchValidator responsibilities

PatchValidator has two jobs.

```text
1. Permission validation
2. Lattice invariant validation
```

## Permission validation

Validator must reject a patch when it touches bits outside capability permissions.

Example:

```text
patch.set_aligned_mask = QUANTITY
capability.may_set_aligned_mask = 0

-> reject
```

This is true even if the producer is deterministic. Authority comes from `CapabilitySpec`, not from the producer label.

## Schema mask validation

Patch must not touch bits outside the schema.

```python
unknown_bits = patch.touched_mask & ~schema.schema_mask
if unknown_bits:
    reject
```

This prevents future adapters from inventing hidden state.

## Payload/source validation

Payload updates need source references unless the slot explicitly allows synthetic or derived values.

MVP default:

```text
payload update requires source_ref_update for the same slot.
```

Examples:

```text
Good:
  payload_updates[QUANTITY] = 6.4
  source_ref_updates[QUANTITY] = ("xlsx:Summary!D2",)

Bad:
  payload_updates[QUANTITY] = 6.4
  source_ref_updates missing
```

Derived values should be represented as normalized payloads or alignment records with derivation metadata, not raw source payload without provenance.

## Lattice invariant validation

After applying the patch to a candidate draft, validator must check:

```python
assigned_mask & ~present_mask == 0
normalized_mask & ~assigned_mask == 0
aligned_mask & ~(normalized_mask | directly_comparable_mask) == 0
```

If the patch would break the lattice, reject it.

## Monotonicity validation

MVP patch should not silently remove state.

Allowed:

```text
set bits
clear ambiguous bits with permission
clear issue bits with permission
```

Not allowed by default:

```text
clear present/assigned/normalized/aligned bit silently
overwrite payload with a different value without event
remove source refs silently
```

Future correction or supersession logic should use explicit conflict/rejection/supersession records, not silent replacement.

## Alignment authority rule

Only alignment capabilities may set `aligned_mask`.

This is a permission rule, not a producer-name rule.

```text
If a future LLM capability is configured only as schema assigner,
it must not set aligned_mask.

If a future LLM-assisted aligner exists,
it still needs explicit may_set_aligned_mask permission
and must pass validator rules.
```

MVP should not include LLM-assisted alignment.

## Normalization authority rule

Only normalizer capabilities may set `normalized_mask`.

Slot assignment capabilities can set `present_mask` and `assigned_mask`, but not `normalized_mask`.

This preserves the distinction:

```text
assignment:
  this source value belongs to this schema slot

normalization:
  this slot value is now comparison-ready

alignment:
  this comparison-ready value matches or contradicts the claim
```

## Bad patch example

Fake LLM schema assigner proposes:

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
llm_schema_assigner.may_set_aligned_mask = 0
```

Expected validator result:

```text
patch_rejected
reason = capability_may_not_set_aligned_mask
candidate.aligned_mask unchanged
```

This is an MVP trust-boundary test and belongs in the first implementation batch.

## Good patch example: slot assignment

```json
{
  "candidate_id": "cand_001",
  "capability_name": "simple_slot_assigner",
  "set_present_mask": "QUANTITY|UNIT",
  "set_assigned_mask": "QUANTITY|UNIT",
  "payload_updates": {
    "QUANTITY": 6.4,
    "UNIT": "MWh"
  },
  "source_ref_updates": {
    "QUANTITY": ["xlsx:Summary!D2"],
    "UNIT": ["xlsx:Summary!D1"]
  }
}
```

Expected validator result:

```text
patch_applied
present_mask includes QUANTITY|UNIT
assigned_mask includes QUANTITY|UNIT
```

## Good patch example: normalization

```json
{
  "candidate_id": "cand_001",
  "capability_name": "deterministic_normalizer",
  "set_normalized_mask": "QUANTITY|UNIT",
  "normalized_payload_updates": {
    "QUANTITY": {
      "value": 6400,
      "unit": "kWh",
      "source_value": 6.4,
      "source_unit": "MWh"
    }
  }
}
```

Expected validator result:

```text
patch_applied only if QUANTITY|UNIT are already assigned
```

## Good patch example: alignment

```json
{
  "candidate_id": "cand_001",
  "capability_name": "simple_aligner",
  "set_aligned_mask": "QUANTITY|UNIT",
  "alignment_updates": {
    "QUANTITY": "supported_after_unit_normalization",
    "UNIT": "supported_after_unit_normalization"
  }
}
```

Expected validator result:

```text
patch_applied only if QUANTITY|UNIT are normalized or directly comparable
```

## Patch event trace

MVP board should record patch events.

Minimum event types:

```text
patch_proposed
patch_applied
patch_rejected
```

Example:

```json
{
  "event_type": "patch_rejected",
  "candidate_id": "cand_001",
  "capability_name": "llm_schema_assigner",
  "reason": "capability_may_not_set_aligned_mask"
}
```

This trace is not optional. It is how the kernel explains why a candidate did or did not converge.

## Validator non-goals

PatchValidator does not solve:

```text
source precedence
supersession
quote-vs-body authority
support set optimization
defeater resolution
downstream policy sufficiency
```

It only enforces patch-level trust boundaries and lattice invariants.

## Summary

```text
Capability proposes.
PatchValidator checks.
Candidate advances.
Trace records.
Downstream decides.
```
