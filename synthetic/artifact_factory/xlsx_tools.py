from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

from synthetic.artifact_factory.compiler import compile_scenario_to_bundle_plan
from synthetic.artifact_factory.executor import (
    GeneratedArtifactBundle,
    artifact_plan_states,
    execute_tool_plan,
)
from synthetic.artifact_factory.plans import ArtifactPlan
from synthetic.artifact_factory.specs import ScenarioSpec
from synthetic.artifact_factory.states import ArtifactState, TraceEntry, TraceLayer
from synthetic.artifact_factory.tool_planner import compile_bundle_plan_to_tool_plan
from synthetic.artifact_factory.tools import (
    ToolContext,
    ToolDescriptor,
    ToolRegistry,
    ToolResult,
)


@dataclass(frozen=True)
class SupplierBreakdownWorkbookBuilderTool:
    def descriptor(self) -> ToolDescriptor:
        return ToolDescriptor(
            id="archetype.supplier_breakdown_workbook.build",
            kind="archetype_builder",
            version="0.1",
            implementation_digest="xlsx-proof:v0:archetype.supplier_breakdown_workbook.build",
            input_state="artifact_plan",
            output_state="logical_document_model",
            supported_carriers=("xlsx",),
        )

    def execute(
        self,
        input_state: ArtifactState,
        params: dict[str, object],
        ctx: ToolContext,
    ) -> ToolResult:
        artifact_plan = _artifact_plan_from_state(input_state)
        evidence_need = dict(artifact_plan.logical_requirements.get("evidence_need", {}))
        columns = ("site", "period", "subject", "amount", "unit")
        row = {
            "site": str(evidence_need.get("site_hint", "SITE-001")),
            "period": str(evidence_need.get("period_hint", "2025-01")),
            "subject": str(evidence_need.get("subject", "activity")),
            "amount": str(evidence_need.get("amount", "0")),
            "unit": str(evidence_need.get("unit", "unit")),
        }
        cells = {
            "site": "raw_data!A2",
            "period": "raw_data!B2",
            "subject": "raw_data!C2",
            "amount": "raw_data!D2",
            "unit": "raw_data!E2",
        }
        trace = TraceLayer(
            entries=tuple(
                TraceEntry(
                    slot_id=f"rows[0].{column}",
                    locator_type="xlsx_cell",
                    locator={
                        "sheet": "Raw Data",
                        "cell": cells[column],
                    },
                )
                for column in columns
            )
        )
        return ToolResult(
            output_state=ArtifactState(
                state_id=str(ctx.metadata["output_state_id"]),
                state_type="logical_document_model",
                artifact_id=input_state.artifact_id,
                model_ref="metadata.logical_workbook_model",
                carrier=input_state.carrier,
                trace=trace,
                metadata={
                    "logical_workbook_model": {
                        "sheet_name": "Raw Data",
                        "columns": list(columns),
                        "rows": [row],
                    }
                },
            ),
            postconditions={"logical_workbook_model_built": True},
        )


@dataclass(frozen=True)
class XlsxWorkbookRendererTool:
    def descriptor(self) -> ToolDescriptor:
        return ToolDescriptor(
            id="renderer.xlsx.workbook",
            kind="renderer",
            version="0.1",
            implementation_digest="xlsx-proof:v0:renderer.xlsx.workbook",
            input_state="logical_document_model",
            output_state="xlsx_artifact",
            supported_carriers=("xlsx",),
            postconditions=("xlsx_file_written",),
        )

    def execute(
        self,
        input_state: ArtifactState,
        params: dict[str, object],
        ctx: ToolContext,
    ) -> ToolResult:
        model = input_state.metadata["logical_workbook_model"]
        if not isinstance(model, dict):
            raise ValueError("logical_workbook_model metadata must be an object")
        columns = [str(column) for column in model["columns"]]
        rows = [dict(row) for row in model["rows"]]
        sheet_name = str(model["sheet_name"])

        input_dir = Path(str(ctx.metadata["input_dir"]))
        file_path = input_dir / f"{input_state.artifact_id}.xlsx"
        _write_minimal_xlsx(file_path, sheet_name=sheet_name, columns=columns, rows=rows)

        return ToolResult(
            output_state=ArtifactState(
                state_id=str(ctx.metadata["output_state_id"]),
                state_type="xlsx_artifact",
                artifact_id=input_state.artifact_id,
                file_ref=f"input/{file_path.name}",
                carrier="xlsx",
                trace=input_state.trace,
                metadata={
                    "media_type": (
                        "application/vnd.openxmlformats-officedocument."
                        "spreadsheetml.sheet"
                    ),
                    "sheet_names": [sheet_name],
                    "row_count": len(rows),
                    "column_count": len(columns),
                },
            ),
            postconditions={"xlsx_file_written": True},
            metrics={"row_count": len(rows), "column_count": len(columns)},
        )


def xlsx_execution_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(SupplierBreakdownWorkbookBuilderTool())
    registry.register(XlsxWorkbookRendererTool())
    return registry


def build_xlsx_artifact_bundle(
    spec: ScenarioSpec,
    output_dir: str | Path,
) -> GeneratedArtifactBundle:
    bundle_plan = compile_scenario_to_bundle_plan(spec)
    tool_plan = compile_bundle_plan_to_tool_plan(bundle_plan)
    return execute_tool_plan(
        tool_plan,
        output_dir,
        registry=xlsx_execution_registry(),
        initial_states=artifact_plan_states(bundle_plan),
    )


def _write_minimal_xlsx(
    path: Path,
    *,
    sheet_name: str,
    columns: list[str],
    rows: list[dict[object, object]],
) -> None:
    values = _shared_string_values(columns, rows)
    shared_indexes = {value: index for index, value in enumerate(values)}
    header_cells = [
        _shared_string_cell(f"{_column_letter(index)}1", shared_indexes[column])
        for index, column in enumerate(columns, start=1)
    ]
    row_cells = [
        _row_xml(row_index, columns, row, shared_indexes)
        for row_index, row in enumerate(rows, start=2)
    ]
    dimension = f"A1:{_column_letter(len(columns))}{len(rows) + 1}"
    shared_string_items = "".join(
        f"  <si><t>{escape(value)}</t></si>\n" for value in values
    )

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
    <sheet name="{escape(sheet_name)}" sheetId="1" r:id="rId1"/>
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
            f"""<?xml version="1.0" encoding="UTF-8"?>
<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
{shared_string_items}</sst>
""",
        )
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            f"""<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <dimension ref="{dimension}"/>
  <sheetData>
    <row r="1">
      {''.join(header_cells)}
    </row>
    {''.join(row_cells)}
  </sheetData>
</worksheet>
""",
        )


def _shared_string_values(
    columns: list[str],
    rows: list[dict[object, object]],
) -> list[str]:
    values: list[str] = []
    for value in [*columns, *(_string_values(columns, rows))]:
        if value not in values:
            values.append(value)
    return values


def _string_values(columns: list[str], rows: list[dict[object, object]]) -> list[str]:
    values: list[str] = []
    for row in rows:
        for column in columns:
            if column == "amount":
                continue
            values.append(str(row[column]))
    return values


def _row_xml(
    row_index: int,
    columns: list[str],
    row: dict[object, object],
    shared_indexes: dict[str, int],
) -> str:
    cells = []
    for column_index, column in enumerate(columns, start=1):
        cell_ref = f"{_column_letter(column_index)}{row_index}"
        value = str(row[column])
        if column == "amount":
            cells.append(f'<c r="{cell_ref}"><v>{escape(value)}</v></c>')
        else:
            cells.append(_shared_string_cell(cell_ref, shared_indexes[value]))
    return f'<row r="{row_index}">{"".join(cells)}</row>'


def _shared_string_cell(cell_ref: str, index: int) -> str:
    return f'<c r="{cell_ref}" t="s"><v>{index}</v></c>'


def _column_letter(index: int) -> str:
    letters = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def _artifact_plan_from_state(state: ArtifactState) -> ArtifactPlan:
    payload = state.metadata.get("artifact_plan")
    if not isinstance(payload, dict):
        raise ValueError("artifact_plan metadata must be available")
    return ArtifactPlan(
        artifact_id=str(payload["artifact_id"]),
        carrier=str(payload["carrier"]),
        archetype=str(payload["archetype"]),
        role=str(payload["role"]),
        evidence_roles_to_realize=tuple(
            str(item) for item in payload.get("evidence_roles_to_realize", [])
        ),
        logical_requirements=dict(payload.get("logical_requirements", {})),
        confusion_requirements=tuple(
            str(item) for item in payload.get("confusion_requirements", [])
        ),
        carrier_profile=(
            None
            if payload.get("carrier_profile") is None
            else str(payload.get("carrier_profile"))
        ),
        expected_postconditions=tuple(
            str(item) for item in payload.get("expected_postconditions", [])
        ),
    )
