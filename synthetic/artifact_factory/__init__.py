"""Contracts for the synthetic artifact factory testkit."""

from synthetic.artifact_factory.catalog import (
    DescriptorOnlyTool,
    ToolPlanValidationReport,
    default_tool_descriptors,
    default_tool_registry,
    infer_state_type,
    validate_tool_plan_against_registry,
)
from synthetic.artifact_factory.compiler import (
    compile_ir_to_bundle_plan,
    compile_scenario_ir,
    compile_scenario_to_bundle_plan,
)
from synthetic.artifact_factory.ir import ConfusionEdge, DocumentIntent, ScenarioIR
from synthetic.artifact_factory.plans import (
    ArtifactPlan,
    BundlePlan,
    ToolInvocation,
    ToolPlan,
)
from synthetic.artifact_factory.specs import (
    ScenarioConfusionSpec,
    ScenarioDocumentSpec,
    ScenarioSpec,
)
from synthetic.artifact_factory.states import ArtifactState, TraceEntry, TraceLayer
from synthetic.artifact_factory.tools import (
    SyntheticTool,
    ToolContext,
    ToolDescriptor,
    ToolRegistry,
    ToolResult,
)
from synthetic.artifact_factory.tool_planner import (
    compile_bundle_plan_to_tool_plan,
    compile_scenario_to_tool_plan,
)

__all__ = [
    "ArtifactState",
    "ArtifactPlan",
    "BundlePlan",
    "ConfusionEdge",
    "DescriptorOnlyTool",
    "DocumentIntent",
    "ScenarioConfusionSpec",
    "ScenarioDocumentSpec",
    "ScenarioIR",
    "ScenarioSpec",
    "SyntheticTool",
    "ToolContext",
    "ToolDescriptor",
    "ToolInvocation",
    "ToolPlan",
    "ToolPlanValidationReport",
    "ToolRegistry",
    "ToolResult",
    "TraceEntry",
    "TraceLayer",
    "compile_ir_to_bundle_plan",
    "compile_bundle_plan_to_tool_plan",
    "compile_scenario_ir",
    "compile_scenario_to_bundle_plan",
    "compile_scenario_to_tool_plan",
    "default_tool_descriptors",
    "default_tool_registry",
    "infer_state_type",
    "validate_tool_plan_against_registry",
]
