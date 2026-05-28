from __future__ import annotations

import json

import pytest

from synthetic.artifact_factory.catalog import validate_tool_plan_against_registry
from synthetic.artifact_factory.compiler import compile_scenario_to_bundle_plan
from synthetic.artifact_factory.executor import artifact_plan_states, execute_tool_plan
from synthetic.artifact_factory.pdf_tools import (
    build_pdf_artifact_bundle,
    pdf_execution_registry,
)
from synthetic.artifact_factory.specs import ScenarioDocumentSpec, ScenarioSpec
from synthetic.artifact_factory.tool_planner import (
    compile_bundle_plan_to_tool_plan,
    compile_scenario_to_tool_plan,
)


def test_pdf_execution_builds_runtime_input_and_synthetic_metadata(tmp_path) -> None:
    generated = build_pdf_artifact_bundle(_supplier_statement_spec(), tmp_path)

    root_dir = tmp_path / "supplier_statement_pdf_001"
    pdf_path = root_dir / "input" / "statement.pdf"
    synthetic_dir = root_dir / "_synthetic"

    assert generated.root_dir == root_dir
    assert pdf_path.exists()
    assert sorted(path.name for path in (root_dir / "input").iterdir()) == [
        "statement.pdf"
    ]
    assert (synthetic_dir / "tool_plan.json").exists()
    assert (synthetic_dir / "manifest.json").exists()
    assert (synthetic_dir / "carrier_trace.json").exists()

    pdf_bytes = pdf_path.read_bytes()
    assert pdf_bytes.startswith(b"%PDF-1.4")
    assert b"Supplier Energy Statement" in pdf_bytes
    assert b"OCH-01" in pdf_bytes
    assert b"6.4 MWh" in pdf_bytes

    manifest = json.loads((synthetic_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["input_artifacts"] == [
        {
            "artifact_id": "statement",
            "carrier": "pdf_text",
            "path": "input/statement.pdf",
            "state_id": "statement.pdf_text",
        }
    ]


def test_pdf_executor_keeps_state_chain_and_trace(tmp_path) -> None:
    bundle_plan = compile_scenario_to_bundle_plan(_supplier_statement_spec())
    tool_plan = compile_bundle_plan_to_tool_plan(bundle_plan)

    generated = execute_tool_plan(
        tool_plan,
        tmp_path,
        registry=pdf_execution_registry(),
        initial_states=artifact_plan_states(bundle_plan),
    )

    states = {state.state_id: state for state in generated.states}
    assert states["statement.logical"].state_type == "logical_document_model"
    assert states["statement.pdf_text"].state_type == "pdf_text_artifact"
    assert states["statement.pdf_text"].file_ref == "input/statement.pdf"
    assert {
        entry.locator["page"]
        for entry in states["statement.pdf_text"].trace.entries
        if entry.slot_id == "summary.amount"
    } == {1}

    carrier_trace = json.loads(
        generated.carrier_trace_path.read_text(encoding="utf-8")
    )
    assert "summary.amount" in {
        entry["slot_id"]
        for entry in carrier_trace["states"]["statement.pdf_text"]["trace"]["entries"]
    }


def test_pdf_execution_registry_validates_pdf_tool_plan() -> None:
    tool_plan = compile_scenario_to_tool_plan(_supplier_statement_spec())

    report = validate_tool_plan_against_registry(
        tool_plan,
        registry=pdf_execution_registry(),
    )

    assert report.checked_invocations == 2
    assert report.tool_ids == (
        "archetype.supplier_monthly_statement.build",
        "renderer.pdf_text",
    )


def test_generated_pdf_can_be_profiled_by_default_pdf_reader(tmp_path) -> None:
    from evidence_toolchain.file_routing import FileKindRouter, SafetyPolicy
    from evidence_toolchain.ingestion import RawAttachment
    from evidence_toolchain.readers import PdfProfileReader

    generated = build_pdf_artifact_bundle(_supplier_statement_spec(), tmp_path)
    pdf_path = generated.root_dir / "input" / "statement.pdf"
    attachment = RawAttachment.from_path(
        pdf_path,
        attachment_id="generated_statement_pdf",
        declared_media_type="application/pdf",
    )

    inventory = PdfProfileReader().read(
        bundle_id="bundle_001",
        attachment=attachment,
        route_decision=FileKindRouter().route(attachment),
        safety_decision=SafetyPolicy().evaluate(attachment),
    )
    payload = inventory.to_dict()

    assert payload["route_decisions"][0]["route"] == "pdf"
    assert payload["artifacts"][0]["metadata"]["page_count"] == 1
    assert payload["units"][0]["value"] == {
        "encrypted": False,
        "has_text_layer": True,
        "page_count": 1,
    }


def test_generated_pdf_can_be_read_by_pdfplumber_extract_reader(tmp_path) -> None:
    pytest.importorskip("pdfplumber")

    from evidence_toolchain.file_routing import FileKindRouter, SafetyPolicy
    from evidence_toolchain.ingestion import RawAttachment
    from evidence_toolchain.readers import PdfPlumberExtractReader

    generated = build_pdf_artifact_bundle(_supplier_statement_spec(), tmp_path)
    pdf_path = generated.root_dir / "input" / "statement.pdf"
    attachment = RawAttachment.from_path(
        pdf_path,
        attachment_id="generated_statement_pdf",
        declared_media_type="application/pdf",
    )

    inventory = PdfPlumberExtractReader().read(
        bundle_id="bundle_001",
        attachment=attachment,
        route_decision=FileKindRouter().route(attachment),
        safety_decision=SafetyPolicy().evaluate(attachment),
    )
    payload = inventory.to_dict()

    text_units = [unit for unit in payload["units"] if unit["unit_type"] == "text_span"]
    assert "Supplier Energy Statement" in text_units[0]["text"]
    assert "OCH-01" in text_units[0]["text"]
    assert "6.4 MWh" in text_units[0]["text"]
    assert payload["issues"] == []


def test_execute_tool_plan_rejects_missing_pdf_initial_state(tmp_path) -> None:
    tool_plan = compile_scenario_to_tool_plan(_supplier_statement_spec())

    with pytest.raises(ValueError, match="Missing input state"):
        execute_tool_plan(
            tool_plan,
            tmp_path,
            registry=pdf_execution_registry(),
            initial_states=(),
        )


def _supplier_statement_spec() -> ScenarioSpec:
    return ScenarioSpec(
        scenario_id="supplier_statement_pdf_001",
        seed=51001,
        evidence_need={
            "subject": "electricity_usage",
            "site_hint": "OCH-01",
            "period_hint": "2025-03",
            "amount": 6.4,
            "unit": "MWh",
        },
        documents=(
            ScenarioDocumentSpec(
                document_id="statement",
                archetype="supplier_monthly_statement",
                role="superseded_summary",
                carrier="pdf_text",
            ),
        ),
    )
