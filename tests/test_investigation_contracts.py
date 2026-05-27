import json
from pathlib import Path


def test_investigation_task_result_and_budget_are_serializable_contracts():
    from evidence_toolchain import (
        EvidenceAtom,
        EvidenceAtomType,
        EvidenceUnit,
        InvestigationBudget,
        InvestigationTask,
        InvestigationTaskResult,
        InvestigationTaskStatus,
        InvestigationTaskType,
        NormalizationResult,
        NormalizationTargetKind,
        NormalizedQuantity,
        NormalizedType,
    )
    from evidence_toolchain.issues import EvidenceIssue

    task = InvestigationTask(
        task_id="task_001",
        task_type=InvestigationTaskType.INSPECT_VISUAL_ARTIFACT,
        target_claim_id="x_001",
        target_need_id="usage_amount",
        target_artifact_ids=("artifact_img_001",),
        question="경유 수량과 단위를 찾아라. 금액은 usage_amount로 보지 마라.",
        allowed_atom_types=("usage_amount", "currency_amount", "date"),
        reason="usage_amount need가 missing 상태",
        metadata={"planned_by": "fixture"},
    )
    result = InvestigationTaskResult(
        task_id="task_001",
        status=InvestigationTaskStatus.COMPLETED,
        produced_units=(
            EvidenceUnit(
                unit_id="unit_visual_001",
                artifact_id="artifact_img_001",
                unit_type="visual_observation",
                producer="fake_vlm_observer",
                text="이미지 중앙 표에 '사용량 6.4 MWh'가 보임",
                locator={"bbox": [120, 410, 380, 455]},
            ),
        ),
        produced_atoms=(
            EvidenceAtom(
                atom_id="atom_usage_001",
                atom_type=EvidenceAtomType.USAGE_AMOUNT,
                source_unit_ids=("unit_visual_001",),
                source_artifact_ids=("artifact_img_001",),
                producer="fake_vlm_observer",
                text="사용량 6.4 MWh",
                value=6.4,
                unit="MWh",
            ),
        ),
        produced_normalization_results=(
            NormalizationResult(
                target_id="atom_usage_001",
                target_kind=NormalizationTargetKind.ATOM,
                normalized_type=NormalizedType.QUANTITY,
                normalized=NormalizedQuantity(value=6400, unit="kWh", dimension="energy"),
                producer="fake_vlm_observer",
            ),
        ),
        produced_unit_ids=("unit_visual_001",),
        produced_atom_ids=("atom_usage_001",),
        produced_normalization_result_ids=("atom_usage_001",),
        issues=(
            EvidenceIssue(
                code="visual_observation_requires_review",
                severity="warning",
                message="VLM observation must be reviewed before final use.",
            ),
        ),
        metadata={"producer": "fake_vlm_observer"},
    )
    budget = InvestigationBudget(
        max_iterations=3,
        max_model_calls=5,
        max_new_units=20,
        max_new_atoms=20,
        metadata={"policy": "unit-test"},
    )

    assert task.to_dict() == {
        "task_id": "task_001",
        "task_type": "inspect_visual_artifact",
        "target_claim_id": "x_001",
        "target_need_id": "usage_amount",
        "target_artifact_ids": ["artifact_img_001"],
        "target_unit_ids": [],
        "question": "경유 수량과 단위를 찾아라. 금액은 usage_amount로 보지 마라.",
        "allowed_atom_types": ["usage_amount", "currency_amount", "date"],
        "reason": "usage_amount need가 missing 상태",
        "metadata": {"planned_by": "fixture"},
    }
    assert result.to_dict()["status"] == "completed"
    assert result.to_dict()["produced_units"][0]["unit_type"] == "visual_observation"
    assert result.to_dict()["produced_atoms"][0]["atom_type"] == "usage_amount"
    assert result.to_dict()["produced_normalization_results"][0]["normalized_type"] == "quantity"
    assert result.to_dict()["produced_atom_ids"] == ["atom_usage_001"]
    assert result.to_dict()["issues"][0]["code"] == "visual_observation_requires_review"
    assert budget.to_dict()["max_model_calls"] == 5
    json.dumps(task.to_dict(), ensure_ascii=False)
    json.dumps(result.to_dict(), ensure_ascii=False)
    json.dumps(budget.to_dict(), ensure_ascii=False)


def test_investigation_state_preserves_inputs_outputs_and_append_only_events():
    from evidence_toolchain import (
        AttachmentBundle,
        DeclaredClaim,
        EvidenceInventory,
        EvidenceResolutionGraph,
        InvestigationBudget,
        InvestigationEvent,
        InvestigationEventType,
        InvestigationState,
        InvestigationTask,
        InvestigationTaskResult,
        InvestigationTaskStatus,
        InvestigationTaskType,
        NeedLedgerEntry,
        NeedLedgerStatus,
        NeedSpec,
    )

    inventory = EvidenceInventory(
        bundle_id="bundle_001",
        attachments=(),
        artifacts=(),
        units=(),
        route_decisions=(),
    )
    claim = DeclaredClaim(x_id="x_001", fields={"amount": 6400, "unit": "kWh"})
    need_spec = NeedSpec(x_id="x_001", needs=())
    graph = EvidenceResolutionGraph(
        bundle_id="bundle_001",
        claim_ids=("x_001",),
        atom_ids=(),
    )
    task = InvestigationTask(
        task_id="task_001",
        task_type=InvestigationTaskType.RETRIEVE_CANDIDATE_UNITS,
        target_claim_id="x_001",
        target_need_id="usage_amount",
    )
    result = InvestigationTaskResult(
        task_id="task_001",
        status=InvestigationTaskStatus.NO_NEW_CLUE,
    )
    ledger = NeedLedgerEntry(
        x_id="x_001",
        need_id="usage_amount",
        status=NeedLedgerStatus.MISSING,
        evidence_atom_ids=(),
        issue_codes=("missing_required_need",),
    )
    event = InvestigationEvent(
        run_id="run_001",
        sequence=1,
        event_type=InvestigationEventType.TASK_PLANNED,
        payload={"task_id": "task_001"},
    )
    state = InvestigationState(
        run_id="run_001",
        inventory=inventory,
        claims=(claim,),
        need_specs=(need_spec,),
        atoms=(),
        normalization_results=(),
        draft_graph=graph,
        agenda=(task,),
        completed_tasks=(result,),
        clue_ledger=(ledger,),
        events=(),
        budget=InvestigationBudget(max_iterations=2),
        metadata={"bundle": AttachmentBundle(bundle_id="bundle_001", attachments=()).to_dict()},
    )

    updated = state.record_event(event)
    payload = updated.to_dict()

    assert state.events == ()
    assert updated.events == (event,)
    assert payload["run_id"] == "run_001"
    assert payload["inventory"]["bundle_id"] == "bundle_001"
    assert payload["claims"][0]["x_id"] == "x_001"
    assert payload["draft_graph"]["claim_ids"] == ["x_001"]
    assert payload["agenda"][0]["task_type"] == "retrieve_candidate_units"
    assert payload["completed_tasks"][0]["status"] == "no_new_clue"
    assert payload["clue_ledger"][0]["status"] == "missing"
    assert payload["events"][0]["event_type"] == "task_planned"
    assert payload["budget"]["max_iterations"] == 2
    json.dumps(payload, ensure_ascii=False)


def test_investigation_task_and_ledger_vocabularies_are_closed_for_v0():
    from evidence_toolchain import (
        InvestigationEventType,
        InvestigationTaskStatus,
        InvestigationTaskType,
        NeedLedgerStatus,
    )

    assert InvestigationTaskType.ALL == (
        "retrieve_candidate_units",
        "atomize_unit_cluster",
        "inspect_visual_artifact",
        "inspect_visual_region",
        "normalize_candidate",
        "request_manual_review",
        "stop",
    )
    assert InvestigationTaskStatus.ALL == (
        "planned",
        "completed",
        "failed",
        "no_new_clue",
        "manual_review_required",
        "skipped",
    )
    assert NeedLedgerStatus.ALL == (
        "missing",
        "partial",
        "satisfied",
        "conflict",
        "ambiguous",
        "needs_review",
    )
    assert InvestigationEventType.ALL == (
        "task_planned",
        "task_started",
        "task_completed",
        "state_updated",
        "budget_exhausted",
        "manual_review_requested",
        "stopped",
    )
    assert InvestigationTaskType.is_core_type("inspect_visual_region") is True
    assert InvestigationTaskType.is_core_type("resolver_authority") is False
    assert NeedLedgerStatus.is_core_status("satisfied") is True
    assert InvestigationEventType.is_core_type("llm_final_verdict") is False


def test_investigation_contract_does_not_import_provider_or_framework_adapters():
    source = Path("src/evidence_toolchain/investigation.py").read_text(encoding="utf-8")

    forbidden_snippets = (
        "openai",
        "langgraph",
        "LLMPlannerPort",
        "VLMObserverPort",
        "LocalInvestigationRunner",
        "HardGateResolver",
    )
    for forbidden in forbidden_snippets:
        assert forbidden not in source
