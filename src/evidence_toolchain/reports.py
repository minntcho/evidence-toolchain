from __future__ import annotations

from dataclasses import asdict, dataclass, field

from evidence_toolchain.artifacts import EvidenceDocument
from evidence_toolchain.planner import EvidenceToolPlan


@dataclass(frozen=True)
class ExtractedField:
    name: str
    value: str
    unit: str | None = None
    confidence: float | None = None
    provenance: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class EvidenceReport:
    document_id: str
    document: EvidenceDocument
    plan: EvidenceToolPlan
    fields: list[ExtractedField] = field(default_factory=list)
    issues: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
