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
from synthetic.artifact_factory.csv_tools import (
    CsvRendererTool,
    ErpExportBuilderTool,
    build_csv_artifact_bundle,
    csv_execution_registry,
)
from synthetic.artifact_factory.executor import (
    GeneratedArtifactBundle,
    artifact_plan_states,
    execute_tool_plan,
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
from synthetic.artifact_factory.xlsx_tools import (
    SupplierBreakdownWorkbookBuilderTool,
    XlsxWorkbookRendererTool,
    build_xlsx_artifact_bundle,
    xlsx_execution_registry,
)

__all__ = [
    "ArtifactState",
    "ArtifactPlan",
    "BundlePlan",
    "ConfusionEdge",
    "CsvRendererTool",
    "DescriptorOnlyTool",
    "DocumentIntent",
    "ErpExportBuilderTool",
    "GeneratedArtifactBundle",
    "ScenarioConfusionSpec",
    "ScenarioDocumentSpec",
    "ScenarioIR",
    "ScenarioSpec",
    "SupplierBreakdownWorkbookBuilderTool",
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
    "XlsxWorkbookRendererTool",
    "artifact_plan_states",
    "build_csv_artifact_bundle",
    "build_xlsx_artifact_bundle",
    "compile_ir_to_bundle_plan",
    "compile_bundle_plan_to_tool_plan",
    "compile_scenario_ir",
    "compile_scenario_to_bundle_plan",
    "compile_scenario_to_tool_plan",
    "csv_execution_registry",
    "default_tool_descriptors",
    "default_tool_registry",
    "execute_tool_plan",
    "infer_state_type",
    "validate_tool_plan_against_registry",
    "xlsx_execution_registry",
]
