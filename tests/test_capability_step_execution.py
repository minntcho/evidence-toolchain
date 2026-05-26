def test_static_capability_runner_executes_supported_pending_steps(tmp_path):
    from evidence_toolchain import (
        EvidenceDocument,
        StaticCapabilityRunner,
        run_capability_steps,
        run_document,
    )

    document_path = tmp_path / "utility_bill.txt"
    document_path.write_text(
        "\n".join(
            [
                "ETC-case_id: utility_bill_basic",
                "ETC-document_kind: utility_bill",
                "ETC-quality: clean",
                "ETC-text_layer: true",
                "",
                "Usage 6.4 MWh",
            ]
        ),
        encoding="utf-8",
    )

    planned = run_document(EvidenceDocument.from_path(document_path))
    executed = run_capability_steps(
        planned,
        StaticCapabilityRunner(
            {
                "docling_parse": {"text_blocks": 1},
                "table_structure_extract": {"tables": 1},
            }
        ),
    )

    assert [step.capability for step in planned.pending_steps] == [
        "docling_parse",
        "table_structure_extract",
        "utility_bill_extract",
    ]
    assert [step.capability for step in executed.completed_steps] == [
        "docling_parse",
        "table_structure_extract",
    ]
    assert [step.status for step in executed.completed_steps] == [
        "completed",
        "completed",
    ]
    assert [step.capability for step in executed.pending_steps] == [
        "utility_bill_extract",
    ]
    assert [result.to_dict() for result in executed.tool_results] == [
        {
            "capability": "docling_parse",
            "status": "completed",
            "outputs": {"text_blocks": 1},
            "warnings": [],
            "errors": [],
            "artifacts": {},
        },
        {
            "capability": "table_structure_extract",
            "status": "completed",
            "outputs": {"tables": 1},
            "warnings": [],
            "errors": [],
            "artifacts": {},
        },
    ]
    assert [event.event_type for event in executed.events[4:]] == [
        "capability_started",
        "capability_completed",
        "capability_started",
        "capability_completed",
    ]
    assert [event.sequence for event in executed.events] == list(range(1, 9))


def test_run_document_can_execute_all_steps_with_static_runner(tmp_path):
    from evidence_toolchain import EvidenceDocument, StaticCapabilityRunner, run_document

    document_path = tmp_path / "utility_bill.txt"
    document_path.write_text(
        "\n".join(
            [
                "ETC-case_id: utility_bill_basic",
                "ETC-document_kind: utility_bill",
                "ETC-quality: clean",
                "ETC-text_layer: true",
                "",
                "Usage 6.4 MWh",
            ]
        ),
        encoding="utf-8",
    )

    state = run_document(
        EvidenceDocument.from_path(document_path),
        capability_runner=StaticCapabilityRunner(
            {
                "docling_parse": {"text_blocks": 1},
                "table_structure_extract": {"tables": 1},
                "utility_bill_extract": {"fields": ["usage"]},
            }
        ),
    )

    assert state.pending_steps == ()
    assert [step.capability for step in state.completed_steps] == [
        "docling_parse",
        "table_structure_extract",
        "utility_bill_extract",
    ]
    assert [result.status for result in state.tool_results] == [
        "completed",
        "completed",
        "completed",
    ]
