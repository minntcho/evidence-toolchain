import json


def test_file_kind_router_routes_pdf_when_extension_and_magic_match(tmp_path):
    from evidence_toolchain.file_routing import FileKindRouter
    from evidence_toolchain.ingestion import RawAttachment

    path = tmp_path / "invoice.pdf"
    path.write_bytes(b"%PDF-1.7\nfake pdf body")
    attachment = RawAttachment.from_path(
        path,
        attachment_id="raw_pdf_001",
        declared_media_type="application/pdf",
    )

    decision = FileKindRouter().route(attachment)
    payload = decision.to_dict()

    assert payload["attachment_id"] == "raw_pdf_001"
    assert payload["route"] == "pdf"
    assert payload["confidence"] == 0.98
    assert payload["matched_by"] == [
        "extension:.pdf",
        "declared_media_type:application/pdf",
        "magic:%PDF",
    ]
    assert payload["rejected_by"] == []
    assert payload["issues"] == []
    json.dumps(payload)


def test_file_kind_router_records_extension_magic_conflict(tmp_path):
    from evidence_toolchain.file_routing import FileKindRouter
    from evidence_toolchain.ingestion import RawAttachment

    path = tmp_path / "not_really.pdf"
    path.write_text("this is plain text", encoding="utf-8")
    attachment = RawAttachment.from_path(path, attachment_id="raw_bad_pdf")

    decision = FileKindRouter().route(attachment)
    payload = decision.to_dict()

    assert payload["route"] == "unknown"
    assert "extension:.pdf" in payload["matched_by"]
    assert "magic:%PDF_missing" in payload["rejected_by"]
    assert payload["issues"][0]["code"] == "file_signature_mismatch"
    assert payload["issues"][0]["severity"] == "blocking"


def test_safety_policy_blocks_files_above_size_limit(tmp_path):
    from evidence_toolchain.file_routing import SafetyLimits, SafetyPolicy
    from evidence_toolchain.ingestion import RawAttachment

    path = tmp_path / "large.txt"
    path.write_bytes(b"x" * 11)
    attachment = RawAttachment.from_path(path, attachment_id="raw_large")

    decision = SafetyPolicy(SafetyLimits(max_file_size_bytes=10)).evaluate(attachment)
    payload = decision.to_dict()

    assert payload["allowed"] is False
    assert "max_file_size:10" in payload["checked_by"]
    assert payload["issues"][0]["code"] == "file_too_large"
    assert payload["issues"][0]["severity"] == "blocking"


def test_safety_policy_flags_macro_enabled_office_without_execution(tmp_path):
    from evidence_toolchain.file_routing import SafetyPolicy
    from evidence_toolchain.ingestion import RawAttachment

    path = tmp_path / "usage.xlsm"
    path.write_bytes(b"macro workbook placeholder")
    attachment = RawAttachment.from_path(path, attachment_id="raw_macro")

    decision = SafetyPolicy().evaluate(attachment)
    payload = decision.to_dict()

    assert payload["allowed"] is True
    assert "macro_no_execute" in payload["checked_by"]
    assert payload["issues"][0]["code"] == "macro_enabled_office_file"
    assert payload["issues"][0]["severity"] == "warning"


def test_unsupported_reader_preserves_attachment_without_units(tmp_path):
    from evidence_toolchain.file_routing import FileKindRouter, SafetyPolicy, UnsupportedReader
    from evidence_toolchain.ingestion import RawAttachment

    path = tmp_path / "binary.bin"
    path.write_bytes(b"\x00\x01\x02")
    attachment = RawAttachment.from_path(path, attachment_id="raw_unknown")
    safety = SafetyPolicy().evaluate(attachment)
    route = FileKindRouter().route(attachment)

    inventory = UnsupportedReader().read(
        bundle_id="bundle_001",
        attachment=attachment,
        route_decision=route,
        safety_decision=safety,
    )
    payload = inventory.to_dict()

    assert payload["bundle_id"] == "bundle_001"
    assert payload["attachments"][0]["attachment_id"] == "raw_unknown"
    assert payload["artifacts"][0]["artifact_type"] == "unsupported_attachment"
    assert payload["artifacts"][0]["parent_id"] == "raw_unknown"
    assert payload["units"] == []
    assert payload["route_decisions"][0]["route"] == "unknown"
    assert payload["issues"][0]["code"] == "unsupported_media_type"


def test_file_routing_does_not_import_optional_reader_dependencies():
    from pathlib import Path

    source = Path("src/evidence_toolchain/file_routing.py").read_text(encoding="utf-8")
    forbidden_imports = [
        "import pypdf",
        "import pdfplumber",
        "import docling",
        "import ocrmypdf",
        "from pypdf",
        "from pdfplumber",
        "from docling",
        "from ocrmypdf",
    ]

    for forbidden in forbidden_imports:
        assert forbidden not in source
