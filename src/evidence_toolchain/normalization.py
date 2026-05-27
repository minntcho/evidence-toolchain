from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from evidence_toolchain.issues import EvidenceIssue

if TYPE_CHECKING:
    from evidence_toolchain.atoms import EvidenceAtom
    from evidence_toolchain.claims import Need


class NormalizationTargetKind:
    """정규화 결과가 어떤 contract object를 대상으로 하는지 나타냅니다."""

    ATOM = "atom"
    NEED = "need"
    CLAIM = "claim"

    ALL = (ATOM, NEED, CLAIM)

    @classmethod
    def is_core_kind(cls, target_kind: str) -> bool:
        return target_kind in cls.ALL


class NormalizedType:
    """resolver가 비교 재료로 소비할 v0 normalized value vocabulary."""

    QUANTITY = "quantity"
    PERIOD = "period"
    DATE = "date"
    CURRENCY = "currency"
    IDENTIFIER = "identifier"
    UNKNOWN = "unknown"

    ALL = (QUANTITY, PERIOD, DATE, CURRENCY, IDENTIFIER, UNKNOWN)

    @classmethod
    def is_core_type(cls, normalized_type: str) -> bool:
        return normalized_type in cls.ALL


NormalizedScalar = str | int | float | bool | None


@dataclass(frozen=True)
class NormalizedQuantity:
    """비교 가능한 quantity form입니다. support 판단은 포함하지 않습니다."""

    value: NormalizedScalar
    unit: str | None
    dimension: str | None
    source_value: NormalizedScalar = None
    source_unit: str | None = None
    original_text: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _to_json_compatible(self)


@dataclass(frozen=True)
class NormalizedPeriod:
    """비교 가능한 service/reporting period form입니다."""

    start_date: str
    end_date: str
    granularity: str
    original_text: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _to_json_compatible(self)


@dataclass(frozen=True)
class NormalizedDate:
    """단일 date 후보입니다. date_role은 bill date와 due date 같은 구분을 담습니다."""

    date: str
    date_role: str | None = None
    original_text: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _to_json_compatible(self)


@dataclass(frozen=True)
class NormalizedCurrency:
    """비교 가능한 currency amount form입니다. usage quantity로 승격하지 않습니다."""

    value: NormalizedScalar
    currency: str
    original_text: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _to_json_compatible(self)


@dataclass(frozen=True)
class NormalizedIdentifier:
    """site, supplier, meter id 같은 identifier 후보의 normalized form입니다."""

    value: str
    namespace: str | None = None
    original_text: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _to_json_compatible(self)


NormalizedValue = (
    NormalizedQuantity
    | NormalizedPeriod
    | NormalizedDate
    | NormalizedCurrency
    | NormalizedIdentifier
)


@dataclass(frozen=True)
class NormalizationResult:
    """atom/need/claim을 resolver가 비교 가능한 normalized value로 낮춘 결과입니다."""

    target_id: str
    target_kind: str
    normalized_type: str
    normalized: NormalizedValue | dict[str, Any] | None
    producer: str
    confidence: float | None = None
    issues: tuple[EvidenceIssue, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _to_json_compatible(self)


@runtime_checkable
class NormalizationAdapter(Protocol):
    """normalizer tool/adapter가 구현해야 하는 최소 interface입니다."""

    producer: str

    def normalize_atom_value(self, atom: "EvidenceAtom") -> tuple[NormalizationResult, ...]:
        """EvidenceAtom 후보를 normalized comparison material로 낮춥니다."""

    def normalize_claim_need(self, need: "Need") -> tuple[NormalizationResult, ...]:
        """NeedSpec의 개별 need를 normalized comparison material로 낮춥니다."""


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
