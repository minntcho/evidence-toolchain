import pytest


SITE = 1 << 0
PERIOD = 1 << 1
ACTIVITY = 1 << 2
QUANTITY = 1 << 3
UNIT = 1 << 4
UNKNOWN = 1 << 9


def _usage_schema(*, directly_comparable_mask: int = 0, provenance_required: bool = True):
    from evidence_toolchain.convergence import EvidenceSchema, SlotDef

    return EvidenceSchema(
        schema_id="utility_usage_record.v1",
        slots=(
            SlotDef("site", SITE, "identifier", directly_comparable=bool(directly_comparable_mask & SITE), provenance_required=provenance_required),
            SlotDef("period", PERIOD, "period", comparable=True, directly_comparable=bool(directly_comparable_mask & PERIOD), provenance_required=provenance_required),
            SlotDef("activity", ACTIVITY, "identifier", directly_comparable=bool(directly_comparable_mask & ACTIVITY), provenance_required=provenance_required),
            SlotDef("quantity", QUANTITY, "quantity", comparable=True, directly_comparable=bool(directly_comparable_mask & QUANTITY), provenance_required=provenance_required),
            SlotDef("unit", UNIT, "unit", comparable=True, directly_comparable=bool(directly_comparable_mask & UNIT), provenance_required=provenance_required),
        ),
    )


def _candidate(mask_state, *, source_refs_by_slot=None):
    from evidence_toolchain.convergence import EvidenceCandidate

    return EvidenceCandidate(
        candidate_id="cand_001",
        claim_id="claim_001",
        schema_id="utility_usage_record.v1",
        mask_state=mask_state,
        source_refs_by_slot=source_refs_by_slot or {},
    )


def _error_codes(result):
    return {error.code for error in result.errors}


def test_schema_computes_slot_masks_without_provenance_slot():
    schema = _usage_schema(directly_comparable_mask=SITE | ACTIVITY)

    assert schema.required_mask == SITE | PERIOD | ACTIVITY | QUANTITY | UNIT
    assert schema.comparable_mask == PERIOD | QUANTITY | UNIT
    assert schema.directly_comparable_mask == SITE | ACTIVITY
    assert schema.alignment_required_mask == SITE | PERIOD | ACTIVITY | QUANTITY | UNIT
    assert schema.provenance_required_mask == SITE | PERIOD | ACTIVITY | QUANTITY | UNIT
    assert schema.schema_mask == SITE | PERIOD | ACTIVITY | QUANTITY | UNIT


def test_schema_rejects_duplicate_or_non_single_bit_slots():
    from evidence_toolchain.convergence import EvidenceSchema, SlotDef

    with pytest.raises(ValueError, match="single-bit"):
        SlotDef("bad", SITE | PERIOD, "identifier")

    with pytest.raises(ValueError, match="unique"):
        EvidenceSchema(
            schema_id="bad",
            slots=(
                SlotDef("site", SITE, "identifier"),
                SlotDef("site", PERIOD, "period"),
            ),
        )


def test_candidate_mask_state_is_the_single_mask_holder_for_candidate():
    from evidence_toolchain.convergence import CandidateMaskState

    state = CandidateMaskState(
        present_mask=QUANTITY | UNIT,
        assigned_mask=QUANTITY,
        ambiguous_mask=UNIT,
    )
    candidate = _candidate(state)

    assert candidate.mask_state is state
    assert candidate.present_mask == QUANTITY | UNIT
    assert candidate.assigned_mask == QUANTITY
    assert candidate.ambiguous_mask == UNIT
    assert state.state_mask == QUANTITY | UNIT


def test_candidate_rejects_assigned_without_present():
    from evidence_toolchain.convergence import CandidateMaskState, validate_candidate_state

    result = validate_candidate_state(
        _candidate(CandidateMaskState(assigned_mask=QUANTITY)),
        _usage_schema(provenance_required=False),
    )

    assert result.accepted is False
    assert "assigned_without_present" in _error_codes(result)


def test_candidate_rejects_normalized_without_assigned():
    from evidence_toolchain.convergence import CandidateMaskState, validate_candidate_state

    result = validate_candidate_state(
        _candidate(
            CandidateMaskState(
                present_mask=QUANTITY,
                normalized_mask=QUANTITY,
            )
        ),
        _usage_schema(provenance_required=False),
    )

    assert result.accepted is False
    assert "normalized_without_assigned" in _error_codes(result)


def test_candidate_rejects_aligned_without_normalized_or_direct_comparable_slot():
    from evidence_toolchain.convergence import CandidateMaskState, validate_candidate_state

    result = validate_candidate_state(
        _candidate(
            CandidateMaskState(
                present_mask=QUANTITY,
                assigned_mask=QUANTITY,
                aligned_mask=QUANTITY,
            )
        ),
        _usage_schema(provenance_required=False),
    )

    assert result.accepted is False
    assert "aligned_without_normalized_or_directly_comparable" in _error_codes(result)


def test_candidate_allows_aligned_directly_comparable_slot():
    from evidence_toolchain.convergence import CandidateMaskState, validate_candidate_state

    result = validate_candidate_state(
        _candidate(
            CandidateMaskState(
                present_mask=SITE,
                assigned_mask=SITE,
                aligned_mask=SITE,
            )
        ),
        _usage_schema(directly_comparable_mask=SITE, provenance_required=False),
    )

    assert result.accepted is True


def test_candidate_rejects_schema_outside_bits():
    from evidence_toolchain.convergence import CandidateMaskState, validate_candidate_state

    result = validate_candidate_state(
        _candidate(
            CandidateMaskState(present_mask=UNKNOWN),
            source_refs_by_slot={UNKNOWN: ("xlsx:Sheet1!A1",)},
        ),
        _usage_schema(provenance_required=False),
    )

    assert result.accepted is False
    assert "present_mask_outside_schema" in _error_codes(result)
    assert "source_refs_by_slot_outside_schema" in _error_codes(result)


def test_candidate_requires_source_refs_for_provenance_required_slots():
    from evidence_toolchain.convergence import CandidateMaskState, validate_candidate_state

    result = validate_candidate_state(
        _candidate(
            CandidateMaskState(
                present_mask=SITE | PERIOD | ACTIVITY | QUANTITY | UNIT,
                assigned_mask=SITE | PERIOD | ACTIVITY | QUANTITY | UNIT,
                normalized_mask=PERIOD | QUANTITY | UNIT,
                aligned_mask=SITE | PERIOD | ACTIVITY | QUANTITY | UNIT,
            ),
            source_refs_by_slot={
                SITE: ("xlsx:Sheet1!A2",),
                PERIOD: ("xlsx:Sheet1!B2",),
                ACTIVITY: ("xlsx:Sheet1!C2",),
                QUANTITY: ("xlsx:Sheet1!D2",),
            },
        ),
        _usage_schema(directly_comparable_mask=SITE | ACTIVITY),
    )

    assert result.accepted is False
    assert "missing_required_provenance" in _error_codes(result)
    assert result.errors[-1].mask == UNIT


def test_valid_candidate_state_passes_lattice_and_provenance_checks():
    from evidence_toolchain.convergence import CandidateMaskState, validate_candidate_state

    all_slots = SITE | PERIOD | ACTIVITY | QUANTITY | UNIT
    result = validate_candidate_state(
        _candidate(
            CandidateMaskState(
                present_mask=all_slots,
                assigned_mask=all_slots,
                normalized_mask=PERIOD | QUANTITY | UNIT,
                aligned_mask=all_slots,
            ),
            source_refs_by_slot={
                SITE: ("xlsx:Sheet1!A2",),
                PERIOD: ("xlsx:Sheet1!B2",),
                ACTIVITY: ("xlsx:Sheet1!C2",),
                QUANTITY: ("xlsx:Sheet1!D2",),
                UNIT: ("xlsx:Sheet1!D1",),
            },
        ),
        _usage_schema(directly_comparable_mask=SITE | ACTIVITY),
    )

    assert result.accepted is True
    assert result.errors == ()


def test_mask_patch_reports_touched_mask_from_masks_and_payload_maps():
    from evidence_toolchain.convergence import MaskPatch

    patch = MaskPatch(
        candidate_id="cand_001",
        producer="fixture",
        capability_name="simple_slot_assigner",
        set_present_mask=SITE,
        set_assigned_mask=SITE,
        payload_updates={QUANTITY: 6.4},
        source_ref_updates={UNIT: ("xlsx:Sheet1!D1",)},
    )

    assert patch.touched_mask == SITE | QUANTITY | UNIT


def test_capability_spec_records_permissions_without_applying_them():
    from evidence_toolchain.convergence import CapabilitySpec

    spec = CapabilitySpec(
        name="simple_slot_assigner",
        handles_mask=SITE | PERIOD | ACTIVITY | QUANTITY | UNIT,
        input_required_mask=0,
        handles_gap_kinds=frozenset({"missing", "unassigned"}),
        may_set_present_mask=SITE | PERIOD | ACTIVITY | QUANTITY | UNIT,
        may_set_assigned_mask=SITE | PERIOD | ACTIVITY | QUANTITY | UNIT,
    )

    assert spec.kind == "deterministic"
    assert spec.cost == 10
    assert spec.may_set_aligned_mask == 0
