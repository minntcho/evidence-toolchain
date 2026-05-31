from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CandidateMaskState:
    present_mask: int = 0
    assigned_mask: int = 0
    normalized_mask: int = 0
    aligned_mask: int = 0
    ambiguous_mask: int = 0
    rejected_mask: int = 0
    issue_mask: int = 0

    @property
    def state_mask(self) -> int:
        return (
            self.present_mask
            | self.assigned_mask
            | self.normalized_mask
            | self.aligned_mask
            | self.ambiguous_mask
            | self.rejected_mask
            | self.issue_mask
        )


@dataclass(frozen=True)
class EvidenceCandidate:
    candidate_id: str
    claim_id: str
    schema_id: str
    mask_state: CandidateMaskState = field(default_factory=CandidateMaskState)
    payload_by_slot: dict[int, Any] = field(default_factory=dict)
    source_refs_by_slot: dict[int, tuple[str, ...]] = field(default_factory=dict)
    normalized_payload_by_slot: dict[int, Any] = field(default_factory=dict)
    alignment_by_slot: dict[int, Any] = field(default_factory=dict)
    tags: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def present_mask(self) -> int:
        return self.mask_state.present_mask

    @property
    def assigned_mask(self) -> int:
        return self.mask_state.assigned_mask

    @property
    def normalized_mask(self) -> int:
        return self.mask_state.normalized_mask

    @property
    def aligned_mask(self) -> int:
        return self.mask_state.aligned_mask

    @property
    def ambiguous_mask(self) -> int:
        return self.mask_state.ambiguous_mask

    @property
    def rejected_mask(self) -> int:
        return self.mask_state.rejected_mask

    @property
    def issue_mask(self) -> int:
        return self.mask_state.issue_mask
