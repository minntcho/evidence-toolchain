import json


def test_emit_evidence_report_preserves_manual_review_result(tmp_path):
    from evidence_toolchain.artifacts import EvidenceDocument
    from evidence_toolchain.capabilities import ManualReviewCapabilityRunner
    from evidence_toolchain.reports import emit_evidence_report
    from evidence_toolchain.runners import run_document

    document_path = tmp_path / "unknown.txt"
    document_path.write_text(
        "\n".join(
            [
                "ETC-case_id: unsupported_case",
                "ETC-quality: unknown",
                "",
                "알 수 없는 증거 문서",
            ]
        ),
        encoding="utf-8",
    )

    state = run_document(
        EvidenceDocument.from_path(document_path),
        capability_runner=ManualReviewCapabilityRunner(),
    )
    report = emit_evidence_report(state)
    payload = report.to_dict()

    assert payload["document_id"] == "unsupported_case"
    assert payload["preflight"]["media_type"] == "text/plain"
    assert payload["tool_results"] == [
        {
            "capability": "manual_review_request",
            "status": "review_requested",
            "outputs": {
                "reason": "unknown_document_class",
                "document_id": "unsupported_case",
            },
            "warnings": [],
            "errors": [],
            "artifacts": {},
        }
    ]
    assert payload["issues"][0]["code"] == "unsupported_media_type"
    assert payload["interrupts"][0]["type"] == "manual_review"
    assert payload["recommended_next_action"] == "manual_review"
    assert "validation_decision" not in payload
    json.dumps(payload)


def test_emit_evidence_report_marks_pending_capabilities(tmp_path):
    from evidence_toolchain.artifacts import EvidenceDocument
    from evidence_toolchain.reports import emit_evidence_report
    from evidence_toolchain.runners import run_document

    document_path = tmp_path / "utility_bill.txt"
    document_path.write_text(
        "\n".join(
            [
                "ETC-case_id: utility_bill_basic",
                "ETC-document_kind: utility_bill",
                "ETC-quality: clean",
                "ETC-text_layer: true",
                "",
                "사용량 6.4 MWh",
            ]
        ),
        encoding="utf-8",
    )

    report = emit_evidence_report(run_document(EvidenceDocument.from_path(document_path)))
    payload = report.to_dict()

    assert payload["tool_results"] == []
    assert [step["capability"] for step in payload["pending_steps"]] == [
        "docling_parse",
        "table_structure_extract",
        "utility_bill_extract",
    ]
    assert payload["recommended_next_action"] == "run_pending_capabilities"
