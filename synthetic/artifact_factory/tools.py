from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from synthetic.artifact_factory.states import ArtifactState


@dataclass(frozen=True)
class ToolDescriptor:
    id: str
    kind: str
    version: str
    implementation_digest: str
    input_state: str
    output_state: str
    supported_carriers: tuple[str, ...] = ()
    params_schema: dict[str, Any] = field(default_factory=dict)
    postconditions: tuple[str, ...] = ()
    deterministic: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "kind": self.kind,
            "version": self.version,
            "implementation_digest": self.implementation_digest,
            "input_state": self.input_state,
            "output_state": self.output_state,
            "supported_carriers": list(self.supported_carriers),
            "params_schema": dict(self.params_schema),
            "postconditions": list(self.postconditions),
            "deterministic": self.deterministic,
        }


@dataclass(frozen=True)
class ToolContext:
    scenario_id: str
    workdir: Path
    seed: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolResult:
    output_state: ArtifactState
    trace_delta: dict[str, Any] = field(default_factory=dict)
    postconditions: dict[str, bool] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "output_state": self.output_state.to_dict(),
            "trace_delta": dict(self.trace_delta),
            "postconditions": dict(self.postconditions),
            "metrics": dict(self.metrics),
            "warnings": list(self.warnings),
        }


class SyntheticTool(Protocol):
    def descriptor(self) -> ToolDescriptor:
        raise NotImplementedError

    def execute(
        self,
        input_state: ArtifactState,
        params: dict[str, object],
        ctx: ToolContext,
    ) -> ToolResult:
        raise NotImplementedError


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, SyntheticTool] = {}

    def register(self, tool: SyntheticTool) -> None:
        descriptor = tool.descriptor()
        if descriptor.id in self._tools:
            raise ValueError(f"Duplicate synthetic tool id: {descriptor.id}")
        self._tools[descriptor.id] = tool

    def get(self, tool_id: str) -> SyntheticTool:
        try:
            return self._tools[tool_id]
        except KeyError as exc:
            raise KeyError(f"Unknown synthetic tool id: {tool_id}") from exc

    def find(
        self,
        *,
        kind: str | None = None,
        input_state: str | None = None,
        output_state: str | None = None,
        carrier: str | None = None,
    ) -> tuple[SyntheticTool, ...]:
        matches: list[SyntheticTool] = []
        for tool in self._tools.values():
            descriptor = tool.descriptor()
            if kind is not None and descriptor.kind != kind:
                continue
            if input_state is not None and descriptor.input_state != input_state:
                continue
            if output_state is not None and descriptor.output_state != output_state:
                continue
            if carrier is not None and not _supports_carrier(descriptor, carrier):
                continue
            matches.append(tool)
        return tuple(matches)

    def require_transition(
        self,
        tool_id: str,
        input_state: ArtifactState,
        *,
        carrier: str | None = None,
    ) -> ToolDescriptor:
        descriptor = self.get(tool_id).descriptor()
        if descriptor.input_state != input_state.state_type:
            raise ValueError(
                f"{tool_id} cannot accept state type {input_state.state_type}; "
                f"expected {descriptor.input_state}"
            )
        carrier_to_check = carrier if carrier is not None else input_state.carrier
        if carrier_to_check is not None and not _supports_carrier(
            descriptor,
            carrier_to_check,
        ):
            raise ValueError(
                f"{tool_id} does not support carrier {carrier_to_check}"
            )
        return descriptor


def _supports_carrier(descriptor: ToolDescriptor, carrier: str) -> bool:
    return not descriptor.supported_carriers or carrier in descriptor.supported_carriers
