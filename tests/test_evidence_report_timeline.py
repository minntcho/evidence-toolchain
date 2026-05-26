import json


def test_report_artifact_preserves_run_resume_event_timeline(tmp_path):
    from evidence_toolchain import (
        EvidenceDocument,
        EvidenceToolResult,
        ManualReviewCapabilityRunner,
        StaticCapabilityRunner,
        emit_evidence_report,
        run_capability_steps,
        run_document,
        write_evidence_report,
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
    failed = run_capability_steps(
        planned,
        StaticCapabilityRunner(
            {
                "ocr_extract": EvidenceToolResult(
                    capability="ocr_extract",
                    status="failed",
                    errors=("ocr_timeout",),
                )
            }
        ),
    )
    resumed = run_capability_steps(failed, ManualReviewCapabilityRunner())

    report = emit_evidence_report(resumed)
    output_path = write_evidence_report(report, tmp_path / "reports")
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert [event["event_type"] for event in payload["events"]] == [
        "document_received",
        "preflight_completed",
        "observation_created",
        "plan_created",
        "capability_started",
        "capability_failed",
        "fallback_selected",
        "capability_started",
        "capability_completed",
        "review_requested",
    ]
    assert [event["sequence"] for event in payload["events"]] == list(range(1, 11))
    assert payload["events"][5]["payload"] == {
        "capability": "ocr_extract",
        "errors": ["ocr_timeout"],
        "status": "failed",
    }
    assert payload["events"][-1]["payload"] == {
        "capability": "manual_review_request",
        "reason": "receipt_quantity_or_price_may_be_ambiguous",
        "source_capability": "ocr_extract",
    }
    assert [step["status"] for step in payload["completed_steps"]] == [
        "failed",
        "completed",
    ]
    assert payload["recommended_next_action"] == "manual_review"
    assert "validation_decision" not in payload
