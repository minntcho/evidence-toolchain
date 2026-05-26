import json
from pathlib import Path


def test_planner_selects_expected_capabilities_for_generated_utility_bill(tmp_path):
    from evidence_toolchain.artifacts import EvidenceDocument
    from evidence_toolchain.planner import plan_document
    from synthetic.generator import generate_case
    from synthetic.manifests import load_manifest

    manifest = load_manifest("utility_bill_basic")
    generated = generate_case(manifest, tmp_path)

    document = EvidenceDocument.from_path(
        generated.document_path,
        declared_document_kind=manifest.document_kind,
    )

    plan = plan_document(document)

    assert [step.name for step in plan.selected_capabilities] == (
        manifest.expected_behavior.plan_includes
    )
    assert [issue.code for issue in plan.issues] == (
        manifest.expected_behavior.issues_include
    )


def test_planner_preserves_failure_mode_for_rotated_scan(tmp_path):
    from evidence_toolchain.artifacts import EvidenceDocument
    from evidence_toolchain.planner import plan_document
    from synthetic.generator import generate_case
    from synthetic.manifests import load_manifest

    manifest = load_manifest("scanned_utility_bill_rotated")
    generated = generate_case(manifest, tmp_path)

    document = EvidenceDocument.from_path(
        generated.document_path,
        declared_document_kind=manifest.document_kind,
    )

    plan = plan_document(document)

    assert "ocr_extract" in [step.name for step in plan.selected_capabilities]
    assert "rotated_document" in [issue.code for issue in plan.issues]
    assert "manual_review_request" in [step.name for step in plan.fallbacks]


def test_generated_expected_manifest_keeps_truth_separate_from_behavior(tmp_path):
    from synthetic.generator import generate_case
    from synthetic.manifests import load_manifest

    manifest = load_manifest("handwritten_meter_log")
    generated = generate_case(manifest, tmp_path)

    payload = json.loads(Path(generated.expected_path).read_text(encoding="utf-8"))

    assert "ground_truth" in payload
    assert "expected_behavior" in payload
    assert payload["ground_truth"]["amount"] == 1180
    assert payload["expected_behavior"]["plan_includes"] == [
        "handwriting_read",
        "table_structure_extract",
    ]
    assert "manual_review_request" in payload["expected_behavior"]["fallbacks_include"]
