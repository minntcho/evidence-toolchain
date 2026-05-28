import json


def _write_manifest(tmp_path):
    evidence_path = tmp_path / "evidence.txt"
    evidence_path.write_text(
        "electricity usage 6.4 MWh\nbill amount 1,230,000 KRW\n",
        encoding="utf-8",
    )
    manifest_path = tmp_path / "experiment.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "experiment_manifest_v0",
                "experiment_id": "experiment_001",
                "bundle_id": "bundle_001",
                "attachments": [
                    {
                        "attachment_id": "raw_evidence",
                        "path": "evidence.txt",
                        "declared_media_type": "text/plain",
                    }
                ],
                "claims": [
                    {
                        "x_id": "x_001",
                        "fields": {
                            "amount": 6400,
                            "unit": "kWh",
                        },
                    }
                ],
                "budget": {"max_iterations": 3},
            }
        ),
        encoding="utf-8",
    )
    return manifest_path


def _write_expected(tmp_path, *, status):
    expected_path = tmp_path / "expected.json"
    expected_path.write_text(
        json.dumps(
            {
                "claim_resolutions": [
                    {
                        "x_id": "x_001",
                        "status": status,
                        "missing_need_ids": [],
                        "supporting_atom_types": ["usage_amount"],
                        "rejected_atom_types": ["currency_amount"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    return expected_path


def test_cli_run_experiment_writes_trace_and_expected_report(tmp_path, capsys):
    from evidence_toolchain.cli import main

    trace_path = tmp_path / "trace.json"
    report_path = tmp_path / "expected-report.json"

    exit_code = main(
        [
            "run-experiment",
            str(_write_manifest(tmp_path)),
            "--trace-out",
            str(trace_path),
            "--expected",
            str(
                _write_expected(
                    tmp_path,
                    status="supported_after_unit_normalization",
                )
            ),
            "--expected-report-out",
            str(report_path),
        ]
    )

    assert exit_code == 0
    trace_payload = json.loads(trace_path.read_text(encoding="utf-8"))
    report_payload = json.loads(report_path.read_text(encoding="utf-8"))
    summary_payload = json.loads(capsys.readouterr().out)

    assert trace_payload["experiment_id"] == "experiment_001"
    assert trace_payload["run"]["final_graph"]["resolutions"][0]["status"] == (
        "supported_after_unit_normalization"
    )
    assert report_payload["passed"] is True
    assert summary_payload["trace_path"] == str(trace_path)
    assert summary_payload["expected_behavior"]["passed"] is True


def test_cli_run_experiment_returns_nonzero_when_expected_behavior_fails(tmp_path):
    from evidence_toolchain.cli import main

    trace_path = tmp_path / "trace.json"
    report_path = tmp_path / "expected-report.json"

    exit_code = main(
        [
            "run-experiment",
            str(_write_manifest(tmp_path)),
            "--trace-out",
            str(trace_path),
            "--expected",
            str(_write_expected(tmp_path, status="contradicted")),
            "--expected-report-out",
            str(report_path),
        ]
    )

    report_payload = json.loads(report_path.read_text(encoding="utf-8"))

    assert exit_code == 1
    assert trace_path.exists()
    assert report_payload["passed"] is False
    assert report_payload["checks"][0]["name"] == "claim_status"
    assert report_payload["checks"][0]["actual"] == (
        "supported_after_unit_normalization"
    )
