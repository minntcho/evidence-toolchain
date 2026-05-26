from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class EvidenceDocument:
    """Neutral wrapper around source material before downstream judgment."""

    document_id: str
    path: Path
    file_name: str
    media_type: str
    file_hash: str
    text: str = ""
    declared_document_kind: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "document_id": self.document_id,
            "path": str(self.path),
            "file_name": self.file_name,
            "media_type": self.media_type,
            "file_hash": self.file_hash,
            "text": self.text,
            "declared_document_kind": self.declared_document_kind,
            "metadata": self.metadata,
        }

    @classmethod
    def from_path(
        cls,
        path: str | Path,
        *,
        declared_document_kind: str | None = None,
    ) -> "EvidenceDocument":
        document_path = Path(path)
        data = document_path.read_bytes()
        file_hash = hashlib.sha256(data).hexdigest()
        text = data.decode("utf-8", errors="replace")

        metadata = _parse_front_matter(text)
        document_id = metadata.get("case_id", document_path.stem)
        document_kind = declared_document_kind or metadata.get("document_kind")

        return cls(
            document_id=document_id,
            path=document_path,
            file_name=document_path.name,
            media_type=_guess_media_type(document_path),
            file_hash=file_hash,
            text=text,
            declared_document_kind=document_kind,
            metadata=metadata,
        )


def _guess_media_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".txt":
        return "text/plain"
    if suffix == ".pdf":
        return "application/pdf"
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".png":
        return "image/png"
    return "application/octet-stream"


def _parse_front_matter(text: str) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for line in text.splitlines():
        if not line.startswith("ETC-"):
            continue
        key, separator, value = line.partition(":")
        if not separator:
            continue
        metadata[key.removeprefix("ETC-").strip().lower()] = value.strip()
    return metadata
