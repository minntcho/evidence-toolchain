from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

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
class ErpExportBuilderTool:
    def descriptor(self) -> ToolDescriptor:
        return ToolDescriptor(
            id="archetype.erp_export.build",
            kind="archetype_builder",
            version="0.1",
            implementation_digest="csv-proof:v0:archetype.erp_export.build",
            input_state="artifact_plan",
            output_state="logical_document_model",
            supported_carriers=("csv",),
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
        trace = TraceLayer(
            entries=tuple(
                TraceEntry(
                    slot_id=f"rows[0].{column}",
                    locator_type="logical_cell",
                    locator={"row": 0, "column": column},
                )
                for column in columns
            )
        )
        return ToolResult(
            output_state=ArtifactState(
                state_id=str(ctx.metadata["output_state_id"]),
                state_type="logical_document_model",
                artifact_id=input_state.artifact_id,
                model_ref="metadata.logical_model",
                carrier=input_state.carrier,
                trace=trace,
                metadata={
                    "logical_model": {
                        "columns": list(columns),
                        "rows": [row],
                    }
                },
            ),
            postconditions={"logical_model_built": True},
        )


@dataclass(frozen=True)
class CsvRendererTool:
    def descriptor(self) -> ToolDescriptor:
        return ToolDescriptor(
            id="renderer.csv",
            kind="renderer",
            version="0.1",
            implementation_digest="csv-proof:v0:renderer.csv",
            input_state="logical_document_model",
            output_state="csv_artifact",
            supported_carriers=("csv",),
            postconditions=("csv_file_written",),
        )

    def execute(
        self,
        input_state: ArtifactState,
        params: dict[str, object],
        ctx: ToolContext,
    ) -> ToolResult:
        logical_model = input_state.metadata["logical_model"]
        if not isinstance(logical_model, dict):
            raise ValueError("logical_model metadata must be an object")
        columns = [str(column) for column in logical_model["columns"]]
        rows = [dict(row) for row in logical_model["rows"]]

        input_dir = Path(str(ctx.metadata["input_dir"]))
        file_path = input_dir / f"{input_state.artifact_id}.csv"
        with file_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)

        return ToolResult(
            output_state=ArtifactState(
                state_id=str(ctx.metadata["output_state_id"]),
                state_type="csv_artifact",
                artifact_id=input_state.artifact_id,
                file_ref=f"input/{file_path.name}",
                carrier="csv",
                trace=input_state.trace,
                metadata={
                    "media_type": "text/csv",
                    "columns": columns,
                    "row_count": len(rows),
                },
            ),
            postconditions={"csv_file_written": True},
            metrics={"row_count": len(rows), "column_count": len(columns)},
        )


def csv_execution_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(ErpExportBuilderTool())
    registry.register(CsvRendererTool())
    return registry


def build_csv_artifact_bundle(
    spec: ScenarioSpec,
    output_dir: str | Path,
) -> GeneratedArtifactBundle:
    bundle_plan = compile_scenario_to_bundle_plan(spec)
    tool_plan = compile_bundle_plan_to_tool_plan(bundle_plan)
    return execute_tool_plan(
        tool_plan,
        output_dir,
        registry=csv_execution_registry(),
        initial_states=artifact_plan_states(bundle_plan),
    )


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
