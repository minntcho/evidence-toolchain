from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from evidence_toolchain.atoms import AtomizerResult, EvidenceAtom
from evidence_toolchain.claims import DeclaredClaim, NeedSpec
from evidence_toolchain.ingestion import EvidenceUnit
from evidence_toolchain.investigation import (
    InvestigationState,
    InvestigationTask,
    InvestigationTaskResult,
)
from evidence_toolchain.issues import EvidenceIssue
from evidence_toolchain.normalization import NormalizationResult
from evidence_toolchain.resolution import EvidenceResolutionGraph


@dataclass(frozen=True)
class InvestigationPlan:
    """LLM planner port가 제안한 다음 조사 task 묶음입니다."""

    tasks: tuple[InvestigationTask, ...]
    stop_reason: str | None = None
    producer: str = "investigation_planner"
    issues: tuple[EvidenceIssue, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _to_json_compatible(self)


@runtime_checkable
class LLMPlannerPort(Protocol):
    """조사 state를 보고 다음 InvestigationPlan을 제안하는 port입니다."""

    producer: str

    def plan_next_tasks(self, state: InvestigationState) -> InvestigationPlan:
        """다음 task agenda를 제안합니다."""


@runtime_checkable
class VLMObserverPort(Protocol):
    """visual artifact 또는 region을 관찰해 task result를 반환하는 port입니다."""

    producer: str

    def inspect(
        self,
        task: InvestigationTask,
        artifact_bytes: bytes,
    ) -> InvestigationTaskResult:
        """시각 자료를 관찰하고 provenance-preserving result를 반환합니다."""


@runtime_checkable
class LLMAtomizerPort(Protocol):
    """text/table unit cluster를 EvidenceAtom 후보로 바꾸는 port입니다."""

    producer: str

    def atomize(
        self,
        task: InvestigationTask,
        units: tuple[EvidenceUnit, ...],
    ) -> AtomizerResult:
        """EvidenceUnit cluster를 AtomizerResult로 변환합니다."""


@runtime_checkable
class LLMNormalizerPort(Protocol):
    """ambiguous atom 후보를 NormalizationResult 후보로 낮추는 port입니다."""

    producer: str

    def normalize(
        self,
        task: InvestigationTask,
        atoms: tuple[EvidenceAtom, ...],
    ) -> tuple[NormalizationResult, ...]:
        """EvidenceAtom 후보를 normalized comparison material로 변환합니다."""


@runtime_checkable
class ResolverPort(Protocol):
    """normalized material을 draft EvidenceResolutionGraph로 변환하는 resolver port입니다."""

    producer: str

    def resolve(
        self,
        *,
        bundle_id: str,
        claims: tuple[DeclaredClaim, ...],
        need_specs: tuple[NeedSpec, ...],
        atoms: tuple[EvidenceAtom, ...],
        normalization_results: tuple[NormalizationResult, ...],
    ) -> EvidenceResolutionGraph:
        """현재 state material로 draft resolution graph를 만듭니다."""


@dataclass(frozen=True)
class FakeLLMPlanner:
    """테스트용 deterministic planner입니다. 외부 모델을 호출하지 않습니다."""

    plan: InvestigationPlan
    producer: str = "fake_llm_planner"

    def plan_next_tasks(self, state: InvestigationState) -> InvestigationPlan:
        del state
        return self.plan


@dataclass(frozen=True)
class FakeVLMObserver:
    """테스트용 deterministic visual observer입니다."""

    result: InvestigationTaskResult
    producer: str = "fake_vlm_observer"

    def inspect(
        self,
        task: InvestigationTask,
        artifact_bytes: bytes,
    ) -> InvestigationTaskResult:
        del task, artifact_bytes
        return self.result


@dataclass(frozen=True)
class FakeLLMAtomizer:
    """테스트용 deterministic atomizer port입니다."""

    result: AtomizerResult
    producer: str = "fake_llm_atomizer"

    def atomize(
        self,
        task: InvestigationTask,
        units: tuple[EvidenceUnit, ...],
    ) -> AtomizerResult:
        del task, units
        return self.result


@dataclass(frozen=True)
class FakeLLMNormalizer:
    """테스트용 deterministic normalizer port입니다."""

    results: tuple[NormalizationResult, ...]
    producer: str = "fake_llm_normalizer"

    def normalize(
        self,
        task: InvestigationTask,
        atoms: tuple[EvidenceAtom, ...],
    ) -> tuple[NormalizationResult, ...]:
        del task, atoms
        return self.results


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
