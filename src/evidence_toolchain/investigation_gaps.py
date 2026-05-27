from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any

from evidence_toolchain.atoms import EvidenceAtomType
from evidence_toolchain.claims import Need, NeedSpec, NeedType
from evidence_toolchain.investigation import (
    InvestigationTask,
    InvestigationTaskType,
    NeedLedgerEntry,
    NeedLedgerStatus,
)
from evidence_toolchain.issues import EvidenceIssue
from evidence_toolchain.resolution import (
    ClaimResolution,
    EvidenceResolutionGraph,
    ResolutionEdge,
    ResolutionRelation,
    ResolutionStatus,
)


@dataclass(frozen=True)
class ResolutionGapPlan:
    """Resolver output에서 조사 ledger와 agenda로 내려간 bridge 결과입니다."""

    bundle_id: str
    ledger_entries: tuple[NeedLedgerEntry, ...]
    tasks: tuple[InvestigationTask, ...]
    issues: tuple[EvidenceIssue, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _to_json_compatible(self)


@dataclass(frozen=True)
class ResolutionGapPlanner:
    """ResolutionGraph gap을 investigation task 후보로 번역하는 v0 bridge입니다."""

    producer: str = "resolution_gap_planner_v0"

    def plan_from_graph(
        self,
        *,
        graph: EvidenceResolutionGraph,
        need_specs: tuple[NeedSpec, ...],
    ) -> ResolutionGapPlan:
        need_specs_by_claim = {need_spec.x_id: need_spec for need_spec in need_specs}
        edges_by_claim_need = _edges_by_claim_need(graph.edges)
        ledger_entries: list[NeedLedgerEntry] = []
        tasks: list[InvestigationTask] = []
        issues: list[EvidenceIssue] = []

        for resolution in graph.resolutions:
            need_spec = need_specs_by_claim.get(resolution.x_id)
            if need_spec is None:
                issues.append(
                    EvidenceIssue(
                        code="resolution_gap_need_spec_missing",
                        severity="warning",
                        message=f"claim '{resolution.x_id}'에 대응하는 NeedSpec이 없습니다.",
                    )
                )
                continue

            task_index = len(tasks) + 1
            for need in need_spec.needs:
                need_edges = edges_by_claim_need.get((resolution.x_id, need.need_id), ())
                if _has_contradiction(resolution, need_edges):
                    ledger_entries.append(
                        _ledger_entry(
                            resolution=resolution,
                            need=need,
                            status=NeedLedgerStatus.CONFLICT,
                            edges=need_edges,
                            producer=self.producer,
                        )
                    )
                    tasks.append(
                        _manual_review_task(
                            resolution=resolution,
                            need=need,
                            edges=need_edges,
                            task_index=task_index,
                            producer=self.producer,
                        )
                    )
                    task_index += 1
                    continue

                if need.need_id in resolution.missing_need_ids:
                    ledger_entries.append(
                        _ledger_entry(
                            resolution=resolution,
                            need=need,
                            status=NeedLedgerStatus.MISSING,
                            edges=need_edges,
                            producer=self.producer,
                        )
                    )
                    tasks.append(
                        _retrieve_task(
                            resolution=resolution,
                            need=need,
                            edges=need_edges,
                            task_index=task_index,
                            producer=self.producer,
                        )
                    )
                    task_index += 1

        return ResolutionGapPlan(
            bundle_id=graph.bundle_id,
            ledger_entries=tuple(ledger_entries),
            tasks=tuple(tasks),
            issues=tuple(issues),
            metadata={"producer": self.producer},
        )


def _edges_by_claim_need(
    edges: tuple[ResolutionEdge, ...],
) -> dict[tuple[str, str], tuple[ResolutionEdge, ...]]:
    grouped: dict[tuple[str, str], list[ResolutionEdge]] = {}
    for edge in edges:
        if edge.need_id is None:
            continue
        grouped.setdefault((edge.x_id, edge.need_id), []).append(edge)
    return {key: tuple(value) for key, value in grouped.items()}


def _has_contradiction(
    resolution: ClaimResolution,
    edges: tuple[ResolutionEdge, ...],
) -> bool:
    return (
        resolution.status == ResolutionStatus.CONTRADICTED
        and any(edge.relation == ResolutionRelation.CONTRADICTS for edge in edges)
    )


def _ledger_entry(
    *,
    resolution: ClaimResolution,
    need: Need,
    status: str,
    edges: tuple[ResolutionEdge, ...],
    producer: str,
) -> NeedLedgerEntry:
    return NeedLedgerEntry(
        x_id=resolution.x_id,
        need_id=need.need_id,
        status=status,
        evidence_atom_ids=_unique_tuple(edge.atom_id for edge in edges),
        issue_codes=_edge_issue_codes(edges),
        metadata={"edge_ids": [edge.edge_id for edge in edges], "producer": producer},
    )


def _retrieve_task(
    *,
    resolution: ClaimResolution,
    need: Need,
    edges: tuple[ResolutionEdge, ...],
    task_index: int,
    producer: str,
) -> InvestigationTask:
    return InvestigationTask(
        task_id=_task_id(resolution.x_id, need.need_id, task_index),
        task_type=InvestigationTaskType.RETRIEVE_CANDIDATE_UNITS,
        target_claim_id=resolution.x_id,
        target_need_id=need.need_id,
        question=_missing_need_question(need),
        allowed_atom_types=_allowed_atom_types_for_need(need.need_type),
        reason="resolver_missing_required_need",
        metadata={
            "producer": producer,
            "resolution_status": resolution.status,
            "rejected_atom_ids": list(resolution.rejected_atom_ids),
            "rejected_reasons": list(_edge_issue_codes(edges)),
        },
    )


def _manual_review_task(
    *,
    resolution: ClaimResolution,
    need: Need,
    edges: tuple[ResolutionEdge, ...],
    task_index: int,
    producer: str,
) -> InvestigationTask:
    return InvestigationTask(
        task_id=_task_id(resolution.x_id, need.need_id, task_index),
        task_type=InvestigationTaskType.REQUEST_MANUAL_REVIEW,
        target_claim_id=resolution.x_id,
        target_need_id=need.need_id,
        question="resolver contradiction을 확인하고 수동 검토 필요 여부를 판단하라.",
        allowed_atom_types=_allowed_atom_types_for_need(need.need_type),
        reason="resolver_contradiction",
        metadata={
            "producer": producer,
            "resolution_status": resolution.status,
            "edge_ids": [edge.edge_id for edge in edges],
            "contradicting_atom_ids": [edge.atom_id for edge in edges],
            "issue_codes": list(_edge_issue_codes(edges)),
        },
    )


def _task_id(x_id: str, need_id: str, index: int) -> str:
    return f"gap_{x_id}_{need_id}_{index:03d}"


def _missing_need_question(need: Need) -> str:
    if need.need_type == NeedType.USAGE_AMOUNT:
        return "사용량 값과 단위를 찾고, 금액/요금 값은 usage_amount로 보지 마라."
    if need.need_type == NeedType.SERVICE_PERIOD:
        return "사용기간 또는 사용월 단서를 찾고, 청구일/납부기한과 구분하라."
    if need.need_type == NeedType.SITE_IDENTITY:
        return "사업장, 현장명, 주소, 식별자 후보를 찾아라."
    if need.need_type == NeedType.SUPPLIER_IDENTITY:
        return "공급자 또는 거래처 identity 후보를 찾아라."
    if need.need_type == NeedType.ACTIVITY_IDENTITY:
        return "활동 항목 또는 사용량 종류를 식별할 수 있는 라벨을 찾아라."
    return "missing need를 채울 수 있는 evidence clue를 찾아라."


def _allowed_atom_types_for_need(need_type: str) -> tuple[str, ...]:
    mapping = {
        NeedType.USAGE_AMOUNT: (
            EvidenceAtomType.USAGE_AMOUNT,
            EvidenceAtomType.CURRENCY_AMOUNT,
        ),
        NeedType.SERVICE_PERIOD: (
            EvidenceAtomType.SERVICE_PERIOD,
            EvidenceAtomType.DATE,
        ),
        NeedType.SITE_IDENTITY: (
            EvidenceAtomType.SITE_IDENTITY,
            EvidenceAtomType.IDENTIFIER,
        ),
        NeedType.SUPPLIER_IDENTITY: (
            EvidenceAtomType.SUPPLIER_IDENTITY,
            EvidenceAtomType.IDENTIFIER,
        ),
        NeedType.ACTIVITY_IDENTITY: (
            EvidenceAtomType.ACTIVITY_IDENTITY,
            EvidenceAtomType.LINE_ITEM,
            EvidenceAtomType.DOCUMENT_TYPE,
        ),
    }
    return mapping.get(need_type, (EvidenceAtomType.UNKNOWN,))


def _edge_issue_codes(edges: tuple[ResolutionEdge, ...]) -> tuple[str, ...]:
    codes: list[str] = []
    for edge in edges:
        reason = edge.metadata.get("reason") or edge.metadata.get("hard_gate") or edge.relation
        codes.append(str(reason))
    return _unique_tuple(codes)


def _unique_tuple(values: Any) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        result.append(value)
        seen.add(value)
    return tuple(result)


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
