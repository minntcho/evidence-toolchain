from __future__ import annotations

from dataclasses import dataclass, field

from evidence_toolchain.artifacts import EvidenceDocument


@dataclass(frozen=True)
class EvidenceObservation:
    document_id: str
    document_class: str
    has_text_layer: bool
    quality: str
    signals: list[str] = field(default_factory=list)


def observe_document(document: EvidenceDocument) -> EvidenceObservation:
    metadata = document.metadata
    document_class = (
        document.declared_document_kind
        or metadata.get("document_kind")
        or "unknown_document"
    )
    quality = metadata.get("quality", "unknown")
    signals = _split_csv(metadata.get("signals", ""))
    has_text_layer = metadata.get("text_layer", "true").lower() == "true"

    if "rotated" in signals and quality == "unknown":
        quality = "rotated"
    if document.media_type.startswith("image/"):
        has_text_layer = False

    return EvidenceObservation(
        document_id=document.document_id,
        document_class=document_class,
        has_text_layer=has_text_layer,
        quality=quality,
        signals=signals,
    )


def _split_csv(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]
