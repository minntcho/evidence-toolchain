from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ArtifactPlan:
    artifact_id: str
    carrier: str
    archetype: str
    role: str
    evidence_roles_to_realize: tuple[str, ...] = ()
    logical_requirements: dict[str, Any] = field(default_factory=dict)
    confusion_requirements: tuple[str, ...] = ()
    carrier_profile: str | None = None
    expected_postconditions: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "artifact_id": self.artifact_id,
            "carrier": self.carrier,
            "archetype": self.archetype,
            "role": self.role,
            "evidence_roles_to_realize": list(self.evidence_roles_to_realize),
            "logical_requirements": dict(self.logical_requirements),
            "confusion_requirements": list(self.confusion_requirements),
            "expected_postconditions": list(self.expected_postconditions),
        }
        if self.carrier_profile is not None:
            payload["carrier_profile"] = self.carrier_profile
        return payload


@dataclass(frozen=True)
class BundlePlan:
    scenario_id: str
    rng_seed: int | None = None
    artifacts: tuple[ArtifactPlan, ...] = ()
    expected_syndrome: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "scenario_id": self.scenario_id,
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
            "expected_syndrome": dict(self.expected_syndrome),
        }
        if self.rng_seed is not None:
            payload["rng_seed"] = self.rng_seed
        return payload


@dataclass(frozen=True)
class ToolInvocation:
    id: str
    tool_id: str
    input_state_id: str
    output_state_id: str
    params: dict[str, Any] = field(default_factory=dict)
    seed: int | None = None
    required_postconditions: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "id": self.id,
            "tool_id": self.tool_id,
            "input_state_id": self.input_state_id,
            "output_state_id": self.output_state_id,
            "params": dict(self.params),
            "required_postconditions": list(self.required_postconditions),
        }
        if self.seed is not None:
            payload["seed"] = self.seed
        return payload


@dataclass(frozen=True)
class ToolPlan:
    scenario_id: str
    rng_seed: int | None = None
    invocations: tuple[ToolInvocation, ...] = ()

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "scenario_id": self.scenario_id,
            "invocations": [invocation.to_dict() for invocation in self.invocations],
        }
        if self.rng_seed is not None:
            payload["rng_seed"] = self.rng_seed
        return payload
