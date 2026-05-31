def _trace_for_supported_usage_claim():
    from evidence_toolchain import (
        DeclaredClaim,
        EvidenceUnit,
        EvidenceInventory,
        ExperimentAttachmentSpec,
        ExperimentManifest,
        build_experiment_run_trace,
        run_resolution_cycle,
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
        inventory=EvidenceInventory(
            bundle_id="bundle_001",
            attachments=(),
            artifacts=(),
            units=(
                EvidenceUnit(
                    unit_id="unit_usage",
                    artifact_id="artifact_text",
                    unit_type="text_span",
                    producer="plain_text_reader",
                    text="electricity usage 6.4 MWh",
                ),
                EvidenceUnit(
                    unit_id="unit_charge",
                    artifact_id="artifact_text",
                    unit_type="text_span",
                    producer="plain_text_reader",
                    text="bill amount 1,230,000 KRW",
                ),
            ),
            route_decisions=(),
        ),
        claims=manifest.claims,
        max_investigation_steps=3,
    )
    return build_experiment_run_trace(manifest=manifest, run=run)


def _trace_for_supported_convergence_claim():
    from evidence_toolchain import (
        DeclaredClaim,
        EvidenceInventory,
        EvidenceUnit,
        ExperimentAttachmentSpec,
        ExperimentManifest,
        build_experiment_run_trace,
    )
    from evidence_toolchain.convergence.runner import run_convergence_cycle

    manifest = ExperimentManifest(
        experiment_id="convergence_experiment_001",
        bundle_id="bundle_001",
        attachments=(
            ExperimentAttachmentSpec(
                attachment_id="raw_usage_csv",
                path="usage.csv",
                declared_media_type="text/csv",
            ),
        ),
        claims=(
            DeclaredClaim(
                x_id="x_usage_001",
                fields={
                    "site": "OCH-01",
                    "period": "2025-03",
                    "activity": "electricity",
                    "amount": 6400,
                    "unit": "kWh",
                },
            ),
        ),
    )
    run = run_convergence_cycle(
        inventory=EvidenceInventory(
            bundle_id="bundle_001",
            attachments=(),
            artifacts=(),
            units=(
                EvidenceUnit(
                    unit_id="cell_site",
                    artifact_id="artifact_usage",
                    unit_type="table_cell",
                    producer="fixture_reader",
                    text="OCH-01",
                    locator={"row": 2, "column": 1, "header": "site"},
                ),
                EvidenceUnit(
                    unit_id="cell_period",
                    artifact_id="artifact_usage",
                    unit_type="table_cell",
                    producer="fixture_reader",
                    text="2025-03",
                    locator={"row": 2, "column": 2, "header": "period"},
                ),
                EvidenceUnit(
                    unit_id="cell_activity",
                    artifact_id="artifact_usage",
                    unit_type="table_cell",
                    producer="fixture_reader",
                    text="electricity",
                    locator={"row": 2, "column": 3, "header": "activity"},
                ),
                EvidenceUnit(
                    unit_id="cell_quantity",
                    artifact_id="artifact_usage",
                    unit_type="table_cell",
                    producer="fixture_reader",
                    text="6.4",
                    value=6.4,
                    locator={"row": 2, "column": 4, "header": "amount"},
                ),
                EvidenceUnit(
                    unit_id="cell_unit",
                    artifact_id="artifact_usage",
                    unit_type="table_cell",
                    producer="fixture_reader",
                    text="MWh",
                    locator={"row": 2, "column": 5, "header": "unit"},
                ),
            ),
            route_decisions=(),
        ),
        claims=manifest.claims,
        run_id="convergence_run_001",
    )
    return build_experiment_run_trace(manifest=manifest, run=run)


def test_expected_behavior_oracle_reports_matching_resolution_expectations():
    from evidence_toolchain import (
        ExpectedClaimResolution,
        ExperimentExpectedBehavior,
        evaluate_expected_behavior,
    )

    report = evaluate_expected_behavior(
        trace=_trace_for_supported_usage_claim(),
        expected=ExperimentExpectedBehavior(
            claim_resolutions=(
                ExpectedClaimResolution(
                    x_id="x_001",
                    status="supported_after_unit_normalization",
                    missing_need_ids=(),
                    supporting_atom_types=("usage_amount",),
                    rejected_atom_types=("currency_amount",),
                ),
            )
        ),
    )
    payload = report.to_dict()

    assert payload["passed"] is True
    assert [check["name"] for check in payload["checks"]] == [
        "claim_status",
        "missing_need_ids",
        "supporting_atom_types",
        "rejected_atom_types",
    ]
    assert all(check["passed"] for check in payload["checks"])
    assert payload["metadata"]["producer"] == "expected_behavior_oracle_v0"


def test_expected_behavior_oracle_reports_matching_convergence_expectations():
    from evidence_toolchain import (
        ExpectedClaimConvergence,
        ExperimentExpectedBehavior,
        evaluate_expected_behavior,
    )

    report = evaluate_expected_behavior(
        trace=_trace_for_supported_convergence_claim(),
        expected=ExperimentExpectedBehavior(
            claim_convergences=(
                ExpectedClaimConvergence(
                    x_id="x_usage_001",
                    claim_alignment_status="supported_after_unit_normalization",
                    evidence_convergence_status="evidence_converged",
                    selected_support_set=("cand_001",),
                    review_trigger_codes=(),
                    partial_failure_codes=(),
                    unresolved_gaps=(),
                ),
            )
        ),
    )
    payload = report.to_dict()

    assert payload["passed"] is True
    assert [check["name"] for check in payload["checks"]] == [
        "claim_alignment_status",
        "evidence_convergence_status",
        "selected_support_set",
        "review_trigger_codes",
        "partial_failure_codes",
        "unresolved_gaps",
    ]
    assert all(check["passed"] for check in payload["checks"])


def test_expected_behavior_oracle_reports_mismatch_without_changing_trace():
    from evidence_toolchain import (
        ExpectedClaimResolution,
        ExperimentExpectedBehavior,
        evaluate_expected_behavior,
    )

    trace = _trace_for_supported_usage_claim()
    report = evaluate_expected_behavior(
        trace=trace,
        expected=ExperimentExpectedBehavior(
            claim_resolutions=(
                ExpectedClaimResolution(
                    x_id="x_001",
                    status="contradicted",
                ),
            )
        ),
    )
    payload = report.to_dict()

    assert payload["passed"] is False
    assert payload["checks"][0]["name"] == "claim_status"
    assert payload["checks"][0]["expected"] == "contradicted"
    assert payload["checks"][0]["actual"] == "supported_after_unit_normalization"
    assert trace.to_dict()["run"]["final_graph"]["resolutions"][0]["status"] == (
        "supported_after_unit_normalization"
    )


def test_expected_behavior_oracle_reports_convergence_mismatch_without_changing_trace():
    from evidence_toolchain import (
        ExpectedClaimConvergence,
        ExperimentExpectedBehavior,
        evaluate_expected_behavior,
    )

    trace = _trace_for_supported_convergence_claim()
    report = evaluate_expected_behavior(
        trace=trace,
        expected=ExperimentExpectedBehavior(
            claim_convergences=(
                ExpectedClaimConvergence(
                    x_id="x_usage_001",
                    evidence_convergence_status="needs_review_due_to_candidate_conflict",
                ),
            )
        ),
    )
    payload = report.to_dict()

    assert payload["passed"] is False
    assert payload["checks"][0]["name"] == "evidence_convergence_status"
    assert payload["checks"][0]["expected"] == "needs_review_due_to_candidate_conflict"
    assert payload["checks"][0]["actual"] == "evidence_converged"
    assert trace.to_dict()["run"]["report"]["claim_reports"][0][
        "evidence_convergence_status"
    ] == "evidence_converged"


def test_expected_behavior_loader_accepts_claim_convergences():
    from evidence_toolchain import experiment_expected_behavior_from_dict

    expected = experiment_expected_behavior_from_dict(
        {
            "claim_convergences": [
                {
                    "x_id": "x_usage_001",
                    "claim_alignment_status": "supported_after_unit_normalization",
                    "evidence_convergence_status": "evidence_converged",
                    "selected_support_set": ["cand_001"],
                    "review_trigger_codes": [],
                    "partial_failure_codes": [],
                    "unresolved_gaps": [],
                }
            ]
        }
    )

    convergence = expected.claim_convergences[0]
    assert convergence.x_id == "x_usage_001"
    assert convergence.claim_alignment_status == "supported_after_unit_normalization"
    assert convergence.selected_support_set == ("cand_001",)
