from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any

from evidence_toolchain.atoms import EvidenceAtom, EvidenceAtomType
from evidence_toolchain.claims import DeclaredClaim, Need, NeedSpec, NeedType
from evidence_toolchain.issues import EvidenceIssue
from evidence_toolchain.normalization import (
    NormalizationResult,
    NormalizationTargetKind,
    NormalizedCurrency,
    NormalizedPeriod,
    NormalizedQuantity,
    NormalizedType,
)


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


@dataclass(frozen=True)
class HardGateResolver:
    """명시적으로 제공된 normalized material만 소비하는 v0 hard-gate resolver입니다."""

    producer: str = "hard_gate_resolver_v0"
    quantity_tolerance: float = 0.0

    def resolve(
        self,
        *,
        bundle_id: str,
        claims: tuple[DeclaredClaim, ...],
        need_specs: tuple[NeedSpec, ...],
        atoms: tuple[EvidenceAtom, ...],
        normalization_results: tuple[NormalizationResult, ...],
    ) -> EvidenceResolutionGraph:
        normalizations = _NormalizationIndex(normalization_results)
        atoms_by_id = {atom.atom_id: atom for atom in atoms}
        edges: list[ResolutionEdge] = []
        resolutions: list[ClaimResolution] = []

        for claim in claims:
            need_spec = _need_spec_for_claim(claim.x_id, need_specs)
            if need_spec is None:
                resolutions.append(
                    ClaimResolution(
                        x_id=claim.x_id,
                        status=ResolutionStatus.INSUFFICIENT,
                        missing_need_ids=(),
                        remaining_gaps=("need_spec_missing",),
                        metadata={"producer": self.producer},
                    )
                )
                continue

            claim_edges: list[ResolutionEdge] = []
            missing_need_ids: list[str] = []
            supporting_atom_ids: list[str] = []
            rejected_atom_ids: list[str] = []

            for need in need_spec.needs:
                produced_edges = self._resolve_need(
                    claim_id=claim.x_id,
                    need=need,
                    atoms_by_id=atoms_by_id,
                    normalizations=normalizations,
                    next_edge_index=len(edges) + len(claim_edges) + 1,
                )
                claim_edges.extend(produced_edges)

                need_supports = [
                    edge
                    for edge in produced_edges
                    if edge.relation
                    in {
                        ResolutionRelation.SUPPORTS,
                        ResolutionRelation.SUPPORTS_AFTER_UNIT_NORMALIZATION,
                    }
                ]
                if need.required and not need_supports:
                    missing_need_ids.append(need.need_id)
                supporting_atom_ids.extend(edge.atom_id for edge in need_supports)
                rejected_atom_ids.extend(
                    edge.atom_id
                    for edge in produced_edges
                    if edge.relation == ResolutionRelation.REJECTED_FOR_NEED
                )

            edges.extend(claim_edges)
            resolutions.append(
                ClaimResolution(
                    x_id=claim.x_id,
                    status=_resolution_status(claim_edges, missing_need_ids),
                    edge_ids=tuple(edge.edge_id for edge in claim_edges),
                    supporting_atom_ids=_unique_tuple(supporting_atom_ids),
                    rejected_atom_ids=_unique_tuple(rejected_atom_ids),
                    missing_need_ids=tuple(missing_need_ids),
                    basis=_resolution_basis(claim_edges, missing_need_ids),
                    remaining_gaps=tuple(missing_need_ids),
                    metadata={"producer": self.producer},
                )
            )

        return EvidenceResolutionGraph(
            bundle_id=bundle_id,
            claim_ids=tuple(claim.x_id for claim in claims),
            atom_ids=tuple(atom.atom_id for atom in atoms),
            edges=tuple(edges),
            resolutions=tuple(resolutions),
            metadata={"producer": self.producer},
        )

    def _resolve_need(
        self,
        *,
        claim_id: str,
        need: Need,
        atoms_by_id: dict[str, EvidenceAtom],
        normalizations: "_NormalizationIndex",
        next_edge_index: int,
    ) -> tuple[ResolutionEdge, ...]:
        if need.need_type == NeedType.USAGE_AMOUNT:
            return self._resolve_usage_amount_need(
                claim_id=claim_id,
                need=need,
                atoms_by_id=atoms_by_id,
                normalizations=normalizations,
                next_edge_index=next_edge_index,
            )
        if need.need_type == NeedType.SERVICE_PERIOD:
            return self._resolve_service_period_need(
                claim_id=claim_id,
                need=need,
                atoms_by_id=atoms_by_id,
                normalizations=normalizations,
                next_edge_index=next_edge_index,
            )
        return ()

    def _resolve_usage_amount_need(
        self,
        *,
        claim_id: str,
        need: Need,
        atoms_by_id: dict[str, EvidenceAtom],
        normalizations: "_NormalizationIndex",
        next_edge_index: int,
    ) -> tuple[ResolutionEdge, ...]:
        need_quantity = normalizations.need_quantity(need.need_id)
        if need_quantity is None:
            return ()

        edges: list[ResolutionEdge] = []
        for atom_result in normalizations.atom_results:
            atom = atoms_by_id.get(atom_result.target_id)
            if atom is None:
                continue

            if atom_result.normalized_type == NormalizedType.CURRENCY and isinstance(
                atom_result.normalized,
                NormalizedCurrency,
            ):
                edges.append(
                    _edge(
                        index=next_edge_index + len(edges),
                        x_id=claim_id,
                        atom_id=atom.atom_id,
                        relation=ResolutionRelation.REJECTED_FOR_NEED,
                        need_id=need.need_id,
                        basis=("currency amount는 usage amount hard gate를 통과할 수 없음",),
                        metadata={"reason": "currency_value_not_usage_quantity"},
                    )
                )
                continue

            if atom.atom_type != EvidenceAtomType.USAGE_AMOUNT:
                continue
            if atom_result.normalized_type != NormalizedType.QUANTITY or not isinstance(
                atom_result.normalized,
                NormalizedQuantity,
            ):
                continue

            atom_quantity = atom_result.normalized
            if atom_quantity.dimension != need_quantity.dimension or atom_quantity.unit != need_quantity.unit:
                edges.append(
                    _edge(
                        index=next_edge_index + len(edges),
                        x_id=claim_id,
                        atom_id=atom.atom_id,
                        relation=ResolutionRelation.REJECTED_FOR_NEED,
                        need_id=need.need_id,
                        basis=("quantity dimension 또는 unit이 usage need와 호환되지 않음",),
                        metadata={"reason": "quantity_dimension_or_unit_mismatch"},
                    )
                )
                continue

            if _numbers_equal(atom_quantity.value, need_quantity.value, tolerance=self.quantity_tolerance):
                relation = _quantity_support_relation(atom_quantity, need_quantity)
                edges.append(
                    _edge(
                        index=next_edge_index + len(edges),
                        x_id=claim_id,
                        atom_id=atom.atom_id,
                        relation=relation,
                        need_id=need.need_id,
                        basis=_quantity_support_basis(atom_quantity, need_quantity),
                        metadata={"hard_gate": _quantity_hard_gate(relation)},
                    )
                )
            else:
                edges.append(
                    _edge(
                        index=next_edge_index + len(edges),
                        x_id=claim_id,
                        atom_id=atom.atom_id,
                        relation=ResolutionRelation.CONTRADICTS,
                        need_id=need.need_id,
                        basis=("usage quantity가 normalized comparison 후 target value와 다름",),
                        metadata={"hard_gate": "quantity_value_mismatch"},
                    )
                )

        return tuple(edges)

    def _resolve_service_period_need(
        self,
        *,
        claim_id: str,
        need: Need,
        atoms_by_id: dict[str, EvidenceAtom],
        normalizations: "_NormalizationIndex",
        next_edge_index: int,
    ) -> tuple[ResolutionEdge, ...]:
        need_period = normalizations.need_period(need.need_id)
        if need_period is None:
            return ()

        edges: list[ResolutionEdge] = []
        for atom_result in normalizations.atom_results:
            atom = atoms_by_id.get(atom_result.target_id)
            if atom is None or atom.atom_type != EvidenceAtomType.SERVICE_PERIOD:
                continue
            if atom_result.normalized_type != NormalizedType.PERIOD or not isinstance(
                atom_result.normalized,
                NormalizedPeriod,
            ):
                continue

            atom_period = atom_result.normalized
            if (
                atom_period.start_date == need_period.start_date
                and atom_period.end_date == need_period.end_date
            ):
                edges.append(
                    _edge(
                        index=next_edge_index + len(edges),
                        x_id=claim_id,
                        atom_id=atom.atom_id,
                        relation=ResolutionRelation.SUPPORTS,
                        need_id=need.need_id,
                        basis=("service period가 claim need와 일치",),
                        metadata={"hard_gate": "period_exact_match"},
                    )
                )
            else:
                edges.append(
                    _edge(
                        index=next_edge_index + len(edges),
                        x_id=claim_id,
                        atom_id=atom.atom_id,
                        relation=ResolutionRelation.CONTRADICTS,
                        need_id=need.need_id,
                        basis=("service period가 claim need와 다름",),
                        metadata={"hard_gate": "period_mismatch"},
                    )
                )

        return tuple(edges)


@dataclass(frozen=True)
class _NormalizationIndex:
    results: tuple[NormalizationResult, ...]

    @property
    def atom_results(self) -> tuple[NormalizationResult, ...]:
        return tuple(
            result
            for result in self.results
            if result.target_kind == NormalizationTargetKind.ATOM
        )

    def need_quantity(self, need_id: str) -> NormalizedQuantity | None:
        result = self._need_result(need_id, NormalizedType.QUANTITY)
        if result is None or not isinstance(result.normalized, NormalizedQuantity):
            return None
        return result.normalized

    def need_period(self, need_id: str) -> NormalizedPeriod | None:
        result = self._need_result(need_id, NormalizedType.PERIOD)
        if result is None or not isinstance(result.normalized, NormalizedPeriod):
            return None
        return result.normalized

    def _need_result(self, need_id: str, normalized_type: str) -> NormalizationResult | None:
        for result in self.results:
            if (
                result.target_kind == NormalizationTargetKind.NEED
                and result.target_id == need_id
                and result.normalized_type == normalized_type
            ):
                return result
        return None


def _need_spec_for_claim(x_id: str, need_specs: tuple[NeedSpec, ...]) -> NeedSpec | None:
    for need_spec in need_specs:
        if need_spec.x_id == x_id:
            return need_spec
    return None


def _edge(
    *,
    index: int,
    x_id: str,
    atom_id: str,
    relation: str,
    need_id: str,
    basis: tuple[str, ...],
    metadata: dict[str, Any],
) -> ResolutionEdge:
    return ResolutionEdge(
        edge_id=f"edge_{index:03d}",
        x_id=x_id,
        atom_id=atom_id,
        relation=relation,
        need_id=need_id,
        basis=basis,
        metadata=metadata,
    )


def _numbers_equal(value: Any, other: Any, *, tolerance: float) -> bool:
    try:
        return abs(float(value) - float(other)) <= tolerance
    except (TypeError, ValueError):
        return value == other


def _quantity_support_relation(
    atom_quantity: NormalizedQuantity,
    need_quantity: NormalizedQuantity,
) -> str:
    if atom_quantity.source_unit == need_quantity.source_unit:
        return ResolutionRelation.SUPPORTS
    return ResolutionRelation.SUPPORTS_AFTER_UNIT_NORMALIZATION


def _quantity_hard_gate(relation: str) -> str:
    if relation == ResolutionRelation.SUPPORTS_AFTER_UNIT_NORMALIZATION:
        return "quantity_equal_after_normalization"
    return "quantity_equal"


def _quantity_support_basis(
    atom_quantity: NormalizedQuantity,
    need_quantity: NormalizedQuantity,
) -> tuple[str, ...]:
    if atom_quantity.source_unit and atom_quantity.source_unit != need_quantity.source_unit:
        return (
            f"{atom_quantity.source_value} {atom_quantity.source_unit} = "
            f"{atom_quantity.value} {atom_quantity.unit}",
            "usage quantity가 normalized comparison 후 target value와 일치",
        )
    return ("usage quantity가 target value와 직접 일치",)


def _resolution_status(
    edges: list[ResolutionEdge],
    missing_need_ids: list[str],
) -> str:
    if any(edge.relation == ResolutionRelation.CONTRADICTS for edge in edges):
        return ResolutionStatus.CONTRADICTED
    if missing_need_ids:
        return ResolutionStatus.INSUFFICIENT
    if any(
        edge.relation == ResolutionRelation.SUPPORTS_AFTER_UNIT_NORMALIZATION
        for edge in edges
    ):
        return ResolutionStatus.SUPPORTED_AFTER_UNIT_NORMALIZATION
    if any(edge.relation == ResolutionRelation.SUPPORTS for edge in edges):
        return ResolutionStatus.SUPPORTED_DIRECT
    return ResolutionStatus.INSUFFICIENT


def _resolution_basis(
    edges: list[ResolutionEdge],
    missing_need_ids: list[str],
) -> tuple[str, ...]:
    if missing_need_ids:
        return tuple(f"required need가 충족되지 않음: {need_id}" for need_id in missing_need_ids)
    return tuple(basis for edge in edges for basis in edge.basis)


def _unique_tuple(values: list[str]) -> tuple[str, ...]:
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
