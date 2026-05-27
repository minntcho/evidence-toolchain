from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any

from evidence_toolchain.issues import EvidenceIssue


class ResolutionRelation:
    """X claim과 EvidenceAtom 사이 edge가 표현할 수 있는 v0 relation vocabulary."""

    SUPPORTS = "supports"
    SUPPORTS_AFTER_UNIT_NORMALIZATION = "supports_after_unit_normalization"
    SUPPORTS_BY_AGGREGATION = "supports_by_aggregation"
    SUPPORTS_BY_DERIVATION = "supports_by_derivation"
    CONTRADICTS = "contradicts"
    CONTEXTUALIZES = "contextualizes"
    REJECTED_FOR_NEED = "rejected_for_need"
    NEEDS_REVIEW = "needs_review"

    ALL = (
        SUPPORTS,
        SUPPORTS_AFTER_UNIT_NORMALIZATION,
        SUPPORTS_BY_AGGREGATION,
        SUPPORTS_BY_DERIVATION,
        CONTRADICTS,
        CONTEXTUALIZES,
        REJECTED_FOR_NEED,
        NEEDS_REVIEW,
    )

    @classmethod
    def is_core_relation(cls, relation: str) -> bool:
        return relation in cls.ALL


class ResolutionStatus:
    """하나의 X claim에 대한 v0 resolution status vocabulary."""

    SUPPORTED_DIRECT = "supported_direct"
    SUPPORTED_AFTER_UNIT_NORMALIZATION = "supported_after_unit_normalization"
    SUPPORTED_BY_AGGREGATION = "supported_by_aggregation"
    SUPPORTED_BY_DERIVATION = "supported_by_derivation"
    CONTRADICTED = "contradicted"
    PARTIAL_SUPPORT = "partial_support"
    AMBIGUOUS = "ambiguous"
    INSUFFICIENT = "insufficient"
    NEEDS_REVIEW = "needs_review"

    ALL = (
        SUPPORTED_DIRECT,
        SUPPORTED_AFTER_UNIT_NORMALIZATION,
        SUPPORTED_BY_AGGREGATION,
        SUPPORTED_BY_DERIVATION,
        CONTRADICTED,
        PARTIAL_SUPPORT,
        AMBIGUOUS,
        INSUFFICIENT,
        NEEDS_REVIEW,
    )

    @classmethod
    def is_core_status(cls, status: str) -> bool:
        return status in cls.ALL


@dataclass(frozen=True)
class ResolutionEdge:
    """DeclaredClaim X와 EvidenceAtom Y 후보 사이의 relation record입니다."""

    edge_id: str
    x_id: str
    atom_id: str
    relation: str
    need_id: str | None = None
    basis: tuple[str, ...] = ()
    confidence: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    issues: tuple[EvidenceIssue, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _to_json_compatible(self)


@dataclass(frozen=True)
class ClaimResolution:
    """하나의 X claim에 대한 resolver output record입니다."""

    x_id: str
    status: str
    edge_ids: tuple[str, ...] = ()
    supporting_atom_ids: tuple[str, ...] = ()
    rejected_atom_ids: tuple[str, ...] = ()
    missing_need_ids: tuple[str, ...] = ()
    basis: tuple[str, ...] = ()
    remaining_gaps: tuple[str, ...] = ()
    issues: tuple[EvidenceIssue, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _to_json_compatible(self)


@dataclass(frozen=True)
class EvidenceResolutionGraph:
    """X claim과 EvidenceAtom 후보 사이의 edge/resolution 묶음입니다."""

    bundle_id: str
    claim_ids: tuple[str, ...]
    atom_ids: tuple[str, ...]
    edges: tuple[ResolutionEdge, ...] = ()
    resolutions: tuple[ClaimResolution, ...] = ()
    issues: tuple[EvidenceIssue, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

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
