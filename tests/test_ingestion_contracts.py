import json
from pathlib import Path


def test_raw_attachment_from_path_records_stable_file_identity(tmp_path):
    from evidence_toolchain.ingestion import RawAttachment

    attachment_path = tmp_path / "March Usage.CSV"
    attachment_path.write_text("site,period,amount\nOCH-01,2025-03,6400\n", encoding="utf-8")

    attachment = RawAttachment.from_path(
        attachment_path,
        attachment_id="raw_001",
        declared_media_type="text/csv",
    )
    payload = attachment.to_dict()

    assert payload["attachment_id"] == "raw_001"
    assert payload["original_filename"] == "March Usage.CSV"
    assert payload["path"] == str(Path(attachment_path))
    assert payload["byte_size"] == attachment_path.stat().st_size
    assert payload["extension"] == ".csv"
    assert payload["declared_media_type"] == "text/csv"
    assert len(payload["sha256"]) == 64
    json.dumps(payload)


def test_evidence_inventory_preserves_attachment_artifact_unit_lineage(tmp_path):
    from evidence_toolchain.ingestion import (
        AttachmentBundle,
        EvidenceArtifact,
        EvidenceInventory,
        EvidenceUnit,
        RawAttachment,
        RouteDecision,
        SafetyDecision,
    )
    from evidence_toolchain.issues import EvidenceIssue

    attachment_path = tmp_path / "evidence.txt"
    attachment_path.write_text("사용량 6.4 MWh\n", encoding="utf-8")
    raw = RawAttachment.from_path(attachment_path, attachment_id="raw_001")
    bundle = AttachmentBundle(bundle_id="bundle_001", attachments=(raw,))
    route_decision = RouteDecision(
        attachment_id="raw_001",
        route="plain_text",
        confidence=0.97,
        matched_by=("extension:.txt", "opened_as:utf-8"),
    )
    safety_decision = SafetyDecision(
        attachment_id="raw_001",
        allowed=True,
        checked_by=("byte_size_limit", "no_external_fetch"),
    )
    artifact = EvidenceArtifact(
        artifact_id="art_001",
        artifact_type="file",
        parent_id="raw_001",
        media_type="text/plain",
        source_locator={"file_name": "evidence.txt"},
    )
    unit = EvidenceUnit(
        unit_id="unit_001",
        artifact_id="art_001",
        unit_type="text_span",
        producer="plain_text_reader",
        text="사용량 6.4 MWh",
        locator={"line": 1},
        confidence=None,
    )
    issue = EvidenceIssue(
        code="plain_text_low_provenance",
        severity="info",
        message="Plain text is preserved as raw evidence, not final authority.",
    )

    inventory = EvidenceInventory(
        bundle_id=bundle.bundle_id,
        attachments=bundle.attachments,
        artifacts=(artifact,),
        units=(unit,),
        route_decisions=(route_decision,),
        safety_decisions=(safety_decision,),
        issues=(issue,),
    )
    payload = inventory.to_dict()

    assert payload["bundle_id"] == "bundle_001"
    assert payload["attachments"][0]["attachment_id"] == "raw_001"
    assert payload["artifacts"][0]["parent_id"] == "raw_001"
    assert payload["units"][0]["artifact_id"] == "art_001"
    assert payload["route_decisions"][0]["matched_by"] == [
        "extension:.txt",
        "opened_as:utf-8",
    ]
    assert payload["safety_decisions"][0]["allowed"] is True
    assert payload["issues"][0]["code"] == "plain_text_low_provenance"
    json.dumps(payload)


def test_evidence_unit_is_not_a_semantic_matching_atom():
    from evidence_toolchain.ingestion import EvidenceUnit

    unit = EvidenceUnit(
        unit_id="unit_001",
        artifact_id="art_001",
        unit_type="table_cell",
        producer="csv_reader",
        text="6400",
        value="6400",
        locator={"row": 2, "column": 3},
    )
    payload = unit.to_dict()

    assert payload["unit_type"] == "table_cell"
    assert payload["producer"] == "csv_reader"
    assert "atom_type" not in payload
    assert "x_id" not in payload
    assert "relation" not in payload


def test_planner_issues_use_shared_contract_type(tmp_path):
    from evidence_toolchain import EvidenceDocument
    from evidence_toolchain.issues import EvidenceIssue
    from evidence_toolchain.planner import plan_document

    document_path = tmp_path / "unknown.txt"
    document_path.write_text("알 수 없는 증거 문서\n", encoding="utf-8")

    plan = plan_document(EvidenceDocument.from_path(document_path))

    assert isinstance(plan.issues[0], EvidenceIssue)
    assert plan.issues[0].to_dict()["code"] == "unsupported_media_type"


def test_core_ingestion_contracts_do_not_import_optional_reader_dependencies():
    forbidden_imports = [
        "import pypdf",
        "import pdfplumber",
        "import docling",
        "import ocrmypdf",
        "import tesseract",
        "from pypdf",
        "from pdfplumber",
        "from docling",
        "from ocrmypdf",
        "from tesseract",
    ]

    core_files = [
        path
        for path in Path("src/evidence_toolchain").rglob("*.py")
        if "__pycache__" not in path.parts
    ]

    assert core_files
    for path in core_files:
        source = path.read_text(encoding="utf-8")
        for forbidden in forbidden_imports:
            assert forbidden not in source, f"{path} imports optional reader {forbidden}"
