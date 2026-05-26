import json


def test_write_evidence_report_persists_json_artifact(tmp_path):
    from evidence_toolchain import (
        EvidenceDocument,
        emit_evidence_report,
        run_document,
        write_evidence_report,
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

    report = emit_evidence_report(
        run_document(EvidenceDocument.from_path(document_path))
    )
    output_path = write_evidence_report(report, tmp_path / "reports")

    assert output_path == tmp_path / "reports" / "utility_bill_basic.evidence-report.json"
    assert output_path.read_text(encoding="utf-8").endswith("\n")

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["document_id"] == "utility_bill_basic"
    assert payload["recommended_next_action"] == "run_pending_capabilities"
    assert "validation_decision" not in payload


def test_write_evidence_report_uses_safe_artifact_name(tmp_path):
    from evidence_toolchain import (
        EvidenceDocument,
        emit_evidence_report,
        run_document,
        write_evidence_report,
    )

    document_path = tmp_path / "unsafe.txt"
    document_path.write_text(
        "\n".join(
            [
                "ETC-case_id: ../unsafe case",
                "ETC-document_kind: utility_bill",
                "",
                "Usage 6.4 MWh",
            ]
        ),
        encoding="utf-8",
    )

    report = emit_evidence_report(
        run_document(EvidenceDocument.from_path(document_path))
    )
    output_dir = tmp_path / "reports"
    output_path = write_evidence_report(report, output_dir)

    assert output_path.parent == output_dir
    assert output_path.name == "unsafe_case.evidence-report.json"
    assert not (tmp_path / "unsafe case.evidence-report.json").exists()
