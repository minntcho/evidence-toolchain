from __future__ import annotations

import json
from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any

from evidence_toolchain.claims import DeclaredClaim
from evidence_toolchain.experiments import (
    ExpectedBehaviorReport,
    ExpectedClaimResolution,
    ExperimentAttachmentSpec,
    ExperimentExpectedBehavior,
    ExperimentManifest,
    ExperimentRunTrace,
    build_experiment_run_trace,
    evaluate_expected_behavior,
)
from evidence_toolchain.ingestion import EvidenceInventory, EvidenceUnit
from evidence_toolchain.investigation_ports import (
    FakeLLMPlanner,
    InvestigationPlan,
    LLMAtomizerPort,
    ResolverPort,
)
from evidence_toolchain.investigation_retrieval import CandidateUnitRetriever
from evidence_toolchain.investigation_runner import LocalInvestigationRunner
from evidence_toolchain.normalization import NormalizationAdapter
from evidence_toolchain.resolution import HardGateResolver
from evidence_toolchain.resolution_cycle import run_resolution_cycle


@dataclass(frozen=True)
class AdapterAcceptanceCheck:
    """One adapter acceptance comparison."""

    name: str
    passed: bool
    expected: Any
    actual: Any
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _to_json_compatible(self)


@dataclass(frozen=True)
class AdapterAcceptanceReport:
    """Acceptance report for a provider or orchestration adapter set."""

    adapter_name: str
    passed: bool
    checks: tuple[AdapterAcceptanceCheck, ...]
    trace: ExperimentRunTrace | None = None
    expected_behavior_report: ExpectedBehaviorReport | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter_name": self.adapter_name,
            "passed": self.passed,
            "checks": [check.to_dict() for check in self.checks],
            "trace": self.trace.to_dict() if self.trace is not None else None,
            "expected_behavior_report": (
                self.expected_behavior_report.to_dict()
                if self.expected_behavior_report is not None
                else None
            ),
            "metadata": _to_json_compatible(self.metadata),
        }


def run_basic_resolution_adapter_acceptance(
    *,
    adapter_name: str,
    llm_atomizer: LLMAtomizerPort,
    normalizer: NormalizationAdapter,
    resolver: ResolverPort | None = None,
    unit_retriever: CandidateUnitRetriever | None = None,
    max_investigation_steps: int = 3,
) -> AdapterAcceptanceReport:
    """Run a minimal manifest-to-trace acceptance scenario for adapter ports."""

    active_resolver = resolver or HardGateResolver()
    checks = [
        _port_check(
            name="llm_atomizer_port",
            protocol_name="LLMAtomizerPort",
            adapter=llm_atomizer,
            passed=isinstance(llm_atomizer, LLMAtomizerPort),
        ),
        _port_check(
            name="normalization_adapter_port",
            protocol_name="NormalizationAdapter",
            adapter=normalizer,
            passed=isinstance(normalizer, NormalizationAdapter),
        ),
        _port_check(
            name="resolver_port",
            protocol_name="ResolverPort",
            adapter=active_resolver,
            passed=isinstance(active_resolver, ResolverPort),
        ),
    ]

    if not all(check.passed for check in checks):
        return AdapterAcceptanceReport(
            adapter_name=adapter_name,
            passed=False,
            checks=tuple(checks),
            metadata={"scenario": "basic_resolution_adapter_acceptance_v0"},
        )

    manifest = _acceptance_manifest()
    active_unit_retriever = unit_retriever or CandidateUnitRetriever()
    run = run_resolution_cycle(
        inventory=_acceptance_inventory(),
        claims=manifest.claims,
        run_id=f"{adapter_name}_acceptance_run",
        max_investigation_steps=max(0, max_investigation_steps),
        normalizer=normalizer,
        resolver=active_resolver,
        unit_retriever=active_unit_retriever,
        investigation_runner=LocalInvestigationRunner(
            planner=FakeLLMPlanner(plan=InvestigationPlan(tasks=())),
            llm_atomizer=llm_atomizer,
            normalizer=normalizer,
            resolver=active_resolver,
            unit_retriever=active_unit_retriever,
            producer=f"{adapter_name}_acceptance_runner",
        ),
    )
    trace = build_experiment_run_trace(
        manifest=manifest,
        run=run,
        metadata={
            "acceptance_adapter": adapter_name,
            "producer": "basic_resolution_adapter_acceptance_v0",
        },
    )
    checks.append(_trace_json_check(trace))

    expected_report = evaluate_expected_behavior(
        trace=trace,
        expected=_acceptance_expected_behavior(),
    )
    checks.extend(_expected_behavior_checks(expected_report))

    return AdapterAcceptanceReport(
        adapter_name=adapter_name,
        passed=all(check.passed for check in checks),
        checks=tuple(checks),
        trace=trace,
        expected_behavior_report=expected_report,
        metadata={"scenario": "basic_resolution_adapter_acceptance_v0"},
    )


def _acceptance_manifest() -> ExperimentManifest:
    return ExperimentManifest(
        experiment_id="basic_resolution_adapter_acceptance",
        bundle_id="acceptance_bundle_001",
        attachments=(
            ExperimentAttachmentSpec(
                attachment_id="acceptance_text",
                path="adapter-acceptance.txt",
                declared_media_type="text/plain",
            ),
        ),
        claims=(
            DeclaredClaim(
                x_id="x_acceptance_001",
                fields={"amount": 6400, "unit": "kWh"},
            ),
        ),
        metadata={"scenario": "basic_resolution_adapter_acceptance_v0"},
    )


def _acceptance_inventory() -> EvidenceInventory:
    return EvidenceInventory(
        bundle_id="acceptance_bundle_001",
        attachments=(),
        artifacts=(),
        units=(
            EvidenceUnit(
                unit_id="unit_acceptance_usage",
                artifact_id="artifact_acceptance_text",
                unit_type="text_span",
                producer="adapter_acceptance_fixture",
                text="electricity usage 6.4 MWh",
            ),
            EvidenceUnit(
                unit_id="unit_acceptance_charge",
                artifact_id="artifact_acceptance_text",
                unit_type="text_span",
                producer="adapter_acceptance_fixture",
                text="bill amount 1,230,000 KRW",
            ),
        ),
        route_decisions=(),
    )


def _acceptance_expected_behavior() -> ExperimentExpectedBehavior:
    return ExperimentExpectedBehavior(
        claim_resolutions=(
            ExpectedClaimResolution(
                x_id="x_acceptance_001",
                status="supported_after_unit_normalization",
                missing_need_ids=(),
                supporting_atom_types=("usage_amount",),
                rejected_atom_types=("currency_amount",),
            ),
        ),
        metadata={"scenario": "basic_resolution_adapter_acceptance_v0"},
    )


def _port_check(
    *,
    name: str,
    protocol_name: str,
    adapter: Any,
    passed: bool,
) -> AdapterAcceptanceCheck:
    return AdapterAcceptanceCheck(
        name=name,
        passed=passed,
        expected=protocol_name,
        actual=type(adapter).__name__,
        metadata={"producer": getattr(adapter, "producer", None)},
    )


def _trace_json_check(trace: ExperimentRunTrace) -> AdapterAcceptanceCheck:
    try:
        json.dumps(trace.to_dict(), ensure_ascii=False)
    except TypeError as error:
        return AdapterAcceptanceCheck(
            name="trace_json_serializable",
            passed=False,
            expected="json_serializable",
            actual=type(error).__name__,
            metadata={"error": str(error)},
        )
    return AdapterAcceptanceCheck(
        name="trace_json_serializable",
        passed=True,
        expected="json_serializable",
        actual="json_serializable",
    )


def _expected_behavior_checks(
    report: ExpectedBehaviorReport,
) -> tuple[AdapterAcceptanceCheck, ...]:
    return tuple(
        AdapterAcceptanceCheck(
            name=f"expected_behavior.{check.name}",
            passed=check.passed,
            expected=check.expected,
            actual=check.actual,
            metadata={"x_id": check.x_id},
        )
        for check in report.checks
    )


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
