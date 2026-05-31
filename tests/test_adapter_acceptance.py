import json


def _minimal_text_pdf_bytes(text="usage 6.4 MWh"):
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length "
        + str(len(stream)).encode("ascii")
        + b" >>\nstream\n"
        + stream
        + b"\nendstream",
    ]
    content = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, body in enumerate(objects, start=1):
        offsets.append(len(content))
        content.extend(f"{index} 0 obj\n".encode("ascii"))
        content.extend(body)
        content.extend(b"\nendobj\n")
    xref_offset = len(content)
    content.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    content.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        content.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    content.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(content)


def _pdf_attachment(tmp_path):
    from evidence_toolchain import RawAttachment

    path = tmp_path / "reader-acceptance.pdf"
    path.write_bytes(_minimal_text_pdf_bytes())
    return RawAttachment.from_path(
        path,
        attachment_id="reader_acceptance_pdf",
        declared_media_type="application/pdf",
    )


def _usage_claim_and_expected_behavior():
    from evidence_toolchain import (
        DeclaredClaim,
        ExpectedClaimResolution,
        ExperimentExpectedBehavior,
    )

    return (
        (
            DeclaredClaim(
                x_id="x_pdf_usage_001",
                fields={"amount": 6400, "unit": "kWh"},
            ),
        ),
        ExperimentExpectedBehavior(
            claim_resolutions=(
                ExpectedClaimResolution(
                    x_id="x_pdf_usage_001",
                    status="supported_after_unit_normalization",
                    missing_need_ids=(),
                    supporting_atom_types=("usage_amount",),
                    rejected_atom_types=(),
                ),
            ),
        ),
    )


def _convergence_inventory():
    from evidence_toolchain import EvidenceInventory, EvidenceUnit

    return EvidenceInventory(
        bundle_id="convergence_acceptance_bundle_001",
        attachments=(),
        artifacts=(),
        route_decisions=(),
        units=(
            EvidenceUnit(
                unit_id="cell_site",
                artifact_id="artifact_usage",
                unit_type="table_cell",
                producer="acceptance_fixture_reader",
                text="OCH-01",
                locator={"row": 2, "column": 1, "header": "site"},
            ),
            EvidenceUnit(
                unit_id="cell_period",
                artifact_id="artifact_usage",
                unit_type="table_cell",
                producer="acceptance_fixture_reader",
                text="2025-03",
                locator={"row": 2, "column": 2, "header": "period"},
            ),
            EvidenceUnit(
                unit_id="cell_activity",
                artifact_id="artifact_usage",
                unit_type="table_cell",
                producer="acceptance_fixture_reader",
                text="electricity",
                locator={"row": 2, "column": 3, "header": "activity"},
            ),
            EvidenceUnit(
                unit_id="cell_quantity",
                artifact_id="artifact_usage",
                unit_type="table_cell",
                producer="acceptance_fixture_reader",
                text="6.4",
                value=6.4,
                locator={"row": 2, "column": 4, "header": "amount"},
            ),
            EvidenceUnit(
                unit_id="cell_unit",
                artifact_id="artifact_usage",
                unit_type="table_cell",
                producer="acceptance_fixture_reader",
                text="MWh",
                locator={"row": 2, "column": 5, "header": "unit"},
            ),
        ),
    )


def _convergence_claim_and_expected_behavior(*, status="evidence_converged"):
    from evidence_toolchain import (
        DeclaredClaim,
        ExpectedClaimConvergence,
        ExperimentExpectedBehavior,
    )

    return (
        (
            DeclaredClaim(
                x_id="x_usage_001",
                fields={
                    "site": "OCH-01",
                    "period": "2025-03",
                    "activity": "electricity",
                    "amount": 6400,
                    "unit": "kWh",
                },
            ),
        ),
        ExperimentExpectedBehavior(
            claim_convergences=(
                ExpectedClaimConvergence(
                    x_id="x_usage_001",
                    claim_alignment_status="supported_after_unit_normalization",
                    evidence_convergence_status=status,
                    selected_support_set=("cand_001",),
                    review_trigger_codes=(),
                    partial_failure_codes=(),
                    unresolved_gaps=(),
                ),
            ),
        ),
    )


def test_basic_resolution_adapter_acceptance_passes_reference_adapters():
    from evidence_toolchain import (
        DeterministicNormalizer,
        HardGateResolver,
        SimpleUnitClusterAtomizer,
        run_basic_resolution_adapter_acceptance,
    )

    report = run_basic_resolution_adapter_acceptance(
        adapter_name="reference_text_resolution",
        llm_atomizer=SimpleUnitClusterAtomizer(bundle_id="acceptance_bundle_001"),
        normalizer=DeterministicNormalizer(),
        resolver=HardGateResolver(),
    )
    payload = report.to_dict()

    assert payload["adapter_name"] == "reference_text_resolution"
    assert payload["passed"] is True
    assert [check["name"] for check in payload["checks"]] == [
        "llm_atomizer_port",
        "normalization_adapter_port",
        "resolver_port",
        "trace_json_serializable",
        "expected_behavior.claim_status",
        "expected_behavior.missing_need_ids",
        "expected_behavior.supporting_atom_types",
        "expected_behavior.rejected_atom_types",
    ]
    assert payload["trace"]["run"]["final_graph"]["resolutions"][0]["status"] == (
        "supported_after_unit_normalization"
    )
    assert payload["expected_behavior_report"]["passed"] is True
    json.dumps(payload, ensure_ascii=False)


def test_basic_resolution_adapter_acceptance_reports_failed_expected_behavior():
    from evidence_toolchain import (
        AtomizerResult,
        DeterministicNormalizer,
        HardGateResolver,
        run_basic_resolution_adapter_acceptance,
    )

    class EmptyAtomizer:
        producer = "empty_atomizer"

        def atomize(self, task, units):
            del task, units
            return AtomizerResult(bundle_id="acceptance_bundle_001", atoms=())

    report = run_basic_resolution_adapter_acceptance(
        adapter_name="empty_atomizer",
        llm_atomizer=EmptyAtomizer(),
        normalizer=DeterministicNormalizer(),
        resolver=HardGateResolver(),
    )
    payload = report.to_dict()

    assert payload["passed"] is False
    assert payload["trace"]["run"]["final_graph"]["resolutions"][0]["status"] == (
        "insufficient"
    )
    failed_checks = [
        check for check in payload["checks"] if check["passed"] is False
    ]
    assert [check["name"] for check in failed_checks] == [
        "expected_behavior.claim_status",
        "expected_behavior.missing_need_ids",
        "expected_behavior.supporting_atom_types",
        "expected_behavior.rejected_atom_types",
    ]
    assert failed_checks[0]["expected"] == "supported_after_unit_normalization"
    assert failed_checks[0]["actual"] == "insufficient"


def test_adapter_acceptance_helper_stays_provider_and_framework_neutral():
    from pathlib import Path

    source = Path("src/evidence_toolchain/adapter_acceptance.py").read_text(
        encoding="utf-8"
    )

    for forbidden in ("openai", "langgraph", "requests", "httpx", "pdfplumber"):
        assert forbidden not in source


def test_reader_resolution_adapter_acceptance_passes_pdfplumber_inventory(tmp_path):
    import pytest

    pytest.importorskip("pdfplumber")

    from evidence_toolchain import (
        PdfPlumberExtractReader,
        run_reader_resolution_adapter_acceptance,
    )

    claims, expected = _usage_claim_and_expected_behavior()
    report = run_reader_resolution_adapter_acceptance(
        adapter_name="pdfplumber_reader",
        reader=PdfPlumberExtractReader(),
        sample_attachment=_pdf_attachment(tmp_path),
        claims=claims,
        expected_behavior=expected,
    )
    payload = report.to_dict()

    assert payload["passed"] is True
    assert payload["metadata"]["reader_producer"] == "pdfplumber_extract"
    assert payload["metadata"]["inventory_issue_codes"] == []
    assert payload["metadata"]["inventory_unit_count"] >= 1
    assert payload["trace"]["run"]["inventory"]["units"][0]["producer"] == (
        "pdfplumber_extract"
    )
    assert payload["trace"]["run"]["final_graph"]["resolutions"][0]["status"] == (
        "supported_after_unit_normalization"
    )
    assert payload["expected_behavior_report"]["passed"] is True
    assert "reader_inventory_units_present" in [
        check["name"] for check in payload["checks"]
    ]


def test_reader_resolution_adapter_acceptance_reports_missing_dependency(tmp_path):
    from evidence_toolchain import (
        PdfPlumberExtractReader,
        run_reader_resolution_adapter_acceptance,
    )

    claims, expected = _usage_claim_and_expected_behavior()
    report = run_reader_resolution_adapter_acceptance(
        adapter_name="pdfplumber_missing",
        reader=PdfPlumberExtractReader(pdfplumber_module=None),
        sample_attachment=_pdf_attachment(tmp_path),
        claims=claims,
        expected_behavior=expected,
    )
    payload = report.to_dict()

    assert payload["passed"] is False
    assert payload["metadata"]["inventory_issue_codes"] == [
        "pdfplumber_dependency_missing"
    ]
    assert payload["trace"]["run"]["final_graph"]["resolutions"][0]["status"] == (
        "insufficient"
    )
    failed_checks = [
        check for check in payload["checks"] if check["passed"] is False
    ]
    assert "reader_inventory_units_present" in [
        check["name"] for check in failed_checks
    ]
    assert payload["expected_behavior_report"]["passed"] is False


def test_convergence_adapter_acceptance_passes_reference_kernel():
    from evidence_toolchain import run_convergence_adapter_acceptance

    claims, expected = _convergence_claim_and_expected_behavior()

    report = run_convergence_adapter_acceptance(
        adapter_name="reference_convergence",
        inventory=_convergence_inventory(),
        claims=claims,
        expected_behavior=expected,
    )
    payload = report.to_dict()

    assert payload["adapter_name"] == "reference_convergence"
    assert payload["passed"] is True
    assert payload["metadata"]["scenario"] == "convergence_adapter_acceptance_v0"
    assert payload["metadata"]["inventory_unit_count"] == 5
    assert [check["name"] for check in payload["checks"]] == [
        "convergence_inventory_units_present",
        "convergence_blocking_issues_absent",
        "trace_json_serializable",
        "expected_behavior.claim_alignment_status",
        "expected_behavior.evidence_convergence_status",
        "expected_behavior.selected_support_set",
        "expected_behavior.review_trigger_codes",
        "expected_behavior.partial_failure_codes",
        "expected_behavior.unresolved_gaps",
    ]
    assert payload["trace"]["run"]["report"]["claim_reports"][0][
        "evidence_convergence_status"
    ] == "evidence_converged"
    assert payload["expected_behavior_report"]["passed"] is True
    json.dumps(payload, ensure_ascii=False)


def test_convergence_adapter_acceptance_reports_failed_expected_behavior():
    from evidence_toolchain import run_convergence_adapter_acceptance

    claims, expected = _convergence_claim_and_expected_behavior(
        status="needs_review_due_to_candidate_conflict"
    )

    report = run_convergence_adapter_acceptance(
        adapter_name="reference_convergence_mismatch",
        inventory=_convergence_inventory(),
        claims=claims,
        expected_behavior=expected,
    )
    payload = report.to_dict()

    assert payload["passed"] is False
    assert payload["trace"]["run"]["report"]["claim_reports"][0][
        "evidence_convergence_status"
    ] == "evidence_converged"
    failed_checks = [
        check for check in payload["checks"] if check["passed"] is False
    ]
    assert [check["name"] for check in failed_checks] == [
        "expected_behavior.evidence_convergence_status"
    ]
    assert failed_checks[0]["expected"] == "needs_review_due_to_candidate_conflict"
    assert failed_checks[0]["actual"] == "evidence_converged"


def test_reader_resolution_adapter_acceptance_reports_extraction_failure(tmp_path):
    from evidence_toolchain import (
        PdfPlumberExtractReader,
        run_reader_resolution_adapter_acceptance,
    )

    class FailingPdfPlumber:
        def open(self, path):
            del path
            raise RuntimeError("boom")

    claims, expected = _usage_claim_and_expected_behavior()
    report = run_reader_resolution_adapter_acceptance(
        adapter_name="pdfplumber_failed",
        reader=PdfPlumberExtractReader(pdfplumber_module=FailingPdfPlumber()),
        sample_attachment=_pdf_attachment(tmp_path),
        claims=claims,
        expected_behavior=expected,
    )
    payload = report.to_dict()

    assert payload["passed"] is False
    assert payload["metadata"]["inventory_issue_codes"] == [
        "pdf_text_extract_failed"
    ]
    assert payload["trace"]["run"]["final_graph"]["resolutions"][0]["status"] == (
        "insufficient"
    )
    assert payload["expected_behavior_report"]["passed"] is False
