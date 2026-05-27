import json


def test_plain_text_reader_creates_file_artifact_and_line_units(tmp_path):
    from evidence_toolchain.file_routing import FileKindRouter, SafetyPolicy
    from evidence_toolchain.ingestion import RawAttachment
    from evidence_toolchain.readers import PlainTextReader

    path = tmp_path / "usage.txt"
    path.write_text("사용량 6.4 MWh\n기간 2025-03\n", encoding="utf-8")
    attachment = RawAttachment.from_path(path, attachment_id="raw_txt_001")
    route = FileKindRouter().route(attachment)
    safety = SafetyPolicy().evaluate(attachment)

    inventory = PlainTextReader().read(
        bundle_id="bundle_001",
        attachment=attachment,
        route_decision=route,
        safety_decision=safety,
    )
    payload = inventory.to_dict()

    assert payload["artifacts"] == [
        {
            "artifact_id": "artifact_raw_txt_001",
            "artifact_type": "file",
            "parent_id": "raw_txt_001",
            "media_type": "text/plain",
            "source_locator": {"file_name": "usage.txt"},
            "metadata": {"reader": "plain_text_reader"},
            "issues": [
                {
                    "code": "plain_text_low_provenance",
                    "severity": "info",
                    "message": "Plain text is preserved as raw evidence, not final authority.",
                }
            ],
        }
    ]
    assert [unit["unit_type"] for unit in payload["units"]] == [
        "text_span",
        "text_span",
    ]
    assert payload["units"][0]["text"] == "사용량 6.4 MWh"
    assert payload["units"][0]["locator"] == {"line": 1}
    assert payload["units"][0]["producer"] == "plain_text_reader"
    assert "atom_type" not in payload["units"][0]
    assert payload["route_decisions"][0]["route"] == "plain_text"
    assert payload["safety_decisions"][0]["allowed"] is True
    json.dumps(payload)


def test_delimited_table_reader_creates_table_and_cell_units(tmp_path):
    from evidence_toolchain.file_routing import FileKindRouter, SafetyPolicy
    from evidence_toolchain.ingestion import RawAttachment
    from evidence_toolchain.readers import DelimitedTableReader

    path = tmp_path / "usage.csv"
    path.write_text(
        "site,period,amount,unit\nOCH-01,2025-03,6400,kWh\n",
        encoding="utf-8",
    )
    attachment = RawAttachment.from_path(
        path,
        attachment_id="raw_csv_001",
        declared_media_type="text/csv",
    )
    route = FileKindRouter().route(attachment)
    safety = SafetyPolicy().evaluate(attachment)

    inventory = DelimitedTableReader().read(
        bundle_id="bundle_001",
        attachment=attachment,
        route_decision=route,
        safety_decision=safety,
    )
    payload = inventory.to_dict()

    assert payload["artifacts"][0]["artifact_type"] == "file"
    assert payload["artifacts"][0]["media_type"] == "text/csv"
    assert payload["route_decisions"][0]["route"] == "delimited_table"
    assert payload["units"][0]["unit_type"] == "table"
    assert payload["units"][0]["metadata"] == {
        "delimiter": ",",
        "headers": ["site", "period", "amount", "unit"],
        "row_count": 1,
    }
    cell_units = [unit for unit in payload["units"] if unit["unit_type"] == "table_cell"]
    assert [unit["text"] for unit in cell_units] == [
        "OCH-01",
        "2025-03",
        "6400",
        "kWh",
    ]
    assert cell_units[2]["locator"] == {
        "row": 2,
        "column": 3,
        "header": "amount",
    }
    assert "atom_type" not in cell_units[2]
    json.dumps(payload)


def test_ingest_attachment_dispatches_text_csv_and_unsupported_routes(tmp_path):
    from evidence_toolchain.file_routing import ingest_attachment
    from evidence_toolchain.ingestion import RawAttachment

    text_path = tmp_path / "usage.txt"
    text_path.write_text("사용량 6.4 MWh\n", encoding="utf-8")
    csv_path = tmp_path / "usage.csv"
    csv_path.write_text("site,amount\nOCH-01,6400\n", encoding="utf-8")
    bin_path = tmp_path / "raw.bin"
    bin_path.write_bytes(b"\x00\x01")

    text_inventory = ingest_attachment(
        "bundle_001",
        RawAttachment.from_path(text_path, attachment_id="raw_txt"),
    )
    csv_inventory = ingest_attachment(
        "bundle_001",
        RawAttachment.from_path(csv_path, attachment_id="raw_csv"),
    )
    unsupported_inventory = ingest_attachment(
        "bundle_001",
        RawAttachment.from_path(bin_path, attachment_id="raw_bin"),
    )

    assert [unit.unit_type for unit in text_inventory.units] == ["text_span"]
    assert [unit.unit_type for unit in csv_inventory.units] == [
        "table",
        "table_cell",
        "table_cell",
    ]
    assert unsupported_inventory.artifacts[0].artifact_type == "unsupported_attachment"
    assert unsupported_inventory.units == ()


def test_ingest_attachment_preserves_blocked_safety_decision_without_reading(tmp_path):
    from evidence_toolchain.file_routing import SafetyLimits, SafetyPolicy, ingest_attachment
    from evidence_toolchain.ingestion import RawAttachment

    path = tmp_path / "large.txt"
    path.write_text("too large", encoding="utf-8")
    attachment = RawAttachment.from_path(path, attachment_id="raw_large_txt")

    inventory = ingest_attachment(
        "bundle_001",
        attachment,
        safety_policy=SafetyPolicy(SafetyLimits(max_file_size_bytes=1)),
    )
    payload = inventory.to_dict()

    assert payload["safety_decisions"][0]["allowed"] is False
    assert payload["artifacts"][0]["artifact_type"] == "unsupported_attachment"
    assert payload["units"] == []
    assert payload["issues"][0]["code"] == "file_too_large"


def test_plain_text_and_csv_readers_do_not_import_optional_pdf_or_ocr_dependencies():
    from pathlib import Path

    source = Path("src/evidence_toolchain/readers.py").read_text(encoding="utf-8")
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
