from evidence_toolchain.claims import DeclaredClaim
from evidence_toolchain.ingestion import EvidenceInventory, EvidenceUnit


def _inventory() -> EvidenceInventory:
    return EvidenceInventory(
        bundle_id="bundle_001",
        attachments=(),
        artifacts=(),
        route_decisions=(),
        units=(
            EvidenceUnit(
                unit_id="cell_site",
                artifact_id="artifact_usage",
                unit_type="table_cell",
                producer="fixture_reader",
                text="OCH-01",
                locator={"row": 2, "column": 1, "header": "site"},
            ),
            EvidenceUnit(
                unit_id="cell_period",
                artifact_id="artifact_usage",
                unit_type="table_cell",
                producer="fixture_reader",
                text="2025-03",
                locator={"row": 2, "column": 2, "header": "period"},
            ),
            EvidenceUnit(
                unit_id="cell_activity",
                artifact_id="artifact_usage",
                unit_type="table_cell",
                producer="fixture_reader",
                text="electricity",
                locator={"row": 2, "column": 3, "header": "activity"},
            ),
            EvidenceUnit(
                unit_id="cell_quantity",
                artifact_id="artifact_usage",
                unit_type="table_cell",
                producer="fixture_reader",
                text="6.4",
                value=6.4,
                locator={"row": 2, "column": 4, "header": "amount"},
            ),
            EvidenceUnit(
                unit_id="cell_unit",
                artifact_id="artifact_usage",
                unit_type="table_cell",
                producer="fixture_reader",
                text="MWh",
                locator={"row": 2, "column": 5, "header": "unit"},
            ),
        ),
    )


def _claim() -> DeclaredClaim:
    return DeclaredClaim(
        x_id="claim_001",
        fields={
            "site": "OCH-01",
            "period": "2025-03",
            "activity": "electricity",
            "amount": 6400,
            "unit": "kWh",
        },
    )


def _apply(candidate, patch, spec, schema):
    from evidence_toolchain.convergence import apply_patch, validate_patch

    validation = validate_patch(candidate, patch, spec, schema)
    assert validation.accepted is True, validation.errors
    return apply_patch(candidate, patch, validation)


def test_clean_support_candidate_converges_through_validated_patches():
    from evidence_toolchain.convergence import compute_candidate_gap, select_capabilities
    from evidence_toolchain.convergence.capabilities import (
        ACTIVITY,
        PERIOD,
        QUANTITY,
        SITE,
        UNIT,
        deterministic_normalizer_spec,
        propose_deterministic_normalization,
        propose_simple_alignment,
        propose_simple_slot_assignment,
        seed_usage_candidate,
        simple_aligner_spec,
        simple_slot_assigner_spec,
        utility_usage_schema,
    )

    schema = utility_usage_schema()
    inventory = _inventory()
    claim = _claim()
    all_slots = SITE | PERIOD | ACTIVITY | QUANTITY | UNIT
    assigner = simple_slot_assigner_spec(schema)
    normalizer = deterministic_normalizer_spec(schema)
    aligner = simple_aligner_spec(schema)

    candidate = seed_usage_candidate(inventory, claim, schema=schema)
    gap = compute_candidate_gap(candidate, schema)
    selected = select_capabilities(candidate, gap, (normalizer, aligner, assigner))

    assert gap.missing_mask == all_slots
    assert selected == (assigner,)

    assignment = propose_simple_slot_assignment(candidate, inventory, schema=schema)
    candidate = _apply(candidate, assignment, assigner, schema)

    assert candidate.present_mask == all_slots
    assert candidate.assigned_mask == all_slots
    assert candidate.payload_by_slot[QUANTITY] == 6.4
    assert candidate.payload_by_slot[UNIT] == "MWh"
    assert candidate.source_refs_by_slot[QUANTITY] == ("cell_quantity",)

    gap = compute_candidate_gap(candidate, schema)
    selected = select_capabilities(candidate, gap, (assigner, aligner, normalizer))

    assert gap.unnormalized_mask == all_slots
    assert selected == (normalizer,)

    normalization = propose_deterministic_normalization(candidate, schema=schema)
    candidate = _apply(candidate, normalization, normalizer, schema)

    assert candidate.normalized_mask == all_slots
    assert candidate.normalized_payload_by_slot[SITE] == "OCH-01"
    assert candidate.normalized_payload_by_slot[PERIOD] == "2025-03"
    assert candidate.normalized_payload_by_slot[ACTIVITY] == "electricity"
    assert candidate.normalized_payload_by_slot[QUANTITY] == 6400
    assert candidate.normalized_payload_by_slot[UNIT] == "kWh"

    gap = compute_candidate_gap(candidate, schema)
    selected = select_capabilities(candidate, gap, (normalizer, assigner, aligner))

    assert gap.unaligned_mask == all_slots
    assert selected == (aligner,)

    alignment = propose_simple_alignment(candidate, claim, schema=schema)
    candidate = _apply(candidate, alignment, aligner, schema)

    assert candidate.aligned_mask == all_slots
    assert candidate.alignment_by_slot[QUANTITY]["claim_value"] == 6400
    assert candidate.alignment_by_slot[QUANTITY]["candidate_value"] == 6400
    assert compute_candidate_gap(candidate, schema).active_mask == 0
