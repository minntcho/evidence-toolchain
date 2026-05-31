import json

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
