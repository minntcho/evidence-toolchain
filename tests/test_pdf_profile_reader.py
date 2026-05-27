import json


def _minimal_pdf_bytes(*, pages: int = 2, encrypted: bool = False) -> bytes:
    page_objects = "\n".join(
        f"{index} 0 obj\n<< /Type /Page /Contents {index + 10} 0 R >>\nendobj"
        for index in range(1, pages + 1)
    )
    text_objects = "\n".join(
        f"{index + 10} 0 obj\n<< /Length 32 >>\nstream\nBT (usage 6.4 MWh) Tj ET\nendstream\nendobj"
        for index in range(1, pages + 1)
    )
    encrypt_marker = "\n<< /Encrypt 99 0 R >>" if encrypted else ""
    return (
        "%PDF-1.7\n"
        f"{page_objects}\n"
        f"{text_objects}\n"
        f"{encrypt_marker}\n"
        "trailer\n<< /Root 1 0 R >>\n%%EOF\n"
    ).encode("ascii")


def test_pdf_profile_reader_creates_file_and_page_artifacts(tmp_path):
    from evidence_toolchain.file_routing import FileKindRouter, SafetyPolicy
    from evidence_toolchain.ingestion import RawAttachment
    from evidence_toolchain.readers import PdfProfileReader

    path = tmp_path / "bill.pdf"
    path.write_bytes(_minimal_pdf_bytes(pages=2))
    attachment = RawAttachment.from_path(
        path,
        attachment_id="raw_pdf_001",
        declared_media_type="application/pdf",
    )
    route = FileKindRouter().route(attachment)
    safety = SafetyPolicy().evaluate(attachment)

    inventory = PdfProfileReader().read(
        bundle_id="bundle_001",
        attachment=attachment,
        route_decision=route,
        safety_decision=safety,
    )
    payload = inventory.to_dict()

    assert payload["route_decisions"][0]["route"] == "pdf"
    assert [artifact["artifact_type"] for artifact in payload["artifacts"]] == [
        "file",
        "pdf_page",
        "pdf_page",
    ]
    assert payload["artifacts"][0]["metadata"] == {
        "reader": "pdf_profile_reader",
        "page_count": 2,
        "encrypted": False,
        "has_text_layer": True,
    }
    assert payload["artifacts"][1]["source_locator"] == {
        "file_name": "bill.pdf",
        "page": 1,
    }
    assert payload["units"] == [
        {
            "unit_id": "unit_raw_pdf_001_pdf_profile",
            "artifact_id": "artifact_raw_pdf_001",
            "unit_type": "metadata",
            "producer": "pdf_profile_reader",
            "text": None,
            "value": {
                "encrypted": False,
                "has_text_layer": True,
                "page_count": 2,
            },
            "bbox": None,
            "locator": {},
            "confidence": None,
            "metadata": {},
        }
    ]
    assert "atom_type" not in payload["units"][0]
    json.dumps(payload)


def test_ingest_attachment_dispatches_pdf_profile_route(tmp_path):
    from evidence_toolchain.file_routing import ingest_attachment
    from evidence_toolchain.ingestion import RawAttachment

    path = tmp_path / "profile.pdf"
    path.write_bytes(_minimal_pdf_bytes(pages=1))
    inventory = ingest_attachment(
        "bundle_001",
        RawAttachment.from_path(path, attachment_id="raw_pdf"),
    )
    payload = inventory.to_dict()

    assert payload["route_decisions"][0]["route"] == "pdf"
    assert payload["artifacts"][0]["artifact_type"] == "file"
    assert payload["artifacts"][1]["artifact_type"] == "pdf_page"
    assert payload["units"][0]["unit_type"] == "metadata"
    assert payload["units"][0]["producer"] == "pdf_profile_reader"


def test_pdf_profile_reader_preserves_encrypted_pdf_issue(tmp_path):
    from evidence_toolchain.file_routing import FileKindRouter, SafetyPolicy
    from evidence_toolchain.ingestion import RawAttachment
    from evidence_toolchain.readers import PdfProfileReader

    path = tmp_path / "encrypted.pdf"
    path.write_bytes(_minimal_pdf_bytes(pages=1, encrypted=True))
    attachment = RawAttachment.from_path(path, attachment_id="raw_pdf_encrypted")

    inventory = PdfProfileReader().read(
        bundle_id="bundle_001",
        attachment=attachment,
        route_decision=FileKindRouter().route(attachment),
        safety_decision=SafetyPolicy().evaluate(attachment),
    )
    payload = inventory.to_dict()

    assert payload["artifacts"][0]["metadata"]["encrypted"] is True
    assert payload["issues"][0]["code"] == "encrypted_pdf"
    assert payload["issues"][0]["severity"] == "blocking"


def test_pdf_profile_reader_does_not_import_pdfplumber_docling_or_ocr_dependencies():
    from pathlib import Path

    source = Path("src/evidence_toolchain/readers.py").read_text(encoding="utf-8")
    forbidden_imports = [
        "import pdfplumber",
        "import docling",
        "import ocrmypdf",
        "from pdfplumber",
        "from docling",
        "from ocrmypdf",
    ]

    for forbidden in forbidden_imports:
        assert forbidden not in source
