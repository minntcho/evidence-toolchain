from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from evidence_toolchain.artifacts import EvidenceDocument
from evidence_toolchain.planner import EvidenceToolPlan
from evidence_toolchain.runtime import EvidenceRunState


@dataclass(frozen=True)
class ExtractedField:
    name: str
    value: str
    unit: str | None = None
    confidence: float | None = None
    provenance: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class EvidenceReport:
    document_id: str
    document: EvidenceDocument
    plan: EvidenceToolPlan
    preflight: dict[str, object] | None = None
    fields: list[ExtractedField] = field(default_factory=list)
    issues: list[dict[str, object]] = field(default_factory=list)
    pending_steps: list[dict[str, object]] = field(default_factory=list)
    completed_steps: list[dict[str, object]] = field(default_factory=list)
    tool_results: list[dict[str, object]] = field(default_factory=list)
    interrupts: list[dict[str, object]] = field(default_factory=list)
    recommended_next_action: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "document_id": self.document_id,
            "document": self.document.to_dict()
            if hasattr(self.document, "to_dict")
            else _to_json_compatible(self.document),
            "preflight": self.preflight,
            "observation": _to_json_compatible(self.plan.observation),
            "plan": _to_json_compatible(self.plan),
            "fields": [_to_json_compatible(field) for field in self.fields],
            "issues": self.issues,
            "pending_steps": self.pending_steps,
            "completed_steps": self.completed_steps,
            "tool_results": self.tool_results,
            "interrupts": self.interrupts,
            "recommended_next_action": self.recommended_next_action,
        }


def emit_evidence_report(state: EvidenceRunState) -> EvidenceReport:
    if state.plan is None:
        raise ValueError("EvidenceRunState must include a plan before reporting.")

    return EvidenceReport(
        document_id=state.document.document_id,
        document=state.document,
        preflight=state.preflight.to_dict() if state.preflight is not None else None,
        plan=state.plan,
        issues=[_to_json_compatible(issue) for issue in state.issues],
        pending_steps=[step.to_dict() for step in state.pending_steps],
        completed_steps=[step.to_dict() for step in state.completed_steps],
        tool_results=[result.to_dict() for result in state.tool_results],
        interrupts=[_to_json_compatible(interrupt) for interrupt in state.interrupts],
        recommended_next_action=_recommended_next_action(state),
    )


def write_evidence_report(report: EvidenceReport, output_dir: str | Path) -> Path:
    report_dir = Path(output_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = (
        report_dir / f"{_safe_artifact_stem(report.document_id)}.evidence-report.json"
    )
    report_path.write_text(
        json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report_path


def _safe_artifact_stem(value: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._-")
    return stem or "evidence-report"


def _recommended_next_action(state: EvidenceRunState) -> str | None:
    if state.interrupts:
        return "manual_review"
    if state.pending_steps:
        return "run_pending_capabilities"
    return None


def _to_json_compatible(value: object) -> object:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if hasattr(value, "__dataclass_fields__"):
        return {
            key: _to_json_compatible(getattr(value, key))
            for key in value.__dataclass_fields__
        }
    if isinstance(value, dict):
        return {
            str(key): _to_json_compatible(item)
            for key, item in value.items()
        }
    if isinstance(value, tuple | list):
        return [_to_json_compatible(item) for item in value]
    return value
