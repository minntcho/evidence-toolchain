from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

from evidence_toolchain.runtime import EvidenceRunState, EvidenceStep, EvidenceToolResult


@dataclass(frozen=True)
class EvidenceCapability:
    name: str
    purpose: str
    strengths: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    fallbacks: list[str] = field(default_factory=list)


class CapabilityRunner(Protocol):
    """evidence run state에서 지원되는 capability step을 실행합니다."""

    def can_run(self, step: EvidenceStep, state: EvidenceRunState) -> bool:
        ...

    def run(self, step: EvidenceStep, state: EvidenceRunState) -> EvidenceToolResult:
        ...


class ManualReviewCapabilityRunner:
    """자동 추출 성공처럼 꾸미지 않고 human review를 요청합니다."""

    def can_run(self, step: EvidenceStep, state: EvidenceRunState) -> bool:
        return step.capability == "manual_review_request"

    def run(self, step: EvidenceStep, state: EvidenceRunState) -> EvidenceToolResult:
        reason = step.reason or "manual_review_requested"
        outputs = {
            "reason": reason,
            "document_id": state.document.document_id,
        }
        source_capability = step.metadata.get("source_capability")
        if source_capability is not None:
            outputs["source_capability"] = source_capability

        return EvidenceToolResult(
            capability="manual_review_request",
            status="review_requested",
            outputs=outputs,
        )


class StaticCapabilityRunner:
    """테스트, dry run, fixture 기반 실행을 위한 deterministic runner입니다."""

    def __init__(
        self,
        outputs_by_capability: Mapping[
            str,
            Mapping[str, Any] | EvidenceToolResult,
        ],
    ) -> None:
        self._results = dict(outputs_by_capability)

    def can_run(self, step: EvidenceStep, state: EvidenceRunState) -> bool:
        return step.capability in self._results

    def run(self, step: EvidenceStep, state: EvidenceRunState) -> EvidenceToolResult:
        if step.capability is None:
            raise ValueError("EvidenceStep에는 capability name이 필요합니다.")

        result = self._results[step.capability]
        if isinstance(result, EvidenceToolResult):
            return result

        return EvidenceToolResult(
            capability=step.capability,
            status="completed",
            outputs=dict(result),
        )


CAPABILITY_REGISTRY: dict[str, EvidenceCapability] = {
    "docling_parse": EvidenceCapability(
        name="docling_parse",
        purpose="text, layout, table이 있는 born-digital 문서를 파싱합니다.",
        strengths=["born_digital_pdf", "tables"],
        limitations=["bad_scans", "handwriting"],
        fallbacks=["ocr_extract", "table_structure_extract"],
    ),
    "ocr_extract": EvidenceCapability(
        name="ocr_extract",
        purpose="스캔 또는 촬영된 문서에서 text를 추출합니다.",
        strengths=["scanned_documents", "receipt_photos"],
        limitations=["digit_confusion", "lost_table_relationships"],
        fallbacks=["vision_extract", "manual_review_request"],
    ),
    "table_structure_extract": EvidenceCapability(
        name="table_structure_extract",
        purpose="table cell, header, row 관계를 복구합니다.",
        strengths=["usage_tables", "line_items"],
        limitations=["merged_cells", "multi_page_tables"],
        fallbacks=["manual_review_request"],
    ),
    "utility_bill_extract": EvidenceCapability(
        name="utility_bill_extract",
        purpose="utility bill에서 후보 field를 추출합니다.",
        strengths=["billing_period", "usage_amount", "usage_unit"],
        limitations=["bill_date_vs_service_period", "estimated_readings"],
        fallbacks=["manual_review_request"],
    ),
    "receipt_extract": EvidenceCapability(
        name="receipt_extract",
        purpose="receipt에서 후보 transaction field를 추출합니다.",
        strengths=["merchant", "transaction_total", "line_items"],
        limitations=["quantity_vs_price_confusion"],
        fallbacks=["manual_review_request"],
    ),
    "handwriting_read": EvidenceCapability(
        name="handwriting_read",
        purpose="수기 field나 수기 log를 읽습니다.",
        strengths=["handwritten_numbers", "handwritten_dates"],
        limitations=["low_trust_handwritten_evidence"],
        fallbacks=["manual_review_request"],
    ),
    "meter_photo_read": EvidenceCapability(
        name="meter_photo_read",
        purpose="물리 meter 사진에서 보이는 값을 읽습니다.",
        strengths=["visible_meter_reading"],
        limitations=["site_meter_mapping_required"],
        fallbacks=["manual_review_request"],
    ),
    "vision_extract": EvidenceCapability(
        name="vision_extract",
        purpose="text extraction만으로 부족한 경우 visual reasoning을 사용합니다.",
        strengths=["screenshots", "photos", "poor_layout_recovery"],
        limitations=["must_ground_visible_regions"],
        fallbacks=["manual_review_request"],
    ),
    "manual_review_request": EvidenceCapability(
        name="manual_review_request",
        purpose="해소되지 않은 불확실성을 human review로 보존합니다.",
        strengths=["ambiguous_or_high_risk_documents"],
        limitations=["not_automated_extraction"],
        fallbacks=[],
    ),
}
