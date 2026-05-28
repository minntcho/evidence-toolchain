from __future__ import annotations

import json
from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any

from evidence_toolchain.claims import DeclaredClaim
from evidence_toolchain.ingestion import AttachmentBundle, RawAttachment
from evidence_toolchain.investigation import InvestigationBudget


EXPERIMENT_MANIFEST_SCHEMA_VERSION = "experiment_manifest_v0"
EXPERIMENT_RUN_TRACE_SCHEMA_VERSION = "experiment_run_trace_v0"


@dataclass(frozen=True)
class ExperimentAttachmentSpec:
    """Attachment input declared by a reproducible experiment manifest."""

    attachment_id: str
    path: str
    declared_media_type: str | None = None
    detected_media_type: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_raw_attachment(self, *, base_dir: str | Path | None = None) -> RawAttachment:
        source_path = Path(self.path)
        if not source_path.is_absolute() and base_dir is not None:
            source_path = Path(base_dir) / source_path
        return RawAttachment.from_path(
            source_path,
            attachment_id=self.attachment_id,
            declared_media_type=self.declared_media_type,
            detected_media_type=self.detected_media_type,
            metadata=self.metadata,
        )

    def to_dict(self) -> dict[str, Any]:
        return _to_json_compatible(self)


@dataclass(frozen=True)
class ExperimentManifest:
    """Reproducible input contract for local evidence experiments."""

    experiment_id: str
    bundle_id: str
    attachments: tuple[ExperimentAttachmentSpec, ...]
    claims: tuple[DeclaredClaim, ...]
    schema_version: str = EXPERIMENT_MANIFEST_SCHEMA_VERSION
    budget: InvestigationBudget = field(default_factory=InvestigationBudget)
    allowed_capabilities: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_attachment_bundle(
        self,
        *,
        base_dir: str | Path | None = None,
    ) -> AttachmentBundle:
        return AttachmentBundle(
            bundle_id=self.bundle_id,
            attachments=tuple(
                attachment.to_raw_attachment(base_dir=base_dir)
                for attachment in self.attachments
            ),
            metadata={
                "experiment_id": self.experiment_id,
                "schema_version": self.schema_version,
                **self.metadata,
            },
        )

    def to_dict(self) -> dict[str, Any]:
        return _to_json_compatible(self)


@dataclass(frozen=True)
class ExperimentRunTrace:
    """Replay-friendly artifact for one local evidence experiment execution."""

    experiment_id: str
    manifest: ExperimentManifest
    run: Any
    schema_version: str = EXPERIMENT_RUN_TRACE_SCHEMA_VERSION
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "experiment_id": self.experiment_id,
            "manifest": self.manifest.to_dict(),
            "run": self.run.to_dict() if hasattr(self.run, "to_dict") else _to_json_compatible(self.run),
            "metadata": {
                "producer": EXPERIMENT_RUN_TRACE_SCHEMA_VERSION,
                **self.metadata,
            },
        }


@dataclass(frozen=True)
class ExpectedClaimResolution:
    """Test expectation for one claim's final resolution trace."""

    x_id: str
    status: str | None = None
    missing_need_ids: tuple[str, ...] | None = None
    supporting_atom_types: tuple[str, ...] | None = None
    rejected_atom_types: tuple[str, ...] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _to_json_compatible(self)


@dataclass(frozen=True)
class ExperimentExpectedBehavior:
    """Expected behavior oracle input for tests, not runtime authority."""

    claim_resolutions: tuple[ExpectedClaimResolution, ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _to_json_compatible(self)


@dataclass(frozen=True)
class ExpectedBehaviorCheck:
    """One comparison made by the expected behavior oracle."""

    name: str
    x_id: str
    passed: bool
    expected: Any
    actual: Any
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _to_json_compatible(self)


@dataclass(frozen=True)
class ExpectedBehaviorReport:
    """Comparison report for a trace and expected behavior contract."""

    passed: bool
    checks: tuple[ExpectedBehaviorCheck, ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _to_json_compatible(self)


def load_experiment_manifest(path: str | Path) -> ExperimentManifest:
    manifest_path = Path(path)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    return experiment_manifest_from_dict(data)


def build_experiment_run_trace(
    *,
    manifest: ExperimentManifest,
    run: Any,
    metadata: dict[str, Any] | None = None,
) -> ExperimentRunTrace:
    return ExperimentRunTrace(
        experiment_id=manifest.experiment_id,
        manifest=manifest,
        run=run,
        metadata=dict(metadata or {}),
    )


def write_experiment_run_trace(
    trace: ExperimentRunTrace,
    path: str | Path,
) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(trace.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path


def evaluate_expected_behavior(
    *,
    trace: ExperimentRunTrace,
    expected: ExperimentExpectedBehavior,
) -> ExpectedBehaviorReport:
    payload = trace.to_dict()
    run_payload = payload["run"]
    final_graph = run_payload["final_graph"]
    resolutions_by_claim = {
        resolution["x_id"]: resolution
        for resolution in final_graph["resolutions"]
    }
    atom_types = _atom_types_by_id(run_payload)
    checks: list[ExpectedBehaviorCheck] = []

    for claim_expectation in expected.claim_resolutions:
        resolution = resolutions_by_claim.get(claim_expectation.x_id)
        if resolution is None:
            checks.append(
                ExpectedBehaviorCheck(
                    name="claim_resolution_present",
                    x_id=claim_expectation.x_id,
                    passed=False,
                    expected="present",
                    actual="missing",
                )
            )
            continue

        if claim_expectation.status is not None:
            checks.append(
                _check(
                    name="claim_status",
                    x_id=claim_expectation.x_id,
                    expected=claim_expectation.status,
                    actual=resolution["status"],
                )
            )
        if claim_expectation.missing_need_ids is not None:
            checks.append(
                _check(
                    name="missing_need_ids",
                    x_id=claim_expectation.x_id,
                    expected=list(claim_expectation.missing_need_ids),
                    actual=resolution["missing_need_ids"],
                )
            )
        if claim_expectation.supporting_atom_types is not None:
            checks.append(
                _check(
                    name="supporting_atom_types",
                    x_id=claim_expectation.x_id,
                    expected=list(claim_expectation.supporting_atom_types),
                    actual=_types_for_ids(resolution["supporting_atom_ids"], atom_types),
                )
            )
        if claim_expectation.rejected_atom_types is not None:
            checks.append(
                _check(
                    name="rejected_atom_types",
                    x_id=claim_expectation.x_id,
                    expected=list(claim_expectation.rejected_atom_types),
                    actual=_types_for_ids(resolution["rejected_atom_ids"], atom_types),
                )
            )

    return ExpectedBehaviorReport(
        passed=all(check.passed for check in checks),
        checks=tuple(checks),
        metadata={"producer": "expected_behavior_oracle_v0"},
    )


def experiment_manifest_from_dict(data: dict[str, Any]) -> ExperimentManifest:
    schema_version = str(
        data.get("schema_version", EXPERIMENT_MANIFEST_SCHEMA_VERSION)
    )
    if schema_version != EXPERIMENT_MANIFEST_SCHEMA_VERSION:
        raise ValueError(f"지원하지 않는 experiment manifest schema입니다: {schema_version}")

    return ExperimentManifest(
        schema_version=schema_version,
        experiment_id=str(data["experiment_id"]),
        bundle_id=str(data["bundle_id"]),
        attachments=tuple(
            _attachment_spec_from_dict(item)
            for item in _required_list(data, "attachments")
        ),
        claims=tuple(
            _declared_claim_from_dict(item)
            for item in _required_list(data, "claims")
        ),
        budget=_budget_from_dict(dict(data.get("budget", {}))),
        allowed_capabilities=tuple(
            str(item) for item in data.get("allowed_capabilities", ())
        ),
        metadata=dict(data.get("metadata", {})),
    )


def _attachment_spec_from_dict(data: Any) -> ExperimentAttachmentSpec:
    if not isinstance(data, dict):
        raise ValueError("attachments 항목은 object여야 합니다.")
    return ExperimentAttachmentSpec(
        attachment_id=str(data["attachment_id"]),
        path=str(data["path"]),
        declared_media_type=_optional_string(data.get("declared_media_type")),
        detected_media_type=_optional_string(data.get("detected_media_type")),
        metadata=dict(data.get("metadata", {})),
    )


def _declared_claim_from_dict(data: Any) -> DeclaredClaim:
    if not isinstance(data, dict):
        raise ValueError("claims 항목은 object여야 합니다.")
    return DeclaredClaim(
        x_id=str(data["x_id"]),
        claim_type=str(data.get("claim_type", "declared_claim")),
        fields=dict(data.get("fields", {})),
        metadata=dict(data.get("metadata", {})),
    )


def _budget_from_dict(data: dict[str, Any]) -> InvestigationBudget:
    return InvestigationBudget(
        max_iterations=int(data.get("max_iterations", 0)),
        max_model_calls=int(data.get("max_model_calls", 0)),
        max_new_units=int(data.get("max_new_units", 0)),
        max_new_atoms=int(data.get("max_new_atoms", 0)),
        metadata=dict(data.get("metadata", {})),
    )


def _atom_types_by_id(run_payload: dict[str, Any]) -> dict[str, str]:
    return {
        atom["atom_id"]: atom["atom_type"]
        for atom in run_payload["investigation_state"]["atoms"]
    }


def _types_for_ids(atom_ids: list[str], atom_types: dict[str, str]) -> list[str]:
    return [
        atom_types[atom_id]
        for atom_id in atom_ids
        if atom_id in atom_types
    ]


def _check(
    *,
    name: str,
    x_id: str,
    expected: Any,
    actual: Any,
) -> ExpectedBehaviorCheck:
    return ExpectedBehaviorCheck(
        name=name,
        x_id=x_id,
        passed=actual == expected,
        expected=expected,
        actual=actual,
    )


def _required_list(data: dict[str, Any], key: str) -> list[Any]:
    value = data[key]
    if not isinstance(value, list):
        raise ValueError(f"{key}는 list여야 합니다.")
    return value


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _to_json_compatible(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value):
        return {
            item.name: _to_json_compatible(getattr(value, item.name))
            for item in fields(value)
        }
    if isinstance(value, dict):
        return {
            str(key): _to_json_compatible(item)
            for key, item in value.items()
        }
    if isinstance(value, tuple | list):
        return [_to_json_compatible(item) for item in value]
    return value
