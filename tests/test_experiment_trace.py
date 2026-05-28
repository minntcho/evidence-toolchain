import json


def _inventory_with_units(*units):
    from evidence_toolchain import EvidenceInventory

    return EvidenceInventory(
        bundle_id="bundle_001",
        attachments=(),
        artifacts=(),
        units=tuple(units),
        route_decisions=(),
    )


def test_experiment_run_trace_preserves_manifest_and_resolution_run(tmp_path):
    from evidence_toolchain import (
        DeclaredClaim,
        EvidenceUnit,
        ExperimentAttachmentSpec,
        ExperimentManifest,
        build_experiment_run_trace,
        run_resolution_cycle,
        write_experiment_run_trace,
    )

    manifest = ExperimentManifest(
        experiment_id="experiment_001",
        bundle_id="bundle_001",
        attachments=(
            ExperimentAttachmentSpec(
                attachment_id="raw_evidence",
                path="evidence.txt",
                declared_media_type="text/plain",
            ),
        ),
        claims=(
            DeclaredClaim(
                x_id="x_001",
                fields={"amount": 6400, "unit": "kWh"},
            ),
        ),
    )
    run = run_resolution_cycle(
        inventory=_inventory_with_units(
            EvidenceUnit(
                unit_id="unit_usage",
                artifact_id="artifact_text",
                unit_type="text_span",
                producer="plain_text_reader",
                text="electricity usage 6.4 MWh",
            )
        ),
        claims=manifest.claims,
        max_investigation_steps=3,
    )

    trace = build_experiment_run_trace(manifest=manifest, run=run)
    output_path = write_experiment_run_trace(trace, tmp_path / "trace.json")
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["schema_version"] == "experiment_run_trace_v0"
    assert payload["experiment_id"] == "experiment_001"
    assert payload["manifest"]["attachments"][0]["path"] == "evidence.txt"
    assert payload["run"]["initial_graph"]["resolutions"][0]["status"] == "insufficient"
    assert payload["run"]["final_graph"]["resolutions"][0]["status"] == (
        "supported_after_unit_normalization"
    )
    completed_tasks = payload["run"]["investigation_state"]["completed_tasks"]
    assert [task["task_id"] for task in completed_tasks] == [
        "gap_x_001_usage_amount_001",
        "gap_x_001_usage_amount_001_atomize_001",
        "gap_x_001_usage_amount_001_atomize_001_normalize_001",
    ]
    assert [task["status"] for task in completed_tasks] == [
        "completed",
        "completed",
        "completed",
    ]
    assert completed_tasks[0]["metadata"]["selected_unit_ids"] == ["unit_usage"]
    assert completed_tasks[1]["produced_atom_ids"] == [
        "gap_x_001_usage_amount_001_atomize_001_atom_001"
    ]
    assert completed_tasks[2]["produced_normalization_result_ids"] == [
        "gap_x_001_usage_amount_001_atomize_001_atom_001"
    ]
    assert payload["metadata"]["producer"] == "experiment_run_trace_v0"
