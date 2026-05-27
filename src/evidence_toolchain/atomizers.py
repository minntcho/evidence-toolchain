from __future__ import annotations

import re
from dataclasses import dataclass

from evidence_toolchain.atoms import AtomizerResult, EvidenceAtom, EvidenceAtomType
from evidence_toolchain.ingestion import EvidenceInventory, EvidenceUnit


ATOMIZABLE_UNIT_TYPES = {"text_span", "table_cell"}


@dataclass(frozen=True)
class SimpleTextAtomizer:
    """명확한 text/table cell 패턴만 EvidenceAtom 후보로 올리는 baseline atomizer."""

    producer: str = "simple_text_atomizer"

    def atomize(self, inventory: EvidenceInventory) -> AtomizerResult:
        atoms: list[EvidenceAtom] = []
        for unit in inventory.units:
            if unit.unit_type not in ATOMIZABLE_UNIT_TYPES or not unit.text:
                continue
            for text in _candidate_texts(unit.text):
                atoms.extend(self._atoms_from_text(inventory, unit, text, len(atoms)))

        return AtomizerResult(bundle_id=inventory.bundle_id, atoms=tuple(atoms))

    def _atoms_from_text(
        self,
        inventory: EvidenceInventory,
        unit: EvidenceUnit,
        text: str,
        existing_count: int,
    ) -> tuple[EvidenceAtom, ...]:
        service_period = _service_period_atom(
            atom_id=_atom_id(inventory.bundle_id, existing_count + 1),
            producer=self.producer,
            unit=unit,
            text=text,
        )
        if service_period is not None:
            return (service_period,)

        currency = _currency_atom(
            atom_id=_atom_id(inventory.bundle_id, existing_count + 1),
            producer=self.producer,
            unit=unit,
            text=text,
        )
        if currency is not None:
            return (currency,)

        usage = _usage_amount_atom(
            atom_id=_atom_id(inventory.bundle_id, existing_count + 1),
            producer=self.producer,
            unit=unit,
            text=text,
        )
        if usage is not None:
            return (usage,)

        date = _date_atom(
            atom_id=_atom_id(inventory.bundle_id, existing_count + 1),
            producer=self.producer,
            unit=unit,
            text=text,
        )
        if date is not None:
            return (date,)

        return ()


def atomize_inventory(
    inventory: EvidenceInventory,
    *,
    atomizer: SimpleTextAtomizer | None = None,
) -> AtomizerResult:
    """EvidenceInventory를 deterministic baseline atom 후보로 변환합니다."""

    return (atomizer or SimpleTextAtomizer()).atomize(inventory)


def _candidate_texts(text: str) -> tuple[str, ...]:
    return tuple(line.strip() for line in text.splitlines() if line.strip())


def _usage_amount_atom(
    *,
    atom_id: str,
    producer: str,
    unit: EvidenceUnit,
    text: str,
) -> EvidenceAtom | None:
    match = _USAGE_AMOUNT_RE.search(text)
    if match is None:
        return None
    value = _parse_number(match.group("value"))
    unit_text = _canonical_usage_unit(match.group("unit"))
    return EvidenceAtom(
        atom_id=atom_id,
        atom_type=EvidenceAtomType.USAGE_AMOUNT,
        source_unit_ids=(unit.unit_id,),
        source_artifact_ids=(unit.artifact_id,),
        producer=producer,
        text=match.group(0).strip(),
        label=_label_from_match(match.group("label"), text),
        value=value,
        unit=unit_text,
        normalization_hint=_normalization_hint_for_usage_unit(unit_text),
        confidence=0.7,
        metadata={"matched_pattern": "usage_amount_with_unit"},
    )


def _currency_atom(
    *,
    atom_id: str,
    producer: str,
    unit: EvidenceUnit,
    text: str,
) -> EvidenceAtom | None:
    match = _CURRENCY_AMOUNT_RE.search(text)
    if match is None:
        return None
    unit_text = _canonical_currency_unit(match.group("unit"))
    return EvidenceAtom(
        atom_id=atom_id,
        atom_type=EvidenceAtomType.CURRENCY_AMOUNT,
        source_unit_ids=(unit.unit_id,),
        source_artifact_ids=(unit.artifact_id,),
        producer=producer,
        text=match.group(0).strip(),
        label=_label_from_match(match.group("label"), text),
        value=_parse_number(match.group("value")),
        unit=unit_text,
        normalization_hint={
            "dimension": "currency",
            "compatible_units": [unit_text],
        },
        confidence=0.7,
        metadata={"matched_pattern": "currency_amount_with_unit"},
    )


def _service_period_atom(
    *,
    atom_id: str,
    producer: str,
    unit: EvidenceUnit,
    text: str,
) -> EvidenceAtom | None:
    match = _SERVICE_PERIOD_RE.search(text)
    if match is None:
        return None
    return EvidenceAtom(
        atom_id=atom_id,
        atom_type=EvidenceAtomType.SERVICE_PERIOD,
        source_unit_ids=(unit.unit_id,),
        source_artifact_ids=(unit.artifact_id,),
        producer=producer,
        text=match.group(0).strip(),
        label=_label_from_match(match.group("label"), text),
        value={
            "start": match.group("start"),
            "end": match.group("end"),
        },
        confidence=0.7,
        metadata={"matched_pattern": "service_period_range"},
    )


def _date_atom(
    *,
    atom_id: str,
    producer: str,
    unit: EvidenceUnit,
    text: str,
) -> EvidenceAtom | None:
    match = _DATE_RE.search(text)
    if match is None:
        return None
    return EvidenceAtom(
        atom_id=atom_id,
        atom_type=EvidenceAtomType.DATE,
        source_unit_ids=(unit.unit_id,),
        source_artifact_ids=(unit.artifact_id,),
        producer=producer,
        text=match.group(0).strip(),
        label=_label_from_match(match.group("label"), text),
        value=match.group("date"),
        confidence=0.65,
        metadata={"matched_pattern": "date"},
    )


def _atom_id(bundle_id: str, index: int) -> str:
    return f"atom_{bundle_id}_{index:03d}"


def _parse_number(text: str) -> int | float:
    value = text.replace(",", "")
    parsed = float(value)
    return int(parsed) if parsed.is_integer() else parsed


def _label_from_match(label: str | None, text: str) -> str | None:
    if label is not None and label.strip():
        return label.strip()
    before_number = re.split(r"\d", text, maxsplit=1)[0].strip()
    return before_number or None


def _canonical_usage_unit(unit: str) -> str:
    lower = unit.lower()
    if lower == "mwh":
        return "MWh"
    if lower == "kwh":
        return "kWh"
    if lower == "wh":
        return "Wh"
    if lower in {"m3", "㎥"}:
        return "m3"
    return unit


def _canonical_currency_unit(unit: str) -> str:
    if unit == "원":
        return "KRW"
    return unit.upper()


def _normalization_hint_for_usage_unit(unit: str) -> dict[str, object]:
    if unit in {"Wh", "kWh", "MWh"}:
        return {"dimension": "energy", "compatible_units": ["kWh", "MWh"]}
    if unit == "L":
        return {"dimension": "volume", "compatible_units": ["L"]}
    if unit == "m3":
        return {"dimension": "volume", "compatible_units": ["m3"]}
    return {"dimension": "quantity", "compatible_units": [unit]}


_LABEL_PATTERN = r"(?P<label>[가-힣A-Za-z0-9_ /-]{0,24}?)"
_NUMBER_PATTERN = r"(?P<value>[0-9][0-9,]*(?:\.[0-9]+)?)"
_DATE_PATTERN = r"(?P<date>\d{4}-\d{2}-\d{2})"

_USAGE_AMOUNT_RE = re.compile(
    rf"{_LABEL_PATTERN}\s*{_NUMBER_PATTERN}\s*(?P<unit>kWh|MWh|Wh|L|m3|㎥)\b",
    re.IGNORECASE,
)
_CURRENCY_AMOUNT_RE = re.compile(
    rf"{_LABEL_PATTERN}\s*{_NUMBER_PATTERN}\s*(?P<unit>KRW|USD|EUR|원)\b",
    re.IGNORECASE,
)
_SERVICE_PERIOD_RE = re.compile(
    r"(?P<label>사용기간|사용월|청구기간|service period)\s*"
    r"(?P<start>\d{4}-\d{2}-\d{2})\s*(?:~|–|-|to)\s*"
    r"(?P<end>\d{4}-\d{2}-\d{2})",
    re.IGNORECASE,
)
_DATE_RE = re.compile(
    rf"{_LABEL_PATTERN}\s*{_DATE_PATTERN}",
    re.IGNORECASE,
)
