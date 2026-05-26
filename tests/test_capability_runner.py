def test_manual_review_capability_runner_records_review_interrupt(tmp_path):
    from evidence_toolchain.artifacts import EvidenceDocument
    from evidence_toolchain.capabilities import ManualReviewCapabilityRunner
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

    assert state.pending_steps == ()
    assert [step.capability for step in state.completed_steps] == [
        "manual_review_request"
    ]
    assert [step.status for step in state.completed_steps] == ["completed"]
    assert state.tool_results[0].capability == "manual_review_request"
    assert state.tool_results[0].status == "review_requested"
    assert state.tool_results[0].outputs["reason"] == "unknown_document_class"
    assert state.interrupts == (
        {
            "type": "manual_review",
            "capability": "manual_review_request",
            "reason": "unknown_document_class",
        },
    )
    assert [event.event_type for event in state.events[-3:]] == [
        "capability_started",
        "capability_completed",
        "review_requested",
    ]


def test_manual_review_runner_leaves_automated_capabilities_pending(tmp_path):
    from evidence_toolchain.artifacts import EvidenceDocument
    from evidence_toolchain.capabilities import ManualReviewCapabilityRunner
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

    state = run_document(
        EvidenceDocument.from_path(document_path),
        capability_runner=ManualReviewCapabilityRunner(),
    )

    assert [step.capability for step in state.pending_steps] == [
        "docling_parse",
        "table_structure_extract",
        "utility_bill_extract",
    ]
    assert state.completed_steps == ()
    assert state.tool_results == ()
    assert [event.event_type for event in state.events] == [
        "document_received",
        "preflight_completed",
        "observation_created",
        "plan_created",
    ]
