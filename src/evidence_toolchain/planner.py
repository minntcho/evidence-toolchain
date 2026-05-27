from __future__ import annotations

from dataclasses import dataclass, field

from evidence_toolchain.artifacts import EvidenceDocument
from evidence_toolchain.issues import EvidenceIssue
from evidence_toolchain.observations import EvidenceObservation, observe_document


@dataclass(frozen=True)
class CapabilityStep:
    name: str
    reason: str


@dataclass(frozen=True)
class EvidenceToolPlan:
    document_id: str
    observation: EvidenceObservation
    selected_capabilities: list[CapabilityStep]
    fallbacks: list[CapabilityStep] = field(default_factory=list)
    issues: list[EvidenceIssue] = field(default_factory=list)


def plan_document(document: EvidenceDocument) -> EvidenceToolPlan:
    observation = observe_document(document)
    selected: list[CapabilityStep] = []
    fallbacks: list[CapabilityStep] = []
    issues: list[EvidenceIssue] = []

    document_class = observation.document_class
    signals = set(observation.signals)

    if document_class == "utility_bill":
        if observation.has_text_layer:
            selected.append(_step("docling_parse", "born_digital_document_with_text_layer"))
        else:
            selected.append(_step("ocr_extract", "document_without_text_layer"))
        selected.append(_step("table_structure_extract", "usage_values_appear_in_table"))
        selected.append(_step("utility_bill_extract", "utility_bill_candidate_fields"))
        if not observation.has_text_layer:
            fallbacks.append(_step("manual_review_request", "scan_requires_review_if_values_conflict"))

    elif document_class == "receipt":
        selected.extend(
            [
                _step("ocr_extract", "receipt_or_photo_without_reliable_text_layer"),
                _step("receipt_extract", "receipt_like_layout"),
            ]
        )
        fallbacks.append(_step("manual_review_request", "receipt_quantity_or_price_may_be_ambiguous"))

    elif document_class == "meter_log":
        selected.extend(
            [
                _step("handwriting_read", "handwriting_present"),
                _step("table_structure_extract", "meter_log_rows_are_table_like"),
            ]
        )
        fallbacks.append(_step("manual_review_request", "handwritten_values_require_review"))
        issues.append(
            _issue(
                "low_trust_handwritten_evidence",
                "warning",
                "Handwritten meter evidence should be reviewed before downstream use.",
            )
        )

    elif document_class == "meter_photo":
        selected.extend(
            [
                _step("vision_extract", "meter_photo_requires_visual_reading"),
                _step("meter_photo_read", "visible_meter_reading_target"),
            ]
        )
        fallbacks.append(_step("manual_review_request", "site_meter_mapping_required"))
        issues.append(
            _issue(
                "site_meter_mapping_required",
                "warning",
                "A meter photo does not prove the site-to-meter relationship.",
            )
        )

    else:
        selected.append(_step("manual_review_request", "unknown_document_class"))
        issues.append(
            _issue(
                "unsupported_media_type",
                "blocking",
                "The document class is not supported by the rule planner.",
            )
        )

    if "rotated" in signals:
        issues.append(
            _issue(
                "rotated_document",
                "warning",
                "The document appears rotated and may require OCR or vision fallback.",
            )
        )
    if "ambiguous_table_header" in signals:
        issues.append(
            _issue(
                "ambiguous_table_structure",
                "warning",
                "Table headers may not map cleanly to values.",
            )
        )
    if "possible_unit_confusion" in signals:
        issues.append(
            _issue(
                "possible_unit_confusion",
                "warning",
                "The document includes unit text that may be confused during extraction.",
            )
        )

    return EvidenceToolPlan(
        document_id=document.document_id,
        observation=observation,
        selected_capabilities=selected,
        fallbacks=fallbacks,
        issues=issues,
    )


def _step(name: str, reason: str) -> CapabilityStep:
    return CapabilityStep(name=name, reason=reason)


def _issue(code: str, severity: str, message: str) -> EvidenceIssue:
    return EvidenceIssue(code=code, severity=severity, message=message)
