from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any

from evidence_toolchain.convergence.board import PartialFailure, ReviewTrigger


@dataclass(frozen=True)
class ClaimConvergenceReport:
    claim_id: str
    target_schema_id: str
    claim_alignment_status: str
    evidence_convergence_status: str
    selected_support_set: tuple[str, ...]
    candidate_ids: tuple[str, ...]
    unresolved_gaps: tuple[str, ...]
    review_triggers: tuple[ReviewTrigger, ...] = ()
    partial_failures: tuple[PartialFailure, ...] = ()
    downstream_verdict: None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _to_json_compatible(self)


@dataclass(frozen=True)
class ConvergenceReport:
    run_id: str
    bundle_id: str
    claim_reports: tuple[ClaimConvergenceReport, ...]
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
