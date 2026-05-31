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
                unit_id="unit_usage",
                artifact_id="artifact_page_1",
                unit_type="text_span",
                producer="fixture_reader",
                text="electricity usage 6.4 MWh",
            ),
            EvidenceUnit(
                unit_id="unit_period",
                artifact_id="artifact_page_1",
                unit_type="text_span",
                producer="fixture_reader",
                text="service period 2025-03-01 ~ 2025-03-31",
            ),
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


def test_resolution_and_convergence_views_reference_same_case_snapshot():
    from evidence_toolchain.convergence.runner import run_convergence_cycle
    from evidence_toolchain.resolution_cycle import run_resolution_cycle

    inventory = _inventory()
    claims = (_claim(),)

    resolution_run = run_resolution_cycle(
        inventory=inventory,
        claims=claims,
        run_id="resolution_run",
        max_investigation_steps=6,
    )
    convergence_run = run_convergence_cycle(
        inventory=inventory,
        claims=claims,
        run_id="convergence_run",
    )

    resolution_metadata = resolution_run.view_metadata
    convergence_metadata = convergence_run.report.metadata

    assert resolution_metadata["case_snapshot_id"] == convergence_metadata["case_snapshot_id"]
    assert resolution_metadata["strategy_id"] == "resolution_cycle"
    assert convergence_metadata["strategy_id"] == "convergence_mvp"
    assert resolution_metadata["view_kind"] == "EvidenceResolutionGraph"
    assert convergence_metadata["view_kind"] == "ConvergenceReport"
    assert resolution_run.inventory == inventory
    assert convergence_run.inventory == inventory


def test_strategy_run_serialization_exposes_snapshot_metadata():
    from evidence_toolchain.convergence.runner import run_convergence_cycle
    from evidence_toolchain.resolution_cycle import run_resolution_cycle

    inventory = _inventory()
    claims = (_claim(),)

    resolution_payload = run_resolution_cycle(
        inventory=inventory,
        claims=claims,
        run_id="resolution_run",
        max_investigation_steps=1,
    ).to_dict()
    convergence_payload = run_convergence_cycle(
        inventory=inventory,
        claims=claims,
        run_id="convergence_run",
    ).to_dict()

    assert resolution_payload["view_metadata"]["case_snapshot_id"].startswith(
        "case_snapshot:"
    )
    assert convergence_payload["report"]["metadata"]["case_snapshot_id"].startswith(
        "case_snapshot:"
    )
