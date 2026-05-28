from __future__ import annotations

from pathlib import Path

import pytest

from synthetic.artifact_factory.ir import ConfusionEdge, DocumentIntent, ScenarioIR
from synthetic.artifact_factory.plans import ToolInvocation, ToolPlan
from synthetic.artifact_factory.specs import ScenarioDocumentSpec, ScenarioSpec
from synthetic.artifact_factory.states import ArtifactState, TraceEntry, TraceLayer
from synthetic.artifact_factory.tools import (
    SyntheticTool,
    ToolContext,
    ToolDescriptor,
    ToolRegistry,
    ToolResult,
)


class DummyTool:
    def __init__(self, descriptor: ToolDescriptor) -> None:
        self._descriptor = descriptor

    def descriptor(self) -> ToolDescriptor:
        return self._descriptor

    def execute(
        self,
        input_state: ArtifactState,
        params: dict[str, object],
        ctx: ToolContext,
    ) -> ToolResult:
        return ToolResult(
            output_state=ArtifactState(
                state_id=f"{input_state.state_id}.out",
                state_type=self._descriptor.output_state,
                artifact_id=input_state.artifact_id,
                carrier=input_state.carrier,
                trace=input_state.trace,
                metadata={"scenario_id": ctx.scenario_id, "params": params},
            )
        )


def test_scenario_spec_is_intake_level_not_tool_level() -> None:
    spec = ScenarioSpec(
        scenario_id="supplier_correction_bundle_001",
        seed=14821,
        intake_story={
            "actor": "external_supplier",
            "channel": "email_with_attachments",
        },
        documents=(
            ScenarioDocumentSpec(
                document_id="statement",
                archetype="supplier_monthly_statement",
                role="superseded_summary",
                carrier="scanned_pdf",
                quality_profile="fax_scan_medium",
            ),
        ),
    )

    payload = spec.to_dict()

    assert payload["scenario_id"] == "supplier_correction_bundle_001"
    assert payload["documents"][0]["quality_profile"] == "fax_scan_medium"
    assert "tool_id" not in payload["documents"][0]
    assert "renderer" not in payload["documents"][0]
    assert "open_cv" not in repr(payload).lower()


def test_scenario_ir_normalizes_document_intents_and_confusion_edges() -> None:
    scenario_ir = ScenarioIR(
        scenario_id="supplier_correction_bundle_001",
        rng_seed=14821,
        document_intents=(
            DocumentIntent(
                document_id="statement",
                archetype="supplier_monthly_statement",
                role="superseded_summary",
                carrier="scanned_pdf",
            ),
        ),
        confusion_graph=(
            ConfusionEdge(
                confusion_type="later_correction_overrides_initial",
                source="statement",
                target="breakdown",
                params={"relation": "superseded_by"},
            ),
        ),
    )

    payload = scenario_ir.to_dict()

    assert payload["rng_seed"] == 14821
    assert payload["document_intents"][0]["document_id"] == "statement"
    assert payload["confusion_graph"][0]["confusion_type"] == (
        "later_correction_overrides_initial"
    )


def test_artifact_state_carries_trace_without_synthetic_oracle() -> None:
    state = ArtifactState(
        state_id="statement.page_images.v1",
        state_type="page_image_bundle",
        artifact_id="statement",
        carrier="scanned_pdf",
        trace=TraceLayer(
            entries=(
                TraceEntry(
                    slot_id="summary_table.rows[0].amount",
                    locator_type="pixel_polygon",
                    locator={
                        "page": 1,
                        "points": [[120, 340], [166, 340], [166, 358], [120, 358]],
                    },
                ),
            )
        ),
    )

    payload = state.to_dict()

    assert payload["state_type"] == "page_image_bundle"
    assert payload["trace"]["entries"][0]["slot_id"] == "summary_table.rows[0].amount"
    assert "latent_oracle" not in payload


def test_tool_descriptor_declares_typed_state_transition() -> None:
    descriptor = ToolDescriptor(
        id="carrier.image.skew",
        kind="carrier_operator",
        version="0.1",
        implementation_digest="sha256:fixture",
        input_state="page_image_bundle",
        output_state="page_image_bundle",
        supported_carriers=("scanned_pdf", "image"),
        params_schema={"degrees": {"type": "number", "minimum": -5, "maximum": 5}},
        postconditions=("image_geometry_changed", "trace_geometry_transformed"),
    )

    payload = descriptor.to_dict()

    assert payload["id"] == "carrier.image.skew"
    assert payload["input_state"] == "page_image_bundle"
    assert payload["output_state"] == "page_image_bundle"
    assert payload["deterministic"] is True


def test_tool_registry_filters_tools_by_capability() -> None:
    registry = ToolRegistry()
    skew = DummyTool(
        ToolDescriptor(
            id="carrier.image.skew",
            kind="carrier_operator",
            version="0.1",
            implementation_digest="sha256:skew",
            input_state="page_image_bundle",
            output_state="page_image_bundle",
            supported_carriers=("scanned_pdf", "image"),
        )
    )
    csv_bom = DummyTool(
        ToolDescriptor(
            id="carrier.csv.add_bom",
            kind="carrier_operator",
            version="0.1",
            implementation_digest="sha256:bom",
            input_state="csv_artifact",
            output_state="csv_artifact",
            supported_carriers=("csv",),
        )
    )

    registry.register(skew)
    registry.register(csv_bom)

    matches = registry.find(
        kind="carrier_operator",
        input_state="page_image_bundle",
        output_state="page_image_bundle",
        carrier="scanned_pdf",
    )

    assert matches == (skew,)


def test_tool_registry_rejects_duplicate_tool_ids() -> None:
    registry = ToolRegistry()
    descriptor = ToolDescriptor(
        id="carrier.image.skew",
        kind="carrier_operator",
        version="0.1",
        implementation_digest="sha256:skew",
        input_state="page_image_bundle",
        output_state="page_image_bundle",
    )

    registry.register(DummyTool(descriptor))

    with pytest.raises(ValueError, match="Duplicate synthetic tool id"):
        registry.register(DummyTool(descriptor))


def test_tool_registry_rejects_invalid_state_transition() -> None:
    registry = ToolRegistry()
    registry.register(
        DummyTool(
            ToolDescriptor(
                id="carrier.image.skew",
                kind="carrier_operator",
                version="0.1",
                implementation_digest="sha256:skew",
                input_state="page_image_bundle",
                output_state="page_image_bundle",
                supported_carriers=("scanned_pdf", "image"),
            )
        )
    )
    csv_state = ArtifactState(
        state_id="breakdown.csv.v1",
        state_type="csv_artifact",
        artifact_id="breakdown",
        carrier="csv",
    )

    with pytest.raises(ValueError, match="cannot accept state type"):
        registry.require_transition("carrier.image.skew", csv_state)


def test_tool_plan_serializes_invocation_dag() -> None:
    plan = ToolPlan(
        scenario_id="supplier_correction_bundle_001",
        invocations=(
            ToolInvocation(
                id="statement.skew",
                tool_id="carrier.image.skew",
                input_state_id="statement.pages.v1",
                output_state_id="statement.pages.v2",
                params={"degrees": 2.1},
                seed=14821,
                required_postconditions=(
                    "image_geometry_changed",
                    "trace_geometry_transformed",
                ),
            ),
        ),
    )

    payload = plan.to_dict()

    assert payload["invocations"][0]["id"] == "statement.skew"
    assert payload["invocations"][0]["tool_id"] == "carrier.image.skew"
    assert payload["invocations"][0]["required_postconditions"] == [
        "image_geometry_changed",
        "trace_geometry_transformed",
    ]


def test_synthetic_tool_protocol_accepts_descriptor_executor_pair(tmp_path: Path) -> None:
    tool: SyntheticTool = DummyTool(
        ToolDescriptor(
            id="renderer.csv",
            kind="renderer",
            version="0.1",
            implementation_digest="sha256:csv",
            input_state="logical_document_model",
            output_state="csv_artifact",
            supported_carriers=("csv",),
        )
    )
    context = ToolContext(
        scenario_id="supplier_correction_bundle_001",
        workdir=tmp_path,
        seed=14821,
    )

    result = tool.execute(
        ArtifactState(
            state_id="breakdown.logical",
            state_type="logical_document_model",
            artifact_id="breakdown",
            carrier="csv",
        ),
        {"delimiter": ";"},
        context,
    )

    assert result.output_state.state_type == "csv_artifact"
    assert result.output_state.metadata["scenario_id"] == "supplier_correction_bundle_001"
