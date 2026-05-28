from __future__ import annotations

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
class SupplierMonthlyStatementBuilderTool:
    def descriptor(self) -> ToolDescriptor:
        return ToolDescriptor(
            id="archetype.supplier_monthly_statement.build",
            kind="archetype_builder",
            version="0.1",
            implementation_digest="pdf-proof:v0:archetype.supplier_monthly_statement.build",
            input_state="artifact_plan",
            output_state="logical_document_model",
            supported_carriers=("pdf_text",),
        )

    def execute(
        self,
        input_state: ArtifactState,
        params: dict[str, object],
        ctx: ToolContext,
    ) -> ToolResult:
        artifact_plan = _artifact_plan_from_state(input_state)
        evidence_need = dict(artifact_plan.logical_requirements.get("evidence_need", {}))
        site = str(evidence_need.get("site_hint", "SITE-001"))
        period = str(evidence_need.get("period_hint", "2025-01"))
        subject = str(evidence_need.get("subject", "activity"))
        amount = str(evidence_need.get("amount", "0"))
        unit = str(evidence_need.get("unit", "unit"))
        lines = (
            {"slot_id": "title", "text": "Supplier Energy Statement", "font_size": 16},
            {"slot_id": "summary.site", "text": f"Site: {site}", "font_size": 12},
            {"slot_id": "summary.period", "text": f"Period: {period}", "font_size": 12},
            {
                "slot_id": "summary.subject",
                "text": f"Activity: {subject}",
                "font_size": 12,
            },
            {
                "slot_id": "summary.amount",
                "text": f"Usage: {amount} {unit}",
                "font_size": 12,
            },
            {
                "slot_id": "unit_context",
                "text": f"All amounts reported in {unit}.",
                "font_size": 10,
            },
        )
        trace = TraceLayer(
            entries=tuple(
                TraceEntry(
                    slot_id=str(line["slot_id"]),
                    locator_type="logical_line",
                    locator={"line_index": index},
                )
                for index, line in enumerate(lines, start=1)
            )
        )
        return ToolResult(
            output_state=ArtifactState(
                state_id=str(ctx.metadata["output_state_id"]),
                state_type="logical_document_model",
                artifact_id=input_state.artifact_id,
                model_ref="metadata.logical_document_model",
                carrier=input_state.carrier,
                trace=trace,
                metadata={
                    "logical_document_model": {
                        "title": "Supplier Energy Statement",
                        "page_size": [612, 792],
                        "lines": list(lines),
                    }
                },
            ),
            postconditions={"logical_document_model_built": True},
        )


@dataclass(frozen=True)
class PdfTextRendererTool:
    def descriptor(self) -> ToolDescriptor:
        return ToolDescriptor(
            id="renderer.pdf_text",
            kind="renderer",
            version="0.1",
            implementation_digest="pdf-proof:v0:renderer.pdf_text",
            input_state="logical_document_model",
            output_state="pdf_text_artifact",
            supported_carriers=("pdf_text",),
            postconditions=("pdf_file_written", "text_layer_present"),
        )

    def execute(
        self,
        input_state: ArtifactState,
        params: dict[str, object],
        ctx: ToolContext,
    ) -> ToolResult:
        model = input_state.metadata["logical_document_model"]
        if not isinstance(model, dict):
            raise ValueError("logical_document_model metadata must be an object")
        lines = [dict(line) for line in model["lines"]]
        page_size = [float(value) for value in model.get("page_size", [612, 792])]

        input_dir = Path(str(ctx.metadata["input_dir"]))
        file_path = input_dir / f"{input_state.artifact_id}.pdf"
        trace = _pdf_trace(lines=lines, page_height=page_size[1])
        file_path.write_bytes(_minimal_text_pdf_bytes(lines=lines, page_size=page_size))

        return ToolResult(
            output_state=ArtifactState(
                state_id=str(ctx.metadata["output_state_id"]),
                state_type="pdf_text_artifact",
                artifact_id=input_state.artifact_id,
                file_ref=f"input/{file_path.name}",
                carrier="pdf_text",
                trace=trace,
                metadata={
                    "media_type": "application/pdf",
                    "page_count": 1,
                    "has_text_layer": True,
                    "line_count": len(lines),
                },
            ),
            postconditions={"pdf_file_written": True, "text_layer_present": True},
            metrics={"page_count": 1, "line_count": len(lines)},
        )


def pdf_execution_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(SupplierMonthlyStatementBuilderTool())
    registry.register(PdfTextRendererTool())
    return registry


def build_pdf_artifact_bundle(
    spec: ScenarioSpec,
    output_dir: str | Path,
) -> GeneratedArtifactBundle:
    bundle_plan = compile_scenario_to_bundle_plan(spec)
    tool_plan = compile_bundle_plan_to_tool_plan(bundle_plan)
    return execute_tool_plan(
        tool_plan,
        output_dir,
        registry=pdf_execution_registry(),
        initial_states=artifact_plan_states(bundle_plan),
    )


def _minimal_text_pdf_bytes(
    *,
    lines: list[dict[object, object]],
    page_size: list[float],
) -> bytes:
    stream = "\n".join(_line_command(line, index) for index, line in enumerate(lines))
    stream_bytes = stream.encode("ascii")
    width = _pdf_number(page_size[0])
    height = _pdf_number(page_size[1])
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {width} {height}] "
            "/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ).encode("ascii"),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        (
            b"<< /Length "
            + str(len(stream_bytes)).encode("ascii")
            + b" >>\nstream\n"
            + stream_bytes
            + b"\nendstream"
        ),
    ]
    content = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, body in enumerate(objects, start=1):
        offsets.append(len(content))
        content.extend(f"{index} 0 obj\n".encode("ascii"))
        content.extend(body)
        content.extend(b"\nendobj\n")
    xref_offset = len(content)
    content.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    content.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        content.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    content.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(content)


def _line_command(line: dict[object, object], index: int) -> str:
    font_size = float(line.get("font_size", 12))
    y = 720 - (index * 24)
    text = _pdf_escape(str(line["text"]))
    return f"BT /F1 {_pdf_number(font_size)} Tf 72 {y} Td ({text}) Tj ET"


def _pdf_trace(*, lines: list[dict[object, object]], page_height: float) -> TraceLayer:
    entries: list[TraceEntry] = []
    for index, line in enumerate(lines, start=1):
        font_size = float(line.get("font_size", 12))
        y = 720 - ((index - 1) * 24)
        text = str(line["text"])
        entries.append(
            TraceEntry(
                slot_id=str(line["slot_id"]),
                locator_type="pdf_text",
                locator={
                    "page": 1,
                    "line_index": index,
                    "bbox": [
                        72,
                        page_height - y - font_size,
                        72 + (len(text) * font_size * 0.55),
                        page_height - y,
                    ],
                    "text": text,
                },
            )
        )
    return TraceLayer(entries=tuple(entries))


def _pdf_escape(value: str) -> str:
    try:
        value.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError("minimal PDF renderer only supports ASCII text") from exc
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _pdf_number(value: float) -> str:
    if value.is_integer():
        return str(int(value))
    return f"{value:.3f}".rstrip("0").rstrip(".")


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
