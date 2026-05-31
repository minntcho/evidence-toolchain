# Candidate Mask State

이 문서는 Evidence Convergence Kernel MVP의 candidate state model을 정의합니다.

핵심은 간단합니다.

```text
Candidate state는 단조 수렴 격자다.
Capability는 slot을 앞으로 전진시키거나 issue를 명시하는 patch만 제안할 수 있다.
PatchValidator는 격자 불변식과 capability 권한을 강제한다.
```

## 왜 mask state인가

MVP는 복잡한 evidence reasoning을 구현하지 않습니다.

대신 candidate가 claim alignment까지 갈 수 있는지 다음 mask로 가볍게 관리합니다.

```text
present_mask
assigned_mask
normalized_mask
aligned_mask
ambiguous_mask
issue_mask
```

이렇게 하면 다음 질문을 LLM에게 묻지 않아도 됩니다.

```text
무엇이 부족한가?
무엇이 아직 배정되지 않았는가?
무엇이 아직 정규화되지 않았는가?
무엇이 아직 claim과 비교되지 않았는가?
```

이 질문들은 bit operation으로 계산되어야 합니다.

## Slot lifecycle

각 slot은 기본적으로 다음 방향으로만 전진합니다.

```text
unknown
-> present
-> assigned
-> normalized
-> aligned
```

각 단계의 의미는 다음과 같습니다.

### unknown

해당 slot에 쓸 수 있는 observation이나 payload가 아직 없습니다.

### present

해당 slot에 들어갈 수 있는 value 또는 source가 관찰되었습니다.

예:

```text
cell C2 = "6.4"
header C = "Usage (MWh)"
```

아직 `quantity` slot으로 확정 배정된 것은 아닙니다.

### assigned

관찰된 value/source가 schema slot에 배정되었습니다.

예:

```text
C2 is assigned to quantity
C1 is assigned to unit
```

이 단계는 semantic schema assignment입니다. 단, claim support 판단은 아닙니다.

### normalized

비교 가능한 normalized material이 생성되었습니다.

예:

```text
6.4 MWh -> 6400 kWh
2025-03 -> 2025-03-01 ~ 2025-03-31
```

Normalization은 support 판단이 아닙니다.

### aligned

해당 slot이 claim과 비교되어 align되거나 contradict되었습니다.

예:

```text
candidate quantity 6400 kWh == claim quantity 6400 kWh
```

Alignment는 downstream verdict가 아닙니다.

## MVP slot set

MVP first schema는 `utility_usage_record.v1`입니다.

최소 slot set:

```text
SITE
PERIOD
ACTIVITY
QUANTITY
UNIT
```

예시 bit assignment:

```text
SITE     = 1 << 0
PERIOD   = 1 << 1
ACTIVITY = 1 << 2
QUANTITY = 1 << 3
UNIT     = 1 << 4
```

## SlotDef

MVP schema는 `SlotDef`로 slot metadata를 선언합니다.

```python
@dataclass(frozen=True)
class SlotDef:
    slot_id: str
    bit: int
    value_kind: str
    required: bool = True
    comparable: bool = False
    alignment_required: bool = True
    provenance_required: bool = True
```

Field 의미:

```text
slot_id:
  사람이 읽는 slot 이름

bit:
  mask에서 사용하는 bit

value_kind:
  identifier, period, quantity, unit 같은 값 종류

required:
  convergence pass에 필요한 slot인지

comparable:
  normalized material이 필요한 slot인지

alignment_required:
  claim과 비교되어야 하는 slot인지

provenance_required:
  source_refs_by_slot이 필요한 slot인지
```

## EvidenceSchema

Schema는 slot set에서 mask를 계산합니다.

```python
@dataclass(frozen=True)
class EvidenceSchema:
    schema_id: str
    slots: tuple[SlotDef, ...]
```

Computed masks:

```text
required_mask
comparable_mask
alignment_required_mask
provenance_required_mask
schema_mask
```

Example:

```text
utility_usage_record.v1

required_mask:
  SITE | PERIOD | ACTIVITY | QUANTITY | UNIT

comparable_mask:
  SITE | PERIOD | ACTIVITY | QUANTITY | UNIT

alignment_required_mask:
  SITE | PERIOD | ACTIVITY | QUANTITY | UNIT

provenance_required_mask:
  SITE | PERIOD | ACTIVITY | QUANTITY | UNIT
```

## Provenance is not a slot

MVP는 `PROVENANCE`를 별도 slot bit로 두지 않습니다.

이유:

```text
provenance는 독립 field가 아니라 각 slot payload에 붙어야 하는 invariant다.
```

Candidate는 다음 map을 가집니다.

```text
source_refs_by_slot: dict[int, tuple[str, ...]]
```

Provenance mask는 저장값이 아니라 계산값입니다.

```python
def provenance_present_mask(candidate: EvidenceCandidate) -> int:
    mask = 0
    for slot_bit, refs in candidate.source_refs_by_slot.items():
        if refs:
            mask |= slot_bit
    return mask
```

Provenance invariant:

```text
(provenance_present_mask & schema.provenance_required_mask)
== schema.provenance_required_mask
```

## EvidenceCandidate

Candidate는 claim-relevant schema state holder입니다.

```python
@dataclass(frozen=True)
class EvidenceCandidate:
    candidate_id: str
    claim_id: str
    schema_id: str

    present_mask: int = 0
    assigned_mask: int = 0
    normalized_mask: int = 0
    aligned_mask: int = 0

    ambiguous_mask: int = 0
    rejected_mask: int = 0
    issue_mask: int = 0

    payload_by_slot: dict[int, object] = field(default_factory=dict)
    source_refs_by_slot: dict[int, tuple[str, ...]] = field(default_factory=dict)
    normalized_payload_by_slot: dict[int, object] = field(default_factory=dict)
    alignment_by_slot: dict[int, object] = field(default_factory=dict)

    tags: tuple[str, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)
```

MVP candidate is immutable in spirit. Runner may materialize a new candidate state after applying a valid patch.

## Lattice invariants

PatchValidator must enforce these invariants after patch application.

```python
assigned_mask & ~present_mask == 0
normalized_mask & ~assigned_mask == 0
aligned_mask & ~(normalized_mask | directly_comparable_mask) == 0
```

If `directly_comparable_mask` is empty, then aligned slots must be normalized first.

## Why aligned may depend on directly comparable

Some slots may be directly comparable without a separate normalized value.

Example:

```text
activity = electricity
site = OCH-01
unit = kWh
```

MVP may still route these through a simple normalizer for uniformity. The schema keeps `directly_comparable_mask` as an escape hatch for future implementation.

## CandidateGap

Gap is structured by kind.

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

Gap calculation:

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
    (schema.alignment_required_mask & candidate.assigned_mask)
    & ~candidate.aligned_mask
)
```

The exact implementation may refine this formula, but the distinction between gap kinds must remain.

## Candidate readiness

A candidate is ready for finalization when all required invariants pass.

```python
coverage_ok = (candidate.present_mask & schema.required_mask) == schema.required_mask
assigned_ok = (candidate.assigned_mask & schema.required_mask) == schema.required_mask
normalized_ok = (
    candidate.normalized_mask & schema.comparable_mask
) == schema.comparable_mask
aligned_ok = (
    candidate.aligned_mask & schema.alignment_required_mask
) == schema.alignment_required_mask
provenance_ok = (
    provenance_present_mask(candidate) & schema.provenance_required_mask
) == schema.provenance_required_mask
no_ambiguous = candidate.ambiguous_mask == 0
no_blocking_issue = not has_blocking_issue(candidate)
```

MVP convergence can only pass when selected candidate satisfies these conditions and the board has no simple conflict trigger.

## State monotonicity

Candidate state should not silently move backward.

Allowed:

```text
set_present_mask
set_assigned_mask
set_normalized_mask
set_aligned_mask
set_issue_mask
set_ambiguous_mask
clear_ambiguous_mask when justified
clear_issue_mask when capability has permission
```

Avoid:

```text
removing payload without event
clearing provenance without event
turning aligned slot back to unknown silently
replacing a value with another value without trace
```

Future source precedence, supersession, and correction handling should use explicit board events, rejected_mask, superseded tags, or conflict resolution records rather than silent overwrite.

## Example candidate progression

Initial seeded candidate:

```text
present_mask:      QUANTITY | UNIT
assigned_mask:     0
normalized_mask:   0
aligned_mask:      0
ambiguous_mask:    QUANTITY
```

After slot assignment patch:

```text
present_mask:      QUANTITY | UNIT
assigned_mask:     QUANTITY | UNIT
normalized_mask:   0
aligned_mask:      0
ambiguous_mask:    0
```

After normalizer patch:

```text
normalized_mask:   QUANTITY | UNIT
normalized payload:
  quantity = 6400 kWh
```

After aligner patch:

```text
aligned_mask:      QUANTITY | UNIT
alignment:
  supports_after_unit_normalization
```

The candidate advanced by validated patches. No capability directly mutated state.
