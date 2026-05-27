from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any


class NeedType:
    """X claim을 evidence search task로 낮출 때 쓰는 v0 need vocabulary."""

    ACTIVITY_IDENTITY = "activity_identity"
    USAGE_AMOUNT = "usage_amount"
    SERVICE_PERIOD = "service_period"
    SITE_IDENTITY = "site_identity"
    SUPPLIER_IDENTITY = "supplier_identity"

    ALL = (
        ACTIVITY_IDENTITY,
        USAGE_AMOUNT,
        SERVICE_PERIOD,
        SITE_IDENTITY,
        SUPPLIER_IDENTITY,
    )

    @classmethod
    def is_core_type(cls, need_type: str) -> bool:
        return need_type in cls.ALL


@dataclass(frozen=True)
class DeclaredClaim:
    """증빙 묶음이 지지하거나 반박해야 하는 X claim입니다."""

    x_id: str
    claim_type: str = "declared_claim"
    fields: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _to_json_compatible(self)


@dataclass(frozen=True)
class Need:
    """X claim을 찾기 쉬운 evidence clue requirement로 낮춘 단위입니다."""

    need_id: str
    need_type: str
    required: bool = True
    target_value: Any | None = None
    target_unit: str | None = None
    target_period: str | None = None
    target_text: str | None = None
    acceptable_units: tuple[str, ...] = ()
    acceptable_clues: tuple[str, ...] = ()
    acceptable_aliases: tuple[str, ...] = ()
    preferred_labels: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _to_json_compatible(self)


@dataclass(frozen=True)
class NeedSpec:
    """DeclaredClaim을 atom retrieval과 resolver가 소비할 need list로 낮춘 결과입니다."""

    x_id: str
    needs: tuple[Need, ...]
    disqualifiers: tuple[str, ...] = ()
    producer: str = "default_need_spec_deriver"
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_need(self, need_id: str) -> Need | None:
        for need in self.needs:
            if need.need_id == need_id:
                return need
        return None

    def require_need(self, need_id: str) -> Need:
        need = self.get_need(need_id)
        if need is None:
            raise KeyError(f"Need not found: {need_id}")
        return need

    def to_dict(self) -> dict[str, Any]:
        return _to_json_compatible(self)


DEFAULT_DISQUALIFIERS = (
    "청구금액",
    "납부금액",
    "요금",
    "세금",
    "KRW",
    "전월사용량",
    "예상사용량",
    "납부기한",
    "bill amount",
    "payment amount",
    "tax",
    "previous usage",
    "estimated usage",
    "payment deadline",
)


def derive_need_spec(claim: DeclaredClaim) -> NeedSpec:
    """DeclaredClaim을 직접 검색하지 않고 LLM-readable NeedSpec으로 낮춥니다."""

    fields_map = claim.fields
    needs: list[Need] = []

    activity = fields_map.get("activity")
    if activity is not None:
        needs.append(
            Need(
                need_id=NeedType.ACTIVITY_IDENTITY,
                need_type=NeedType.ACTIVITY_IDENTITY,
                target_text=str(activity),
                acceptable_clues=_string_tuple(activity, *(_field_tuple(fields_map, "activity_aliases"))),
                preferred_labels=("활동", "항목", "activity"),
            )
        )

    amount = fields_map.get("amount")
    unit = fields_map.get("unit")
    if amount is not None or unit is not None:
        target_unit = str(unit) if unit is not None else None
        needs.append(
            Need(
                need_id=NeedType.USAGE_AMOUNT,
                need_type=NeedType.USAGE_AMOUNT,
                target_value=amount,
                target_unit=target_unit,
                acceptable_units=_acceptable_units(target_unit),
                preferred_labels=("사용량", "수량", "usage", "amount", "quantity"),
            )
        )

    period = fields_map.get("period")
    if period is not None:
        needs.append(
            Need(
                need_id=NeedType.SERVICE_PERIOD,
                need_type=NeedType.SERVICE_PERIOD,
                target_period=str(period),
                preferred_labels=("사용기간", "사용월", "청구기간", "service period"),
            )
        )

    site = fields_map.get("site")
    if site is not None:
        needs.append(
            Need(
                need_id=NeedType.SITE_IDENTITY,
                need_type=NeedType.SITE_IDENTITY,
                target_text=str(site),
                acceptable_aliases=_field_tuple(fields_map, "site_aliases"),
                preferred_labels=("사업장", "현장", "site", "location"),
            )
        )

    supplier = fields_map.get("supplier")
    if supplier is not None:
        needs.append(
            Need(
                need_id=NeedType.SUPPLIER_IDENTITY,
                need_type=NeedType.SUPPLIER_IDENTITY,
                required=False,
                target_text=str(supplier),
                acceptable_aliases=_field_tuple(fields_map, "supplier_aliases"),
                preferred_labels=("공급자", "거래처", "supplier", "source"),
            )
        )

    return NeedSpec(
        x_id=claim.x_id,
        needs=tuple(needs),
        disqualifiers=DEFAULT_DISQUALIFIERS,
        metadata={"claim_type": claim.claim_type},
    )


def _field_tuple(fields_map: dict[str, Any], key: str) -> tuple[str, ...]:
    value = fields_map.get(key)
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, tuple | list):
        return tuple(str(item) for item in value)
    return (str(value),)


def _string_tuple(*values: Any) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value)
        if text in seen:
            continue
        result.append(text)
        seen.add(text)
    return tuple(result)


def _acceptable_units(unit: str | None) -> tuple[str, ...]:
    if unit is None:
        return ()

    normalized_unit = unit.strip()
    unit_key = normalized_unit.lower()
    unit_families = {
        "kwh": ("kWh", "MWh"),
        "mwh": ("kWh", "MWh"),
        "l": ("L", "liter", "litre"),
        "liter": ("L", "liter", "litre"),
        "litre": ("L", "liter", "litre"),
        "m3": ("m3", "m^3"),
        "m^3": ("m3", "m^3"),
    }
    return unit_families.get(unit_key, (normalized_unit,))


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
