from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from typing import Any

from evidence_toolchain.atoms import EvidenceAtom, EvidenceAtomType
from evidence_toolchain.claims import Need, NeedType
from evidence_toolchain.normalization import (
    NormalizationResult,
    NormalizationTargetKind,
    NormalizedCurrency,
    NormalizedDate,
    NormalizedPeriod,
    NormalizedQuantity,
    NormalizedType,
)


@dataclass(frozen=True)
class DeterministicNormalizer:
    """명확한 atom/need 값만 normalized comparison material로 낮추는 v0 normalizer."""

    producer: str = "deterministic_normalizer_v0"

    def normalize_atom_value(self, atom: EvidenceAtom) -> tuple[NormalizationResult, ...]:
        if atom.atom_type == EvidenceAtomType.USAGE_AMOUNT:
            quantity = _normalize_quantity(
                value=atom.value,
                unit=atom.unit,
                original_text=atom.text,
            )
            if quantity is None:
                return ()
            return (
                NormalizationResult(
                    target_id=atom.atom_id,
                    target_kind=NormalizationTargetKind.ATOM,
                    normalized_type=NormalizedType.QUANTITY,
                    normalized=quantity,
                    producer=self.producer,
                    confidence=1.0,
                ),
            )

        if atom.atom_type == EvidenceAtomType.CURRENCY_AMOUNT:
            currency = _normalize_currency(
                value=atom.value,
                unit=atom.unit,
                original_text=atom.text,
            )
            if currency is None:
                return ()
            return (
                NormalizationResult(
                    target_id=atom.atom_id,
                    target_kind=NormalizationTargetKind.ATOM,
                    normalized_type=NormalizedType.CURRENCY,
                    normalized=currency,
                    producer=self.producer,
                    confidence=1.0,
                ),
            )

        if atom.atom_type == EvidenceAtomType.SERVICE_PERIOD:
            period = _normalize_period(atom.value, original_text=atom.text)
            if period is None:
                return ()
            return (
                NormalizationResult(
                    target_id=atom.atom_id,
                    target_kind=NormalizationTargetKind.ATOM,
                    normalized_type=NormalizedType.PERIOD,
                    normalized=period,
                    producer=self.producer,
                    confidence=1.0,
                ),
            )

        if atom.atom_type == EvidenceAtomType.DATE:
            date = _normalize_date(atom.value, label=atom.label, original_text=atom.text)
            if date is None:
                return ()
            return (
                NormalizationResult(
                    target_id=atom.atom_id,
                    target_kind=NormalizationTargetKind.ATOM,
                    normalized_type=NormalizedType.DATE,
                    normalized=date,
                    producer=self.producer,
                    confidence=1.0,
                ),
            )

        return ()

    def normalize_claim_need(self, need: Need) -> tuple[NormalizationResult, ...]:
        if need.need_type == NeedType.USAGE_AMOUNT:
            quantity = _normalize_quantity(
                value=need.target_value,
                unit=need.target_unit,
                original_text=None,
            )
            if quantity is None:
                return ()
            return (
                NormalizationResult(
                    target_id=need.need_id,
                    target_kind=NormalizationTargetKind.NEED,
                    normalized_type=NormalizedType.QUANTITY,
                    normalized=quantity,
                    producer=self.producer,
                    confidence=1.0,
                ),
            )

        if need.need_type == NeedType.SERVICE_PERIOD:
            period = _normalize_period(need.target_period, original_text=need.target_period)
            if period is None:
                return ()
            return (
                NormalizationResult(
                    target_id=need.need_id,
                    target_kind=NormalizationTargetKind.NEED,
                    normalized_type=NormalizedType.PERIOD,
                    normalized=period,
                    producer=self.producer,
                    confidence=1.0,
                ),
            )

        return ()


def _normalize_quantity(
    *,
    value: Any,
    unit: str | None,
    original_text: str | None,
) -> NormalizedQuantity | None:
    if value is None or unit is None:
        return None

    numeric_value = _parse_number(value)
    if numeric_value is None:
        return None

    canonical_unit = _canonical_unit(unit)
    if canonical_unit is None:
        return NormalizedQuantity(
            value=numeric_value,
            unit=unit,
            dimension="quantity",
            source_value=value,
            source_unit=unit,
            original_text=original_text,
        )

    factor, target_unit, dimension = canonical_unit
    normalized_value = _clean_number(numeric_value * factor)
    metadata = {}
    source_unit = _canonical_source_unit(unit)
    if source_unit != target_unit:
        metadata["conversion"] = f"{source_unit}_to_{target_unit}"

    return NormalizedQuantity(
        value=normalized_value,
        unit=target_unit,
        dimension=dimension,
        source_value=value,
        source_unit=source_unit,
        original_text=original_text,
        metadata=metadata,
    )


def _normalize_currency(
    *,
    value: Any,
    unit: str | None,
    original_text: str | None,
) -> NormalizedCurrency | None:
    if value is None or unit is None:
        return None
    numeric_value = _parse_number(value)
    if numeric_value is None:
        return None
    return NormalizedCurrency(
        value=numeric_value,
        currency=_canonical_currency(unit),
        original_text=original_text,
    )


def _normalize_period(value: Any, *, original_text: str | None) -> NormalizedPeriod | None:
    if isinstance(value, dict):
        start = value.get("start")
        end = value.get("end")
        if isinstance(start, str) and isinstance(end, str):
            return NormalizedPeriod(
                start_date=start,
                end_date=end,
                granularity=_period_granularity(start, end),
                original_text=original_text,
            )

    if isinstance(value, str):
        month_match = _MONTH_RE.fullmatch(value.strip())
        if month_match is not None:
            year = int(month_match.group("year"))
            month = int(month_match.group("month"))
            last_day = calendar.monthrange(year, month)[1]
            return NormalizedPeriod(
                start_date=f"{year:04d}-{month:02d}-01",
                end_date=f"{year:04d}-{month:02d}-{last_day:02d}",
                granularity="month",
                original_text=original_text,
            )

        range_match = _RANGE_RE.search(value)
        if range_match is not None:
            start = range_match.group("start")
            end = range_match.group("end")
            return NormalizedPeriod(
                start_date=start,
                end_date=end,
                granularity=_period_granularity(start, end),
                original_text=original_text,
            )

    return None


def _normalize_date(
    value: Any,
    *,
    label: str | None,
    original_text: str | None,
) -> NormalizedDate | None:
    if not isinstance(value, str) or _DATE_RE.fullmatch(value.strip()) is None:
        return None
    return NormalizedDate(
        date=value.strip(),
        date_role=_date_role(label=label, original_text=original_text),
        original_text=original_text,
    )


def _parse_number(value: Any) -> int | float | None:
    if isinstance(value, int | float):
        return value
    if isinstance(value, str):
        try:
            return _clean_number(float(value.replace(",", "").strip()))
        except ValueError:
            return None
    return None


def _clean_number(value: float | int) -> int | float:
    parsed = float(value)
    return int(parsed) if parsed.is_integer() else parsed


def _canonical_unit(unit: str) -> tuple[float, str, str] | None:
    key = _canonical_source_unit(unit)
    unit_map = {
        "Wh": (0.001, "kWh", "energy"),
        "kWh": (1.0, "kWh", "energy"),
        "MWh": (1000.0, "kWh", "energy"),
        "GWh": (1_000_000.0, "kWh", "energy"),
        "L": (1.0, "L", "volume"),
        "m3": (1000.0, "L", "volume"),
        "kg": (1.0, "kg", "mass"),
        "t": (1000.0, "kg", "mass"),
        "tonne": (1000.0, "kg", "mass"),
    }
    return unit_map.get(key)


def _canonical_source_unit(unit: str) -> str:
    cleaned = unit.strip()
    lowered = cleaned.lower()
    if lowered == "wh":
        return "Wh"
    if lowered == "kwh":
        return "kWh"
    if lowered == "mwh":
        return "MWh"
    if lowered == "gwh":
        return "GWh"
    if lowered in {"l", "liter", "litre"}:
        return "L"
    if lowered in {"m3", "m^3", "m³", "㎥"}:
        return "m3"
    if lowered == "kg":
        return "kg"
    if lowered in {"t", "ton", "tons", "tonne", "tonnes"}:
        return "t"
    return cleaned


def _canonical_currency(unit: str) -> str:
    if unit.strip() == "원":
        return "KRW"
    return unit.strip().upper()


def _period_granularity(start: str, end: str) -> str:
    if start.endswith("-01") and start[:7] == end[:7]:
        year, month = (int(part) for part in start[:7].split("-"))
        if end.endswith(f"-{calendar.monthrange(year, month)[1]:02d}"):
            return "month"
    return "date_range"


def _date_role(*, label: str | None, original_text: str | None) -> str | None:
    text = " ".join(part for part in (label, original_text) if part).lower()
    if any(marker in text for marker in ("납부기한", "due", "payment deadline")):
        return "payment_due_date"
    if any(marker in text for marker in ("청구일", "bill date")):
        return "bill_date"
    if any(marker in text for marker in ("발행일", "issue date")):
        return "issue_date"
    return None


_MONTH_RE = re.compile(r"(?P<year>\d{4})-(?P<month>\d{2})")
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
_RANGE_RE = re.compile(
    r"(?P<start>\d{4}-\d{2}-\d{2})\s*(?:~|–|-|to)\s*(?P<end>\d{4}-\d{2}-\d{2})",
    re.IGNORECASE,
)
