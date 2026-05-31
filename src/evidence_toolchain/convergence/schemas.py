from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SlotDef:
    slot_id: str
    bit: int
    value_kind: str
    required: bool = True
    comparable: bool = False
    directly_comparable: bool = False
    alignment_required: bool = True
    provenance_required: bool = True

    def __post_init__(self) -> None:
        if not self.slot_id:
            raise ValueError("slot_id must not be empty")
        if self.bit <= 0 or self.bit & (self.bit - 1):
            raise ValueError("bit must be a positive single-bit mask")
        if not self.value_kind:
            raise ValueError("value_kind must not be empty")


@dataclass(frozen=True)
class EvidenceSchema:
    schema_id: str
    slots: tuple[SlotDef, ...]

    def __post_init__(self) -> None:
        if not self.schema_id:
            raise ValueError("schema_id must not be empty")
        if not self.slots:
            raise ValueError("schema must define at least one slot")

        slot_ids = [slot.slot_id for slot in self.slots]
        if len(slot_ids) != len(set(slot_ids)):
            raise ValueError("slot_id values must be unique")

        bits = [slot.bit for slot in self.slots]
        if len(bits) != len(set(bits)):
            raise ValueError("slot bits must be unique")

    @property
    def required_mask(self) -> int:
        return _mask_for(slot.bit for slot in self.slots if slot.required)

    @property
    def comparable_mask(self) -> int:
        return _mask_for(slot.bit for slot in self.slots if slot.comparable)

    @property
    def directly_comparable_mask(self) -> int:
        return _mask_for(slot.bit for slot in self.slots if slot.directly_comparable)

    @property
    def alignment_required_mask(self) -> int:
        return _mask_for(slot.bit for slot in self.slots if slot.alignment_required)

    @property
    def provenance_required_mask(self) -> int:
        return _mask_for(slot.bit for slot in self.slots if slot.provenance_required)

    @property
    def schema_mask(self) -> int:
        return _mask_for(slot.bit for slot in self.slots)


def _mask_for(bits: object) -> int:
    mask = 0
    for bit in bits:
        mask |= bit
    return mask
