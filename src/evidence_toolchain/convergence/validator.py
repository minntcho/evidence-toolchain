from __future__ import annotations

from dataclasses import dataclass

from evidence_toolchain.convergence.candidates import EvidenceCandidate
from evidence_toolchain.convergence.masks import provenance_present_mask
from evidence_toolchain.convergence.schemas import EvidenceSchema


@dataclass(frozen=True)
class PatchValidationError:
    code: str
    message: str
    mask: int = 0


@dataclass(frozen=True)
class PatchValidationResult:
    accepted: bool
    errors: tuple[PatchValidationError, ...] = ()

    @classmethod
    def accept(cls) -> "PatchValidationResult":
        return cls(accepted=True)

    @classmethod
    def reject(cls, errors: tuple[PatchValidationError, ...]) -> "PatchValidationResult":
        return cls(accepted=False, errors=errors)


def validate_candidate_state(
    candidate: EvidenceCandidate,
    schema: EvidenceSchema,
) -> PatchValidationResult:
    errors: list[PatchValidationError] = []

    if candidate.schema_id != schema.schema_id:
        errors.append(
            PatchValidationError(
                code="schema_id_mismatch",
                message="candidate schema_id must match schema",
            )
        )

    for code, mask in _candidate_masks(candidate):
        unknown_bits = mask & ~schema.schema_mask
        if unknown_bits:
            errors.append(
                PatchValidationError(
                    code=f"{code}_outside_schema",
                    message="candidate mask touches bits outside schema",
                    mask=unknown_bits,
                )
            )

    for code, slot_bits in _candidate_slot_maps(candidate):
        unknown_bits = slot_bits & ~schema.schema_mask
        if unknown_bits:
            errors.append(
                PatchValidationError(
                    code=f"{code}_outside_schema",
                    message="candidate slot map touches bits outside schema",
                    mask=unknown_bits,
                )
            )

    assigned_without_present = candidate.assigned_mask & ~candidate.present_mask
    if assigned_without_present:
        errors.append(
            PatchValidationError(
                code="assigned_without_present",
                message="assigned slots must also be present",
                mask=assigned_without_present,
            )
        )

    normalized_without_assigned = candidate.normalized_mask & ~candidate.assigned_mask
    if normalized_without_assigned:
        errors.append(
            PatchValidationError(
                code="normalized_without_assigned",
                message="normalized slots must also be assigned",
                mask=normalized_without_assigned,
            )
        )

    aligned_without_material = candidate.aligned_mask & ~(
        candidate.normalized_mask | schema.directly_comparable_mask
    )
    if aligned_without_material:
        errors.append(
            PatchValidationError(
                code="aligned_without_normalized_or_directly_comparable",
                message="aligned slots must be normalized or directly comparable",
                mask=aligned_without_material,
            )
        )

    missing_provenance = schema.provenance_required_mask & ~provenance_present_mask(candidate)
    if missing_provenance:
        errors.append(
            PatchValidationError(
                code="missing_required_provenance",
                message="provenance-required slots must have source refs",
                mask=missing_provenance,
            )
        )

    if errors:
        return PatchValidationResult.reject(tuple(errors))
    return PatchValidationResult.accept()


def _candidate_masks(candidate: EvidenceCandidate) -> tuple[tuple[str, int], ...]:
    return (
        ("present_mask", candidate.present_mask),
        ("assigned_mask", candidate.assigned_mask),
        ("normalized_mask", candidate.normalized_mask),
        ("aligned_mask", candidate.aligned_mask),
        ("ambiguous_mask", candidate.ambiguous_mask),
        ("rejected_mask", candidate.rejected_mask),
        ("issue_mask", candidate.issue_mask),
    )


def _candidate_slot_maps(candidate: EvidenceCandidate) -> tuple[tuple[str, int], ...]:
    return (
        ("payload_by_slot", _keys_mask(candidate.payload_by_slot)),
        ("source_refs_by_slot", _keys_mask(candidate.source_refs_by_slot)),
        ("normalized_payload_by_slot", _keys_mask(candidate.normalized_payload_by_slot)),
        ("alignment_by_slot", _keys_mask(candidate.alignment_by_slot)),
    )


def _keys_mask(mapping: dict[int, object]) -> int:
    mask = 0
    for slot_bit in mapping:
        mask |= slot_bit
    return mask
