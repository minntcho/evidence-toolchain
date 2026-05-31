from __future__ import annotations

from evidence_toolchain.convergence.candidates import EvidenceCandidate
from evidence_toolchain.convergence.gaps import CandidateGap
from evidence_toolchain.convergence.patches import CapabilitySpec


def select_capabilities(
    candidate: EvidenceCandidate,
    gap: CandidateGap,
    capabilities: tuple[CapabilitySpec, ...],
) -> tuple[CapabilitySpec, ...]:
    eligible = [
        capability
        for capability in capabilities
        if _is_eligible(candidate, gap, capability)
    ]
    return tuple(sorted(eligible, key=_capability_sort_key))


def _is_eligible(
    candidate: EvidenceCandidate,
    gap: CandidateGap,
    capability: CapabilitySpec,
) -> bool:
    if capability.input_required_mask & ~candidate.present_mask:
        return False

    matching_masks = _matching_gap_masks(gap, capability.handles_gap_kinds)
    if not matching_masks:
        return False

    return any(mask & capability.handles_mask for mask in matching_masks)


def _matching_gap_masks(
    gap: CandidateGap,
    handles_gap_kinds: frozenset[str],
) -> tuple[int, ...]:
    masks: list[int] = []
    if "missing" in handles_gap_kinds and gap.missing_mask:
        masks.append(gap.missing_mask)
    if "unassigned" in handles_gap_kinds and gap.unassigned_mask:
        masks.append(gap.unassigned_mask)
    if "unnormalized" in handles_gap_kinds and gap.unnormalized_mask:
        masks.append(gap.unnormalized_mask)
    if "unaligned" in handles_gap_kinds and gap.unaligned_mask:
        masks.append(gap.unaligned_mask)
    if "ambiguous" in handles_gap_kinds and gap.ambiguous_mask:
        masks.append(gap.ambiguous_mask)
    if "issue" in handles_gap_kinds and gap.issue_mask:
        masks.append(gap.issue_mask)
    return tuple(masks)


def _capability_sort_key(capability: CapabilitySpec) -> tuple[int, int, int, str]:
    return (
        _kind_priority(capability.kind),
        capability.cost,
        len(capability.handles_gap_kinds),
        capability.name,
    )


def _kind_priority(kind: str) -> int:
    if kind == "deterministic":
        return 0
    if kind == "llm":
        return 1
    if kind == "manual":
        return 2
    return 3
