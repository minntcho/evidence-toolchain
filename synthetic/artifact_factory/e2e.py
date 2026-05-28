from __future__ import annotations

import csv
import json
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from synthetic.artifact_factory.compiler import (
    compile_ir_to_bundle_plan,
    compile_scenario_ir,
)
from synthetic.artifact_factory.csv_tools import CsvRendererTool, ErpExportBuilderTool
from synthetic.artifact_factory.executor import (
    GeneratedArtifactBundle,
    artifact_plan_states,
    execute_tool_plan,
)
from synthetic.artifact_factory.specs import ScenarioDocumentSpec, ScenarioSpec
from synthetic.artifact_factory.tool_planner import compile_bundle_plan_to_tool_plan
from synthetic.artifact_factory.tools import ToolRegistry
from synthetic.artifact_factory.xlsx_tools import (
    SupplierBreakdownWorkbookBuilderTool,
    XlsxWorkbookRendererTool,
)

V0_E2E_CARRIERS = ("csv", "xlsx")
RuntimeArtifactReader = Callable[..., dict[str, object]]


@dataclass(frozen=True)
class SyntheticScenarioCase:
    source_path: Path
    raw_text: str
    spec: ScenarioSpec
    expected_predicates: tuple[dict[str, object], ...]


@dataclass(frozen=True)
class SyntheticCaseBuildResult:
    root_dir: Path
    generated_bundle: GeneratedArtifactBundle
    verification_report: "VerificationReport"


@dataclass(frozen=True)
class SyntheticCaseRunResult:
    root_dir: Path
    build_result: SyntheticCaseBuildResult
    runtime_report: "RuntimeReport"


@dataclass(frozen=True)
class VerificationReport:
    case_id: str
    status: str
    artifacts: tuple[dict[str, object], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "status": self.status,
            "artifacts": [dict(artifact) for artifact in self.artifacts],
        }


@dataclass(frozen=True)
class RuntimeReport:
    case_id: str
    status: str
    artifacts: tuple[dict[str, object], ...]
    predicates: tuple[dict[str, object], ...]
    links: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "status": self.status,
            "artifacts": [dict(artifact) for artifact in self.artifacts],
            "predicates": [dict(predicate) for predicate in self.predicates],
            "links": dict(self.links),
        }


def load_scenario_case(path: str | Path) -> SyntheticScenarioCase:
    source_path = Path(path)
    raw_text = source_path.read_text(encoding="utf-8")
    payload = _parse_v0_scenario_yaml(raw_text)
    documents = tuple(
        ScenarioDocumentSpec(
            document_id=str(document["id"]),
            archetype=str(document["archetype"]),
            role=str(document["role"]),
            carrier=str(document["carrier"]),
        )
        for document in payload["documents"]
    )
    spec = ScenarioSpec(
        scenario_id=str(payload["scenario_id"]),
        seed=int(payload["seed"]),
        evidence_need=dict(payload.get("evidence_need", {})),
        documents=documents,
    )
    return SyntheticScenarioCase(
        source_path=source_path,
        raw_text=raw_text,
        spec=spec,
        expected_predicates=tuple(
            dict(predicate) for predicate in payload["expected_predicates"]
        ),
    )


def build_synthetic_case(
    scenario_path: str | Path,
    output_dir: str | Path,
) -> SyntheticCaseBuildResult:
    scenario = load_scenario_case(scenario_path)
    _require_v0_carriers(scenario.spec)

    scenario_ir = compile_scenario_ir(scenario.spec)
    bundle_plan = compile_ir_to_bundle_plan(scenario_ir)
    tool_plan = compile_bundle_plan_to_tool_plan(bundle_plan)
    generated = execute_tool_plan(
        tool_plan,
        output_dir,
        registry=_v0_execution_registry(),
        initial_states=artifact_plan_states(bundle_plan),
    )

    expected_dir = generated.root_dir / "expected"
    expected_dir.mkdir(parents=True, exist_ok=True)
    _write_json(
        expected_dir / "expected_predicates.json",
        {"predicates": list(scenario.expected_predicates)},
    )

    synthetic_dir = generated.synthetic_dir
    (synthetic_dir / "scenario_spec.yaml").write_text(
        scenario.raw_text,
        encoding="utf-8",
    )
    _write_json(synthetic_dir / "scenario_ir.json", scenario_ir.to_dict())
    _write_json(synthetic_dir / "bundle_plan.json", bundle_plan.to_dict())

    verification_report = verify_generated_case(generated.root_dir)
    return SyntheticCaseBuildResult(
        root_dir=generated.root_dir,
        generated_bundle=generated,
        verification_report=verification_report,
    )


def run_synthetic_case(
    scenario_path: str | Path,
    output_dir: str | Path,
    *,
    runtime_reader: RuntimeArtifactReader | None = None,
) -> SyntheticCaseRunResult:
    scenario = load_scenario_case(scenario_path)
    build_result = build_synthetic_case(scenario_path, output_dir)
    manifest = _read_json(build_result.root_dir / "_synthetic" / "manifest.json")
    active_runtime_reader = runtime_reader or _default_runtime_reader()

    runtime_input_dir = _prepare_runtime_input_dir(build_result.root_dir)
    artifact_reports = tuple(
        _run_manifest_artifact(
            build_result.root_dir,
            runtime_input_dir,
            artifact,
            active_runtime_reader,
        )
        for artifact in manifest.get("input_artifacts", [])
    )
    predicate_reports = tuple(
        _evaluate_predicate(predicate, artifact_reports)
        for predicate in scenario.expected_predicates
    )
    status = (
        "passed"
        if build_result.verification_report.status == "passed"
        and artifact_reports
        and all(artifact["reader_status"] == "ingested" for artifact in artifact_reports)
        and all(predicate["status"] == "passed" for predicate in predicate_reports)
        else "failed"
    )
    runtime_report = RuntimeReport(
        case_id=scenario.spec.scenario_id,
        status=status,
        artifacts=artifact_reports,
        predicates=predicate_reports,
        links={
            "carrier_trace": "_synthetic/carrier_trace.json",
            "manifest": "_synthetic/manifest.json",
            "verification_report": "_synthetic/verification_report.json",
        },
    )
    _write_json(
        build_result.root_dir / "_synthetic" / "runtime_report.json",
        runtime_report.to_dict(),
    )
    return SyntheticCaseRunResult(
        root_dir=build_result.root_dir,
        build_result=build_result,
        runtime_report=runtime_report,
    )


def verify_generated_case(root_dir: str | Path) -> VerificationReport:
    root = Path(root_dir)
    synthetic_dir = root / "_synthetic"
    manifest = _read_json(synthetic_dir / "manifest.json")
    carrier_trace = _read_json(synthetic_dir / "carrier_trace.json")

    artifact_reports = tuple(
        _verify_manifest_artifact(root, artifact, carrier_trace)
        for artifact in manifest.get("input_artifacts", [])
    )
    status = (
        "passed"
        if artifact_reports
        and all(artifact["status"] == "passed" for artifact in artifact_reports)
        else "failed"
    )
    report = VerificationReport(
        case_id=str(manifest["scenario_id"]),
        status=status,
        artifacts=artifact_reports,
    )
    _write_json(synthetic_dir / "verification_report.json", report.to_dict())
    return report


def _prepare_runtime_input_dir(root_dir: Path) -> Path:
    runtime_root = root_dir / "runtime_tmp"
    if runtime_root.exists():
        shutil.rmtree(runtime_root)
    runtime_input_dir = runtime_root / "input"
    runtime_input_dir.mkdir(parents=True, exist_ok=True)
    return runtime_input_dir


def _default_runtime_reader() -> RuntimeArtifactReader:
    from evidence_synthetic_runtime import run_runtime_artifact

    return run_runtime_artifact


def _run_manifest_artifact(
    root_dir: Path,
    runtime_input_dir: Path,
    artifact: object,
    runtime_reader: RuntimeArtifactReader,
) -> dict[str, object]:
    if not isinstance(artifact, dict):
        raise ValueError("manifest input_artifacts entries must be objects")
    artifact_id = str(artifact["artifact_id"])
    carrier = str(artifact["carrier"])
    path = str(artifact["path"])
    source_path = root_dir / path
    runtime_path = runtime_input_dir / source_path.name
    shutil.copy2(source_path, runtime_path)

    reader_result = runtime_reader(
        bundle_id=f"{root_dir.name}_runtime",
        attachment_id=artifact_id,
        path=runtime_path,
    )
    return {
        "artifact_id": artifact_id,
        "path": path,
        "carrier": carrier,
        **reader_result,
    }


def _evaluate_predicate(
    predicate: dict[str, object],
    artifact_reports: tuple[dict[str, object], ...],
) -> dict[str, object]:
    predicate_id = str(predicate["id"])
    artifact_id = str(predicate["artifact_id"])
    artifact_report = _artifact_report_by_id(artifact_reports, artifact_id)
    if predicate_id == "artifact_ingested":
        expected = bool(predicate.get("expected", True))
        actual = (
            artifact_report is not None
            and artifact_report["reader_status"] == "ingested"
        )
        status = "passed" if actual is expected else "failed"
        reader = "unknown" if artifact_report is None else str(artifact_report["reader"])
        return {
            "id": predicate_id,
            "artifact_id": artifact_id,
            "status": status,
            "message": (
                f"{artifact_id} was ingested by {reader}."
                if actual
                else f"{artifact_id} was not ingested."
            ),
        }
    if predicate_id == "minimum_observation_count":
        expected_min = int(predicate["min_count"])
        actual_count = (
            0
            if artifact_report is None
            else int(artifact_report["observation_count"])
        )
        status = "passed" if actual_count >= expected_min else "failed"
        return {
            "id": predicate_id,
            "artifact_id": artifact_id,
            "status": status,
            "actual": actual_count,
            "expected_min": expected_min,
            "message": (
                f"{artifact_id} produced {actual_count} observations; "
                f"expected at least {expected_min}."
            ),
        }
    raise ValueError(f"Unsupported expected predicate: {predicate_id}")


def _artifact_report_by_id(
    artifact_reports: tuple[dict[str, object], ...],
    artifact_id: str,
) -> dict[str, object] | None:
    for artifact_report in artifact_reports:
        if artifact_report["artifact_id"] == artifact_id:
            return artifact_report
    return None


def _verify_manifest_artifact(
    root_dir: Path,
    artifact: object,
    carrier_trace: dict[str, object],
) -> dict[str, object]:
    if not isinstance(artifact, dict):
        raise ValueError("manifest input_artifacts entries must be objects")
    artifact_id = str(artifact["artifact_id"])
    carrier = str(artifact["carrier"])
    path = str(artifact["path"])
    state_id = str(artifact["state_id"])
    artifact_path = root_dir / path

    checks: list[dict[str, object]] = [
        {"id": "manifest_entry_present", "status": "passed"},
        {
            "id": "input_artifact_exists",
            "status": "passed" if artifact_path.exists() else "failed",
        },
        {
            "id": "carrier_trace_present",
            "status": (
                "passed"
                if _carrier_trace_has_entries(carrier_trace, state_id)
                else "failed"
            ),
        },
    ]
    if artifact_path.exists():
        checks.append(_verify_carrier_artifact(carrier, artifact_path))

    artifact_status = (
        "passed"
        if all(check["status"] == "passed" for check in checks)
        else "failed"
    )
    return {
        "artifact_id": artifact_id,
        "carrier": carrier,
        "path": path,
        "status": artifact_status,
        "checks": checks,
    }


def _verify_carrier_artifact(carrier: str, artifact_path: Path) -> dict[str, object]:
    match carrier:
        case "csv":
            with artifact_path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            status = "passed" if rows else "failed"
            return {"id": "csv_readable", "status": status, "row_count": len(rows)}
        case "xlsx":
            try:
                with ZipFile(artifact_path) as archive:
                    names = set(archive.namelist())
                    workbook = archive.read("xl/workbook.xml").decode("utf-8")
            except (BadZipFile, KeyError, UnicodeDecodeError):
                return {"id": "xlsx_readable", "status": "failed", "sheet_count": 0}
            required = {
                "[Content_Types].xml",
                "xl/workbook.xml",
                "xl/worksheets/sheet1.xml",
            }
            sheet_count = workbook.count("<sheet ")
            return {
                "id": "xlsx_readable",
                "status": "passed" if required <= names and sheet_count else "failed",
                "sheet_count": sheet_count,
            }
        case _:
            return {"id": f"{carrier}_readable", "status": "failed"}


def _carrier_trace_has_entries(
    carrier_trace: dict[str, object],
    state_id: str,
) -> bool:
    states = carrier_trace.get("states", {})
    if not isinstance(states, dict):
        return False
    state = states.get(state_id, {})
    if not isinstance(state, dict):
        return False
    trace = state.get("trace", {})
    if not isinstance(trace, dict):
        return False
    entries = trace.get("entries", [])
    return isinstance(entries, list) and bool(entries)


def _require_v0_carriers(spec: ScenarioSpec) -> None:
    unsupported = sorted(
        {document.carrier for document in spec.documents}
        - set(V0_E2E_CARRIERS)
    )
    if unsupported:
        raise ValueError(
            "v0 synthetic e2e only supports csv, xlsx; "
            f"got {', '.join(unsupported)}"
        )


def _v0_execution_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(ErpExportBuilderTool())
    registry.register(CsvRendererTool())
    registry.register(SupplierBreakdownWorkbookBuilderTool())
    registry.register(XlsxWorkbookRendererTool())
    return registry


def _parse_v0_scenario_yaml(raw_text: str) -> dict[str, object]:
    payload: dict[str, object] = {}
    current_section: str | None = None
    current_item: dict[str, object] | None = None
    for raw_line in raw_text.splitlines():
        if not raw_line.strip():
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()
        if indent == 0:
            key, value = _split_yaml_pair(line)
            if value == "":
                current_section = key
                if key in {"documents", "expected_predicates"}:
                    payload[key] = []
                else:
                    payload[key] = {}
                current_item = None
            else:
                payload[key] = _parse_scalar(value)
                current_section = None
                current_item = None
            continue

        if current_section is None:
            raise ValueError(f"Unexpected nested YAML line: {raw_line}")
        if current_section in {"documents", "expected_predicates"}:
            if indent == 2 and line.startswith("- "):
                key, value = _split_yaml_pair(line[2:])
                current_item = {key: _parse_scalar(value)}
                items = payload[current_section]
                if not isinstance(items, list):
                    raise ValueError(f"{current_section} must be a list")
                items.append(current_item)
            elif indent == 4 and current_item is not None:
                key, value = _split_yaml_pair(line)
                current_item[key] = _parse_scalar(value)
            else:
                raise ValueError(f"Unsupported YAML list line: {raw_line}")
        else:
            key, value = _split_yaml_pair(line)
            section = payload[current_section]
            if not isinstance(section, dict):
                raise ValueError(f"{current_section} must be a mapping")
            section[key] = _parse_scalar(value)
    return payload


def _split_yaml_pair(line: str) -> tuple[str, str]:
    if ":" not in line:
        raise ValueError(f"Expected YAML key/value pair: {line}")
    key, value = line.split(":", 1)
    return key.strip(), value.strip()


def _parse_scalar(value: str) -> object:
    if value == "true":
        return True
    if value == "false":
        return False
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
