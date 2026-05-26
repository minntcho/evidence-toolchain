import inspect
import re

import pytest


HANGUL = re.compile(r"[가-힣]")


def assert_korean(text: str) -> None:
    assert HANGUL.search(text), text


def test_public_runtime_docstrings_are_korean():
    import evidence_toolchain
    from evidence_toolchain import artifacts, capabilities, preflight, routers, runners
    from evidence_toolchain.runtime import (
        EvidenceEvent,
        EvidenceRunState,
        EvidenceStep,
        EvidenceToolResult,
    )
    import synthetic

    public_objects = [
        evidence_toolchain,
        synthetic,
        artifacts.EvidenceDocument,
        preflight.EvidencePreflight,
        routers.ObservationRouter,
        routers.RuleObservationRouter,
        runners.run_document,
        capabilities.CapabilityRunner,
        capabilities.ManualReviewCapabilityRunner,
        capabilities.StaticCapabilityRunner,
        EvidenceEvent,
        EvidenceStep,
        EvidenceToolResult,
        EvidenceRunState,
    ]

    for public_object in public_objects:
        assert_korean(inspect.getdoc(public_object) or "")


def test_capability_purposes_are_korean_while_ids_remain_stable():
    from evidence_toolchain.capabilities import CAPABILITY_REGISTRY

    expected_ids = {
        "docling_parse",
        "ocr_extract",
        "table_structure_extract",
        "utility_bill_extract",
        "receipt_extract",
        "handwriting_read",
        "meter_photo_read",
        "vision_extract",
        "manual_review_request",
    }

    assert set(CAPABILITY_REGISTRY) == expected_ids
    assert (
        CAPABILITY_REGISTRY["docling_parse"].purpose
        == "text, layout, table이 있는 born-digital 문서를 파싱합니다."
    )
    for capability in CAPABILITY_REGISTRY.values():
        assert capability.name in expected_ids
        assert_korean(capability.purpose)


def test_runtime_errors_are_korean():
    from evidence_toolchain.capabilities import StaticCapabilityRunner
    from evidence_toolchain.reports import emit_evidence_report
    from evidence_toolchain.runtime import EvidenceRunState, EvidenceStep

    state = EvidenceRunState(run_id="run-001", document={"document_id": "doc-001"})
    runner = StaticCapabilityRunner({})

    with pytest.raises(ValueError, match="capability name이 필요합니다"):
        runner.run(EvidenceStep(name="execute_capability", status="pending"), state)

    with pytest.raises(ValueError, match="plan이 있어야 합니다"):
        emit_evidence_report(state)


def test_synthetic_validation_errors_are_korean(tmp_path, monkeypatch):
    from synthetic import manifests
    from synthetic.generators import render_document
    from synthetic.manifests import ExpectedBehavior, SyntheticCaseManifest

    manifest_path = tmp_path / "bad.json"
    manifest_path.write_text(
        """{
  "case_id": "bad",
  "document_kind": "utility_bill",
  "title": "bad",
  "quality": "clean",
  "text_layer": true,
  "signals": [],
  "ground_truth": {},
  "expected_behavior": []
}
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(manifests, "MANIFEST_DIR", tmp_path)

    with pytest.raises(ValueError, match="expected_behavior는 object여야 합니다"):
        manifests.load_manifest("bad")

    unsupported_manifest = SyntheticCaseManifest(
        case_id="bad_kind",
        document_kind="spreadsheet",
        title="bad kind",
        quality="clean",
        text_layer=True,
        signals=[],
        ground_truth={},
        expected_behavior=ExpectedBehavior(
            plan_includes=[],
            fallbacks_include=[],
            issues_include=[],
        ),
    )

    with pytest.raises(ValueError, match="지원하지 않는 synthetic document kind"):
        render_document(unsupported_manifest)
