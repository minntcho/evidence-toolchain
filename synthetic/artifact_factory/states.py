from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class TraceEntry:
    slot_id: str
    locator_type: str
    locator: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "slot_id": self.slot_id,
            "locator_type": self.locator_type,
            "locator": dict(self.locator),
        }
        if self.metadata:
            payload["metadata"] = dict(self.metadata)
        return payload


@dataclass(frozen=True)
class TraceLayer:
    entries: tuple[TraceEntry, ...] = ()
    transforms: tuple[dict[str, Any], ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "entries": [entry.to_dict() for entry in self.entries],
            "transforms": [dict(transform) for transform in self.transforms],
        }


@dataclass(frozen=True)
class ArtifactState:
    state_id: str
    state_type: str
    artifact_id: str
    model_ref: str | None = None
    file_ref: str | None = None
    carrier: str | None = None
    trace: TraceLayer = field(default_factory=TraceLayer)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "state_id": self.state_id,
            "state_type": self.state_type,
            "artifact_id": self.artifact_id,
            "trace": self.trace.to_dict(),
            "metadata": dict(self.metadata),
        }
        if self.model_ref is not None:
            payload["model_ref"] = self.model_ref
        if self.file_ref is not None:
            payload["file_ref"] = self.file_ref
        if self.carrier is not None:
            payload["carrier"] = self.carrier
        return payload
