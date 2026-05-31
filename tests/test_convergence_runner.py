import json

from evidence_toolchain.claims import DeclaredClaim
from evidence_toolchain.ingestion import EvidenceInventory, EvidenceUnit
from evidence_toolchain.issues import EvidenceIssue


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


def _inventory_with_nonblocking_issue() -> EvidenceInventory:
    inventory = _inventory()
    return EvidenceInventory(
        bundle_id=inventory.bundle_id,
        attachments=inventory.attachments,
        artifacts=inventory.artifacts,
        route_decisions=inventory.route_decisions,
        safety_decisions=inventory.safety_decisions,
        units=inventory.units,
        issues=(
            EvidenceIssue(
                code="unsupported_attachment",
                severity="warning",
                message="Attachment preserved as unsupported evidence.",
            ),
        ),
    )


def _conflicting_inventory() -> EvidenceInventory:
    def cell(unit_id, row, column, header, text, value=None):
        return EvidenceUnit(
            unit_id=unit_id,
            artifact_id="artifact_usage",
            unit_type="table_cell",
            producer="fixture_reader",
            text=text,
            value=value,
            locator={"row": row, "column": column, "header": header},
        )

    return EvidenceInventory(
        bundle_id="bundle_001",
        attachments=(),
        artifacts=(),
        route_decisions=(),
        units=(
            cell("row2_site", 2, 1, "site", "OCH-01"),
            cell("row2_period", 2, 2, "period", "2025-03"),
            cell("row2_activity", 2, 3, "activity", "electricity"),
            cell("row2_quantity", 2, 4, "amount", "6.4", 6.4),
            cell("row2_unit", 2, 5, "unit", "MWh"),
            cell("row3_site", 3, 1, "site", "OCH-01"),
            cell("row3_period", 3, 2, "period", "2025-03"),
            cell("row3_activity", 3, 3, "activity", "electricity"),
            cell("row3_quantity", 3, 4, "amount", "6.8", 6.8),
            cell("row3_unit", 3, 5, "unit", "MWh"),
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


def test_run_convergence_cycle_reports_clean_support_with_trace():
    from evidence_toolchain.convergence.runner import run_convergence_cycle

    run = run_convergence_cycle(
        inventory=_inventory(),
        claims=(_claim(),),
        run_id="run_001",
    )

    report = run.report.claim_reports[0]
    event_types = [event.event_type for event in run.final_board.events]

    assert run.stop_reason == "converged"
    assert report.claim_id == "claim_001"
    assert report.claim_alignment_status == "supported_after_unit_normalization"
    assert report.evidence_convergence_status == "evidence_converged"
    assert report.selected_support_set == ("cand_001",)
    assert report.downstream_verdict is None
    assert report.unresolved_gaps == ()
    assert "candidate_seeded" in event_types
    assert "patch_applied" in event_types
    assert event_types[-1] == "finalized"
    json.dumps(run.to_dict())
    json.dumps(run.report.to_dict())


def test_run_convergence_cycle_preserves_nonblocking_issue_when_support_converges():
    from evidence_toolchain.convergence.runner import run_convergence_cycle

    run = run_convergence_cycle(
        inventory=_inventory_with_nonblocking_issue(),
        claims=(_claim(),),
        run_id="run_nonblocking",
    )

    report = run.report.claim_reports[0]

    assert report.claim_alignment_status == "supported_after_unit_normalization"
    assert report.evidence_convergence_status == "evidence_converged"
    assert report.review_triggers == ()
    assert [failure.code for failure in report.partial_failures] == [
        "nonblocking_failure"
    ]
    assert report.partial_failures[0].metadata["issue_code"] == "unsupported_attachment"


def test_run_convergence_cycle_reports_candidate_conflict_without_retiring_candidate():
    from evidence_toolchain.convergence.runner import run_convergence_cycle

    run = run_convergence_cycle(
        inventory=_conflicting_inventory(),
        claims=(_claim(),),
        run_id="run_conflict",
    )

    report = run.report.claim_reports[0]

    assert report.claim_alignment_status == "supported_after_unit_normalization"
    assert report.evidence_convergence_status == "needs_review_due_to_candidate_conflict"
    assert report.selected_support_set == ("cand_001",)
    assert report.candidate_ids == ("cand_001", "cand_002")
    assert [trigger.code for trigger in report.review_triggers] == [
        "candidate_conflict"
    ]


def test_run_convergence_cycle_rejects_unauthorized_patch_producer():
    from evidence_toolchain.convergence.capabilities import QUANTITY, utility_usage_schema
    from evidence_toolchain.convergence.patches import CapabilitySpec, MaskPatch
    from evidence_toolchain.convergence.runner import PatchProducer, run_convergence_cycle

    schema = utility_usage_schema()
    bad_spec = CapabilitySpec(
        name="llm_schema_assigner",
        handles_mask=schema.required_mask,
        input_required_mask=0,
        handles_gap_kinds=frozenset({"missing"}),
        may_set_present_mask=schema.required_mask,
        may_set_assigned_mask=schema.required_mask,
        cost=1,
        kind="llm",
    )

    def bad_patch(candidate, _inventory, _claims, _schema):
        return MaskPatch(
            candidate_id=candidate.candidate_id,
            producer="fake_llm",
            capability_name="llm_schema_assigner",
            set_aligned_mask=QUANTITY,
            alignment_updates={QUANTITY: {"status": "fake_support"}},
        )

    run = run_convergence_cycle(
        inventory=_inventory(),
        claims=(_claim(),),
        capabilities=(PatchProducer(bad_spec, bad_patch),),
        run_id="run_bad_patch",
    )

    report = run.report.claim_reports[0]
    event_types = [event.event_type for event in run.final_board.events]
    candidate = run.final_board.candidates[0]

    assert "patch_proposed" in event_types
    assert "patch_rejected" in event_types
    assert candidate.aligned_mask == 0
    assert report.claim_alignment_status != "supported_after_unit_normalization"
    assert report.evidence_convergence_status != "evidence_converged"
    assert [trigger.code for trigger in report.review_triggers] == ["patch_rejected"]
