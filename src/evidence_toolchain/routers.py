from __future__ import annotations

from typing import Protocol

from evidence_toolchain.artifacts import EvidenceDocument
from evidence_toolchain.planner import EvidenceToolPlan, plan_document
from evidence_toolchain.preflight import EvidencePreflight


class ObservationRouter(Protocol):
    """Framework-neutral router port for observation and tool planning."""

    def route(
        self,
        document: EvidenceDocument,
        preflight: EvidencePreflight,
    ) -> EvidenceToolPlan:
        ...


class RuleObservationRouter:
    """Deterministic router that preserves the current rule planner behavior."""

    def route(
        self,
        document: EvidenceDocument,
        preflight: EvidencePreflight,
    ) -> EvidenceToolPlan:
        return plan_document(document)
