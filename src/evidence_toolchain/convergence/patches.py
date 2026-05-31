from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


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

    payload_updates: dict[int, Any] = field(default_factory=dict)
    source_ref_updates: dict[int, tuple[str, ...]] = field(default_factory=dict)
    normalized_payload_updates: dict[int, Any] = field(default_factory=dict)
    alignment_updates: dict[int, Any] = field(default_factory=dict)

    notes: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def touched_mask(self) -> int:
        mask = (
            self.set_present_mask
            | self.set_assigned_mask
            | self.set_normalized_mask
            | self.set_aligned_mask
            | self.set_ambiguous_mask
            | self.clear_ambiguous_mask
            | self.set_issue_mask
            | self.clear_issue_mask
        )
        for mapping in (
            self.payload_updates,
            self.source_ref_updates,
            self.normalized_payload_updates,
            self.alignment_updates,
        ):
            for slot_bit in mapping:
                mask |= slot_bit
        return mask


@dataclass(frozen=True)
class CapabilitySpec:
    name: str
    handles_mask: int
    input_required_mask: int
    handles_gap_kinds: frozenset[str]

    may_set_present_mask: int = 0
    may_set_assigned_mask: int = 0
    may_set_normalized_mask: int = 0
    may_set_aligned_mask: int = 0

    may_set_ambiguous_mask: int = 0
    may_clear_ambiguous_mask: int = 0

    may_set_issue_mask: int = 0
    may_clear_issue_mask: int = 0

    cost: int = 10
    kind: Literal["deterministic", "llm", "manual"] = "deterministic"
