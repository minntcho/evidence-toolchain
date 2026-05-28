from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from pathlib import Path

from synthetic.artifact_factory.e2e import run_synthetic_case


def test_run_csv_scenario_writes_runtime_report_from_input_only(tmp_path) -> None:
    result = run_synthetic_case(Path("scenarios/erp_export_basic.yaml"), tmp_path)

    root_dir = tmp_path / "erp_export_basic"
    runtime_report_path = root_dir / "_synthetic" / "runtime_report.json"
    report = _read_json(runtime_report_path)

    assert result.root_dir == root_dir
    assert result.runtime_report.status == "passed"
    assert (root_dir / "runtime_tmp" / "input" / "export.csv").exists()
    assert not (root_dir / "runtime_tmp" / "_synthetic").exists()
    assert not (root_dir / "runtime_tmp" / "expected").exists()

    assert report["case_id"] == "erp_export_basic"
    assert report["status"] == "passed"
    assert report["links"] == {
        "carrier_trace": "_synthetic/carrier_trace.json",
        "manifest": "_synthetic/manifest.json",
        "verification_report": "_synthetic/verification_report.json",
    }
    assert report["artifacts"] == [
        {
            "artifact_id": "export",
            "path": "input/export.csv",
            "carrier": "csv",
            "reader": "delimited_table_reader",
            "reader_status": "ingested",
            "observation_count": 6,
            "issue_count": 0,
        }
    ]
    assert report["predicates"] == [
        {
            "id": "artifact_ingested",
            "artifact_id": "export",
            "status": "passed",
            "message": "export was ingested by delimited_table_reader.",
        },
        {
            "id": "minimum_observation_count",
            "artifact_id": "export",
            "status": "passed",
            "actual": 6,
            "expected_min": 1,
            "message": "export produced 6 observations; expected at least 1.",
        },
    ]


def test_run_xlsx_scenario_uses_spreadsheet_reader(tmp_path) -> None:
    result = run_synthetic_case(
        Path("scenarios/supplier_breakdown_workbook_basic.yaml"),
        tmp_path,
    )

    report = _read_json(
        tmp_path
        / "supplier_breakdown_workbook_basic"
        / "_synthetic"
        / "runtime_report.json"
    )

    assert result.runtime_report.status == "passed"
    artifact = report["artifacts"][0]
    assert artifact["artifact_id"] == "breakdown"
    assert artifact["path"] == "input/breakdown.xlsx"
    assert artifact["carrier"] == "xlsx"
    assert artifact["reader"] == "spreadsheet_reader"
    assert artifact["reader_status"] == "ingested"
    assert artifact["observation_count"] >= 1
    assert {predicate["status"] for predicate in report["predicates"]} == {"passed"}


def test_run_marks_predicate_failed_when_observation_count_is_too_low(tmp_path) -> None:
    scenario_path = tmp_path / "too_many_observations.yaml"
    scenario_path.write_text(
        """
scenario_id: too_many_observations
seed: 31001
evidence_need:
  subject: electricity_usage
  site_hint: OCH-01
  period_hint: 2025-03
  amount: 6.4
  unit: MWh
documents:
  - id: export
    archetype: erp_export
    role: source_export
    carrier: csv
expected_predicates:
  - id: artifact_ingested
    artifact_id: export
    expected: true
  - id: minimum_observation_count
    artifact_id: export
    min_count: 999
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = run_synthetic_case(scenario_path, tmp_path)
    report = _read_json(
        tmp_path / "too_many_observations" / "_synthetic" / "runtime_report.json"
    )

    assert result.runtime_report.status == "failed"
    assert report["status"] == "failed"
    assert report["predicates"][1]["status"] == "failed"
    assert report["predicates"][1]["actual"] == 6
    assert report["predicates"][1]["expected_min"] == 999


def test_cli_run_command_builds_verifies_and_writes_runtime_report(tmp_path) -> None:
    from synthetic.artifact_factory.cli import main

    assert main(["run", "scenarios/erp_export_basic.yaml", "--out", str(tmp_path)]) == 0
    assert (tmp_path / "erp_export_basic" / "_synthetic" / "runtime_report.json").exists()


def test_pyproject_exposes_existing_evidence_synthetic_entrypoint() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["scripts"]["evidence-synthetic"] == (
        "synthetic.artifact_factory.cli:main"
    )
    includes = pyproject["tool"]["setuptools"]["packages"]["find"]["include"]
    assert "evidence_synthetic_runtime*" in includes


def test_importing_synthetic_e2e_does_not_load_runtime_bridge() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                "import synthetic.artifact_factory.e2e; "
                "print('evidence_toolchain' in sys.modules); "
                "print('evidence_synthetic_runtime' in sys.modules)"
            ),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.splitlines() == ["False", "False"]


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))
