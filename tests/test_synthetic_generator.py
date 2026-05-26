import json
import subprocess
import sys
from pathlib import Path


def test_generate_evidence_cases_writes_documents_and_expected_manifests(tmp_path):
    output_dir = tmp_path / "generated"

    result = subprocess.run(
        [
            sys.executable,
            "tools/generate_evidence_cases.py",
            "--output-dir",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "generated 3 evidence cases" in result.stdout

    utility_dir = output_dir / "utility_bill_basic"
    utility_doc = utility_dir / "evidence.txt"
    utility_expected = utility_dir / "expected.json"
    assert utility_dir.exists()
    assert utility_doc.exists()
    assert utility_expected.exists()

    payload = json.loads(utility_expected.read_text(encoding="utf-8"))
    assert payload["case_id"] == "utility_bill_basic"
    assert payload["artifact"] == {
        "path": "evidence.txt",
        "format": "txt",
        "media_type": "text/plain",
        "document_kind": "utility_bill",
    }
    assert payload["ground_truth"]["amount"] == 6.4
    assert payload["expected_observation"] == {
        "document_class": "utility_bill",
        "has_text_layer": True,
        "quality": "clean",
        "signals": [],
    }
    assert payload["expected_plan"]["selected_capabilities"] == [
        "docling_parse",
        "table_structure_extract",
        "utility_bill_extract",
    ]


def test_synthetic_package_does_not_import_core_pipeline_modules():
    synthetic_files = [
        path
        for path in Path("synthetic").rglob("*.py")
        if "__pycache__" not in path.parts
    ]

    assert synthetic_files
    forbidden_imports = [
        "evidence_toolchain.planner",
        "evidence_toolchain.capabilities",
        "evidence_toolchain.observations",
        "evidence_toolchain.reports",
    ]

    for path in synthetic_files:
        source = path.read_text(encoding="utf-8")
        for forbidden in forbidden_imports:
            assert forbidden not in source, f"{path} imports {forbidden}"


def test_generated_case_bundle_can_drive_local_runner(tmp_path):
    from evidence_toolchain.artifacts import EvidenceDocument
    from evidence_toolchain.runners import run_document
    from synthetic.generator import generate_case
    from synthetic.manifests import load_manifest

    generated = generate_case(load_manifest("receipt_quantity_vs_price"), tmp_path)
    payload = json.loads(generated.expected_path.read_text(encoding="utf-8"))

    state = run_document(EvidenceDocument.from_path(generated.document_path))

    assert generated.document_path.name == payload["artifact"]["path"]
    assert state.observation is not None
    assert state.observation.document_class == payload["expected_observation"]["document_class"]
    assert state.observation.has_text_layer == payload["expected_observation"]["has_text_layer"]
    assert state.observation.quality == payload["expected_observation"]["quality"]
    assert state.observation.signals == payload["expected_observation"]["signals"]
    assert state.plan is not None
    assert [step.name for step in state.plan.selected_capabilities] == (
        payload["expected_plan"]["selected_capabilities"]
    )
    assert [step.name for step in state.plan.fallbacks] == payload["expected_plan"]["fallbacks"]
    assert [issue.code for issue in state.plan.issues] == payload["expected_plan"]["issues"]
