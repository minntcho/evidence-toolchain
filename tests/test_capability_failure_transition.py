def test_failed_capability_records_failure_and_selects_plan_fallback(tmp_path):
    from evidence_toolchain import (
        EvidenceDocument,
        EvidenceToolResult,
        StaticCapabilityRunner,
        run_capability_steps,
        run_document,
    )

    document_path = tmp_path / "receipt.txt"
    document_path.write_text(
        "\n".join(
            [
                "ETC-case_id: receipt_quantity_vs_price",
                "ETC-document_kind: receipt",
                "ETC-quality: medium",
                "ETC-text_layer: false",
                "",
                "Diesel quantity: 42.0 L",
                "Total: 62.58",
            ]
        ),
        encoding="utf-8",
    )

    planned = run_document(EvidenceDocument.from_path(document_path))
    failed_result = EvidenceToolResult(
        capability="ocr_extract",
        status="failed",
        errors=("ocr_timeout",),
    )
    executed = run_capability_steps(
        planned,
        StaticCapabilityRunner({"ocr_extract": failed_result}),
    )

    assert [step.capability for step in executed.completed_steps] == ["ocr_extract"]
    assert [step.status for step in executed.completed_steps] == ["failed"]
    assert [result.to_dict() for result in executed.tool_results] == [
        {
            "capability": "ocr_extract",
            "status": "failed",
            "outputs": {},
            "warnings": [],
            "errors": ["ocr_timeout"],
            "artifacts": {},
        }
    ]
    assert [step.capability for step in executed.pending_steps] == [
        "receipt_extract",
        "manual_review_request",
    ]
    assert executed.pending_steps[-1].reason == (
        "receipt_quantity_or_price_may_be_ambiguous"
    )
    assert [event.event_type for event in executed.events[4:]] == [
        "capability_started",
        "capability_failed",
        "fallback_selected",
    ]
    assert executed.events[-1].payload == {
        "capability": "manual_review_request",
        "reason": "receipt_quantity_or_price_may_be_ambiguous",
        "source_capability": "ocr_extract",
    }


def test_capability_exception_is_recorded_as_failed_result(tmp_path):
    from evidence_toolchain import EvidenceDocument, run_capability_steps, run_document

    class ExplodingCapabilityRunner:
        def can_run(self, step, state):
            return step.capability == "ocr_extract"

        def run(self, step, state):
            raise RuntimeError("ocr engine crashed")

    document_path = tmp_path / "receipt.txt"
    document_path.write_text(
        "\n".join(
            [
                "ETC-case_id: receipt_quantity_vs_price",
                "ETC-document_kind: receipt",
                "ETC-quality: medium",
                "ETC-text_layer: false",
                "",
                "Diesel quantity: 42.0 L",
                "Total: 62.58",
            ]
        ),
        encoding="utf-8",
    )

    planned = run_document(EvidenceDocument.from_path(document_path))
    executed = run_capability_steps(planned, ExplodingCapabilityRunner())

    assert [step.status for step in executed.completed_steps] == ["failed"]
    assert [result.to_dict() for result in executed.tool_results] == [
        {
            "capability": "ocr_extract",
            "status": "failed",
            "outputs": {},
            "warnings": [],
            "errors": ["RuntimeError: ocr engine crashed"],
            "artifacts": {},
        }
    ]
    assert [step.capability for step in executed.pending_steps] == [
        "receipt_extract",
        "manual_review_request",
    ]
    assert [event.event_type for event in executed.events[4:]] == [
        "capability_started",
        "capability_failed",
        "fallback_selected",
    ]
