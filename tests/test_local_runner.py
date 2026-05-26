from pathlib import Path


def test_local_runner_observes_and_plans_without_executing_capabilities(tmp_path):
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
                "Usage 6.4 MWh",
            ]
        ),
        encoding="utf-8",
    )

    document = EvidenceDocument.from_path(document_path)
    state = run_document(document, run_id="run-utility-bill")

    assert state.run_id == "run-utility-bill"
    assert state.document == document
    assert state.observation is not None
    assert state.observation.document_class == "utility_bill"
    assert state.plan is not None
    assert [step.name for step in state.plan.selected_capabilities] == [
        "docling_parse",
        "table_structure_extract",
        "utility_bill_extract",
    ]
    assert [event.event_type for event in state.events] == [
        "document_received",
        "observation_created",
        "plan_created",
    ]
    assert [event.sequence for event in state.events] == [1, 2, 3]
    assert [step.capability for step in state.pending_steps] == [
        "docling_parse",
        "table_structure_extract",
        "utility_bill_extract",
    ]
    assert state.completed_steps == ()
    assert state.tool_results == ()
    assert state.final_report is None
    assert str(Path(state.to_dict()["document"]["path"])) == str(document_path)


def test_local_runner_uses_document_id_as_default_run_id(tmp_path):
    from evidence_toolchain import run_document
    from evidence_toolchain.artifacts import EvidenceDocument

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

    state = run_document(EvidenceDocument.from_path(document_path))

    assert state.run_id == "receipt_quantity_vs_price"
    assert state.events[0].payload["document_id"] == "receipt_quantity_vs_price"
