from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path
from typing import Sequence

from evidence_toolchain.experiments import (
    build_experiment_run_trace,
    evaluate_expected_behavior,
    load_experiment_expected_behavior,
    load_experiment_manifest,
    write_experiment_run_trace,
)
from evidence_toolchain.file_routing import ingest_bundle
from evidence_toolchain.investigation import InvestigationBudget
from evidence_toolchain.resolution_cycle import run_resolution_cycle


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


def _run_experiment(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest)
    manifest = load_experiment_manifest(manifest_path)
    bundle = manifest.to_attachment_bundle(base_dir=manifest_path.parent)
    inventory = ingest_bundle(bundle)
    max_steps = _max_investigation_steps(
        cli_value=args.max_investigation_steps,
        manifest_budget=manifest.budget,
    )
    run = run_resolution_cycle(
        inventory=inventory,
        claims=manifest.claims,
        run_id=args.run_id or f"{manifest.experiment_id}_run",
        max_investigation_steps=max_steps,
        budget=_budget_for_run(manifest.budget, max_steps=max_steps),
    )
    trace = build_experiment_run_trace(
        manifest=manifest,
        run=run,
        metadata={
            "cli_command": "run-experiment",
            "manifest_path": str(manifest_path),
            "inventory_unit_count": len(inventory.units),
        },
    )
    trace_path = write_experiment_run_trace(trace, args.trace_out)

    expected_report = None
    expected_report_path = None
    if args.expected is not None:
        expected = load_experiment_expected_behavior(args.expected)
        expected_report = evaluate_expected_behavior(trace=trace, expected=expected)
        expected_report_path = Path(args.expected_report_out) if args.expected_report_out else (
            Path(args.trace_out).with_suffix(".expected-report.json")
        )
        expected_report_path.parent.mkdir(parents=True, exist_ok=True)
        expected_report_path.write_text(
            json.dumps(
                expected_report.to_dict(),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    print(
        json.dumps(
            _summary_payload(
                manifest_id=manifest.experiment_id,
                trace_path=trace_path,
                expected_report_path=expected_report_path,
                expected_report=expected_report,
            ),
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    if expected_report is not None and not expected_report.passed:
        return 1
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="evidence-toolchain",
        description="Local evidence-toolchain experiment utilities.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser(
        "run-experiment",
        help="Run an ExperimentManifest through the deterministic resolution cycle.",
    )
    run_parser.add_argument("manifest", help="Path to an experiment manifest JSON file.")
    run_parser.add_argument(
        "--trace-out",
        required=True,
        help="Path where the ExperimentRunTrace JSON artifact will be written.",
    )
    run_parser.add_argument(
        "--expected",
        help="Optional ExperimentExpectedBehavior JSON file to compare against.",
    )
    run_parser.add_argument(
        "--expected-report-out",
        help="Optional path for the ExpectedBehaviorReport JSON artifact.",
    )
    run_parser.add_argument(
        "--max-investigation-steps",
        type=int,
        help="Override the manifest investigation iteration budget for this run.",
    )
    run_parser.add_argument(
        "--run-id",
        help="Optional run id. Defaults to '<experiment_id>_run'.",
    )
    run_parser.set_defaults(func=_run_experiment)
    return parser


def _max_investigation_steps(
    *,
    cli_value: int | None,
    manifest_budget: InvestigationBudget,
) -> int:
    if cli_value is not None:
        return max(0, cli_value)
    if manifest_budget.max_iterations > 0:
        return manifest_budget.max_iterations
    return 10


def _budget_for_run(
    manifest_budget: InvestigationBudget,
    *,
    max_steps: int,
) -> InvestigationBudget | None:
    if manifest_budget.max_iterations <= 0:
        return None
    return replace(manifest_budget, max_iterations=max_steps)


def _summary_payload(
    *,
    manifest_id: str,
    trace_path: Path,
    expected_report_path: Path | None,
    expected_report,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "experiment_id": manifest_id,
        "trace_path": str(trace_path),
    }
    if expected_report is not None:
        payload["expected_behavior"] = {
            "passed": expected_report.passed,
            "report_path": str(expected_report_path),
        }
    return payload


if __name__ == "__main__":
    raise SystemExit(main())
