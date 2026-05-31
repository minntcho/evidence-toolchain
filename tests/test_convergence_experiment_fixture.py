import json
from pathlib import Path


def _run_convergence_fixture(fixture_name, tmp_path, capsys, run_id):
    from evidence_toolchain.cli import main

    fixture_dir = Path("tests/fixtures") / fixture_name
    evidence_path = fixture_dir / "usage.csv"
    manifest_path = fixture_dir / "experiment.json"
    expected_path = fixture_dir / "expected-behavior.json"

    assert evidence_path.exists()
    assert manifest_path.exists()
    assert expected_path.exists()

    trace_path = tmp_path / "convergence-trace.json"
    report_path = tmp_path / "expected-report.json"

    exit_code = main(
        [
            "run-convergence",
            str(manifest_path),
            "--trace-out",
            str(trace_path),
            "--expected",
            str(expected_path),
            "--expected-report-out",
            str(report_path),
            "--run-id",
            run_id,
        ]
    )

    trace_payload = json.loads(trace_path.read_text(encoding="utf-8"))
    report_payload = json.loads(report_path.read_text(encoding="utf-8"))
    summary_payload = json.loads(capsys.readouterr().out)

    return exit_code, trace_payload, report_payload, summary_payload, report_path


def test_convergence_clean_support_fixture_runs_through_cli(tmp_path, capsys):
    (
        exit_code,
        trace_payload,
        report_payload,
        summary_payload,
        report_path,
    ) = _run_convergence_fixture(
        "convergence_clean_support",
        tmp_path,
        capsys,
        "fixture_convergence_run",
    )

    run_payload = trace_payload["run"]
    claim_report = run_payload["report"]["claim_reports"][0]

    assert exit_code == 0
    assert trace_payload["experiment_id"] == "convergence_clean_support"
    assert report_payload["passed"] is True
    assert summary_payload["expected_behavior"]["passed"] is True
    assert summary_payload["expected_behavior"]["report_path"] == str(report_path)

    assert run_payload["run_id"] == "fixture_convergence_run"
    assert run_payload["report"]["metadata"]["case_snapshot_id"].startswith(
        "case_snapshot:"
    )
    assert run_payload["report"]["metadata"]["strategy_id"] == "convergence_mvp"
    assert run_payload["report"]["metadata"]["view_kind"] == "ConvergenceReport"

    assert claim_report["claim_id"] == "x_usage_001"
    assert claim_report["claim_alignment_status"] == (
        "supported_after_unit_normalization"
    )
    assert claim_report["evidence_convergence_status"] == "evidence_converged"
    assert claim_report["selected_support_set"] == ["cand_001"]
    assert claim_report["review_triggers"] == []
    assert claim_report["partial_failures"] == []
    assert claim_report["unresolved_gaps"] == []
    assert claim_report["downstream_verdict"] is None


def test_convergence_nonblocking_issue_fixture_runs_through_cli(tmp_path, capsys):
    (
        exit_code,
        trace_payload,
        report_payload,
        summary_payload,
        _report_path,
    ) = _run_convergence_fixture(
        "convergence_nonblocking_issue",
        tmp_path,
        capsys,
        "fixture_convergence_nonblocking_run",
    )

    claim_report = trace_payload["run"]["report"]["claim_reports"][0]

    assert exit_code == 0
    assert trace_payload["experiment_id"] == "convergence_nonblocking_issue"
    assert report_payload["passed"] is True
    assert summary_payload["expected_behavior"]["passed"] is True
    assert claim_report["claim_alignment_status"] == (
        "supported_after_unit_normalization"
    )
    assert claim_report["evidence_convergence_status"] == "evidence_converged"
    assert claim_report["selected_support_set"] == ["cand_001"]
    assert [failure["code"] for failure in claim_report["partial_failures"]] == [
        "nonblocking_failure"
    ]
    assert claim_report["review_triggers"] == []
    assert claim_report["unresolved_gaps"] == []


def test_convergence_candidate_conflict_fixture_runs_through_cli(tmp_path, capsys):
    (
        exit_code,
        trace_payload,
        report_payload,
        summary_payload,
        _report_path,
    ) = _run_convergence_fixture(
        "convergence_candidate_conflict",
        tmp_path,
        capsys,
        "fixture_convergence_conflict_run",
    )

    claim_report = trace_payload["run"]["report"]["claim_reports"][0]

    assert exit_code == 0
    assert trace_payload["experiment_id"] == "convergence_candidate_conflict"
    assert report_payload["passed"] is True
    assert summary_payload["expected_behavior"]["passed"] is True
    assert claim_report["claim_alignment_status"] == (
        "supported_after_unit_normalization"
    )
    assert claim_report["evidence_convergence_status"] == (
        "needs_review_due_to_candidate_conflict"
    )
    assert claim_report["selected_support_set"] == ["cand_001"]
    assert claim_report["candidate_ids"] == ["cand_001", "cand_002"]
    assert [trigger["code"] for trigger in claim_report["review_triggers"]] == [
        "candidate_conflict"
    ]
    assert claim_report["partial_failures"] == []
    assert claim_report["unresolved_gaps"] == ["quantity"]
