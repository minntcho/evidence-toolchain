from pathlib import Path
from dataclasses import replace


def _state_with_inventory(*units):
    from evidence_toolchain import EvidenceInventory, InvestigationBudget, InvestigationState

    return InvestigationState(
        run_id="run_001",
        inventory=EvidenceInventory(
            bundle_id="bundle_001",
            attachments=(),
            artifacts=(),
            units=tuple(units),
            route_decisions=(),
        ),
        claims=(),
        need_specs=(),
        atoms=(),
        normalization_results=(),
        budget=InvestigationBudget(max_iterations=3, max_model_calls=3),
    )


def test_local_investigation_runner_plans_tasks_when_agenda_is_empty():
    from evidence_toolchain import (
        FakeLLMPlanner,
        InvestigationPlan,
        InvestigationTask,
        InvestigationTaskType,
        InvestigationEventType,
        LocalInvestigationRunner,
    )

    task = InvestigationTask(
        task_id="task_001",
        task_type=InvestigationTaskType.INSPECT_VISUAL_ARTIFACT,
        target_artifact_ids=("artifact_image_001",),
        question="사용량 후보를 찾아라.",
        reason="usage_amount need가 missing 상태",
    )
    runner = LocalInvestigationRunner(
        planner=FakeLLMPlanner(
            plan=InvestigationPlan(tasks=(task,), producer="fake_llm_planner")
        )
    )

    updated = runner.run_once(_state_with_inventory())
    payload = updated.to_dict()

    assert payload["agenda"][0]["task_id"] == "task_001"
    assert payload["completed_tasks"] == []
    assert payload["events"][0]["event_type"] == InvestigationEventType.TASK_PLANNED
    assert payload["events"][0]["payload"]["task_ids"] == ["task_001"]
    assert payload["metadata"]["runner"] == "local_investigation_runner_v0"


def test_local_investigation_runner_executes_visual_task_with_fake_vlm_observer():
    from evidence_toolchain import (
        EvidenceAtom,
        EvidenceAtomType,
        EvidenceUnit,
        FakeLLMPlanner,
        FakeVLMObserver,
        InvestigationPlan,
        InvestigationTask,
        InvestigationTaskResult,
        InvestigationTaskStatus,
        InvestigationTaskType,
        LocalInvestigationRunner,
        NormalizationResult,
        NormalizationTargetKind,
        NormalizedQuantity,
        NormalizedType,
    )

    task = InvestigationTask(
        task_id="task_visual",
        task_type=InvestigationTaskType.INSPECT_VISUAL_ARTIFACT,
        target_artifact_ids=("artifact_image_001",),
    )
    result = InvestigationTaskResult(
        task_id="task_visual",
        status=InvestigationTaskStatus.COMPLETED,
        produced_units=(
            EvidenceUnit(
                unit_id="unit_visual_001",
                artifact_id="artifact_image_001",
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
                source_artifact_ids=("artifact_image_001",),
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
    )
    runner = LocalInvestigationRunner(
        planner=FakeLLMPlanner(plan=InvestigationPlan(tasks=())),
        vlm_observer=FakeVLMObserver(result=result),
        artifact_bytes={"artifact_image_001": b"fake-image"},
    )
    state = _state_with_inventory()
    state = replace(state, agenda=(task,))

    updated = runner.run_once(state)
    payload = updated.to_dict()

    assert payload["agenda"] == []
    assert payload["inventory"]["units"][0]["unit_id"] == "unit_visual_001"
    assert payload["inventory"]["units"][0]["unit_type"] == "visual_observation"
    assert payload["atoms"][0]["atom_id"] == "atom_usage_001"
    assert payload["normalization_results"][0]["target_id"] == "atom_usage_001"
    assert payload["completed_tasks"][0]["task_id"] == "task_visual"
    assert payload["completed_tasks"][0]["produced_atom_ids"] == ["atom_usage_001"]
    assert payload["completed_tasks"][0]["produced_normalization_result_ids"] == [
        "atom_usage_001"
    ]
    assert [event["event_type"] for event in payload["events"]] == [
        "task_started",
        "task_completed",
    ]


def test_local_investigation_runner_executes_atomizer_task_and_appends_atoms():
    from evidence_toolchain import (
        AtomizerResult,
        EvidenceAtom,
        EvidenceAtomType,
        EvidenceUnit,
        FakeLLMAtomizer,
        FakeLLMPlanner,
        InvestigationPlan,
        InvestigationTask,
        InvestigationTaskType,
        LocalInvestigationRunner,
    )

    unit = EvidenceUnit(
        unit_id="unit_001",
        artifact_id="artifact_001",
        unit_type="text_span",
        producer="test_reader",
        text="사용량 6.4 MWh",
    )
    atom = EvidenceAtom(
        atom_id="atom_001",
        atom_type=EvidenceAtomType.USAGE_AMOUNT,
        source_unit_ids=("unit_001",),
        source_artifact_ids=("artifact_001",),
        producer="fake_llm_atomizer",
        text="사용량 6.4 MWh",
        value=6.4,
        unit="MWh",
    )
    task = InvestigationTask(
        task_id="task_atomize",
        task_type=InvestigationTaskType.ATOMIZE_UNIT_CLUSTER,
        target_unit_ids=("unit_001",),
    )
    runner = LocalInvestigationRunner(
        planner=FakeLLMPlanner(plan=InvestigationPlan(tasks=())),
        llm_atomizer=FakeLLMAtomizer(
            result=AtomizerResult(bundle_id="bundle_001", atoms=(atom,))
        ),
    )
    state = _state_with_inventory(unit)
    state = replace(state, agenda=(task,))

    updated = runner.run_once(state)
    payload = updated.to_dict()

    assert payload["atoms"][0]["atom_id"] == "atom_001"
    assert payload["completed_tasks"][0]["status"] == "completed"
    assert payload["completed_tasks"][0]["produced_atom_ids"] == ["atom_001"]
    assert "relation" not in payload["completed_tasks"][0]


def test_local_investigation_runner_rejects_model_atoms_without_allowed_type_or_provenance():
    from evidence_toolchain import (
        AtomizerResult,
        EvidenceAtom,
        EvidenceAtomType,
        EvidenceUnit,
        FakeLLMAtomizer,
        FakeLLMPlanner,
        InvestigationPlan,
        InvestigationTask,
        InvestigationTaskType,
        LocalInvestigationRunner,
    )

    unit = EvidenceUnit(
        unit_id="unit_001",
        artifact_id="artifact_001",
        unit_type="text_span",
        producer="test_reader",
        text="사용량 6.4 MWh / 금액 120000 KRW",
    )
    valid_atom = EvidenceAtom(
        atom_id="atom_usage_001",
        atom_type=EvidenceAtomType.USAGE_AMOUNT,
        source_unit_ids=("unit_001",),
        source_artifact_ids=("artifact_001",),
        producer="fake_llm_atomizer",
        text="사용량 6.4 MWh",
        value=6.4,
        unit="MWh",
    )
    disallowed_atom = EvidenceAtom(
        atom_id="atom_currency_001",
        atom_type=EvidenceAtomType.CURRENCY_AMOUNT,
        source_unit_ids=("unit_001",),
        source_artifact_ids=("artifact_001",),
        producer="fake_llm_atomizer",
        text="금액 120000 KRW",
        value=120000,
        unit="KRW",
    )
    missing_provenance_atom = EvidenceAtom(
        atom_id="atom_no_source_001",
        atom_type=EvidenceAtomType.USAGE_AMOUNT,
        source_unit_ids=(),
        source_artifact_ids=(),
        producer="fake_llm_atomizer",
        text="6.4 MWh",
        value=6.4,
        unit="MWh",
    )
    unknown_type_atom = EvidenceAtom(
        atom_id="atom_unknown_type_001",
        atom_type="llm_freeform_amount",
        source_unit_ids=("unit_001",),
        source_artifact_ids=("artifact_001",),
        producer="fake_llm_atomizer",
        text="6.4 MWh",
        value=6.4,
        unit="MWh",
    )
    task = InvestigationTask(
        task_id="task_atomize",
        task_type=InvestigationTaskType.ATOMIZE_UNIT_CLUSTER,
        target_unit_ids=("unit_001",),
        allowed_atom_types=(EvidenceAtomType.USAGE_AMOUNT,),
    )
    runner = LocalInvestigationRunner(
        planner=FakeLLMPlanner(plan=InvestigationPlan(tasks=())),
        llm_atomizer=FakeLLMAtomizer(
            result=AtomizerResult(
                bundle_id="bundle_001",
                atoms=(
                    valid_atom,
                    disallowed_atom,
                    missing_provenance_atom,
                    unknown_type_atom,
                ),
            )
        ),
    )
    state = _state_with_inventory(unit)
    state = replace(state, agenda=(task,))

    updated = runner.run_once(state)
    payload = updated.to_dict()

    assert [atom["atom_id"] for atom in payload["atoms"]] == ["atom_usage_001"]
    assert payload["completed_tasks"][0]["produced_atom_ids"] == ["atom_usage_001"]
    assert [issue["code"] for issue in payload["completed_tasks"][0]["issues"]] == [
        "model_output_atom_type_not_allowed",
        "model_output_missing_provenance",
        "model_output_atom_type_unknown",
    ]


def test_local_investigation_runner_filters_visual_observer_atoms_with_same_guardrails():
    from evidence_toolchain import (
        EvidenceAtom,
        EvidenceAtomType,
        FakeLLMPlanner,
        FakeVLMObserver,
        InvestigationPlan,
        InvestigationTask,
        InvestigationTaskResult,
        InvestigationTaskStatus,
        InvestigationTaskType,
        LocalInvestigationRunner,
    )

    valid_atom = EvidenceAtom(
        atom_id="atom_date_001",
        atom_type=EvidenceAtomType.DATE,
        source_unit_ids=(),
        source_artifact_ids=("artifact_image_001",),
        producer="fake_vlm_observer",
        text="2025-03-31",
        value="2025-03-31",
    )
    disallowed_atom = EvidenceAtom(
        atom_id="atom_currency_001",
        atom_type=EvidenceAtomType.CURRENCY_AMOUNT,
        source_unit_ids=(),
        source_artifact_ids=("artifact_image_001",),
        producer="fake_vlm_observer",
        text="120000 KRW",
        value=120000,
        unit="KRW",
    )
    task = InvestigationTask(
        task_id="task_visual",
        task_type=InvestigationTaskType.INSPECT_VISUAL_ARTIFACT,
        target_artifact_ids=("artifact_image_001",),
        allowed_atom_types=(EvidenceAtomType.DATE,),
    )
    runner = LocalInvestigationRunner(
        planner=FakeLLMPlanner(plan=InvestigationPlan(tasks=())),
        vlm_observer=FakeVLMObserver(
            result=InvestigationTaskResult(
                task_id="task_visual",
                status=InvestigationTaskStatus.COMPLETED,
                produced_atoms=(valid_atom, disallowed_atom),
            )
        ),
        artifact_bytes={"artifact_image_001": b"fake-image"},
    )
    state = replace(_state_with_inventory(), agenda=(task,))

    updated = runner.run_once(state)
    payload = updated.to_dict()

    assert [atom["atom_id"] for atom in payload["atoms"]] == ["atom_date_001"]
    assert payload["completed_tasks"][0]["produced_atom_ids"] == ["atom_date_001"]
    assert payload["completed_tasks"][0]["issues"][0]["code"] == (
        "model_output_atom_type_not_allowed"
    )


def test_local_investigation_runner_stops_when_iteration_budget_is_exhausted():
    from evidence_toolchain import (
        FakeLLMPlanner,
        InvestigationBudget,
        InvestigationPlan,
        InvestigationTaskResult,
        InvestigationTaskStatus,
        LocalInvestigationRunner,
    )

    state = _state_with_inventory()
    state = replace(
        state,
        budget=InvestigationBudget(max_iterations=1),
        completed_tasks=(
            InvestigationTaskResult(
                task_id="task_done",
                status=InvestigationTaskStatus.COMPLETED,
            ),
        ),
    )
    runner = LocalInvestigationRunner(
        planner=FakeLLMPlanner(plan=InvestigationPlan(tasks=()))
    )

    updated = runner.run_once(state)
    payload = updated.to_dict()

    assert payload["events"][0]["event_type"] == "budget_exhausted"
    assert payload["metadata"]["stop_reason"] == "max_iterations_exhausted"


def test_local_investigation_runner_does_not_import_provider_framework_or_resolver():
    source = Path("src/evidence_toolchain/investigation_runner.py").read_text(encoding="utf-8")

    forbidden_snippets = (
        "openai",
        "langgraph",
        "requests",
        "httpx",
        "HardGateResolver",
        "DeterministicNormalizer",
    )
    for forbidden in forbidden_snippets:
        assert forbidden not in source
