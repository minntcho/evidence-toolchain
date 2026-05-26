def test_resume_processes_manual_review_fallback_with_source_lineage(tmp_path):
    from evidence_toolchain import (
        EvidenceDocument,
        EvidenceToolResult,
        ManualReviewCapabilityRunner,
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

    assert [step.capability for step in failed.pending_steps] == [
        "receipt_extract",
        "manual_review_request",
    ]
    assert failed.pending_steps[-1].metadata == {
        "source_capability": "ocr_extract",
    }

    resumed = run_capability_steps(failed, ManualReviewCapabilityRunner())

    assert [step.capability for step in resumed.completed_steps] == [
        "ocr_extract",
        "manual_review_request",
    ]
    assert [step.status for step in resumed.completed_steps] == [
        "failed",
        "completed",
    ]
    assert [step.capability for step in resumed.pending_steps] == [
        "receipt_extract",
    ]
    assert resumed.tool_results[-1].to_dict() == {
        "capability": "manual_review_request",
        "status": "review_requested",
        "outputs": {
            "document_id": "receipt_quantity_vs_price",
            "reason": "receipt_quantity_or_price_may_be_ambiguous",
            "source_capability": "ocr_extract",
        },
        "warnings": [],
        "errors": [],
        "artifacts": {},
    }
    assert resumed.interrupts[-1] == {
        "type": "manual_review",
        "capability": "manual_review_request",
        "reason": "receipt_quantity_or_price_may_be_ambiguous",
        "source_capability": "ocr_extract",
    }
    assert resumed.events[-1].event_type == "review_requested"
    assert resumed.events[-1].payload == {
        "capability": "manual_review_request",
        "reason": "receipt_quantity_or_price_may_be_ambiguous",
        "source_capability": "ocr_extract",
    }
