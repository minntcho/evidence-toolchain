from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any

from evidence_toolchain.issues import EvidenceIssue


class EvidenceAtomType:
    """LLM/VLM과 resolver가 공유하는 v0 semantic evidence candidate vocabulary."""

    DOCUMENT_TYPE = "document_type"
    ACTIVITY_IDENTITY = "activity_identity"
    USAGE_AMOUNT = "usage_amount"
    SERVICE_PERIOD = "service_period"
    SITE_IDENTITY = "site_identity"
    SUPPLIER_IDENTITY = "supplier_identity"
    METER_READING = "meter_reading"
    METER_DELTA = "meter_delta"
    LINE_ITEM = "line_item"
    CURRENCY_AMOUNT = "currency_amount"
    DATE = "date"
    IDENTIFIER = "identifier"
    TABLE_ROW = "table_row"
    NOTE = "note"
    UNKNOWN = "unknown"

    ALL = (
        DOCUMENT_TYPE,
        ACTIVITY_IDENTITY,
        USAGE_AMOUNT,
        SERVICE_PERIOD,
        SITE_IDENTITY,
        SUPPLIER_IDENTITY,
        METER_READING,
        METER_DELTA,
        LINE_ITEM,
        CURRENCY_AMOUNT,
        DATE,
        IDENTIFIER,
        TABLE_ROW,
        NOTE,
        UNKNOWN,
    )

    @classmethod
    def is_core_type(cls, atom_type: str) -> bool:
        return atom_type in cls.ALL


@dataclass(frozen=True)
class EvidenceAtom:
    """X와 매칭 가능한 semantic evidence candidate이며 support 판정은 아닙니다."""

    atom_id: str
    atom_type: str
    source_unit_ids: tuple[str, ...]
    source_artifact_ids: tuple[str, ...]
    producer: str
    text: str | None = None
    label: str | None = None
    value: Any | None = None
    unit: str | None = None
    normalized: dict[str, Any] | None = None
    normalization_hint: dict[str, Any] = field(default_factory=dict)
    confidence: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    issues: tuple[EvidenceIssue, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _to_json_compatible(self)


@dataclass(frozen=True)
class AtomizerResult:
    """EvidenceInventory에서 생성한 atom 후보 묶음입니다."""

    bundle_id: str
    atoms: tuple[EvidenceAtom, ...]
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
