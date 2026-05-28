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
