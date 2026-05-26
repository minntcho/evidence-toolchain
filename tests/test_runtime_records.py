import json
from pathlib import Path


def test_runtime_records_are_json_serializable(tmp_path):
    from evidence_toolchain.artifacts import EvidenceDocument
    from evidence_toolchain.planner import plan_document
    from evidence_toolchain.runtime import (
        EvidenceEvent,
        EvidenceRunState,
        EvidenceStep,
        EvidenceToolResult,
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
                "사용량 6.4 MWh",
            ]
        ),
        encoding="utf-8",
    )
    document = EvidenceDocument.from_path(document_path)
    plan = plan_document(document)

    state = EvidenceRunState(
        run_id="run-001",
        document=document,
        plan=plan,
        pending_steps=(
            EvidenceStep(
                name="execute_capability",
                status="pending",
                capability="docling_parse",
                reason="born_digital_document_with_text_layer",
            ),
        ),
        tool_results=(
            EvidenceToolResult(
                capability="docling_parse",
                status="completed",
                outputs={"text_spans": ["사용량 6.4 MWh"]},
                artifacts={"raw_text": "artifacts/run-001/docling.txt"},
            ),
        ),
    )
    state = state.record_event(
        EvidenceEvent(
            run_id="run-001",
            sequence=1,
            event_type="plan_created",
            payload={"selected_capabilities": ["docling_parse"]},
        )
    )

    payload = state.to_dict()

    assert payload["run_id"] == "run-001"
    assert payload["document"]["path"] == str(Path(document_path))
    assert payload["plan"]["selected_capabilities"][0]["name"] == "docling_parse"
    assert payload["pending_steps"][0]["capability"] == "docling_parse"
    assert payload["tool_results"][0]["artifacts"]["raw_text"].endswith("docling.txt")
    assert payload["events"][0]["event_type"] == "plan_created"
    json.dumps(payload)


def test_runtime_events_are_append_only_snapshots():
    from evidence_toolchain.runtime import EvidenceEvent, EvidenceRunState

    state = EvidenceRunState(run_id="run-001", document={"document_id": "doc-001"})
    next_state = state.record_event(
        EvidenceEvent(
            run_id="run-001",
            sequence=1,
            event_type="document_received",
        )
    )

    assert state.events == ()
    assert [event.event_type for event in next_state.events] == ["document_received"]
