from __future__ import annotations

from dataclasses import dataclass

from evidence_toolchain.ingestion import (
    EvidenceArtifact,
    EvidenceInventory,
    RawAttachment,
    RouteDecision,
    SafetyDecision,
)
from evidence_toolchain.issues import EvidenceIssue


MACRO_ENABLED_EXTENSIONS = {".docm", ".pptm", ".xlsm"}


@dataclass(frozen=True)
class SafetyLimits:
    """attachment reader 실행 전에 적용할 크기 제한입니다."""

    max_file_size_bytes: int = 50 * 1024 * 1024


class SafetyPolicy:
    """untrusted attachment를 reader에 넘기기 전 최소 안전 결정을 만듭니다."""

    def __init__(self, limits: SafetyLimits | None = None) -> None:
        self._limits = limits or SafetyLimits()

    def evaluate(self, attachment: RawAttachment) -> SafetyDecision:
        checked_by = [
            f"max_file_size:{self._limits.max_file_size_bytes}",
            "no_external_fetch",
        ]
        issues: list[EvidenceIssue] = []
        allowed = True

        if attachment.byte_size > self._limits.max_file_size_bytes:
            allowed = False
            issues.append(
                EvidenceIssue(
                    code="file_too_large",
                    severity="blocking",
                    message="Attachment exceeds the configured file size limit.",
                )
            )

        if attachment.extension in MACRO_ENABLED_EXTENSIONS:
            checked_by.append("macro_no_execute")
            issues.append(
                EvidenceIssue(
                    code="macro_enabled_office_file",
                    severity="warning",
                    message="Macro-enabled Office files must not execute macros during ingestion.",
                )
            )

        return SafetyDecision(
            attachment_id=attachment.attachment_id,
            allowed=allowed,
            checked_by=tuple(checked_by),
            issues=tuple(issues),
        )


class FileKindRouter:
    """raw attachment의 물리 형식을 route decision으로 낮춥니다."""

    def route(self, attachment: RawAttachment) -> RouteDecision:
        extension = attachment.extension
        matched_by = [f"extension:{extension}"] if extension else []
        rejected_by: list[str] = []
        issues: list[EvidenceIssue] = []

        if attachment.declared_media_type is not None:
            matched_by.append(f"declared_media_type:{attachment.declared_media_type}")
        if attachment.detected_media_type is not None:
            matched_by.append(f"detected_media_type:{attachment.detected_media_type}")

        if extension == ".pdf":
            if _has_magic(attachment, b"%PDF"):
                matched_by.append("magic:%PDF")
                return _decision(attachment, "pdf", 0.98, matched_by)
            rejected_by.append("magic:%PDF_missing")
            issues.append(
                EvidenceIssue(
                    code="file_signature_mismatch",
                    severity="blocking",
                    message="Attachment has a PDF extension but does not start with a PDF signature.",
                )
            )
            return _decision(
                attachment,
                "unknown",
                0.2,
                matched_by,
                rejected_by=rejected_by,
                issues=issues,
            )

        route = _route_from_extension_or_media_type(attachment)
        if route is not None:
            return _decision(attachment, route, 0.9, matched_by)

        issues.append(
            EvidenceIssue(
                code="unsupported_media_type",
                severity="blocking",
                message="Attachment media type is not supported by the file router.",
            )
        )
        return _decision(attachment, "unknown", 0.0, matched_by, issues=issues)


class UnsupportedReader:
    """지원하지 않는 attachment를 실행하지 않고 inventory issue로 보존합니다."""

    def read(
        self,
        *,
        bundle_id: str,
        attachment: RawAttachment,
        route_decision: RouteDecision,
        safety_decision: SafetyDecision,
    ) -> EvidenceInventory:
        issues = tuple(route_decision.issues + safety_decision.issues)
        if not any(issue.code == "unsupported_media_type" for issue in issues):
            issues = issues + (
                EvidenceIssue(
                    code="unsupported_media_type",
                    severity="blocking",
                    message="Attachment cannot be read by the available file routes.",
                ),
            )

        artifact = EvidenceArtifact(
            artifact_id=f"unsupported_{attachment.attachment_id}",
            artifact_type="unsupported_attachment",
            parent_id=attachment.attachment_id,
            media_type=(
                attachment.detected_media_type
                or attachment.declared_media_type
                or "application/octet-stream"
            ),
            source_locator={"file_name": attachment.original_filename},
            issues=issues,
        )
        return EvidenceInventory(
            bundle_id=bundle_id,
            attachments=(attachment,),
            artifacts=(artifact,),
            units=(),
            route_decisions=(route_decision,),
            safety_decisions=(safety_decision,),
            issues=issues,
        )


def _decision(
    attachment: RawAttachment,
    route: str,
    confidence: float,
    matched_by: list[str],
    *,
    rejected_by: list[str] | None = None,
    issues: list[EvidenceIssue] | None = None,
) -> RouteDecision:
    return RouteDecision(
        attachment_id=attachment.attachment_id,
        route=route,
        confidence=confidence,
        matched_by=tuple(matched_by),
        rejected_by=tuple(rejected_by or []),
        issues=tuple(issues or []),
    )


def _route_from_extension_or_media_type(attachment: RawAttachment) -> str | None:
    extension = attachment.extension
    media_types = {
        item
        for item in (
            attachment.declared_media_type,
            attachment.detected_media_type,
        )
        if item is not None
    }

    if extension in {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"}:
        return "image"
    if extension in {".xlsx", ".xls", ".ods", ".xlsm"}:
        return "spreadsheet"
    if extension in {".csv", ".tsv"}:
        return "delimited_table"
    if extension in {".docx", ".pptx", ".docm", ".pptm"}:
        return "office_document"
    if extension in {".eml", ".msg", ".html", ".mhtml"}:
        return "email"
    if extension == ".zip":
        return "archive"
    if extension in {".txt", ".md", ".log"}:
        return "plain_text"
    if any(item.startswith("image/") for item in media_types):
        return "image"
    if "text/csv" in media_types:
        return "delimited_table"
    if "text/plain" in media_types:
        return "plain_text"
    return None


def _has_magic(attachment: RawAttachment, signature: bytes) -> bool:
    try:
        with attachment.path.open("rb") as handle:
            return handle.read(len(signature)) == signature
    except OSError:
        return False
