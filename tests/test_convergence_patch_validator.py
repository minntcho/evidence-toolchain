import pytest


SITE = 1 << 0
PERIOD = 1 << 1
ACTIVITY = 1 << 2
QUANTITY = 1 << 3
UNIT = 1 << 4
UNKNOWN = 1 << 9


def _usage_schema(*, directly_comparable_mask: int = 0, provenance_required: bool = False):
    from evidence_toolchain.convergence import EvidenceSchema, SlotDef

    return EvidenceSchema(
        schema_id="utility_usage_record.v1",
        slots=(
            SlotDef(
                "site",
                SITE,
                "identifier",
                directly_comparable=bool(directly_comparable_mask & SITE),
                provenance_required=provenance_required,
            ),
            SlotDef(
                "period",
                PERIOD,
                "period",
                comparable=True,
                directly_comparable=bool(directly_comparable_mask & PERIOD),
                provenance_required=provenance_required,
            ),
            SlotDef(
                "activity",
                ACTIVITY,
                "identifier",
                directly_comparable=bool(directly_comparable_mask & ACTIVITY),
                provenance_required=provenance_required,
            ),
            SlotDef(
                "quantity",
                QUANTITY,
                "quantity",
                comparable=True,
                directly_comparable=bool(directly_comparable_mask & QUANTITY),
                provenance_required=provenance_required,
            ),
            SlotDef(
                "unit",
                UNIT,
                "unit",
                comparable=True,
                directly_comparable=bool(directly_comparable_mask & UNIT),
                provenance_required=provenance_required,
            ),
        ),
    )


def _candidate(mask_state=None):
    from evidence_toolchain.convergence import CandidateMaskState, EvidenceCandidate

    return EvidenceCandidate(
        candidate_id="cand_001",
        claim_id="claim_001",
        schema_id="utility_usage_record.v1",
        mask_state=mask_state or CandidateMaskState(),
    )


def _capability(**overrides):
    from evidence_toolchain.convergence import CapabilitySpec

    values = {
        "name": "simple_slot_assigner",
        "handles_mask": SITE | PERIOD | ACTIVITY | QUANTITY | UNIT,
        "input_required_mask": 0,
        "handles_gap_kinds": frozenset({"missing", "unassigned"}),
        "may_set_present_mask": SITE | PERIOD | ACTIVITY | QUANTITY | UNIT,
        "may_set_assigned_mask": SITE | PERIOD | ACTIVITY | QUANTITY | UNIT,
    }
    values.update(overrides)
    return CapabilitySpec(**values)


def _patch(**overrides):
    from evidence_toolchain.convergence import MaskPatch

    values = {
        "candidate_id": "cand_001",
        "producer": "fixture",
        "capability_name": "simple_slot_assigner",
    }
    values.update(overrides)
    return MaskPatch(**values)


def _error_codes(result):
    return {error.code for error in result.errors}


def test_patch_validator_rejects_permissionless_aligned_mask_update():
    from evidence_toolchain.convergence import (
        CandidateMaskState,
        validate_patch,
    )

    candidate = _candidate(
        CandidateMaskState(
            present_mask=QUANTITY,
            assigned_mask=QUANTITY,
            normalized_mask=QUANTITY,
        )
    )
    patch = _patch(set_aligned_mask=QUANTITY)
    capability = _capability(may_set_aligned_mask=0)

    result = validate_patch(candidate, patch, capability, _usage_schema())

    assert result.accepted is False
    assert "set_aligned_mask_not_permitted" in _error_codes(result)


def test_patch_validator_rejects_payload_update_without_source_ref_update():
    from evidence_toolchain.convergence import validate_patch

    patch = _patch(
        set_present_mask=QUANTITY,
        set_assigned_mask=QUANTITY,
        payload_updates={QUANTITY: 6.4},
    )

    result = validate_patch(_candidate(), patch, _capability(), _usage_schema())

    assert result.accepted is False
    assert "payload_update_missing_source_ref" in _error_codes(result)


def test_patch_validator_rejects_assigned_without_present_after_patch():
    from evidence_toolchain.convergence import validate_patch

    patch = _patch(set_assigned_mask=QUANTITY)

    result = validate_patch(_candidate(), patch, _capability(), _usage_schema())

    assert result.accepted is False
    assert "assigned_without_present" in _error_codes(result)


def test_patch_validator_rejects_normalized_without_assigned_after_patch():
    from evidence_toolchain.convergence import CandidateMaskState, validate_patch

    candidate = _candidate(CandidateMaskState(present_mask=QUANTITY))
    patch = _patch(set_normalized_mask=QUANTITY)
    capability = _capability(may_set_normalized_mask=QUANTITY)

    result = validate_patch(candidate, patch, capability, _usage_schema())

    assert result.accepted is False
    assert "normalized_without_assigned" in _error_codes(result)


def test_patch_validator_rejects_aligned_without_normalized_after_patch():
    from evidence_toolchain.convergence import CandidateMaskState, validate_patch

    candidate = _candidate(
        CandidateMaskState(
            present_mask=QUANTITY,
            assigned_mask=QUANTITY,
        )
    )
    patch = _patch(set_aligned_mask=QUANTITY)
    capability = _capability(may_set_aligned_mask=QUANTITY)

    result = validate_patch(candidate, patch, capability, _usage_schema())

    assert result.accepted is False
    assert "aligned_without_normalized_or_directly_comparable" in _error_codes(result)


def test_apply_patch_requires_accepted_validation_result():
    from evidence_toolchain.convergence import apply_patch, validate_patch

    rejected = validate_patch(
        _candidate(),
        _patch(set_assigned_mask=QUANTITY),
        _capability(),
        _usage_schema(),
    )

    with pytest.raises(ValueError, match="rejected patch"):
        apply_patch(_candidate(), _patch(set_assigned_mask=QUANTITY), rejected)


def test_apply_patch_returns_updated_candidate_without_mutating_original():
    from evidence_toolchain.convergence import apply_patch, validate_patch

    candidate = _candidate()
    patch = _patch(
        set_present_mask=QUANTITY,
        set_assigned_mask=QUANTITY,
        payload_updates={QUANTITY: 6.4},
        source_ref_updates={QUANTITY: ("xlsx:Sheet1!D2",)},
    )
    validation = validate_patch(candidate, patch, _capability(), _usage_schema())

    updated = apply_patch(candidate, patch, validation)

    assert validation.accepted is True
    assert candidate.present_mask == 0
    assert updated.present_mask == QUANTITY
    assert updated.assigned_mask == QUANTITY
    assert updated.payload_by_slot[QUANTITY] == 6.4
    assert updated.source_refs_by_slot[QUANTITY] == ("xlsx:Sheet1!D2",)
