from __future__ import annotations

import pytest

from synthetic.artifact_factory.compiler import compile_scenario_to_bundle_plan
from synthetic.artifact_factory.plans import ArtifactPlan, BundlePlan
from synthetic.artifact_factory.specs import (
    ScenarioConfusionSpec,
    ScenarioDocumentSpec,
    ScenarioSpec,
)
from synthetic.artifact_factory.tool_planner import compile_bundle_plan_to_tool_plan
from synthetic.artifact_factory import compile_scenario_to_tool_plan


def test_compile_bundle_plan_to_tool_plan_builds_fixed_stack_by_carrier() -> None:
    bundle_plan = compile_scenario_to_bundle_plan(_supplier_correction_spec())

    tool_plan = compile_bundle_plan_to_tool_plan(bundle_plan)
    payload = tool_plan.to_dict()

    assert payload["scenario_id"] == "supplier_correction_bundle_001"

    statement = _invocations_for_artifact(payload, "statement")
    assert [invocation["tool_id"] for invocation in statement] == [
        "archetype.supplier_monthly_statement.build",
        "confusion.later_correction_overrides_initial",
        "confusion.unit_context_detached",
        "renderer.pdf_text",
        "carrier.pdf.rasterize",
        "carrier.image.skew",
        "carrier.image.downsample_upscale",
        "carrier.image.salt_pepper_noise",
        "carrier.pdf.image_only_packager",
    ]
    assert statement[0]["input_state_id"] == "statement.plan"
    assert statement[-1]["output_state_id"] == "statement.scanned_pdf"
    assert _is_linear_chain(statement)

    breakdown = _invocations_for_artifact(payload, "breakdown")
    assert [invocation["tool_id"] for invocation in breakdown] == [
        "archetype.supplier_breakdown_workbook.build",
        "confusion.later_correction_overrides_initial",
        "renderer.xlsx.workbook",
    ]
    assert breakdown[-1]["output_state_id"] == "breakdown.xlsx"

    correction_email = _invocations_for_artifact(payload, "correction_email")
    assert [invocation["tool_id"] for invocation in correction_email] == [
        "archetype.supplier_correction_reply.build",
        "confusion.later_correction_overrides_initial",
        "confusion.quoted_old_value_remains",
        "renderer.eml.message",
    ]
    assert correction_email[-1]["output_state_id"] == "correction_email.eml"


def test_tool_plan_applies_confusions_before_renderers() -> None:
    bundle_plan = compile_scenario_to_bundle_plan(_supplier_correction_spec())

    invocations = compile_bundle_plan_to_tool_plan(bundle_plan).to_dict()["invocations"]

    statement_tools = [item["tool_id"] for item in _select(invocations, "statement")]
    assert statement_tools.index("confusion.unit_context_detached") < statement_tools.index(
        "renderer.pdf_text"
    )

    email_tools = [item["tool_id"] for item in _select(invocations, "correction_email")]
    assert email_tools.index("confusion.quoted_old_value_remains") < email_tools.index(
        "renderer.eml.message"
    )


def test_compile_bundle_plan_to_tool_plan_is_deterministic() -> None:
    bundle_plan = compile_scenario_to_bundle_plan(_supplier_correction_spec())

    first = compile_bundle_plan_to_tool_plan(bundle_plan).to_dict()
    second = compile_bundle_plan_to_tool_plan(bundle_plan).to_dict()

    assert first == second


def test_compile_scenario_to_tool_plan_composes_scenario_compilers() -> None:
    spec = _supplier_correction_spec()

    direct = compile_scenario_to_tool_plan(spec).to_dict()
    staged = compile_bundle_plan_to_tool_plan(
        compile_scenario_to_bundle_plan(spec)
    ).to_dict()

    assert direct == staged


def test_compile_bundle_plan_to_tool_plan_rejects_unknown_carrier() -> None:
    bundle_plan = BundlePlan(
        scenario_id="unsupported_carrier",
        artifacts=(
            ArtifactPlan(
                artifact_id="statement",
                carrier="docx",
                archetype="supplier_monthly_statement",
                role="superseded_summary",
            ),
        ),
    )

    with pytest.raises(ValueError, match="Unsupported artifact carrier"):
        compile_bundle_plan_to_tool_plan(bundle_plan)


def test_compile_bundle_plan_to_tool_plan_rejects_unknown_profile() -> None:
    bundle_plan = BundlePlan(
        scenario_id="unsupported_profile",
        artifacts=(
            ArtifactPlan(
                artifact_id="statement",
                carrier="scanned_pdf",
                archetype="supplier_monthly_statement",
                role="superseded_summary",
                carrier_profile="glitter_scan",
            ),
        ),
    )

    with pytest.raises(ValueError, match="Unsupported carrier profile"):
        compile_bundle_plan_to_tool_plan(bundle_plan)


def _invocations_for_artifact(
    payload: dict[str, object],
    artifact_id: str,
) -> list[dict[str, object]]:
    invocations = payload["invocations"]
    assert isinstance(invocations, list)
    return _select(invocations, artifact_id)


def _select(
    invocations: list[dict[str, object]],
    artifact_id: str,
) -> list[dict[str, object]]:
    return [
        invocation
        for invocation in invocations
        if str(invocation["id"]).startswith(f"{artifact_id}.")
    ]


def _is_linear_chain(invocations: list[dict[str, object]]) -> bool:
    return all(
        previous["output_state_id"] == current["input_state_id"]
        for previous, current in zip(invocations, invocations[1:])
    )


def _supplier_correction_spec() -> ScenarioSpec:
    return ScenarioSpec(
        scenario_id="supplier_correction_bundle_001",
        seed=14821,
        intake_story={
            "actor": "external_supplier",
            "channel": "email_with_attachments",
            "lifecycle": [
                "initial_statement_sent",
                "breakdown_workbook_attached",
                "later_reply_correction_sent",
            ],
        },
        evidence_need={
            "subject": "electricity_usage",
            "site_hint": "OCH-01",
            "period_hint": "2025-03",
        },
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
        expected_syndrome={
            "conflicting_values": True,
            "correction_relation_required": True,
        },
    )
