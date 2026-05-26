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

    utility_doc = output_dir / "utility_bill_basic.txt"
    utility_expected = output_dir / "utility_bill_basic.expected.json"
    assert utility_doc.exists()
    assert utility_expected.exists()

    payload = json.loads(utility_expected.read_text(encoding="utf-8"))
    assert payload["case_id"] == "utility_bill_basic"
    assert payload["ground_truth"]["amount"] == 6.4
    assert payload["expected_behavior"]["plan_includes"] == [
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
