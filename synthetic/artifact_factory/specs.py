from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ScenarioDocumentSpec:
    document_id: str
    archetype: str
    role: str
    carrier: str
    quality_profile: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "document_id": self.document_id,
            "archetype": self.archetype,
            "role": self.role,
            "carrier": self.carrier,
        }
        if self.quality_profile is not None:
            payload["quality_profile"] = self.quality_profile
        if self.metadata:
            payload["metadata"] = dict(self.metadata)
        return payload


@dataclass(frozen=True)
class ScenarioConfusionSpec:
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
class ScenarioSpec:
    scenario_id: str
    seed: int
    intake_story: dict[str, Any] = field(default_factory=dict)
    evidence_need: dict[str, Any] = field(default_factory=dict)
    documents: tuple[ScenarioDocumentSpec, ...] = ()
    confusions: tuple[ScenarioConfusionSpec, ...] = ()
    expected_syndrome: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "scenario_id": self.scenario_id,
            "seed": self.seed,
            "intake_story": dict(self.intake_story),
            "evidence_need": dict(self.evidence_need),
            "documents": [document.to_dict() for document in self.documents],
            "confusions": [confusion.to_dict() for confusion in self.confusions],
            "expected_syndrome": dict(self.expected_syndrome),
        }
