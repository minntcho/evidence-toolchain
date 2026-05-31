from __future__ import annotations

from dataclasses import dataclass


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
