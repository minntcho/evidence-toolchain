from __future__ import annotations

from dataclasses import dataclass, field

from evidence_toolchain.artifacts import EvidenceDocument


@dataclass(frozen=True)
class EvidencePreflight:
    """의미 관찰 전에 수집하는 가벼운 문서 신호입니다."""

    document_id: str
    file_name: str
    format: str
    media_type: str
    file_hash: str
    byte_size: int
    has_text_layer: bool
    signals: tuple[str, ...] = ()
    detected_rotation: bool = False
    sample_text: str = ""
    metadata: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "document_id": self.document_id,
            "file_name": self.file_name,
            "format": self.format,
            "media_type": self.media_type,
            "file_hash": self.file_hash,
            "byte_size": self.byte_size,
            "has_text_layer": self.has_text_layer,
            "signals": list(self.signals),
            "detected_rotation": self.detected_rotation,
            "sample_text": self.sample_text,
            "metadata": self.metadata,
        }


def preflight_document(document: EvidenceDocument) -> EvidencePreflight:
    signals = tuple(_split_csv(document.metadata.get("signals", "")))
    return EvidencePreflight(
        document_id=document.document_id,
        file_name=document.file_name,
        format=document.path.suffix.lower().removeprefix(".") or "unknown",
        media_type=document.media_type,
        file_hash=document.file_hash,
        byte_size=document.path.stat().st_size,
        has_text_layer=_has_text_layer(document),
        signals=signals,
        detected_rotation="rotated" in signals,
        sample_text=_sample_text(document.text),
        metadata=dict(document.metadata),
    )


def _has_text_layer(document: EvidenceDocument) -> bool:
    if document.media_type.startswith("image/"):
        return False
    return document.metadata.get("text_layer", "true").lower() == "true"


def _sample_text(text: str, *, max_chars: int = 500) -> str:
    lines = [
        line
        for line in text.splitlines()
        if line.strip() and not line.startswith("ETC-")
    ]
    return "\n".join(lines)[:max_chars]


def _split_csv(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]
