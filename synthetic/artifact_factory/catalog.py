from __future__ import annotations

from dataclasses import dataclass

from synthetic.artifact_factory.plans import ToolPlan
from synthetic.artifact_factory.states import ArtifactState
from synthetic.artifact_factory.tools import (
    ToolContext,
    ToolDescriptor,
    ToolRegistry,
    ToolResult,
)


@dataclass(frozen=True)
class ToolPlanValidationReport:
    checked_invocations: int
    tool_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "checked_invocations": self.checked_invocations,
            "tool_ids": list(self.tool_ids),
        }


@dataclass(frozen=True)
class DescriptorOnlyTool:
    _descriptor: ToolDescriptor

    def descriptor(self) -> ToolDescriptor:
        return self._descriptor

    def execute(
        self,
        input_state: ArtifactState,
        params: dict[str, object],
        ctx: ToolContext,
    ) -> ToolResult:
        raise NotImplementedError(
            f"{self._descriptor.id} is a descriptor-only catalog entry"
        )


def default_tool_descriptors() -> tuple[ToolDescriptor, ...]:
    return (
        _descriptor(
            "archetype.supplier_monthly_statement.build",
            kind="archetype_builder",
            input_state="artifact_plan",
            output_state="logical_document_model",
        ),
        _descriptor(
            "archetype.supplier_breakdown_workbook.build",
            kind="archetype_builder",
            input_state="artifact_plan",
            output_state="logical_document_model",
        ),
        _descriptor(
            "archetype.supplier_correction_reply.build",
            kind="archetype_builder",
            input_state="artifact_plan",
            output_state="logical_document_model",
        ),
        _descriptor(
            "confusion.later_correction_overrides_initial",
            kind="confusion_operator",
            input_state="logical_document_model",
            output_state="logical_document_model",
        ),
        _descriptor(
            "confusion.quoted_old_value_remains",
            kind="confusion_operator",
            input_state="logical_document_model",
            output_state="logical_document_model",
        ),
        _descriptor(
            "confusion.unit_context_detached",
            kind="confusion_operator",
            input_state="logical_document_model",
            output_state="logical_document_model",
        ),
        _descriptor(
            "renderer.pdf_text",
            kind="renderer",
            input_state="logical_document_model",
            output_state="pdf_text_artifact",
            supported_carriers=("pdf_text", "scanned_pdf"),
        ),
        _descriptor(
            "renderer.xlsx.workbook",
            kind="renderer",
            input_state="logical_document_model",
            output_state="xlsx_artifact",
            supported_carriers=("xlsx",),
        ),
        _descriptor(
            "renderer.eml.message",
            kind="renderer",
            input_state="logical_document_model",
            output_state="eml_artifact",
            supported_carriers=("eml",),
        ),
        _descriptor(
            "renderer.csv",
            kind="renderer",
            input_state="logical_document_model",
            output_state="csv_artifact",
            supported_carriers=("csv",),
        ),
        _descriptor(
            "carrier.pdf.rasterize",
            kind="carrier_operator",
            input_state="pdf_text_artifact",
            output_state="page_image_bundle",
            supported_carriers=("scanned_pdf",),
        ),
        _descriptor(
            "carrier.image.skew",
            kind="carrier_operator",
            input_state="page_image_bundle",
            output_state="page_image_bundle",
            supported_carriers=("image", "scanned_pdf"),
            postconditions=("image_geometry_changed", "trace_geometry_transformed"),
        ),
        _descriptor(
            "carrier.image.downsample_upscale",
            kind="carrier_operator",
            input_state="page_image_bundle",
            output_state="page_image_bundle",
            supported_carriers=("image", "scanned_pdf"),
            postconditions=("image_resolution_changed", "trace_preserved"),
        ),
        _descriptor(
            "carrier.image.salt_pepper_noise",
            kind="carrier_operator",
            input_state="page_image_bundle",
            output_state="page_image_bundle",
            supported_carriers=("image", "scanned_pdf"),
            postconditions=("image_noise_changed", "trace_preserved"),
        ),
        _descriptor(
            "carrier.pdf.image_only_packager",
            kind="packager",
            input_state="page_image_bundle",
            output_state="scanned_pdf_artifact",
            supported_carriers=("scanned_pdf",),
            postconditions=("image_only_pdf",),
        ),
    )


def default_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    for descriptor in default_tool_descriptors():
        registry.register(DescriptorOnlyTool(descriptor))
    return registry


def validate_tool_plan_against_registry(
    tool_plan: ToolPlan,
    *,
    registry: ToolRegistry | None = None,
) -> ToolPlanValidationReport:
    registry = default_tool_registry() if registry is None else registry
    checked_tool_ids: list[str] = []
    for invocation in tool_plan.invocations:
        try:
            descriptor = registry.get(invocation.tool_id).descriptor()
        except KeyError as exc:
            raise ValueError(
                f"Unknown tool descriptor: {invocation.tool_id}"
            ) from exc

        input_state = infer_state_type(invocation.input_state_id)
        output_state = infer_state_type(invocation.output_state_id)
        if descriptor.input_state != input_state:
            raise ValueError(
                "ToolPlan state mismatch: "
                f"{invocation.id} expects {descriptor.input_state} input, "
                f"got {input_state}"
            )
        if descriptor.output_state != output_state:
            raise ValueError(
                "ToolPlan state mismatch: "
                f"{invocation.id} emits {output_state}, "
                f"descriptor declares {descriptor.output_state}"
            )
        checked_tool_ids.append(invocation.tool_id)

    return ToolPlanValidationReport(
        checked_invocations=len(checked_tool_ids),
        tool_ids=tuple(checked_tool_ids),
    )


def infer_state_type(state_id: str) -> str:
    if state_id.endswith(".plan"):
        return "artifact_plan"
    if ".logical" in state_id:
        return "logical_document_model"
    if state_id.endswith(".pdf_text"):
        return "pdf_text_artifact"
    if ".page_images" in state_id:
        return "page_image_bundle"
    if state_id.endswith(".scanned_pdf"):
        return "scanned_pdf_artifact"
    if state_id.endswith(".xlsx"):
        return "xlsx_artifact"
    if state_id.endswith(".eml"):
        return "eml_artifact"
    if state_id.endswith(".csv"):
        return "csv_artifact"
    raise ValueError(f"Unknown ToolPlan state id: {state_id}")


def _descriptor(
    tool_id: str,
    *,
    kind: str,
    input_state: str,
    output_state: str,
    supported_carriers: tuple[str, ...] = (),
    postconditions: tuple[str, ...] = (),
) -> ToolDescriptor:
    return ToolDescriptor(
        id=tool_id,
        kind=kind,
        version="0.1",
        implementation_digest=f"descriptor-only:v0:{tool_id}",
        input_state=input_state,
        output_state=output_state,
        supported_carriers=supported_carriers,
        postconditions=postconditions,
    )
