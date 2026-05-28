from __future__ import annotations

import pytest

from synthetic.artifact_factory.compiler import (
    compile_ir_to_bundle_plan,
    compile_scenario_ir,
    compile_scenario_to_bundle_plan,
)
from synthetic.artifact_factory.specs import (
    ScenarioConfusionSpec,
    ScenarioDocumentSpec,
    ScenarioSpec,
)


def test_compile_scenario_ir_preserves_intake_semantics_without_tools() -> None:
    spec = _supplier_correction_spec()

    scenario_ir = compile_scenario_ir(spec)
    payload = scenario_ir.to_dict()

    assert payload["scenario_id"] == "supplier_correction_bundle_001"
    assert payload["rng_seed"] == 14821
    assert payload["intake_events"] == [
        {"event_id": "initial_statement_sent", "ordinal": 0},
        {"event_id": "breakdown_workbook_attached", "ordinal": 1},
        {"event_id": "later_reply_correction_sent", "ordinal": 2},
    ]
    assert payload["document_intents"] == [
        {
            "document_id": "statement",
            "archetype": "supplier_monthly_statement",
            "role": "superseded_summary",
            "carrier": "scanned_pdf",
            "carrier_profile": "fax_scan_medium",
        },
        {
            "document_id": "breakdown",
            "archetype": "supplier_breakdown_workbook",
            "role": "corrected_source",
            "carrier": "xlsx",
        },
        {
            "document_id": "correction_email",
            "archetype": "supplier_correction_reply",
            "role": "correction_context",
            "carrier": "eml",
        },
    ]
    assert payload["confusion_graph"][0] == {
        "confusion_type": "later_correction_overrides_initial",
        "source": "statement",
        "target": "breakdown",
        "params": {"correction_source": "correction_email"},
    }
    assert "renderer" not in repr(payload).lower()
    assert "tool_id" not in repr(payload).lower()


def test_compile_ir_to_bundle_plan_groups_confusions_by_artifact() -> None:
    scenario_ir = compile_scenario_ir(_supplier_correction_spec())

    bundle_plan = compile_ir_to_bundle_plan(scenario_ir)
    payload = bundle_plan.to_dict()

    assert payload["scenario_id"] == "supplier_correction_bundle_001"
    assert payload["expected_syndrome"] == {
        "conflicting_values": True,
        "correction_relation_required": True,
    }

    artifacts = {artifact["artifact_id"]: artifact for artifact in payload["artifacts"]}
    assert artifacts["statement"] == {
        "artifact_id": "statement",
        "carrier": "scanned_pdf",
        "archetype": "supplier_monthly_statement",
        "role": "superseded_summary",
        "evidence_roles_to_realize": ["superseded_summary"],
        "logical_requirements": {
            "evidence_need": {
                "subject": "electricity_usage",
                "site_hint": "OCH-01",
                "period_hint": "2025-03",
            }
        },
        "confusion_requirements": [
            "later_correction_overrides_initial",
            "unit_context_detached",
        ],
        "expected_postconditions": [],
        "carrier_profile": "fax_scan_medium",
    }
    assert artifacts["breakdown"]["confusion_requirements"] == [
        "later_correction_overrides_initial"
    ]
    assert artifacts["correction_email"]["confusion_requirements"] == [
        "later_correction_overrides_initial",
        "quoted_old_value_remains",
    ]


def test_compile_scenario_to_bundle_plan_is_deterministic() -> None:
    spec = _supplier_correction_spec()

    first = compile_scenario_to_bundle_plan(spec).to_dict()
    second = compile_scenario_to_bundle_plan(spec).to_dict()

    assert first == second


def test_compile_scenario_ir_rejects_duplicate_document_ids() -> None:
    spec = ScenarioSpec(
        scenario_id="duplicate_documents",
        seed=1,
        documents=(
            ScenarioDocumentSpec(
                document_id="statement",
                archetype="supplier_monthly_statement",
                role="superseded_summary",
                carrier="scanned_pdf",
            ),
            ScenarioDocumentSpec(
                document_id="statement",
                archetype="supplier_breakdown_workbook",
                role="corrected_source",
                carrier="xlsx",
            ),
        ),
    )

    with pytest.raises(ValueError, match="Duplicate document id"):
        compile_scenario_ir(spec)


def test_compile_scenario_ir_rejects_confusion_with_unknown_document_ref() -> None:
    spec = ScenarioSpec(
        scenario_id="unknown_ref",
        seed=1,
        documents=(
            ScenarioDocumentSpec(
                document_id="statement",
                archetype="supplier_monthly_statement",
                role="superseded_summary",
                carrier="scanned_pdf",
            ),
        ),
        confusions=(
            ScenarioConfusionSpec(
                confusion_type="later_correction_overrides_initial",
                source="statement",
                target="breakdown",
            ),
        ),
    )

    with pytest.raises(ValueError, match="Unknown document reference"):
        compile_scenario_ir(spec)


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
