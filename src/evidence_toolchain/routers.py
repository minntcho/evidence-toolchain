from __future__ import annotations

from typing import Protocol

from evidence_toolchain.artifacts import EvidenceDocument
from evidence_toolchain.planner import EvidenceToolPlan, plan_document
from evidence_toolchain.preflight import EvidencePreflight


class ObservationRouter(Protocol):
    """observation과 tool planning을 연결하는 framework-neutral router port입니다."""

    def route(
        self,
        document: EvidenceDocument,
        preflight: EvidencePreflight,
    ) -> EvidenceToolPlan:
        ...


class RuleObservationRouter:
    """현재 rule planner 동작을 보존하는 deterministic router입니다."""

    def route(
        self,
        document: EvidenceDocument,
        preflight: EvidencePreflight,
    ) -> EvidenceToolPlan:
        return plan_document(document)
