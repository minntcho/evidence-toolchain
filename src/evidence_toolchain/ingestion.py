from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any

from evidence_toolchain.issues import EvidenceIssue


@dataclass(frozen=True)
class AttachmentBundle:
    """함께 제출된 raw attachment 묶음입니다."""

    bundle_id: str
    attachments: tuple["RawAttachment", ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _to_json_compatible(self)


@dataclass(frozen=True)
class RawAttachment:
    """라우팅 전 원본 첨부 파일의 안정적인 identity record입니다."""

    attachment_id: str
    original_filename: str
    path: Path
    byte_size: int
    sha256: str
    extension: str
    declared_media_type: str | None = None
    detected_media_type: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _to_json_compatible(self)

    @classmethod
    def from_path(
        cls,
        path: str | Path,
        *,
        attachment_id: str | None = None,
        declared_media_type: str | None = None,
        detected_media_type: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "RawAttachment":
        attachment_path = Path(path)
        data = attachment_path.read_bytes()
        return cls(
            attachment_id=attachment_id or attachment_path.stem,
            original_filename=attachment_path.name,
            path=attachment_path,
            byte_size=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
            extension=attachment_path.suffix.lower(),
            declared_media_type=declared_media_type,
            detected_media_type=detected_media_type,
            metadata=dict(metadata or {}),
        )


@dataclass(frozen=True)
class RouteDecision:
    """FileKindRouter가 선택한 route와 그 근거를 보존합니다."""

    attachment_id: str
    route: str
    confidence: float
    matched_by: tuple[str, ...]
    rejected_by: tuple[str, ...] = ()
    issues: tuple[EvidenceIssue, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _to_json_compatible(self)


@dataclass(frozen=True)
class SafetyDecision:
    """reader 실행 전에 적용된 safety check 결과입니다."""

    attachment_id: str
    allowed: bool
    checked_by: tuple[str, ...]
    issues: tuple[EvidenceIssue, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _to_json_compatible(self)


@dataclass(frozen=True)
class EvidenceArtifact:
    """파일, 페이지, 시트 같은 출처/물리 단위입니다."""

    artifact_id: str
    artifact_type: str
    parent_id: str | None
    media_type: str
    source_locator: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)
    issues: tuple[EvidenceIssue, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _to_json_compatible(self)


@dataclass(frozen=True)
class EvidenceUnit:
    """reader가 관찰한 raw evidence 단위이며 semantic atom은 아닙니다."""

    unit_id: str
    artifact_id: str
    unit_type: str
    producer: str
    text: str | None = None
    value: Any | None = None
    bbox: tuple[float, float, float, float] | None = None
    locator: dict[str, Any] = field(default_factory=dict)
    confidence: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _to_json_compatible(self)


@dataclass(frozen=True)
class EvidenceInventory:
    """bundle ingestion 결과로 생성된 공통 provenance inventory입니다."""

    bundle_id: str
    attachments: tuple[RawAttachment, ...]
    artifacts: tuple[EvidenceArtifact, ...]
    units: tuple[EvidenceUnit, ...]
    route_decisions: tuple[RouteDecision, ...]
    safety_decisions: tuple[SafetyDecision, ...] = ()
    issues: tuple[EvidenceIssue, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _to_json_compatible(self)


def merge_evidence_inventories(
    *,
    bundle_id: str,
    inventories: tuple[EvidenceInventory, ...],
) -> EvidenceInventory:
    """single-attachment inventories를 bundle-level inventory로 결합합니다."""

    return EvidenceInventory(
        bundle_id=bundle_id,
        attachments=tuple(
            attachment
            for inventory in inventories
            for attachment in inventory.attachments
        ),
        artifacts=tuple(
            artifact
            for inventory in inventories
            for artifact in inventory.artifacts
        ),
        units=tuple(
            unit
            for inventory in inventories
            for unit in inventory.units
        ),
        route_decisions=tuple(
            route_decision
            for inventory in inventories
            for route_decision in inventory.route_decisions
        ),
        safety_decisions=tuple(
            safety_decision
            for inventory in inventories
            for safety_decision in inventory.safety_decisions
        ),
        issues=tuple(
            issue
            for inventory in inventories
            for issue in inventory.issues
        ),
    )


def _to_json_compatible(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value):
        return {
            item.name: _to_json_compatible(getattr(value, item.name))
            for item in fields(value)
        }
    if isinstance(value, dict):
        return {
            str(key): _to_json_compatible(item)
            for key, item in value.items()
        }
    if isinstance(value, tuple | list):
        return [_to_json_compatible(item) for item in value]
    return value
