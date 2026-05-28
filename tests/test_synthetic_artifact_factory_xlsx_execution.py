from __future__ import annotations

import json
from zipfile import ZipFile

import pytest

from synthetic.artifact_factory.catalog import validate_tool_plan_against_registry
from synthetic.artifact_factory.compiler import compile_scenario_to_bundle_plan
from synthetic.artifact_factory.executor import artifact_plan_states, execute_tool_plan
from synthetic.artifact_factory.specs import ScenarioDocumentSpec, ScenarioSpec
from synthetic.artifact_factory.tool_planner import (
    compile_bundle_plan_to_tool_plan,
    compile_scenario_to_tool_plan,
)
from synthetic.artifact_factory.xlsx_tools import (
    build_xlsx_artifact_bundle,
    xlsx_execution_registry,
)


def test_xlsx_execution_builds_runtime_input_and_synthetic_metadata(tmp_path) -> None:
    generated = build_xlsx_artifact_bundle(_supplier_breakdown_spec(), tmp_path)

    root_dir = tmp_path / "supplier_breakdown_xlsx_001"
    xlsx_path = root_dir / "input" / "breakdown.xlsx"
    synthetic_dir = root_dir / "_synthetic"

    assert generated.root_dir == root_dir
    assert xlsx_path.exists()
    assert sorted(path.name for path in (root_dir / "input").iterdir()) == [
        "breakdown.xlsx"
    ]
    assert (synthetic_dir / "tool_plan.json").exists()
    assert (synthetic_dir / "manifest.json").exists()
    assert (synthetic_dir / "carrier_trace.json").exists()

    with ZipFile(xlsx_path) as archive:
        assert "[Content_Types].xml" in archive.namelist()
        assert "xl/workbook.xml" in archive.namelist()
        assert "xl/worksheets/sheet1.xml" in archive.namelist()
        assert "Raw Data" in archive.read("xl/workbook.xml").decode("utf-8")
        assert "OCH-01" in archive.read("xl/sharedStrings.xml").decode("utf-8")

    manifest = json.loads((synthetic_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["input_artifacts"] == [
        {
            "artifact_id": "breakdown",
            "carrier": "xlsx",
            "path": "input/breakdown.xlsx",
            "state_id": "breakdown.xlsx",
        }
    ]


def test_xlsx_executor_keeps_state_chain_and_trace(tmp_path) -> None:
    bundle_plan = compile_scenario_to_bundle_plan(_supplier_breakdown_spec())
    tool_plan = compile_bundle_plan_to_tool_plan(bundle_plan)

    generated = execute_tool_plan(
        tool_plan,
        tmp_path,
        registry=xlsx_execution_registry(),
        initial_states=artifact_plan_states(bundle_plan),
    )

    states = {state.state_id: state for state in generated.states}
    assert states["breakdown.logical"].state_type == "logical_document_model"
    assert states["breakdown.xlsx"].state_type == "xlsx_artifact"
    assert states["breakdown.xlsx"].file_ref == "input/breakdown.xlsx"
    assert "raw_data!D2" in {
        entry.locator["cell"] for entry in states["breakdown.xlsx"].trace.entries
    }

    carrier_trace = json.loads(
        generated.carrier_trace_path.read_text(encoding="utf-8")
    )
    assert "rows[0].amount" in {
        entry["slot_id"]
        for entry in carrier_trace["states"]["breakdown.xlsx"]["trace"]["entries"]
    }


def test_xlsx_execution_registry_validates_xlsx_tool_plan() -> None:
    tool_plan = compile_scenario_to_tool_plan(_supplier_breakdown_spec())

    report = validate_tool_plan_against_registry(
        tool_plan,
        registry=xlsx_execution_registry(),
    )

    assert report.checked_invocations == 2
    assert report.tool_ids == (
        "archetype.supplier_breakdown_workbook.build",
        "renderer.xlsx.workbook",
    )


def test_generated_xlsx_can_be_read_by_spreadsheet_reader(tmp_path) -> None:
    from evidence_toolchain.file_routing import FileKindRouter, SafetyPolicy
    from evidence_toolchain.ingestion import RawAttachment
    from evidence_toolchain.readers import SpreadsheetReader

    generated = build_xlsx_artifact_bundle(_supplier_breakdown_spec(), tmp_path)
    xlsx_path = generated.root_dir / "input" / "breakdown.xlsx"

    inventory = SpreadsheetReader().read(
        bundle_id="bundle_001",
        attachment=RawAttachment.from_path(
            xlsx_path,
            attachment_id="generated_breakdown_xlsx",
        ),
        route_decision=FileKindRouter().route(
            RawAttachment.from_path(xlsx_path, attachment_id="route_xlsx")
        ),
        safety_decision=SafetyPolicy().evaluate(
            RawAttachment.from_path(xlsx_path, attachment_id="safe_xlsx")
        ),
    )
    payload = inventory.to_dict()

    table_unit = payload["units"][0]
    assert table_unit["metadata"]["headers"] == [
        "site",
        "period",
        "subject",
        "amount",
        "unit",
    ]
    assert [unit["text"] for unit in payload["units"] if unit["unit_type"] == "table_cell"] == [
        "site",
        "period",
        "subject",
        "amount",
        "unit",
        "OCH-01",
        "2025-03",
        "electricity_usage",
        "6.4",
        "MWh",
    ]


def test_execute_tool_plan_rejects_missing_xlsx_initial_state(tmp_path) -> None:
    tool_plan = compile_scenario_to_tool_plan(_supplier_breakdown_spec())

    with pytest.raises(ValueError, match="Missing input state"):
        execute_tool_plan(
            tool_plan,
            tmp_path,
            registry=xlsx_execution_registry(),
            initial_states=(),
        )


def _supplier_breakdown_spec() -> ScenarioSpec:
    return ScenarioSpec(
        scenario_id="supplier_breakdown_xlsx_001",
        seed=41001,
        evidence_need={
            "subject": "electricity_usage",
            "site_hint": "OCH-01",
            "period_hint": "2025-03",
            "amount": 6.4,
            "unit": "MWh",
        },
        documents=(
            ScenarioDocumentSpec(
                document_id="breakdown",
                archetype="supplier_breakdown_workbook",
                role="corrected_source",
                carrier="xlsx",
            ),
        ),
    )
