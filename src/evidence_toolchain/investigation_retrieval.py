from __future__ import annotations

import re
from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any

from evidence_toolchain.claims import Need, NeedSpec, NeedType
from evidence_toolchain.ingestion import EvidenceInventory, EvidenceUnit
from evidence_toolchain.investigation import (
    InvestigationTask,
    InvestigationTaskResult,
    InvestigationTaskStatus,
    InvestigationTaskType,
)
from evidence_toolchain.issues import EvidenceIssue


@dataclass(frozen=True)
class EvidenceUnitRetrievalResult:
    """Existing EvidenceUnit ids selected for a follow-up atomization task."""

    task_id: str
    target_claim_id: str | None
    target_need_id: str | None
    selected_unit_ids: tuple[str, ...]
    rejected_unit_ids: tuple[str, ...] = ()
    matched_clues: tuple[str, ...] = ()
    issues: tuple[EvidenceIssue, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_task_result(self) -> InvestigationTaskResult:
        status = InvestigationTaskStatus.COMPLETED
        if not self.selected_unit_ids:
            status = InvestigationTaskStatus.NO_NEW_CLUE
        if any(issue.code == "candidate_unit_retrieval_invalid_task_type" for issue in self.issues):
            status = InvestigationTaskStatus.FAILED

        metadata = {
            **self.metadata,
            "selected_unit_ids": list(self.selected_unit_ids),
            "rejected_unit_ids": list(self.rejected_unit_ids),
            "matched_clues": list(self.matched_clues),
        }
        if self.selected_unit_ids:
            metadata["next_task_type"] = InvestigationTaskType.ATOMIZE_UNIT_CLUSTER

        return InvestigationTaskResult(
            task_id=self.task_id,
            status=status,
            issues=self.issues,
            metadata=metadata,
        )

    def to_atomize_task(
        self,
        *,
        source_task: InvestigationTask,
    ) -> InvestigationTask | None:
        if not self.selected_unit_ids:
            return None
        return InvestigationTask(
            task_id=f"{source_task.task_id}_atomize_001",
            task_type=InvestigationTaskType.ATOMIZE_UNIT_CLUSTER,
            target_claim_id=source_task.target_claim_id,
            target_need_id=source_task.target_need_id,
            target_artifact_ids=source_task.target_artifact_ids,
            target_unit_ids=self.selected_unit_ids,
            question=source_task.question,
            allowed_atom_types=source_task.allowed_atom_types,
            reason="candidate_units_retrieved",
            metadata={
                "producer": self.metadata.get("producer"),
                "source_task_id": source_task.task_id,
                "retrieval_profile": self.metadata.get("retrieval_profile"),
                "matched_clues": list(self.matched_clues),
            },
        )

    def to_dict(self) -> dict[str, Any]:
        return _to_json_compatible(self)


@dataclass(frozen=True)
class CandidateUnitRetriever:
    """Deterministic v0 bridge from retrieve_candidate_units to unit ids."""

    producer: str = "candidate_unit_retriever_v0"
    max_units: int = 12

    def retrieve(
        self,
        *,
        task: InvestigationTask,
        inventory: EvidenceInventory,
        need_spec: NeedSpec | None = None,
    ) -> EvidenceUnitRetrievalResult:
        if task.task_type != InvestigationTaskType.RETRIEVE_CANDIDATE_UNITS:
            return EvidenceUnitRetrievalResult(
                task_id=task.task_id,
                target_claim_id=task.target_claim_id,
                target_need_id=task.target_need_id,
                selected_unit_ids=(),
                issues=(
                    EvidenceIssue(
                        code="candidate_unit_retrieval_invalid_task_type",
                        severity="warning",
                        message="CandidateUnitRetriever only handles retrieve_candidate_units tasks.",
                    ),
                ),
                metadata={"producer": self.producer},
            )

        need = _matching_need(task, need_spec)
        profile = _profile_for(task, need)
        disqualifiers = tuple(need_spec.disqualifiers if need_spec is not None else ())
        selected: list[str] = []
        rejected: list[str] = []
        matched_clues: list[str] = []
        unit_scores: list[dict[str, Any]] = []

        for unit in inventory.units:
            score = _score_unit(
                unit=unit,
                need=need,
                profile=profile,
                disqualifiers=disqualifiers,
                allowed_atom_types=task.allowed_atom_types,
            )
            if score.selected and len(selected) < self.max_units:
                selected.append(unit.unit_id)
                matched_clues.extend(score.matched_clues)
            elif score.rejected:
                rejected.append(unit.unit_id)
            if score.matched_clues or score.rejected_clues:
                unit_scores.append(
                    {
                        "unit_id": unit.unit_id,
                        "score": score.value,
                        "matched_clues": list(score.matched_clues),
                        "rejected_clues": list(score.rejected_clues),
                    }
                )

        issues: list[EvidenceIssue] = []
        if need_spec is not None and need is None and task.target_need_id:
            issues.append(
                EvidenceIssue(
                    code="candidate_unit_retrieval_need_missing",
                    severity="warning",
                    message=f"NeedSpec does not include target need '{task.target_need_id}'.",
                )
            )
        if not selected:
            issues.append(
                EvidenceIssue(
                    code="candidate_unit_retrieval_no_units_selected",
                    severity="info",
                    message="No EvidenceUnit matched the retrieve_candidate_units task.",
                )
            )

        return EvidenceUnitRetrievalResult(
            task_id=task.task_id,
            target_claim_id=task.target_claim_id,
            target_need_id=task.target_need_id,
            selected_unit_ids=tuple(selected),
            rejected_unit_ids=tuple(rejected),
            matched_clues=_unique_tuple(matched_clues),
            issues=tuple(issues),
            metadata={
                "producer": self.producer,
                "retrieval_profile": profile.name,
                "unit_scores": unit_scores,
            },
        )


@dataclass(frozen=True)
class _RetrievalProfile:
    name: str
    positive_clues: tuple[str, ...]
    counter_clues: tuple[str, ...] = ()
    rejected_clues: tuple[str, ...] = ()


@dataclass(frozen=True)
class _UnitScore:
    value: int
    selected: bool
    rejected: bool
    matched_clues: tuple[str, ...]
    rejected_clues: tuple[str, ...]


def _matching_need(task: InvestigationTask, need_spec: NeedSpec | None) -> Need | None:
    if need_spec is None or task.target_need_id is None:
        return None
    return need_spec.get_need(task.target_need_id)


def _profile_for(task: InvestigationTask, need: Need | None) -> _RetrievalProfile:
    need_type = need.need_type if need is not None else task.target_need_id
    if need_type == NeedType.USAGE_AMOUNT:
        return _RetrievalProfile(
            name=NeedType.USAGE_AMOUNT,
            positive_clues=(
                "사용량",
                "수량",
                "전력량",
                "공급량",
                "소비량",
                "usage",
                "quantity",
                "amount",
                "kWh",
                "MWh",
                "Wh",
                "L",
                "m3",
                "m³",
                "㎥",
                "kg",
                "ton",
                "tonne",
            ),
            counter_clues=("금액", "요금", "합계", "부가세", "KRW", "USD", "EUR"),
            rejected_clues=("납부", "납부기한", "payment deadline"),
        )
    if need_type == NeedType.SERVICE_PERIOD:
        return _RetrievalProfile(
            name=NeedType.SERVICE_PERIOD,
            positive_clues=(
                "사용기간",
                "사용월",
                "청구기간",
                "검침기간",
                "service period",
                "billing period",
                "청구일",
                "발행일",
                "납부기한",
            ),
        )
    if need_type == NeedType.SITE_IDENTITY:
        return _RetrievalProfile(
            name=NeedType.SITE_IDENTITY,
            positive_clues=(
                "사업장",
                "현장",
                "고객명",
                "주소",
                "site",
                "plant",
                "facility",
                "meter id",
            ),
        )
    if need_type == NeedType.SUPPLIER_IDENTITY:
        return _RetrievalProfile(
            name=NeedType.SUPPLIER_IDENTITY,
            positive_clues=("공급자", "거래처", "상호", "supplier", "vendor", "source"),
        )
    if need_type == NeedType.ACTIVITY_IDENTITY:
        return _RetrievalProfile(
            name=NeedType.ACTIVITY_IDENTITY,
            positive_clues=(
                "전력",
                "전기",
                "수도",
                "경유",
                "휘발유",
                "activity",
                "electricity",
                "diesel",
                "water",
                "fuel",
            ),
        )
    return _RetrievalProfile(name="unknown", positive_clues=("evidence", "clue"))


def _score_unit(
    *,
    unit: EvidenceUnit,
    need: Need | None,
    profile: _RetrievalProfile,
    disqualifiers: tuple[str, ...],
    allowed_atom_types: tuple[str, ...],
) -> _UnitScore:
    content = _unit_content(unit)
    if not content:
        return _UnitScore(0, False, False, (), ())

    matched: list[str] = []
    rejected: list[str] = []
    value = 0

    for clue in _need_specific_clues(need):
        if _contains_clue(content, clue):
            matched.append(clue)
            value += 4

    for clue in profile.positive_clues:
        if _contains_clue(content, clue):
            matched.append(clue)
            value += 2

    allow_counter_clues = "currency_amount" in allowed_atom_types
    if allow_counter_clues:
        for clue in profile.counter_clues:
            if _contains_clue(content, clue):
                matched.append(clue)
                value += 1

    for clue in profile.rejected_clues + disqualifiers:
        if _contains_clue(content, clue):
            rejected.append(clue)

    has_match = bool(matched)
    has_rejection_only = bool(rejected) and not has_match
    return _UnitScore(
        value=value,
        selected=has_match,
        rejected=has_rejection_only,
        matched_clues=_unique_tuple(matched),
        rejected_clues=_unique_tuple(rejected),
    )


def _need_specific_clues(need: Need | None) -> tuple[str, ...]:
    if need is None:
        return ()
    clues: list[str] = []
    for value in (
        need.target_text,
        need.target_unit,
        need.target_period,
        *need.acceptable_units,
        *need.acceptable_clues,
        *need.acceptable_aliases,
        *need.preferred_labels,
    ):
        if value is not None:
            clues.append(str(value))
    return _unique_tuple(clues)


def _unit_content(unit: EvidenceUnit) -> str:
    parts: list[str] = []
    if unit.text is not None:
        parts.append(unit.text)
    if unit.value is not None:
        parts.append(str(unit.value))
    for value in unit.locator.values():
        parts.append(str(value))
    return " ".join(parts)


def _contains_clue(content: str, clue: str) -> bool:
    if not clue:
        return False
    if _is_short_ascii_token(clue):
        pattern = rf"(?<![A-Za-z0-9]){re.escape(clue)}(?![A-Za-z0-9])"
        return re.search(pattern, content, flags=re.IGNORECASE) is not None
    return clue.casefold() in content.casefold()


def _is_short_ascii_token(clue: str) -> bool:
    return clue.isascii() and clue.replace("^", "").replace("³", "").isalnum() and len(clue) <= 4


def _unique_tuple(values: Any) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        item = str(value)
        if item in seen:
            continue
        result.append(item)
        seen.add(item)
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
        return {str(key): _to_json_compatible(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_to_json_compatible(item) for item in value]
    return value
