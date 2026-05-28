from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class DocumentIntent:
    document_id: str
    archetype: str
    role: str
    carrier: str

    def to_dict(self) -> dict[str, object]:
        return {
            "document_id": self.document_id,
            "archetype": self.archetype,
            "role": self.role,
            "carrier": self.carrier,
        }


@dataclass(frozen=True)
class ConfusionEdge:
    confusion_type: str
    source: str
    target: str | None = None
    params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "confusion_type": self.confusion_type,
            "source": self.source,
            "params": dict(self.params),
        }
        if self.target is not None:
            payload["target"] = self.target
        return payload


@dataclass(frozen=True)
class ScenarioIR:
    scenario_id: str
    rng_seed: int
    intake_events: tuple[dict[str, Any], ...] = ()
    document_intents: tuple[DocumentIntent, ...] = ()
    evidence_need: dict[str, Any] = field(default_factory=dict)
    latent_evidence_roles: dict[str, Any] = field(default_factory=dict)
    confusion_graph: tuple[ConfusionEdge, ...] = ()
    expected_syndrome: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "scenario_id": self.scenario_id,
            "rng_seed": self.rng_seed,
            "intake_events": [dict(event) for event in self.intake_events],
            "document_intents": [intent.to_dict() for intent in self.document_intents],
            "evidence_need": dict(self.evidence_need),
            "latent_evidence_roles": dict(self.latent_evidence_roles),
            "confusion_graph": [edge.to_dict() for edge in self.confusion_graph],
            "expected_syndrome": dict(self.expected_syndrome),
        }
