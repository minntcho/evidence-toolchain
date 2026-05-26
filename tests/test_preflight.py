import json


def test_preflight_extracts_cheap_document_signals(tmp_path):
    from evidence_toolchain.artifacts import EvidenceDocument
    from evidence_toolchain.preflight import preflight_document

    document_path = tmp_path / "rotated_bill.txt"
    document_path.write_text(
        "\n".join(
            [
                "ETC-case_id: scanned_utility_bill_rotated",
                "ETC-document_kind: utility_bill",
                "ETC-quality: rotated_scan",
                "ETC-text_layer: false",
                "ETC-signals: rotated",
                "",
                "회전된 합성 스캔 유틸리티 청구서",
                "사용량 6.4 MWh",
            ]
        ),
        encoding="utf-8",
    )

    document = EvidenceDocument.from_path(document_path)
    preflight = preflight_document(document)
    payload = preflight.to_dict()

    assert payload["document_id"] == "scanned_utility_bill_rotated"
    assert payload["file_name"] == "rotated_bill.txt"
    assert payload["format"] == "txt"
    assert payload["media_type"] == "text/plain"
    assert payload["byte_size"] > 0
    assert payload["has_text_layer"] is False
    assert payload["signals"] == ["rotated"]
    assert payload["detected_rotation"] is True
    assert payload["sample_text"] == "회전된 합성 스캔 유틸리티 청구서\n사용량 6.4 MWh"
    json.dumps(payload)


def test_local_runner_records_preflight_before_observation(tmp_path):
    from evidence_toolchain.artifacts import EvidenceDocument
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

    state = run_document(EvidenceDocument.from_path(document_path))

    assert state.preflight is not None
    assert state.preflight.media_type == "text/plain"
    assert [event.event_type for event in state.events] == [
        "document_received",
        "preflight_completed",
        "observation_created",
        "plan_created",
    ]
    assert state.events[1].payload["format"] == "txt"
    assert state.to_dict()["preflight"]["sample_text"] == "사용량 6.4 MWh"
