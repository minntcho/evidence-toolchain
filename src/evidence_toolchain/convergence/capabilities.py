from __future__ import annotations

from typing import Any

from evidence_toolchain.claims import DeclaredClaim
from evidence_toolchain.convergence.candidates import EvidenceCandidate
from evidence_toolchain.convergence.patches import CapabilitySpec, MaskPatch
from evidence_toolchain.convergence.schemas import EvidenceSchema, SlotDef
from evidence_toolchain.ingestion import EvidenceInventory, EvidenceUnit


SITE = 1 << 0
PERIOD = 1 << 1
ACTIVITY = 1 << 2
QUANTITY = 1 << 3
UNIT = 1 << 4

SCHEMA_ID = "utility_usage_record.v1"


def utility_usage_schema() -> EvidenceSchema:
    return EvidenceSchema(
        schema_id=SCHEMA_ID,
        slots=(
            SlotDef("site", SITE, "identifier", directly_comparable=True),
            SlotDef("period", PERIOD, "period", comparable=True),
            SlotDef("activity", ACTIVITY, "identifier", directly_comparable=True),
            SlotDef("quantity", QUANTITY, "quantity", comparable=True),
            SlotDef("unit", UNIT, "unit", comparable=True),
        ),
    )


def simple_slot_assigner_spec(schema: EvidenceSchema) -> CapabilitySpec:
    return CapabilitySpec(
        name="simple_slot_assigner",
        handles_mask=schema.required_mask,
        input_required_mask=0,
        handles_gap_kinds=frozenset({"missing", "unassigned"}),
        may_set_present_mask=schema.required_mask,
        may_set_assigned_mask=schema.required_mask,
        cost=5,
    )


def deterministic_normalizer_spec(schema: EvidenceSchema) -> CapabilitySpec:
    return CapabilitySpec(
        name="deterministic_normalizer",
        handles_mask=schema.comparable_mask,
        input_required_mask=schema.comparable_mask,
        handles_gap_kinds=frozenset({"unnormalized"}),
        may_set_normalized_mask=schema.comparable_mask,
        cost=10,
    )


def simple_aligner_spec(schema: EvidenceSchema) -> CapabilitySpec:
    return CapabilitySpec(
        name="simple_aligner",
        handles_mask=schema.alignment_required_mask,
        input_required_mask=schema.alignment_required_mask,
        handles_gap_kinds=frozenset({"unaligned"}),
        may_set_aligned_mask=schema.alignment_required_mask,
        cost=20,
    )


def seed_usage_candidate(
    inventory: EvidenceInventory,
    claim: DeclaredClaim,
    *,
    schema: EvidenceSchema | None = None,
    candidate_id: str = "cand_001",
    metadata: dict[str, Any] | None = None,
) -> EvidenceCandidate:
    active_schema = schema or utility_usage_schema()
    candidate_metadata = {"bundle_id": inventory.bundle_id}
    candidate_metadata.update(metadata or {})
    return EvidenceCandidate(
        candidate_id=candidate_id,
        claim_id=claim.x_id,
        schema_id=active_schema.schema_id,
        metadata=candidate_metadata,
    )


def propose_simple_slot_assignment(
    candidate: EvidenceCandidate,
    inventory: EvidenceInventory,
    *,
    schema: EvidenceSchema | None = None,
) -> MaskPatch:
    active_schema = schema or utility_usage_schema()
    payload_updates: dict[int, Any] = {}
    source_ref_updates: dict[int, tuple[str, ...]] = {}

    for unit in _candidate_units(candidate, inventory):
        slot_bit = _slot_bit_for_unit(unit)
        if slot_bit is None or slot_bit not in _schema_bits(active_schema):
            continue
        if slot_bit in payload_updates:
            continue

        value = _payload_value_for_slot(unit, slot_bit)
        if value is None:
            continue

        payload_updates[slot_bit] = value
        source_ref_updates[slot_bit] = (unit.unit_id,)

    assigned_mask = _keys_mask(payload_updates)
    return MaskPatch(
        candidate_id=candidate.candidate_id,
        producer="simple_slot_assigner",
        capability_name="simple_slot_assigner",
        set_present_mask=assigned_mask,
        set_assigned_mask=assigned_mask,
        payload_updates=payload_updates,
        source_ref_updates=source_ref_updates,
    )


def propose_deterministic_normalization(
    candidate: EvidenceCandidate,
    *,
    schema: EvidenceSchema | None = None,
) -> MaskPatch:
    active_schema = schema or utility_usage_schema()
    normalized_payload_updates: dict[int, Any] = {}

    quantity_value, unit_value = _normalize_quantity_and_unit(
        candidate.payload_by_slot.get(QUANTITY),
        candidate.payload_by_slot.get(UNIT),
    )

    for slot in active_schema.slots:
        if not slot.comparable or not candidate.assigned_mask & slot.bit:
            continue

        if slot.bit == QUANTITY:
            value = quantity_value
        elif slot.bit == UNIT:
            value = unit_value
        else:
            value = _normalize_text(candidate.payload_by_slot.get(slot.bit))

        if value is None:
            continue
        normalized_payload_updates[slot.bit] = value

    return MaskPatch(
        candidate_id=candidate.candidate_id,
        producer="deterministic_normalizer",
        capability_name="deterministic_normalizer",
        set_normalized_mask=_keys_mask(normalized_payload_updates),
        normalized_payload_updates=normalized_payload_updates,
    )


def propose_simple_alignment(
    candidate: EvidenceCandidate,
    claim: DeclaredClaim,
    *,
    schema: EvidenceSchema | None = None,
) -> MaskPatch:
    active_schema = schema or utility_usage_schema()
    alignment_updates: dict[int, dict[str, Any]] = {}

    for slot in active_schema.slots:
        if not candidate.assigned_mask & slot.bit:
            continue

        candidate_value = candidate.normalized_payload_by_slot.get(
            slot.bit,
            candidate.payload_by_slot.get(slot.bit),
        )
        claim_value = _claim_value_for_slot(claim, slot.bit)

        if _values_align(candidate_value, claim_value, slot.bit):
            alignment_updates[slot.bit] = {
                "status": "matched",
                "candidate_value": candidate_value,
                "claim_value": claim_value,
            }

    return MaskPatch(
        candidate_id=candidate.candidate_id,
        producer="simple_aligner",
        capability_name="simple_aligner",
        set_aligned_mask=_keys_mask(alignment_updates),
        alignment_updates=alignment_updates,
    )


def _slot_bit_for_unit(unit: EvidenceUnit) -> int | None:
    header = unit.metadata.get("slot") or unit.locator.get("header")
    if header is None:
        return None
    return _SLOT_BY_HEADER.get(str(header).strip().lower())


def _candidate_units(
    candidate: EvidenceCandidate,
    inventory: EvidenceInventory,
) -> tuple[EvidenceUnit, ...]:
    row = candidate.metadata.get("row")
    artifact_id = candidate.metadata.get("artifact_id")
    if row is None and artifact_id is None:
        return inventory.units

    units: list[EvidenceUnit] = []
    for unit in inventory.units:
        if row is not None and unit.locator.get("row") != row:
            continue
        if artifact_id is not None and unit.artifact_id != artifact_id:
            continue
        units.append(unit)
    return tuple(units)


def _payload_value_for_slot(unit: EvidenceUnit, slot_bit: int) -> Any | None:
    raw_value = unit.value if unit.value is not None else unit.text
    if raw_value is None:
        return None
    if slot_bit == QUANTITY:
        return _to_number(raw_value)
    return str(raw_value).strip()


def _normalize_quantity_and_unit(
    quantity: Any,
    unit: Any,
) -> tuple[int | float | None, str | None]:
    quantity_value = _to_number(quantity)
    unit_text = _normalize_text(unit)
    if quantity_value is None or unit_text is None:
        return quantity_value, unit_text

    unit_key = unit_text.lower()
    if unit_key == "mwh":
        return _compact_number(quantity_value * 1000), "kWh"
    if unit_key == "kwh":
        return _compact_number(quantity_value), "kWh"
    if unit_key == "wh":
        return _compact_number(quantity_value / 1000), "kWh"
    return _compact_number(quantity_value), unit_text


def _claim_value_for_slot(claim: DeclaredClaim, slot_bit: int) -> Any | None:
    if slot_bit == SITE:
        return claim.fields.get("site")
    if slot_bit == PERIOD:
        return claim.fields.get("period")
    if slot_bit == ACTIVITY:
        return claim.fields.get("activity")
    if slot_bit == QUANTITY:
        return claim.fields.get("amount")
    if slot_bit == UNIT:
        return claim.fields.get("unit")
    return None


def _values_align(candidate_value: Any, claim_value: Any, slot_bit: int) -> bool:
    if claim_value is None or candidate_value is None:
        return False
    if slot_bit == QUANTITY:
        candidate_number = _to_number(candidate_value)
        claim_number = _to_number(claim_value)
        if candidate_number is None or claim_number is None:
            return False
        return abs(candidate_number - claim_number) < 1e-9
    return str(candidate_value).strip().lower() == str(claim_value).strip().lower()


def _normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _to_number(value: Any) -> int | float | None:
    if value is None:
        return None
    if isinstance(value, int | float):
        return _compact_number(float(value))
    text = str(value).replace(",", "").strip()
    if not text:
        return None
    try:
        return _compact_number(float(text))
    except ValueError:
        return None


def _compact_number(value: float) -> int | float:
    if value.is_integer():
        return int(value)
    return value


def _schema_bits(schema: EvidenceSchema) -> set[int]:
    return {slot.bit for slot in schema.slots}


def _keys_mask(mapping: dict[int, object]) -> int:
    mask = 0
    for slot_bit in mapping:
        mask |= slot_bit
    return mask


_SLOT_BY_HEADER = {
    "site": SITE,
    "location": SITE,
    "period": PERIOD,
    "service period": PERIOD,
    "activity": ACTIVITY,
    "fuel": ACTIVITY,
    "amount": QUANTITY,
    "quantity": QUANTITY,
    "usage": QUANTITY,
    "usage amount": QUANTITY,
    "unit": UNIT,
    "uom": UNIT,
}
