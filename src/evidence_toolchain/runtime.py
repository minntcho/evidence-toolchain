from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass, replace
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class EvidenceEvent:
    """Append-only event emitted during an evidence processing run."""

    run_id: str
    sequence: int
    event_type: str
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _to_json_compatible(self)


@dataclass(frozen=True)
class EvidenceStep:
    """A framework-neutral planned or executed unit of work."""

    name: str
    status: str
    capability: str | None = None
    reason: str | None = None
    target: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _to_json_compatible(self)


@dataclass(frozen=True)
class EvidenceToolResult:
    """Framework-neutral output from a capability execution."""

    capability: str
    status: str
    outputs: dict[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    artifacts: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _to_json_compatible(self)


@dataclass(frozen=True)
class EvidenceRunState:
    """Serializable snapshot of an evidence processing run."""

    run_id: str
    document: Any
    observation: Any | None = None
    plan: Any | None = None
    completed_steps: tuple[EvidenceStep, ...] = ()
    pending_steps: tuple[EvidenceStep, ...] = ()
    tool_results: tuple[EvidenceToolResult, ...] = ()
    issues: tuple[Any, ...] = ()
    interrupts: tuple[Any, ...] = ()
    events: tuple[EvidenceEvent, ...] = ()
    final_report: Any | None = None

    def record_event(self, event: EvidenceEvent) -> "EvidenceRunState":
        return replace(self, events=self.events + (event,))

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
