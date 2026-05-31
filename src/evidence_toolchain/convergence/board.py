from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any

from evidence_toolchain.claims import DeclaredClaim
from evidence_toolchain.convergence.candidates import EvidenceCandidate
from evidence_toolchain.ingestion import EvidenceInventory


@dataclass(frozen=True)
class ConvergenceEvent:
    event_type: str
    candidate_id: str | None = None
    capability_name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _to_json_compatible(self)


@dataclass(frozen=True)
class ReviewTrigger:
    code: str
    severity: str = "review"
    message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _to_json_compatible(self)


@dataclass(frozen=True)
class PartialFailure:
    code: str
    severity: str = "nonblocking"
    message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _to_json_compatible(self)


@dataclass(frozen=True)
class ConvergenceBoard:
    board_id: str
    run_id: str
    inventory: EvidenceInventory
    claims: tuple[DeclaredClaim, ...]
    candidates: tuple[EvidenceCandidate, ...]
    events: tuple[ConvergenceEvent, ...] = ()
    review_triggers: tuple[ReviewTrigger, ...] = ()
    partial_failures: tuple[PartialFailure, ...] = ()
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
