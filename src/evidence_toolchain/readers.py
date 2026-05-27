from __future__ import annotations

import csv
import re
import struct
from pathlib import Path

from evidence_toolchain.ingestion import (
    EvidenceArtifact,
    EvidenceInventory,
    EvidenceUnit,
    RawAttachment,
    RouteDecision,
    SafetyDecision,
)
from evidence_toolchain.issues import EvidenceIssue


class PlainTextReader:
    """plain text attachment를 line-level EvidenceUnit으로 낮춥니다."""

    producer = "plain_text_reader"

    def read(
        self,
        *,
        bundle_id: str,
        attachment: RawAttachment,
        route_decision: RouteDecision,
        safety_decision: SafetyDecision,
    ) -> EvidenceInventory:
        issue = EvidenceIssue(
            code="plain_text_low_provenance",
            severity="info",
            message="Plain text is preserved as raw evidence, not final authority.",
        )
        artifact = _file_artifact(
            attachment,
            media_type="text/plain",
            reader=self.producer,
            issues=(issue,),
        )
        units = tuple(
            EvidenceUnit(
                unit_id=f"unit_{attachment.attachment_id}_line_{line_number}",
                artifact_id=artifact.artifact_id,
                unit_type="text_span",
                producer=self.producer,
                text=line,
                locator={"line": line_number},
            )
            for line_number, line in _non_empty_lines(attachment.path)
        )
        return EvidenceInventory(
            bundle_id=bundle_id,
            attachments=(attachment,),
            artifacts=(artifact,),
            units=units,
            route_decisions=(route_decision,),
            safety_decisions=(safety_decision,),
            issues=(issue,),
        )


class DelimitedTableReader:
    """CSV/TSV attachment를 table 및 table_cell EvidenceUnit으로 낮춥니다."""

    producer = "delimited_table_reader"

    def read(
        self,
        *,
        bundle_id: str,
        attachment: RawAttachment,
        route_decision: RouteDecision,
        safety_decision: SafetyDecision,
    ) -> EvidenceInventory:
        delimiter = "\t" if attachment.extension == ".tsv" else ","
        rows = _read_delimited_rows(attachment.path, delimiter)
        headers = rows[0] if rows else []
        data_rows = rows[1:] if rows else []
        artifact = _file_artifact(
            attachment,
            media_type=_delimited_media_type(attachment),
            reader=self.producer,
        )
        units: list[EvidenceUnit] = [
            EvidenceUnit(
                unit_id=f"unit_{attachment.attachment_id}_table_1",
                artifact_id=artifact.artifact_id,
                unit_type="table",
                producer=self.producer,
                metadata={
                    "delimiter": delimiter,
                    "headers": headers,
                    "row_count": len(data_rows),
                },
            )
        ]

        for row_index, row in enumerate(data_rows, start=2):
            for column_index, text in enumerate(row, start=1):
                header = headers[column_index - 1] if column_index <= len(headers) else ""
                units.append(
                    EvidenceUnit(
                        unit_id=(
                            f"unit_{attachment.attachment_id}_r{row_index}_c{column_index}"
                        ),
                        artifact_id=artifact.artifact_id,
                        unit_type="table_cell",
                        producer=self.producer,
                        text=text,
                        value=text,
                        locator={
                            "row": row_index,
                            "column": column_index,
                            "header": header,
                        },
                    )
                )

        return EvidenceInventory(
            bundle_id=bundle_id,
            attachments=(attachment,),
            artifacts=(artifact,),
            units=tuple(units),
            route_decisions=(route_decision,),
            safety_decisions=(safety_decision,),
        )


class PdfProfileReader:
    """PDF attachment를 cheap profile artifact와 page artifact로 낮춥니다."""

    producer = "pdf_profile_reader"

    def read(
        self,
        *,
        bundle_id: str,
        attachment: RawAttachment,
        route_decision: RouteDecision,
        safety_decision: SafetyDecision,
    ) -> EvidenceInventory:
        data = attachment.path.read_bytes()
        page_count = _count_pdf_pages(data)
        encrypted = b"/Encrypt" in data
        has_text_layer = _has_pdf_text_markers(data)
        issues = (
            (
                EvidenceIssue(
                    code="encrypted_pdf",
                    severity="blocking",
                    message="Encrypted PDFs require review or a password-aware reader.",
                ),
            )
            if encrypted
            else ()
        )
        file_artifact = _file_artifact(
            attachment,
            media_type="application/pdf",
            reader=self.producer,
            metadata={
                "page_count": page_count,
                "encrypted": encrypted,
                "has_text_layer": has_text_layer,
            },
            issues=issues,
        )
        page_artifacts = tuple(
            EvidenceArtifact(
                artifact_id=f"artifact_{attachment.attachment_id}_page_{page_number}",
                artifact_type="pdf_page",
                parent_id=file_artifact.artifact_id,
                media_type="application/pdf-page",
                source_locator={
                    "file_name": attachment.original_filename,
                    "page": page_number,
                },
                metadata={
                    "reader": self.producer,
                    "has_text_layer": has_text_layer,
                },
            )
            for page_number in range(1, page_count + 1)
        )
        profile_unit = EvidenceUnit(
            unit_id=f"unit_{attachment.attachment_id}_pdf_profile",
            artifact_id=file_artifact.artifact_id,
            unit_type="metadata",
            producer=self.producer,
            value={
                "encrypted": encrypted,
                "has_text_layer": has_text_layer,
                "page_count": page_count,
            },
        )
        return EvidenceInventory(
            bundle_id=bundle_id,
            attachments=(attachment,),
            artifacts=(file_artifact,) + page_artifacts,
            units=(profile_unit,),
            route_decisions=(route_decision,),
            safety_decisions=(safety_decision,),
            issues=issues,
        )


class ImageProfileReader:
    """이미지를 OCR/VLM 없이 profile artifact와 metadata unit으로 낮춥니다."""

    producer = "image_profile_reader"

    def read(
        self,
        *,
        bundle_id: str,
        attachment: RawAttachment,
        route_decision: RouteDecision,
        safety_decision: SafetyDecision,
    ) -> EvidenceInventory:
        data = attachment.path.read_bytes()
        profile = _profile_image(data)
        issues = (
            (
                EvidenceIssue(
                    code="image_profile_unreadable",
                    severity="warning",
                    message="Image dimensions or format could not be read by the profile reader.",
                ),
            )
            if profile["format"] == "unknown"
            else ()
        )
        artifact = EvidenceArtifact(
            artifact_id=f"artifact_{attachment.attachment_id}",
            artifact_type="image",
            parent_id=attachment.attachment_id,
            media_type=_image_media_type(attachment, profile),
            source_locator={"file_name": attachment.original_filename},
            metadata={"reader": self.producer, **profile},
            issues=issues,
        )
        profile_unit = EvidenceUnit(
            unit_id=f"unit_{attachment.attachment_id}_image_profile",
            artifact_id=artifact.artifact_id,
            unit_type="metadata",
            producer=self.producer,
            value=profile,
        )
        return EvidenceInventory(
            bundle_id=bundle_id,
            attachments=(attachment,),
            artifacts=(artifact,),
            units=(profile_unit,),
            route_decisions=(route_decision,),
            safety_decisions=(safety_decision,),
            issues=issues,
        )


def _file_artifact(
    attachment: RawAttachment,
    *,
    media_type: str,
    reader: str,
    metadata: dict[str, object] | None = None,
    issues: tuple[EvidenceIssue, ...] = (),
) -> EvidenceArtifact:
    return EvidenceArtifact(
        artifact_id=f"artifact_{attachment.attachment_id}",
        artifact_type="file",
        parent_id=attachment.attachment_id,
        media_type=media_type,
        source_locator={"file_name": attachment.original_filename},
        metadata={"reader": reader, **dict(metadata or {})},
        issues=issues,
    )


def _non_empty_lines(path: Path) -> tuple[tuple[int, str], ...]:
    return tuple(
        (line_number, line.strip())
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
        if line.strip()
    )


def _read_delimited_rows(path: Path, delimiter: str) -> list[list[str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [row for row in csv.reader(handle, delimiter=delimiter)]


def _delimited_media_type(attachment: RawAttachment) -> str:
    if attachment.declared_media_type is not None:
        return attachment.declared_media_type
    if attachment.detected_media_type is not None:
        return attachment.detected_media_type
    if attachment.extension == ".tsv":
        return "text/tab-separated-values"
    return "text/csv"


def _count_pdf_pages(data: bytes) -> int:
    text = data.decode("latin-1", errors="ignore")
    count = len(re.findall(r"/Type\s*/Page\b", text))
    return max(count, 1)


def _has_pdf_text_markers(data: bytes) -> bool:
    return b"BT" in data and (b"Tj" in data or b"TJ" in data)


def _profile_image(data: bytes) -> dict[str, object]:
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 33:
        width, height, bit_depth, color_type = struct.unpack(">IIBB", data[16:26])
        return _image_profile(
            image_format="PNG",
            width=width,
            height=height,
            mode=_png_mode(bit_depth, color_type),
        )

    jpeg_profile = _profile_jpeg(data)
    if jpeg_profile is not None:
        return jpeg_profile

    return _image_profile(
        image_format="unknown",
        width=None,
        height=None,
        mode=None,
    )


def _profile_jpeg(data: bytes) -> dict[str, object] | None:
    if not data.startswith(b"\xff\xd8"):
        return None
    index = 2
    while index + 4 <= len(data):
        if data[index] != 0xFF:
            index += 1
            continue
        marker = data[index + 1]
        index += 2
        if marker in {0xD8, 0xD9}:
            continue
        if index + 2 > len(data):
            return None
        segment_length = int.from_bytes(data[index:index + 2], "big")
        segment_start = index + 2
        segment_end = index + segment_length
        if marker in {0xC0, 0xC1, 0xC2} and segment_end <= len(data):
            height = int.from_bytes(data[segment_start + 1:segment_start + 3], "big")
            width = int.from_bytes(data[segment_start + 3:segment_start + 5], "big")
            components = data[segment_start + 5]
            return _image_profile(
                image_format="JPEG",
                width=width,
                height=height,
                mode=_jpeg_mode(components),
            )
        index = segment_end
    return None


def _image_profile(
    *,
    image_format: str,
    width: int | None,
    height: int | None,
    mode: str | None,
) -> dict[str, object]:
    aspect_ratio = round(width / height, 6) if width is not None and height else None
    return {
        "aspect_ratio": aspect_ratio,
        "exif_orientation": None,
        "format": image_format,
        "height": height,
        "mode": mode,
        "width": width,
    }


def _png_mode(bit_depth: int, color_type: int) -> str:
    modes = {
        0: "L",
        2: "RGB",
        3: "P",
        4: "LA",
        6: "RGBA",
    }
    return modes.get(color_type, f"unknown_png_color_type_{color_type}_{bit_depth}")


def _jpeg_mode(components: int) -> str:
    modes = {
        1: "L",
        3: "RGB",
        4: "CMYK",
    }
    return modes.get(components, f"unknown_jpeg_components_{components}")


def _image_media_type(attachment: RawAttachment, profile: dict[str, object]) -> str:
    if attachment.declared_media_type is not None:
        return attachment.declared_media_type
    if attachment.detected_media_type is not None:
        return attachment.detected_media_type
    image_format = profile["format"]
    if image_format == "PNG":
        return "image/png"
    if image_format == "JPEG":
        return "image/jpeg"
    return "application/octet-stream"
