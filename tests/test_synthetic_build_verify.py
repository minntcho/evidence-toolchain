from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest

from synthetic.artifact_factory.e2e import (
    build_synthetic_case,
    load_scenario_case,
    verify_generated_case,
)


def test_build_csv_scenario_writes_expected_metadata_and_verification(tmp_path) -> None:
    result = build_synthetic_case(Path("scenarios/erp_export_basic.yaml"), tmp_path)

    root_dir = tmp_path / "erp_export_basic"
    assert result.root_dir == root_dir
    assert (root_dir / "input" / "export.csv").exists()
    assert (root_dir / "expected" / "expected_predicates.json").exists()
    assert (root_dir / "_synthetic" / "scenario_spec.yaml").exists()
    assert (root_dir / "_synthetic" / "scenario_ir.json").exists()
    assert (root_dir / "_synthetic" / "bundle_plan.json").exists()
    assert (root_dir / "_synthetic" / "tool_plan.json").exists()
    assert (root_dir / "_synthetic" / "manifest.json").exists()
    assert (root_dir / "_synthetic" / "carrier_trace.json").exists()
    assert (root_dir / "_synthetic" / "verification_report.json").exists()

    expected = _read_json(root_dir / "expected" / "expected_predicates.json")
    assert expected["predicates"] == [
        {
            "id": "artifact_ingested",
            "artifact_id": "export",
            "expected": True,
        },
        {
            "id": "minimum_observation_count",
            "artifact_id": "export",
            "min_count": 1,
        },
    ]

    report = _read_json(root_dir / "_synthetic" / "verification_report.json")
    assert report["case_id"] == "erp_export_basic"
    assert report["status"] == "passed"
    assert report["artifacts"] == [
        {
            "artifact_id": "export",
            "carrier": "csv",
            "path": "input/export.csv",
            "status": "passed",
            "checks": [
                {"id": "manifest_entry_present", "status": "passed"},
                {"id": "input_artifact_exists", "status": "passed"},
                {"id": "carrier_trace_present", "status": "passed"},
                {"id": "csv_readable", "status": "passed", "row_count": 1},
            ],
        }
    ]


def test_build_xlsx_scenario_writes_workbook_verification(tmp_path) -> None:
    result = build_synthetic_case(
        Path("scenarios/supplier_breakdown_workbook_basic.yaml"),
        tmp_path,
    )

    root_dir = tmp_path / "supplier_breakdown_workbook_basic"
    assert result.root_dir == root_dir
    assert (root_dir / "input" / "breakdown.xlsx").exists()

    report = _read_json(root_dir / "_synthetic" / "verification_report.json")
    assert report["case_id"] == "supplier_breakdown_workbook_basic"
    assert report["status"] == "passed"
    assert report["artifacts"][0]["artifact_id"] == "breakdown"
    assert report["artifacts"][0]["carrier"] == "xlsx"
    assert report["artifacts"][0]["checks"][-1] == {
        "id": "xlsx_readable",
        "status": "passed",
        "sheet_count": 1,
    }


def test_verify_generated_case_rejects_missing_input_artifact(tmp_path) -> None:
    build_synthetic_case(Path("scenarios/erp_export_basic.yaml"), tmp_path)
    root_dir = tmp_path / "erp_export_basic"
    (root_dir / "input" / "export.csv").unlink()

    report = verify_generated_case(root_dir)

    assert report.status == "failed"
    payload = _read_json(root_dir / "_synthetic" / "verification_report.json")
    assert payload["status"] == "failed"
    checks = payload["artifacts"][0]["checks"]
    assert {"id": "input_artifact_exists", "status": "failed"} in checks


def test_build_rejects_carriers_outside_v0_e2e_scope(tmp_path) -> None:
    scenario_path = tmp_path / "pdf_text.yaml"
    scenario_path.write_text(
        """
scenario_id: pdf_text_basic
seed: 51001
evidence_need:
  subject: electricity_usage
documents:
  - id: statement
    archetype: supplier_monthly_statement
    role: source_statement
    carrier: pdf_text
expected_predicates:
  - id: artifact_ingested
    artifact_id: statement
    expected: true
""".strip()
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="v0 synthetic e2e only supports csv, xlsx"):
        build_synthetic_case(scenario_path, tmp_path)


def test_cli_build_and_verify_commands(tmp_path) -> None:
    from synthetic.artifact_factory.cli import main

    assert main(["build", "scenarios/erp_export_basic.yaml", "--out", str(tmp_path)]) == 0
    assert main(["verify", str(tmp_path / "erp_export_basic")]) == 0


def test_pyproject_exposes_evidence_synthetic_cli_entrypoint() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["scripts"]["evidence-synthetic"] == (
        "synthetic.artifact_factory.cli:main"
    )


def test_artifact_factory_package_exports_build_verify_helpers() -> None:
    from synthetic.artifact_factory import build_synthetic_case, verify_generated_case

    assert build_synthetic_case.__name__ == "build_synthetic_case"
    assert verify_generated_case.__name__ == "verify_generated_case"


def test_load_scenario_case_preserves_spec_and_expected_predicates() -> None:
    scenario = load_scenario_case(Path("scenarios/erp_export_basic.yaml"))

    assert scenario.spec.scenario_id == "erp_export_basic"
    assert scenario.spec.documents[0].document_id == "export"
    assert scenario.spec.documents[0].carrier == "csv"
    assert scenario.expected_predicates == (
        {
            "id": "artifact_ingested",
            "artifact_id": "export",
            "expected": True,
        },
        {
            "id": "minimum_observation_count",
            "artifact_id": "export",
            "min_count": 1,
        },
    )


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))
