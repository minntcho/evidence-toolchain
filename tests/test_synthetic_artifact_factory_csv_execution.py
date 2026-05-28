from __future__ import annotations

import csv
import json

import pytest

from synthetic.artifact_factory.csv_tools import (
    build_csv_artifact_bundle,
    csv_execution_registry,
)
from synthetic.artifact_factory.executor import artifact_plan_states, execute_tool_plan
from synthetic.artifact_factory.specs import ScenarioDocumentSpec, ScenarioSpec
from synthetic.artifact_factory.tool_planner import (
    compile_bundle_plan_to_tool_plan,
    compile_scenario_to_tool_plan,
)
from synthetic.artifact_factory.catalog import validate_tool_plan_against_registry
from synthetic.artifact_factory.compiler import compile_scenario_to_bundle_plan


def test_csv_execution_builds_runtime_input_and_synthetic_metadata(tmp_path) -> None:
    generated = build_csv_artifact_bundle(_erp_csv_spec(), tmp_path)

    root_dir = tmp_path / "erp_export_csv_001"
    csv_path = root_dir / "input" / "export.csv"
    synthetic_dir = root_dir / "_synthetic"

    assert generated.root_dir == root_dir
    assert csv_path.exists()
    assert sorted(path.name for path in (root_dir / "input").iterdir()) == [
        "export.csv"
    ]
    assert (synthetic_dir / "tool_plan.json").exists()
    assert (synthetic_dir / "manifest.json").exists()
    assert (synthetic_dir / "carrier_trace.json").exists()

    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert rows == [
        {
            "site": "OCH-01",
            "period": "2025-03",
            "subject": "electricity_usage",
            "amount": "6.4",
            "unit": "MWh",
        }
    ]

    manifest = json.loads((synthetic_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["scenario_id"] == "erp_export_csv_001"
    assert manifest["input_artifacts"] == [
        {
            "artifact_id": "export",
            "carrier": "csv",
            "path": "input/export.csv",
            "state_id": "export.csv",
        }
    ]


def test_csv_executor_keeps_state_chain_and_trace(tmp_path) -> None:
    bundle_plan = compile_scenario_to_bundle_plan(_erp_csv_spec())
    tool_plan = compile_bundle_plan_to_tool_plan(bundle_plan)

    generated = execute_tool_plan(
        tool_plan,
        tmp_path,
        registry=csv_execution_registry(),
        initial_states=artifact_plan_states(bundle_plan),
    )

    states = {state.state_id: state for state in generated.states}
    assert states["export.logical"].state_type == "logical_document_model"
    assert states["export.csv"].state_type == "csv_artifact"
    assert states["export.csv"].file_ref == "input/export.csv"
    assert "rows[0].amount" in {
        entry.slot_id for entry in states["export.csv"].trace.entries
    }

    carrier_trace = json.loads(
        generated.carrier_trace_path.read_text(encoding="utf-8")
    )
    assert "rows[0].amount" in {
        entry["slot_id"]
        for entry in carrier_trace["states"]["export.csv"]["trace"]["entries"]
    }


def test_csv_execution_registry_validates_csv_tool_plan() -> None:
    tool_plan = compile_scenario_to_tool_plan(_erp_csv_spec())

    report = validate_tool_plan_against_registry(
        tool_plan,
        registry=csv_execution_registry(),
    )

    assert report.checked_invocations == 2
    assert report.tool_ids == (
        "archetype.erp_export.build",
        "renderer.csv",
    )


def test_execute_tool_plan_rejects_missing_initial_state(tmp_path) -> None:
    tool_plan = compile_scenario_to_tool_plan(_erp_csv_spec())

    with pytest.raises(ValueError, match="Missing input state"):
        execute_tool_plan(
            tool_plan,
            tmp_path,
            registry=csv_execution_registry(),
            initial_states=(),
        )


def _erp_csv_spec() -> ScenarioSpec:
    return ScenarioSpec(
        scenario_id="erp_export_csv_001",
        seed=31001,
        evidence_need={
            "subject": "electricity_usage",
            "site_hint": "OCH-01",
            "period_hint": "2025-03",
            "amount": 6.4,
            "unit": "MWh",
        },
        documents=(
            ScenarioDocumentSpec(
                document_id="export",
                archetype="erp_export",
                role="source_export",
                carrier="csv",
            ),
        ),
    )
