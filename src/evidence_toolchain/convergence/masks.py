from __future__ import annotations

from evidence_toolchain.convergence.candidates import EvidenceCandidate


def mask_has_unknown_bits(mask: int, allowed_mask: int) -> bool:
    return bool(mask & ~allowed_mask)


def provenance_present_mask(candidate: EvidenceCandidate) -> int:
    mask = 0
    for slot_bit, refs in candidate.source_refs_by_slot.items():
        if refs:
            mask |= slot_bit
    return mask
