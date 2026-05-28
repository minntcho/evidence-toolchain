from __future__ import annotations

from synthetic.artifact_factory.compiler import compile_scenario_to_bundle_plan
from synthetic.artifact_factory.plans import (
    ArtifactPlan,
    BundlePlan,
    ToolInvocation,
    ToolPlan,
)
from synthetic.artifact_factory.specs import ScenarioSpec


def compile_scenario_to_tool_plan(spec: ScenarioSpec) -> ToolPlan:
    return compile_bundle_plan_to_tool_plan(compile_scenario_to_bundle_plan(spec))


def compile_bundle_plan_to_tool_plan(bundle_plan: BundlePlan) -> ToolPlan:
    invocations: list[ToolInvocation] = []
    for artifact in bundle_plan.artifacts:
        invocations.extend(_plan_artifact(artifact))
    return ToolPlan(
        scenario_id=bundle_plan.scenario_id,
        invocations=tuple(invocations),
    )


def _plan_artifact(artifact: ArtifactPlan) -> list[ToolInvocation]:
    invocations: list[ToolInvocation] = []
    current_state = f"{artifact.artifact_id}.plan"
    current_state = _append(
        invocations,
        artifact,
        step_id="build_model",
        tool_id=f"archetype.{artifact.archetype}.build",
        input_state_id=current_state,
        output_state_id=f"{artifact.artifact_id}.logical",
        params={
            "archetype": artifact.archetype,
            "role": artifact.role,
            "evidence_roles_to_realize": list(artifact.evidence_roles_to_realize),
            "logical_requirements": dict(artifact.logical_requirements),
        },
    )

    for index, confusion in enumerate(artifact.confusion_requirements, start=1):
        current_state = _append(
            invocations,
            artifact,
            step_id=f"confusion.{confusion}",
            tool_id=f"confusion.{confusion}",
            input_state_id=current_state,
            output_state_id=f"{artifact.artifact_id}.logical.v{index}",
            params={"confusion_type": confusion},
        )

    return _append_carrier_stack(invocations, artifact, current_state)


def _append_carrier_stack(
    invocations: list[ToolInvocation],
    artifact: ArtifactPlan,
    current_state: str,
) -> list[ToolInvocation]:
    match artifact.carrier:
        case "scanned_pdf":
            return _append_scanned_pdf_stack(invocations, artifact, current_state)
        case "pdf_text":
            _append(
                invocations,
                artifact,
                step_id="render_pdf_text",
                tool_id="renderer.pdf_text",
                input_state_id=current_state,
                output_state_id=f"{artifact.artifact_id}.pdf_text",
            )
            return invocations
        case "xlsx":
            _append(
                invocations,
                artifact,
                step_id="render_xlsx",
                tool_id="renderer.xlsx.workbook",
                input_state_id=current_state,
                output_state_id=f"{artifact.artifact_id}.xlsx",
            )
            return invocations
        case "eml":
            _append(
                invocations,
                artifact,
                step_id="render_eml",
                tool_id="renderer.eml.message",
                input_state_id=current_state,
                output_state_id=f"{artifact.artifact_id}.eml",
            )
            return invocations
        case "csv":
            _append(
                invocations,
                artifact,
                step_id="render_csv",
                tool_id="renderer.csv",
                input_state_id=current_state,
                output_state_id=f"{artifact.artifact_id}.csv",
            )
            return invocations
        case _:
            raise ValueError(f"Unsupported artifact carrier: {artifact.carrier}")


def _append_scanned_pdf_stack(
    invocations: list[ToolInvocation],
    artifact: ArtifactPlan,
    current_state: str,
) -> list[ToolInvocation]:
    current_state = _append(
        invocations,
        artifact,
        step_id="render_pdf_text",
        tool_id="renderer.pdf_text",
        input_state_id=current_state,
        output_state_id=f"{artifact.artifact_id}.pdf_text",
    )
    current_state = _append(
        invocations,
        artifact,
        step_id="rasterize",
        tool_id="carrier.pdf.rasterize",
        input_state_id=current_state,
        output_state_id=f"{artifact.artifact_id}.page_images",
    )

    for step_id, tool_id, state_suffix in _profile_steps(artifact):
        current_state = _append(
            invocations,
            artifact,
            step_id=step_id,
            tool_id=tool_id,
            input_state_id=current_state,
            output_state_id=f"{artifact.artifact_id}.page_images.{state_suffix}",
            params={"profile": artifact.carrier_profile},
        )

    _append(
        invocations,
        artifact,
        step_id="package_scanned_pdf",
        tool_id="carrier.pdf.image_only_packager",
        input_state_id=current_state,
        output_state_id=f"{artifact.artifact_id}.scanned_pdf",
    )
    return invocations


def _profile_steps(artifact: ArtifactPlan) -> tuple[tuple[str, str, str], ...]:
    match artifact.carrier_profile:
        case None:
            return ()
        case "fax_scan_medium":
            return (
                ("skew", "carrier.image.skew", "skewed"),
                ("downsample_upscale", "carrier.image.downsample_upscale", "downsampled"),
                ("salt_pepper_noise", "carrier.image.salt_pepper_noise", "noisy"),
            )
        case _:
            raise ValueError(
                f"Unsupported carrier profile for {artifact.artifact_id}: "
                f"{artifact.carrier_profile}"
            )


def _append(
    invocations: list[ToolInvocation],
    artifact: ArtifactPlan,
    *,
    step_id: str,
    tool_id: str,
    input_state_id: str,
    output_state_id: str,
    params: dict[str, object] | None = None,
) -> str:
    invocations.append(
        ToolInvocation(
            id=f"{artifact.artifact_id}.{step_id}",
            tool_id=tool_id,
            input_state_id=input_state_id,
            output_state_id=output_state_id,
            params={} if params is None else params,
            required_postconditions=artifact.expected_postconditions,
        )
    )
    return output_state_id
