from pathlib import Path


def test_resolution_gap_planner_turns_missing_needs_into_investigation_tasks():
    from evidence_toolchain import (
        ClaimResolution,
        EvidenceResolutionGraph,
        InvestigationTaskType,
        Need,
        NeedLedgerStatus,
        NeedSpec,
        NeedType,
        ResolutionEdge,
        ResolutionGapPlanner,
        ResolutionRelation,
        ResolutionStatus,
    )

    need_spec = NeedSpec(
        x_id="x_001",
        needs=(
            Need(
                need_id=NeedType.USAGE_AMOUNT,
                need_type=NeedType.USAGE_AMOUNT,
                target_value=6400,
                target_unit="kWh",
            ),
            Need(
                need_id=NeedType.SERVICE_PERIOD,
                need_type=NeedType.SERVICE_PERIOD,
                target_period="2025-03",
            ),
        ),
    )
    graph = EvidenceResolutionGraph(
        bundle_id="bundle_001",
        claim_ids=("x_001",),
        atom_ids=("atom_currency",),
        edges=(
            ResolutionEdge(
                edge_id="edge_001",
                x_id="x_001",
                atom_id="atom_currency",
                relation=ResolutionRelation.REJECTED_FOR_NEED,
                need_id=NeedType.USAGE_AMOUNT,
                metadata={"reason": "currency_value_not_usage_quantity"},
            ),
        ),
        resolutions=(
            ClaimResolution(
                x_id="x_001",
                status=ResolutionStatus.INSUFFICIENT,
                rejected_atom_ids=("atom_currency",),
                missing_need_ids=(NeedType.USAGE_AMOUNT, NeedType.SERVICE_PERIOD),
            ),
        ),
    )

    plan = ResolutionGapPlanner().plan_from_graph(
        graph=graph,
        need_specs=(need_spec,),
    )
    payload = plan.to_dict()

    assert payload["bundle_id"] == "bundle_001"
    assert payload["metadata"]["producer"] == "resolution_gap_planner_v0"
    assert [entry["status"] for entry in payload["ledger_entries"]] == [
        NeedLedgerStatus.MISSING,
        NeedLedgerStatus.MISSING,
    ]
    assert payload["ledger_entries"][0]["issue_codes"] == [
        "currency_value_not_usage_quantity"
    ]
    assert [task["task_type"] for task in payload["tasks"]] == [
        InvestigationTaskType.RETRIEVE_CANDIDATE_UNITS,
        InvestigationTaskType.RETRIEVE_CANDIDATE_UNITS,
    ]
    assert payload["tasks"][0]["task_id"] == "gap_x_001_usage_amount_001"
    assert payload["tasks"][0]["target_claim_id"] == "x_001"
    assert payload["tasks"][0]["target_need_id"] == NeedType.USAGE_AMOUNT
    assert payload["tasks"][0]["allowed_atom_types"] == [
        "usage_amount",
        "currency_amount",
    ]
    assert payload["tasks"][0]["metadata"]["rejected_atom_ids"] == ["atom_currency"]
    assert payload["tasks"][0]["metadata"]["rejected_reasons"] == [
        "currency_value_not_usage_quantity"
    ]
    assert payload["tasks"][1]["allowed_atom_types"] == ["service_period", "date"]


def test_resolution_gap_planner_turns_contradiction_into_manual_review_task():
    from evidence_toolchain import (
        ClaimResolution,
        EvidenceResolutionGraph,
        InvestigationTaskType,
        Need,
        NeedLedgerStatus,
        NeedSpec,
        NeedType,
        ResolutionEdge,
        ResolutionGapPlanner,
        ResolutionRelation,
        ResolutionStatus,
    )

    need_spec = NeedSpec(
        x_id="x_002",
        needs=(
            Need(
                need_id=NeedType.USAGE_AMOUNT,
                need_type=NeedType.USAGE_AMOUNT,
                target_value=6400,
                target_unit="kWh",
            ),
        ),
    )
    graph = EvidenceResolutionGraph(
        bundle_id="bundle_001",
        claim_ids=("x_002",),
        atom_ids=("atom_usage_bad",),
        edges=(
            ResolutionEdge(
                edge_id="edge_001",
                x_id="x_002",
                atom_id="atom_usage_bad",
                relation=ResolutionRelation.CONTRADICTS,
                need_id=NeedType.USAGE_AMOUNT,
                metadata={"hard_gate": "quantity_value_mismatch"},
            ),
        ),
        resolutions=(
            ClaimResolution(
                x_id="x_002",
                status=ResolutionStatus.CONTRADICTED,
                edge_ids=("edge_001",),
                missing_need_ids=(),
            ),
        ),
    )

    plan = ResolutionGapPlanner().plan_from_graph(
        graph=graph,
        need_specs=(need_spec,),
    )
    payload = plan.to_dict()

    assert payload["ledger_entries"] == [
        {
            "x_id": "x_002",
            "need_id": "usage_amount",
            "status": NeedLedgerStatus.CONFLICT,
            "evidence_atom_ids": ["atom_usage_bad"],
            "issue_codes": ["quantity_value_mismatch"],
            "metadata": {"edge_ids": ["edge_001"], "producer": "resolution_gap_planner_v0"},
        }
    ]
    assert payload["tasks"][0]["task_id"] == "gap_x_002_usage_amount_001"
    assert payload["tasks"][0]["task_type"] == InvestigationTaskType.REQUEST_MANUAL_REVIEW
    assert payload["tasks"][0]["reason"] == "resolver_contradiction"
    assert payload["tasks"][0]["metadata"]["edge_ids"] == ["edge_001"]


def test_resolution_gap_planner_does_not_import_resolver_provider_or_frameworks():
    source = Path("src/evidence_toolchain/investigation_gaps.py").read_text(
        encoding="utf-8"
    )

    forbidden_snippets = (
        "HardGateResolver",
        "DeterministicNormalizer",
        "openai",
        "langgraph",
        "requests",
        "httpx",
    )
    for forbidden in forbidden_snippets:
        assert forbidden not in source
