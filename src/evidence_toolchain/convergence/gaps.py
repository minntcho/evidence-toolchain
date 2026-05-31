from __future__ import annotations

from dataclasses import dataclass

from evidence_toolchain.convergence.candidates import EvidenceCandidate
from evidence_toolchain.convergence.schemas import EvidenceSchema


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


def compute_candidate_gap(
    candidate: EvidenceCandidate,
    schema: EvidenceSchema,
) -> CandidateGap:
    missing_mask = schema.required_mask & ~candidate.present_mask
    unassigned_mask = candidate.present_mask & schema.required_mask & ~candidate.assigned_mask

    normalization_required_mask = schema.comparable_mask & ~schema.directly_comparable_mask
    unnormalized_mask = (
        candidate.assigned_mask
        & normalization_required_mask
        & ~candidate.normalized_mask
    )

    alignment_ready_mask = candidate.normalized_mask | schema.directly_comparable_mask
    unaligned_mask = (
        candidate.assigned_mask
        & schema.alignment_required_mask
        & alignment_ready_mask
        & ~candidate.aligned_mask
    )

    return CandidateGap(
        missing_mask=missing_mask,
        unassigned_mask=unassigned_mask,
        unnormalized_mask=unnormalized_mask,
        unaligned_mask=unaligned_mask,
        ambiguous_mask=candidate.ambiguous_mask,
        issue_mask=candidate.issue_mask,
    )
