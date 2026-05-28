from __future__ import annotations

from dataclasses import replace

import pytest

from synthetic.artifact_factory.catalog import (
    default_tool_descriptors,
    default_tool_registry,
    infer_state_type,
    validate_tool_plan_against_registry,
)
from synthetic.artifact_factory.plans import ToolInvocation, ToolPlan
from synthetic.artifact_factory.specs import (
    ScenarioConfusionSpec,
    ScenarioDocumentSpec,
    ScenarioSpec,
)
from synthetic.artifact_factory.states import ArtifactState
from synthetic.artifact_factory.tool_planner import compile_scenario_to_tool_plan
from synthetic.artifact_factory.tools import ToolContext, ToolRegistry


def test_default_catalog_covers_fixed_tool_plan_invocations() -> None:
    tool_plan = compile_scenario_to_tool_plan(_supplier_correction_spec())
    planned_tool_ids = {invocation.tool_id for invocation in tool_plan.invocations}

    catalog_tool_ids = {descriptor.id for descriptor in default_tool_descriptors()}

    assert planned_tool_ids <= catalog_tool_ids


def test_validate_tool_plan_against_default_registry_accepts_fixed_stack() -> None:
    tool_plan = compile_scenario_to_tool_plan(_supplier_correction_spec())

    report = validate_tool_plan_against_registry(tool_plan)

    assert report.checked_invocations == len(tool_plan.invocations)
    assert report.tool_ids == tuple(invocation.tool_id for invocation in tool_plan.invocations)


def test_default_registry_filters_descriptors_by_state_and_carrier() -> None:
    registry = default_tool_registry()

    matches = registry.find(
        kind="renderer",
        input_state="logical_document_model",
        output_state="xlsx_artifact",
        carrier="xlsx",
    )

    assert [tool.descriptor().id for tool in matches] == ["renderer.xlsx.workbook"]


def test_descriptor_catalog_entries_are_not_executable_tools(tmp_path) -> None:
    tool = default_tool_registry().get("renderer.csv")

    with pytest.raises(NotImplementedError, match="descriptor-only"):
        tool.execute(
            ArtifactState(
                state_id="breakdown.logical",
                state_type="logical_document_model",
                artifact_id="breakdown",
                carrier="csv",
            ),
            {},
            ToolContext(
                scenario_id="supplier_correction_bundle_001",
                workdir=tmp_path,
                seed=14821,
            ),
        )


def test_validate_tool_plan_rejects_unknown_tool_descriptor() -> None:
    tool_plan = ToolPlan(
        scenario_id="missing_descriptor",
        invocations=(
            ToolInvocation(
                id="statement.missing",
                tool_id="renderer.missing",
                input_state_id="statement.logical",
                output_state_id="statement.csv",
            ),
        ),
    )

    with pytest.raises(ValueError, match="Unknown tool descriptor"):
        validate_tool_plan_against_registry(tool_plan, registry=ToolRegistry())


def test_validate_tool_plan_rejects_state_mismatch() -> None:
    tool_plan = compile_scenario_to_tool_plan(_supplier_correction_spec())
    first = tool_plan.invocations[0]
    bad_invocation = replace(first, input_state_id="statement.page_images")
    bad_plan = ToolPlan(
        scenario_id=tool_plan.scenario_id,
        invocations=(bad_invocation, *tool_plan.invocations[1:]),
    )

    with pytest.raises(ValueError, match="ToolPlan state mismatch"):
        validate_tool_plan_against_registry(bad_plan)


def test_infer_state_type_uses_planner_state_id_conventions() -> None:
    assert infer_state_type("statement.plan") == "artifact_plan"
    assert infer_state_type("statement.logical.v2") == "logical_document_model"
    assert infer_state_type("statement.pdf_text") == "pdf_text_artifact"
    assert infer_state_type("statement.page_images.noisy") == "page_image_bundle"
    assert infer_state_type("statement.scanned_pdf") == "scanned_pdf_artifact"
    assert infer_state_type("breakdown.xlsx") == "xlsx_artifact"
    assert infer_state_type("correction_email.eml") == "eml_artifact"
    assert infer_state_type("export.csv") == "csv_artifact"


def _supplier_correction_spec() -> ScenarioSpec:
    return ScenarioSpec(
        scenario_id="supplier_correction_bundle_001",
        seed=14821,
        documents=(
            ScenarioDocumentSpec(
                document_id="statement",
                archetype="supplier_monthly_statement",
                role="superseded_summary",
                carrier="scanned_pdf",
                quality_profile="fax_scan_medium",
            ),
            ScenarioDocumentSpec(
                document_id="breakdown",
                archetype="supplier_breakdown_workbook",
                role="corrected_source",
                carrier="xlsx",
            ),
            ScenarioDocumentSpec(
                document_id="correction_email",
                archetype="supplier_correction_reply",
                role="correction_context",
                carrier="eml",
            ),
        ),
        confusions=(
            ScenarioConfusionSpec(
                confusion_type="later_correction_overrides_initial",
                source="statement",
                target="breakdown",
                params={"correction_source": "correction_email"},
            ),
            ScenarioConfusionSpec(
                confusion_type="quoted_old_value_remains",
                source="correction_email",
                params={"quoted_source": "statement"},
            ),
            ScenarioConfusionSpec(
                confusion_type="unit_context_detached",
                source="statement",
                params={"placement": "footnote"},
            ),
        ),
    )
