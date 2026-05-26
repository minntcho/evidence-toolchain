from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class EvidenceCapability:
    name: str
    purpose: str
    strengths: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    fallbacks: list[str] = field(default_factory=list)


CAPABILITY_REGISTRY: dict[str, EvidenceCapability] = {
    "docling_parse": EvidenceCapability(
        name="docling_parse",
        purpose="Parse born-digital documents with text, layout, and tables.",
        strengths=["born_digital_pdf", "tables"],
        limitations=["bad_scans", "handwriting"],
        fallbacks=["ocr_extract", "table_structure_extract"],
    ),
    "ocr_extract": EvidenceCapability(
        name="ocr_extract",
        purpose="Extract text from scanned or photographed documents.",
        strengths=["scanned_documents", "receipt_photos"],
        limitations=["digit_confusion", "lost_table_relationships"],
        fallbacks=["vision_extract", "manual_review_request"],
    ),
    "table_structure_extract": EvidenceCapability(
        name="table_structure_extract",
        purpose="Recover table cells, headers, and row relationships.",
        strengths=["usage_tables", "line_items"],
        limitations=["merged_cells", "multi_page_tables"],
        fallbacks=["manual_review_request"],
    ),
    "utility_bill_extract": EvidenceCapability(
        name="utility_bill_extract",
        purpose="Extract candidate fields from utility bills.",
        strengths=["billing_period", "usage_amount", "usage_unit"],
        limitations=["bill_date_vs_service_period", "estimated_readings"],
        fallbacks=["manual_review_request"],
    ),
    "receipt_extract": EvidenceCapability(
        name="receipt_extract",
        purpose="Extract candidate transaction fields from receipts.",
        strengths=["merchant", "transaction_total", "line_items"],
        limitations=["quantity_vs_price_confusion"],
        fallbacks=["manual_review_request"],
    ),
    "handwriting_read": EvidenceCapability(
        name="handwriting_read",
        purpose="Read handwritten fields or handwritten logs.",
        strengths=["handwritten_numbers", "handwritten_dates"],
        limitations=["low_trust_handwritten_evidence"],
        fallbacks=["manual_review_request"],
    ),
    "meter_photo_read": EvidenceCapability(
        name="meter_photo_read",
        purpose="Read visible values from physical meter photos.",
        strengths=["visible_meter_reading"],
        limitations=["site_meter_mapping_required"],
        fallbacks=["manual_review_request"],
    ),
    "vision_extract": EvidenceCapability(
        name="vision_extract",
        purpose="Use visual reasoning where text extraction is insufficient.",
        strengths=["screenshots", "photos", "poor_layout_recovery"],
        limitations=["must_ground_visible_regions"],
        fallbacks=["manual_review_request"],
    ),
    "manual_review_request": EvidenceCapability(
        name="manual_review_request",
        purpose="Preserve unresolved uncertainty for human review.",
        strengths=["ambiguous_or_high_risk_documents"],
        limitations=["not_automated_extraction"],
        fallbacks=[],
    ),
}
