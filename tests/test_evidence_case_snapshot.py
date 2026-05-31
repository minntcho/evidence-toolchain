from pathlib import Path

from evidence_toolchain.claims import DeclaredClaim
from evidence_toolchain.ingestion import (
    EvidenceInventory,
    EvidenceUnit,
    RawAttachment,
)


def _attachment(path: Path, *, sha256: str = "abc123") -> RawAttachment:
    return RawAttachment(
        attachment_id="attachment_001",
        original_filename="usage.csv",
        path=path,
        byte_size=42,
        sha256=sha256,
        extension=".csv",
        declared_media_type="text/csv",
    )


def _inventory(*, unit_text: str = "6.4", path: Path | None = None) -> EvidenceInventory:
    return EvidenceInventory(
        bundle_id="bundle_001",
        attachments=(_attachment(path or Path("C:/tmp/a/usage.csv")),),
        artifacts=(),
        route_decisions=(),
        units=(
            EvidenceUnit(
                unit_id="cell_quantity",
                artifact_id="artifact_usage",
                unit_type="table_cell",
                producer="fixture_reader",
                text=unit_text,
                value=float(unit_text),
                locator={"row": 2, "column": 4, "header": "amount"},
            ),
        ),
    )


def _claim(*, amount: int = 6400) -> DeclaredClaim:
    return DeclaredClaim(
        x_id="claim_001",
        fields={"amount": amount, "unit": "kWh"},
    )


def test_case_snapshot_id_is_stable_for_same_case_material():
    from evidence_toolchain.case_snapshot import build_evidence_case_snapshot

    first = build_evidence_case_snapshot(
        inventory=_inventory(),
        claims=(_claim(),),
        schema_bindings=("utility_usage_record.v1",),
    )
    second = build_evidence_case_snapshot(
        inventory=_inventory(),
        claims=(_claim(),),
        schema_bindings=("utility_usage_record.v1",),
    )

    assert first.snapshot_id == second.snapshot_id
    assert first.snapshot_id.startswith("case_snapshot:")
    assert first.inventory is not None
    assert first.claims[0].x_id == "claim_001"
    assert first.schema_bindings == ("utility_usage_record.v1",)


def test_case_snapshot_id_ignores_local_attachment_path():
    from evidence_toolchain.case_snapshot import build_evidence_case_snapshot

    first = build_evidence_case_snapshot(
        inventory=_inventory(path=Path("C:/machine-a/usage.csv")),
        claims=(_claim(),),
    )
    second = build_evidence_case_snapshot(
        inventory=_inventory(path=Path("D:/machine-b/copied/usage.csv")),
        claims=(_claim(),),
    )

    assert first.snapshot_id == second.snapshot_id


def test_case_snapshot_id_changes_when_durable_case_material_changes():
    from evidence_toolchain.case_snapshot import build_evidence_case_snapshot

    baseline = build_evidence_case_snapshot(
        inventory=_inventory(),
        claims=(_claim(),),
        schema_bindings=("utility_usage_record.v1",),
    )

    changed_claim = build_evidence_case_snapshot(
        inventory=_inventory(),
        claims=(_claim(amount=6800),),
        schema_bindings=("utility_usage_record.v1",),
    )
    changed_unit = build_evidence_case_snapshot(
        inventory=_inventory(unit_text="6.8"),
        claims=(_claim(),),
        schema_bindings=("utility_usage_record.v1",),
    )
    changed_schema = build_evidence_case_snapshot(
        inventory=_inventory(),
        claims=(_claim(),),
        schema_bindings=("utility_usage_record.v2",),
    )

    assert changed_claim.snapshot_id != baseline.snapshot_id
    assert changed_unit.snapshot_id != baseline.snapshot_id
    assert changed_schema.snapshot_id != baseline.snapshot_id


def test_case_snapshot_payload_excludes_strategy_view_material():
    from evidence_toolchain.case_snapshot import build_evidence_case_snapshot

    snapshot = build_evidence_case_snapshot(
        inventory=_inventory(),
        claims=(_claim(),),
        metadata={
            "run_id": "run_001",
            "view_kind": "ConvergenceReport",
            "selected_support_set": ("cand_001",),
        },
    )
    payload = snapshot.identity_payload()

    assert "EvidenceResolutionGraph" not in repr(payload)
    assert "ConvergenceReport" not in repr(payload)
    assert "selected_support_set" not in repr(payload)
    assert "metadata" not in payload
