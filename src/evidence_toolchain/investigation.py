from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass, replace
from pathlib import Path
from typing import Any

from evidence_toolchain.atoms import EvidenceAtom
from evidence_toolchain.claims import DeclaredClaim, NeedSpec
from evidence_toolchain.ingestion import EvidenceInventory, EvidenceUnit
from evidence_toolchain.issues import EvidenceIssue
from evidence_toolchain.normalization import NormalizationResult
from evidence_toolchain.resolution import EvidenceResolutionGraph


class InvestigationTaskType:
    """조사 루프가 실행할 수 있는 v0 task vocabulary입니다."""

    RETRIEVE_CANDIDATE_UNITS = "retrieve_candidate_units"
    ATOMIZE_UNIT_CLUSTER = "atomize_unit_cluster"
    INSPECT_VISUAL_ARTIFACT = "inspect_visual_artifact"
    INSPECT_VISUAL_REGION = "inspect_visual_region"
    NORMALIZE_CANDIDATE = "normalize_candidate"
    REQUEST_MANUAL_REVIEW = "request_manual_review"
    STOP = "stop"

    ALL = (
        RETRIEVE_CANDIDATE_UNITS,
        ATOMIZE_UNIT_CLUSTER,
        INSPECT_VISUAL_ARTIFACT,
        INSPECT_VISUAL_REGION,
        NORMALIZE_CANDIDATE,
        REQUEST_MANUAL_REVIEW,
        STOP,
    )

    @classmethod
    def is_core_type(cls, task_type: str) -> bool:
        return task_type in cls.ALL


class InvestigationTaskStatus:
    """조사 task 결과의 v0 status vocabulary입니다."""

    PLANNED = "planned"
    COMPLETED = "completed"
    FAILED = "failed"
    NO_NEW_CLUE = "no_new_clue"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"
    SKIPPED = "skipped"

    ALL = (
        PLANNED,
        COMPLETED,
        FAILED,
        NO_NEW_CLUE,
        MANUAL_REVIEW_REQUIRED,
        SKIPPED,
    )

    @classmethod
    def is_core_status(cls, status: str) -> bool:
        return status in cls.ALL


class NeedLedgerStatus:
    """각 need의 조사 진행 상태를 표현하는 v0 vocabulary입니다."""

    MISSING = "missing"
    PARTIAL = "partial"
    SATISFIED = "satisfied"
    CONFLICT = "conflict"
    AMBIGUOUS = "ambiguous"
    NEEDS_REVIEW = "needs_review"

    ALL = (
        MISSING,
        PARTIAL,
        SATISFIED,
        CONFLICT,
        AMBIGUOUS,
        NEEDS_REVIEW,
    )

    @classmethod
    def is_core_status(cls, status: str) -> bool:
        return status in cls.ALL


class InvestigationEventType:
    """조사 루프 state transition event의 v0 vocabulary입니다."""

    TASK_PLANNED = "task_planned"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    STATE_UPDATED = "state_updated"
    BUDGET_EXHAUSTED = "budget_exhausted"
    MANUAL_REVIEW_REQUESTED = "manual_review_requested"
    STOPPED = "stopped"

    ALL = (
        TASK_PLANNED,
        TASK_STARTED,
        TASK_COMPLETED,
        STATE_UPDATED,
        BUDGET_EXHAUSTED,
        MANUAL_REVIEW_REQUESTED,
        STOPPED,
    )

    @classmethod
    def is_core_type(cls, event_type: str) -> bool:
        return event_type in cls.ALL


@dataclass(frozen=True)
class InvestigationBudget:
    """조사 루프가 무제한 반복되지 않도록 하는 budget contract입니다."""

    max_iterations: int = 0
    max_model_calls: int = 0
    max_new_units: int = 0
    max_new_atoms: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _to_json_compatible(self)


@dataclass(frozen=True)
class InvestigationTask:
    """missing/conflict/ambiguous clue를 채우기 위해 계획된 작업 단위입니다."""

    task_id: str
    task_type: str
    target_claim_id: str | None = None
    target_need_id: str | None = None
    target_artifact_ids: tuple[str, ...] = ()
    target_unit_ids: tuple[str, ...] = ()
    question: str | None = None
    allowed_atom_types: tuple[str, ...] = ()
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _to_json_compatible(self)


@dataclass(frozen=True)
class InvestigationTaskResult:
    """task 실행 결과 record입니다. 모델 판단 authority가 아닙니다."""

    task_id: str
    status: str
    produced_units: tuple[EvidenceUnit, ...] = ()
    produced_atoms: tuple[EvidenceAtom, ...] = ()
    produced_normalization_results: tuple[NormalizationResult, ...] = ()
    produced_unit_ids: tuple[str, ...] = ()
    produced_atom_ids: tuple[str, ...] = ()
    produced_normalization_result_ids: tuple[str, ...] = ()
    issues: tuple[EvidenceIssue, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _to_json_compatible(self)


@dataclass(frozen=True)
class NeedLedgerEntry:
    """claim need 단위로 현재 clue 상태를 요약하는 ledger entry입니다."""

    x_id: str
    need_id: str
    status: str
    evidence_atom_ids: tuple[str, ...] = ()
    issue_codes: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _to_json_compatible(self)


@dataclass(frozen=True)
class InvestigationEvent:
    """EvidenceInvestigationLoop의 append-only event record입니다."""

    run_id: str
    sequence: int
    event_type: str
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _to_json_compatible(self)


@dataclass(frozen=True)
class InvestigationState:
    """조사 루프가 소비하고 갱신할 framework-neutral state snapshot입니다."""

    run_id: str
    inventory: EvidenceInventory
    claims: tuple[DeclaredClaim, ...]
    need_specs: tuple[NeedSpec, ...]
    atoms: tuple[EvidenceAtom, ...]
    normalization_results: tuple[NormalizationResult, ...]
    draft_graph: EvidenceResolutionGraph | None = None
    agenda: tuple[InvestigationTask, ...] = ()
    completed_tasks: tuple[InvestigationTaskResult, ...] = ()
    clue_ledger: tuple[NeedLedgerEntry, ...] = ()
    events: tuple[InvestigationEvent, ...] = ()
    budget: InvestigationBudget = field(default_factory=InvestigationBudget)
    metadata: dict[str, Any] = field(default_factory=dict)

    def record_event(self, event: InvestigationEvent) -> "InvestigationState":
        return replace(self, events=self.events + (event,))

    def to_dict(self) -> dict[str, Any]:
        return _to_json_compatible(self)


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
