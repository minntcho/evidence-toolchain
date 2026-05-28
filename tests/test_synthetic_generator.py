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

    assert "evidence case 3개 생성" in result.stdout

    utility_dir = output_dir / "utility_bill_basic"
    utility_doc = utility_dir / "evidence.txt"
    utility_expected = utility_dir / "expected.json"
    utility_experiment = utility_dir / "experiment.json"
    utility_expected_behavior = utility_dir / "expected-behavior.json"
    assert utility_dir.exists()
    assert utility_doc.exists()
    assert utility_expected.exists()
    assert utility_experiment.exists()
    assert utility_expected_behavior.exists()
    utility_text = utility_doc.read_text(encoding="utf-8")
    assert "Synthetic utility bill" not in utility_text
    assert "합성 유틸리티 청구서" in utility_text
    assert "공급자:" in utility_text
    assert "사용량 표" in utility_text

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

    experiment_payload = json.loads(utility_experiment.read_text(encoding="utf-8"))
    assert experiment_payload["schema_version"] == "experiment_manifest_v0"
    assert experiment_payload["experiment_id"] == "utility_bill_basic"
    assert experiment_payload["attachments"][0] == {
        "attachment_id": "utility_bill_basic_evidence",
        "path": "evidence.txt",
        "declared_media_type": "text/plain",
    }
    assert experiment_payload["claims"] == [
        {
            "x_id": "x_usage_amount_001",
            "fields": {
                "amount": 6.4,
                "unit": "MWh",
            },
        }
    ]

    behavior_payload = json.loads(utility_expected_behavior.read_text(encoding="utf-8"))
    assert behavior_payload == {
        "claim_resolutions": [
            {
                "x_id": "x_usage_amount_001",
                "status": "supported_direct",
                "missing_need_ids": [],
                "supporting_atom_types": ["usage_amount"],
                "rejected_atom_types": [],
            }
        ],
        "metadata": {
            "case_id": "utility_bill_basic",
            "source": "synthetic_generator",
        },
    }


def test_generate_evidence_cases_help_is_korean():
    result = subprocess.run(
        [
            sys.executable,
            "tools/generate_evidence_cases.py",
            "--help",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "synthetic evidence case를 생성합니다" in result.stdout
    assert "생성할 synthetic case id" in result.stdout


def test_synthetic_package_does_not_import_core_pipeline_modules():
    synthetic_files = [
        path
        for path in Path("synthetic").rglob("*.py")
        if "__pycache__" not in path.parts
    ]

    assert synthetic_files
    forbidden_imports = [
        "evidence_toolchain",
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


def test_generated_case_bundle_can_drive_experiment_cli_runner(tmp_path, capsys):
    from evidence_toolchain.cli import main
    from synthetic.generator import generate_case
    from synthetic.manifests import load_manifest

    generated = generate_case(load_manifest("utility_bill_basic"), tmp_path)
    trace_path = generated.case_dir / "out" / "trace.json"
    report_path = generated.case_dir / "out" / "expected-report.json"

    exit_code = main(
        [
            "run-experiment",
            str(generated.experiment_manifest_path),
            "--trace-out",
            str(trace_path),
            "--expected",
            str(generated.expected_behavior_path),
            "--expected-report-out",
            str(report_path),
        ]
    )

    trace_payload = json.loads(trace_path.read_text(encoding="utf-8"))
    report_payload = json.loads(report_path.read_text(encoding="utf-8"))
    summary_payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert trace_payload["experiment_id"] == "utility_bill_basic"
    assert trace_payload["run"]["final_graph"]["resolutions"][0]["status"] == (
        "supported_direct"
    )
    assert report_payload["passed"] is True
    assert summary_payload["expected_behavior"]["passed"] is True
