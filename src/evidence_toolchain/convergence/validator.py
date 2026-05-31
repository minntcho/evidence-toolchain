from __future__ import annotations

from dataclasses import dataclass, replace

from evidence_toolchain.convergence.candidates import CandidateMaskState, EvidenceCandidate
from evidence_toolchain.convergence.masks import provenance_present_mask
from evidence_toolchain.convergence.patches import CapabilitySpec, MaskPatch
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


def validate_patch(
    candidate: EvidenceCandidate,
    patch: MaskPatch,
    capability_spec: CapabilitySpec,
    schema: EvidenceSchema,
) -> PatchValidationResult:
    errors: list[PatchValidationError] = []

    if patch.candidate_id != candidate.candidate_id:
        errors.append(
            PatchValidationError(
                code="candidate_id_mismatch",
                message="patch candidate_id must match candidate",
            )
        )

    if patch.capability_name != capability_spec.name:
        errors.append(
            PatchValidationError(
                code="capability_name_mismatch",
                message="patch capability_name must match capability spec",
            )
        )

    missing_input = capability_spec.input_required_mask & ~candidate.present_mask
    if missing_input:
        errors.append(
            PatchValidationError(
                code="input_required_mask_not_satisfied",
                message="candidate does not satisfy capability input requirements",
                mask=missing_input,
            )
        )

    unhandled_slots = patch.touched_mask & ~capability_spec.handles_mask
    if unhandled_slots:
        errors.append(
            PatchValidationError(
                code="patch_touches_unhandled_slots",
                message="patch touches slots outside capability handles_mask",
                mask=unhandled_slots,
            )
        )

    for code, mask in _patch_masks(patch):
        unknown_bits = mask & ~schema.schema_mask
        if unknown_bits:
            errors.append(
                PatchValidationError(
                    code=f"{code}_outside_schema",
                    message="patch mask touches bits outside schema",
                    mask=unknown_bits,
                )
            )

    for code, slot_bits in _patch_slot_maps(patch):
        unknown_bits = slot_bits & ~schema.schema_mask
        if unknown_bits:
            errors.append(
                PatchValidationError(
                    code=f"{code}_outside_schema",
                    message="patch slot map touches bits outside schema",
                    mask=unknown_bits,
                )
            )

    errors.extend(
        _permission_errors(
            "set_present_mask",
            patch.set_present_mask,
            capability_spec.may_set_present_mask,
        )
    )
    errors.extend(
        _permission_errors(
            "set_assigned_mask",
            patch.set_assigned_mask,
            capability_spec.may_set_assigned_mask,
        )
    )
    errors.extend(
        _permission_errors(
            "set_normalized_mask",
            patch.set_normalized_mask,
            capability_spec.may_set_normalized_mask,
        )
    )
    errors.extend(
        _permission_errors(
            "set_aligned_mask",
            patch.set_aligned_mask,
            capability_spec.may_set_aligned_mask,
        )
    )
    errors.extend(
        _permission_errors(
            "set_ambiguous_mask",
            patch.set_ambiguous_mask,
            capability_spec.may_set_ambiguous_mask,
        )
    )
    errors.extend(
        _permission_errors(
            "clear_ambiguous_mask",
            patch.clear_ambiguous_mask,
            capability_spec.may_clear_ambiguous_mask,
        )
    )
    errors.extend(
        _permission_errors(
            "set_issue_mask",
            patch.set_issue_mask,
            capability_spec.may_set_issue_mask,
        )
    )
    errors.extend(
        _permission_errors(
            "clear_issue_mask",
            patch.clear_issue_mask,
            capability_spec.may_clear_issue_mask,
        )
    )

    errors.extend(
        _permission_errors(
            "payload_updates",
            _keys_mask(patch.payload_updates),
            capability_spec.may_set_assigned_mask,
        )
    )
    errors.extend(
        _permission_errors(
            "source_ref_updates",
            _keys_mask(patch.source_ref_updates),
            capability_spec.may_set_present_mask | capability_spec.may_set_assigned_mask,
        )
    )
    errors.extend(
        _permission_errors(
            "normalized_payload_updates",
            _keys_mask(patch.normalized_payload_updates),
            capability_spec.may_set_normalized_mask,
        )
    )
    errors.extend(
        _permission_errors(
            "alignment_updates",
            _keys_mask(patch.alignment_updates),
            capability_spec.may_set_aligned_mask,
        )
    )

    for slot_bit in patch.payload_updates:
        if not patch.source_ref_updates.get(slot_bit):
            errors.append(
                PatchValidationError(
                    code="payload_update_missing_source_ref",
                    message="payload updates must include source refs in the same patch",
                    mask=slot_bit,
                )
            )

    patched_candidate = _candidate_after_patch(candidate, patch)
    candidate_result = validate_candidate_state(patched_candidate, schema)
    errors.extend(candidate_result.errors)

    if errors:
        return PatchValidationResult.reject(tuple(errors))
    return PatchValidationResult.accept()


def apply_patch(
    candidate: EvidenceCandidate,
    patch: MaskPatch,
    validation_result: PatchValidationResult,
) -> EvidenceCandidate:
    if not validation_result.accepted:
        raise ValueError("cannot apply rejected patch")
    return _candidate_after_patch(candidate, patch)


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


def _patch_masks(patch: MaskPatch) -> tuple[tuple[str, int], ...]:
    return (
        ("set_present_mask", patch.set_present_mask),
        ("set_assigned_mask", patch.set_assigned_mask),
        ("set_normalized_mask", patch.set_normalized_mask),
        ("set_aligned_mask", patch.set_aligned_mask),
        ("set_ambiguous_mask", patch.set_ambiguous_mask),
        ("clear_ambiguous_mask", patch.clear_ambiguous_mask),
        ("set_issue_mask", patch.set_issue_mask),
        ("clear_issue_mask", patch.clear_issue_mask),
    )


def _patch_slot_maps(patch: MaskPatch) -> tuple[tuple[str, int], ...]:
    return (
        ("payload_updates", _keys_mask(patch.payload_updates)),
        ("source_ref_updates", _keys_mask(patch.source_ref_updates)),
        ("normalized_payload_updates", _keys_mask(patch.normalized_payload_updates)),
        ("alignment_updates", _keys_mask(patch.alignment_updates)),
    )


def _permission_errors(
    code: str,
    requested_mask: int,
    allowed_mask: int,
) -> tuple[PatchValidationError, ...]:
    disallowed_mask = requested_mask & ~allowed_mask
    if not disallowed_mask:
        return ()
    return (
        PatchValidationError(
            code=f"{code}_not_permitted",
            message="patch is not permitted by capability spec",
            mask=disallowed_mask,
        ),
    )


def _candidate_after_patch(candidate: EvidenceCandidate, patch: MaskPatch) -> EvidenceCandidate:
    return replace(
        candidate,
        mask_state=CandidateMaskState(
            present_mask=candidate.present_mask | patch.set_present_mask,
            assigned_mask=candidate.assigned_mask | patch.set_assigned_mask,
            normalized_mask=candidate.normalized_mask | patch.set_normalized_mask,
            aligned_mask=candidate.aligned_mask | patch.set_aligned_mask,
            ambiguous_mask=(
                candidate.ambiguous_mask | patch.set_ambiguous_mask
            )
            & ~patch.clear_ambiguous_mask,
            rejected_mask=candidate.rejected_mask,
            issue_mask=(candidate.issue_mask | patch.set_issue_mask) & ~patch.clear_issue_mask,
        ),
        payload_by_slot={**candidate.payload_by_slot, **patch.payload_updates},
        source_refs_by_slot=_merge_source_refs(
            candidate.source_refs_by_slot,
            patch.source_ref_updates,
        ),
        normalized_payload_by_slot={
            **candidate.normalized_payload_by_slot,
            **patch.normalized_payload_updates,
        },
        alignment_by_slot={**candidate.alignment_by_slot, **patch.alignment_updates},
    )


def _merge_source_refs(
    current_refs: dict[int, tuple[str, ...]],
    patch_refs: dict[int, tuple[str, ...]],
) -> dict[int, tuple[str, ...]]:
    merged = dict(current_refs)
    for slot_bit, refs in patch_refs.items():
        slot_refs = list(merged.get(slot_bit, ()))
        for ref in refs:
            if ref not in slot_refs:
                slot_refs.append(ref)
        merged[slot_bit] = tuple(slot_refs)
    return merged


def _keys_mask(mapping: dict[int, object]) -> int:
    mask = 0
    for slot_bit in mapping:
        mask |= slot_bit
    return mask
