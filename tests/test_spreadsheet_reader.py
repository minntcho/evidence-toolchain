import json
from zipfile import ZIP_DEFLATED, ZipFile


def _write_minimal_xlsx(path, *, hidden_sheet: bool = False, formula: bool = False):
    sheet_state = ' state="hidden"' if hidden_sheet else ""
    formula_cell = "<f>B2*2</f><v>12800</v>" if formula else "<v>6400</v>"
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>
</Types>
""",
        )
        archive.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>
""",
        )
        archive.writestr(
            "xl/workbook.xml",
            f"""<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
          xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="2025-03" sheetId="1" r:id="rId1"{sheet_state}/>
  </sheets>
</workbook>
""",
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>
""",
        )
        archive.writestr(
            "xl/sharedStrings.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <si><t>site</t></si>
  <si><t>period</t></si>
  <si><t>amount</t></si>
  <si><t>unit</t></si>
  <si><t>OCH-01</t></si>
  <si><t>2025-03</t></si>
  <si><t>kWh</t></si>
</sst>
""",
        )
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            f"""<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <dimension ref="A1:D2"/>
  <sheetData>
    <row r="1">
      <c r="A1" t="s"><v>0</v></c>
      <c r="B1" t="s"><v>1</v></c>
      <c r="C1" t="s"><v>2</v></c>
      <c r="D1" t="s"><v>3</v></c>
    </row>
    <row r="2">
      <c r="A2" t="s"><v>4</v></c>
      <c r="B2" t="s"><v>5</v></c>
      <c r="C2">{formula_cell}</c>
      <c r="D2" t="s"><v>6</v></c>
    </row>
  </sheetData>
</worksheet>
""",
        )


def test_spreadsheet_reader_creates_workbook_sheet_table_and_cell_units(tmp_path):
    from evidence_toolchain.file_routing import FileKindRouter, SafetyPolicy
    from evidence_toolchain.ingestion import RawAttachment
    from evidence_toolchain.readers import SpreadsheetReader

    path = tmp_path / "usage.xlsx"
    _write_minimal_xlsx(path)
    attachment = RawAttachment.from_path(
        path,
        attachment_id="raw_xlsx_001",
        declared_media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    inventory = SpreadsheetReader().read(
        bundle_id="bundle_001",
        attachment=attachment,
        route_decision=FileKindRouter().route(attachment),
        safety_decision=SafetyPolicy().evaluate(attachment),
    )
    payload = inventory.to_dict()

    assert payload["route_decisions"][0]["route"] == "spreadsheet"
    assert [artifact["artifact_type"] for artifact in payload["artifacts"]] == [
        "spreadsheet_workbook",
        "spreadsheet_sheet",
    ]
    assert payload["artifacts"][1]["source_locator"] == {
        "file_name": "usage.xlsx",
        "sheet": "2025-03",
        "sheet_index": 1,
    }
    assert payload["artifacts"][1]["metadata"] == {
        "hidden_state": None,
        "reader": "spreadsheet_reader",
        "used_range": "A1:D2",
    }

    table_unit = payload["units"][0]
    assert table_unit["unit_type"] == "table"
    assert table_unit["metadata"] == {
        "column_count": 4,
        "formula_cell_count": 0,
        "headers": ["site", "period", "amount", "unit"],
        "non_empty_cell_count": 8,
        "row_count": 2,
        "sheet": "2025-03",
        "used_range": "A1:D2",
    }
    cell_units = [unit for unit in payload["units"] if unit["unit_type"] == "table_cell"]
    assert [unit["text"] for unit in cell_units] == [
        "site",
        "period",
        "amount",
        "unit",
        "OCH-01",
        "2025-03",
        "6400",
        "kWh",
    ]
    assert cell_units[6]["locator"] == {
        "cell": "C2",
        "column": 3,
        "column_letter": "C",
        "row": 2,
        "sheet": "2025-03",
    }
    assert cell_units[6]["metadata"] == {
        "data_type": None,
        "formula": None,
        "has_formula": False,
    }
    assert "atom_type" not in cell_units[6]
    json.dumps(payload)


def test_ingest_attachment_dispatches_spreadsheet_route(tmp_path):
    from evidence_toolchain.file_routing import ingest_attachment
    from evidence_toolchain.ingestion import RawAttachment

    path = tmp_path / "monthly_usage.xlsx"
    _write_minimal_xlsx(path)

    inventory = ingest_attachment(
        "bundle_001",
        RawAttachment.from_path(path, attachment_id="raw_xlsx"),
    )
    payload = inventory.to_dict()

    assert payload["route_decisions"][0]["route"] == "spreadsheet"
    assert payload["artifacts"][0]["artifact_type"] == "spreadsheet_workbook"
    assert payload["artifacts"][1]["artifact_type"] == "spreadsheet_sheet"
    assert payload["units"][0]["producer"] == "spreadsheet_reader"


def test_spreadsheet_reader_preserves_formula_without_executing_it(tmp_path):
    from evidence_toolchain.file_routing import FileKindRouter, SafetyPolicy
    from evidence_toolchain.ingestion import RawAttachment
    from evidence_toolchain.readers import SpreadsheetReader

    path = tmp_path / "formula.xlsx"
    _write_minimal_xlsx(path, formula=True)
    attachment = RawAttachment.from_path(path, attachment_id="raw_formula_xlsx")

    inventory = SpreadsheetReader().read(
        bundle_id="bundle_001",
        attachment=attachment,
        route_decision=FileKindRouter().route(attachment),
        safety_decision=SafetyPolicy().evaluate(attachment),
    )
    payload = inventory.to_dict()

    table_unit = payload["units"][0]
    formula_cell = next(unit for unit in payload["units"] if unit["locator"].get("cell") == "C2")

    assert table_unit["metadata"]["formula_cell_count"] == 1
    assert formula_cell["text"] == "12800"
    assert formula_cell["metadata"] == {
        "data_type": None,
        "formula": "B2*2",
        "has_formula": True,
    }
    assert not any(issue["code"] == "evidence_atom_created" for issue in payload["issues"])


def test_spreadsheet_reader_flags_hidden_sheets(tmp_path):
    from evidence_toolchain.file_routing import FileKindRouter, SafetyPolicy
    from evidence_toolchain.ingestion import RawAttachment
    from evidence_toolchain.readers import SpreadsheetReader

    path = tmp_path / "hidden.xlsx"
    _write_minimal_xlsx(path, hidden_sheet=True)
    attachment = RawAttachment.from_path(path, attachment_id="raw_hidden_xlsx")

    inventory = SpreadsheetReader().read(
        bundle_id="bundle_001",
        attachment=attachment,
        route_decision=FileKindRouter().route(attachment),
        safety_decision=SafetyPolicy().evaluate(attachment),
    )
    payload = inventory.to_dict()

    assert payload["artifacts"][1]["metadata"]["hidden_state"] == "hidden"
    assert payload["issues"][0]["code"] == "hidden_spreadsheet_sheet"
    assert payload["issues"][0]["severity"] == "warning"
