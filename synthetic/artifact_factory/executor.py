from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from synthetic.artifact_factory.catalog import validate_tool_plan_against_registry
from synthetic.artifact_factory.plans import BundlePlan, ToolPlan
from synthetic.artifact_factory.states import ArtifactState
from synthetic.artifact_factory.tools import ToolContext, ToolRegistry


@dataclass(frozen=True)
class GeneratedArtifactBundle:
    scenario_id: str
    root_dir: Path
    input_dir: Path
    synthetic_dir: Path
    states: tuple[ArtifactState, ...]
    manifest_path: Path
    tool_plan_path: Path
    carrier_trace_path: Path


def artifact_plan_states(bundle_plan: BundlePlan) -> tuple[ArtifactState, ...]:
    return tuple(
        ArtifactState(
            state_id=f"{artifact.artifact_id}.plan",
            state_type="artifact_plan",
            artifact_id=artifact.artifact_id,
            carrier=artifact.carrier,
            metadata={"artifact_plan": artifact.to_dict()},
        )
        for artifact in bundle_plan.artifacts
    )


def execute_tool_plan(
    tool_plan: ToolPlan,
    output_dir: str | Path,
    *,
    registry: ToolRegistry,
    initial_states: tuple[ArtifactState, ...],
) -> GeneratedArtifactBundle:
    validate_tool_plan_against_registry(tool_plan, registry=registry)

    root_dir = Path(output_dir) / tool_plan.scenario_id
    input_dir = root_dir / "input"
    synthetic_dir = root_dir / "_synthetic"
    input_dir.mkdir(parents=True, exist_ok=True)
    synthetic_dir.mkdir(parents=True, exist_ok=True)

    states_by_id = {state.state_id: state for state in initial_states}
    ordered_states = list(initial_states)

    for invocation in tool_plan.invocations:
        input_state = states_by_id.get(invocation.input_state_id)
        if input_state is None:
            raise ValueError(f"Missing input state: {invocation.input_state_id}")

        registry.require_transition(invocation.tool_id, input_state)
        tool = registry.get(invocation.tool_id)
        context = ToolContext(
            scenario_id=tool_plan.scenario_id,
            workdir=root_dir,
            seed=invocation.seed if invocation.seed is not None else 0,
            metadata={
                "input_dir": str(input_dir),
                "synthetic_dir": str(synthetic_dir),
                "invocation_id": invocation.id,
                "output_state_id": invocation.output_state_id,
            },
        )
        result = tool.execute(input_state, invocation.params, context)
        if result.output_state.state_id != invocation.output_state_id:
            raise ValueError(
                f"{invocation.id} returned state {result.output_state.state_id}; "
                f"expected {invocation.output_state_id}"
            )
        states_by_id[result.output_state.state_id] = result.output_state
        ordered_states.append(result.output_state)

    tool_plan_path = synthetic_dir / "tool_plan.json"
    manifest_path = synthetic_dir / "manifest.json"
    carrier_trace_path = synthetic_dir / "carrier_trace.json"

    tool_plan_path.write_text(
        json.dumps(tool_plan.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    final_states = tuple(ordered_states)
    manifest_path.write_text(
        json.dumps(_manifest_payload(tool_plan, final_states), indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    carrier_trace_path.write_text(
        json.dumps(
            {
                "scenario_id": tool_plan.scenario_id,
                "states": {
                    state.state_id: state.to_dict()
                    for state in final_states
                    if state.trace.entries
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    return GeneratedArtifactBundle(
        scenario_id=tool_plan.scenario_id,
        root_dir=root_dir,
        input_dir=input_dir,
        synthetic_dir=synthetic_dir,
        states=final_states,
        manifest_path=manifest_path,
        tool_plan_path=tool_plan_path,
        carrier_trace_path=carrier_trace_path,
    )


def _manifest_payload(
    tool_plan: ToolPlan,
    states: tuple[ArtifactState, ...],
) -> dict[str, object]:
    input_artifacts = [
        {
            "artifact_id": state.artifact_id,
            "carrier": state.carrier,
            "path": state.file_ref,
            "state_id": state.state_id,
        }
        for state in states
        if state.file_ref is not None
    ]
    return {
        "scenario_id": tool_plan.scenario_id,
        "input_artifacts": input_artifacts,
        "synthetic": {
            "tool_plan": "_synthetic/tool_plan.json",
            "carrier_trace": "_synthetic/carrier_trace.json",
        },
    }
