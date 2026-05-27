from dataclasses import replace


def _state_with_inventory(*units):
    from evidence_toolchain import EvidenceInventory, InvestigationBudget, InvestigationState

    return InvestigationState(
        run_id="run_cycle_001",
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
        budget=InvestigationBudget(max_iterations=5),
    )


class _NoPlanner:
    producer = "no_planner"

    def plan_next_tasks(self, state):
        raise AssertionError("run_agenda must not ask the planner for new tasks")


class _UnitEchoAtomizer:
    producer = "unit_echo_atomizer"

    def atomize(self, task, units):
        from evidence_toolchain import AtomizerResult, EvidenceAtom, EvidenceAtomType

        assert task.task_type == "atomize_unit_cluster"
        assert [unit.unit_id for unit in units] == ["unit_usage"]
        unit = units[0]
        return AtomizerResult(
            bundle_id="bundle_001",
            atoms=(
                EvidenceAtom(
                    atom_id="atom_from_cycle_001",
                    atom_type=EvidenceAtomType.USAGE_AMOUNT,
                    source_unit_ids=(unit.unit_id,),
                    source_artifact_ids=(unit.artifact_id,),
                    producer=self.producer,
                    text=unit.text,
                    value=6.4,
                    unit="MWh",
                ),
            ),
        )


class _StuckRunner:
    def run_agenda(self, state, *, max_steps):
        from evidence_toolchain import LocalInvestigationRunner

        class Runner(LocalInvestigationRunner):
            def run_once(self, state):
                return state

        return Runner(planner=_NoPlanner()).run_agenda(state, max_steps=max_steps)


def test_local_investigation_runner_run_agenda_completes_retrieve_to_atomize_cycle():
    from evidence_toolchain import (
        CandidateUnitRetriever,
        EvidenceAtomType,
        EvidenceUnit,
        InvestigationTask,
        InvestigationTaskType,
        LocalInvestigationRunner,
        Need,
        NeedSpec,
        NeedType,
    )

    unit = EvidenceUnit(
        unit_id="unit_usage",
        artifact_id="artifact_pdf_page_1",
        unit_type="text_span",
        producer="pdfplumber_extract",
        text="전력 사용량 6.4 MWh",
    )
    retrieve_task = InvestigationTask(
        task_id="gap_x_001_usage_amount_001",
        task_type=InvestigationTaskType.RETRIEVE_CANDIDATE_UNITS,
        target_claim_id="x_001",
        target_need_id=NeedType.USAGE_AMOUNT,
        allowed_atom_types=(
            EvidenceAtomType.USAGE_AMOUNT,
            EvidenceAtomType.CURRENCY_AMOUNT,
        ),
    )
    state = replace(
        _state_with_inventory(unit),
        need_specs=(
            NeedSpec(
                x_id="x_001",
                needs=(
                    Need(
                        need_id=NeedType.USAGE_AMOUNT,
                        need_type=NeedType.USAGE_AMOUNT,
                        target_value=6400,
                        target_unit="kWh",
                        acceptable_units=("kWh", "MWh"),
                    ),
                ),
            ),
        ),
        agenda=(retrieve_task,),
    )
    runner = LocalInvestigationRunner(
        planner=_NoPlanner(),
        unit_retriever=CandidateUnitRetriever(),
        llm_atomizer=_UnitEchoAtomizer(),
    )

    updated = runner.run_agenda(state, max_steps=2)
    payload = updated.to_dict()

    assert payload["agenda"] == []
    assert [task["task_id"] for task in payload["completed_tasks"]] == [
        "gap_x_001_usage_amount_001",
        "gap_x_001_usage_amount_001_atomize_001",
    ]
    assert payload["completed_tasks"][0]["metadata"]["selected_unit_ids"] == [
        "unit_usage"
    ]
    assert payload["completed_tasks"][1]["produced_atom_ids"] == [
        "atom_from_cycle_001"
    ]
    assert payload["atoms"] == [
        {
            "atom_id": "atom_from_cycle_001",
            "atom_type": "usage_amount",
            "source_unit_ids": ["unit_usage"],
            "source_artifact_ids": ["artifact_pdf_page_1"],
            "producer": "unit_echo_atomizer",
            "text": "전력 사용량 6.4 MWh",
            "label": None,
            "value": 6.4,
            "unit": "MWh",
            "normalized": None,
            "normalization_hint": {},
            "confidence": None,
            "metadata": {},
            "issues": [],
        }
    ]
    assert payload["normalization_results"] == []
    assert [event["event_type"] for event in payload["events"]] == [
        "task_started",
        "task_completed",
        "task_planned",
        "task_started",
        "task_completed",
    ]


def test_local_investigation_runner_run_agenda_completes_retrieve_atomize_normalize_cycle():
    from evidence_toolchain import (
        CandidateUnitRetriever,
        DeterministicNormalizer,
        EvidenceAtomType,
        EvidenceUnit,
        InvestigationTask,
        InvestigationTaskType,
        LocalInvestigationRunner,
        Need,
        NeedSpec,
        NeedType,
        NormalizedType,
    )

    unit = EvidenceUnit(
        unit_id="unit_usage",
        artifact_id="artifact_pdf_page_1",
        unit_type="text_span",
        producer="pdfplumber_extract",
        text="electricity usage 6.4 MWh",
    )
    retrieve_task = InvestigationTask(
        task_id="gap_x_001_usage_amount_001",
        task_type=InvestigationTaskType.RETRIEVE_CANDIDATE_UNITS,
        target_claim_id="x_001",
        target_need_id=NeedType.USAGE_AMOUNT,
        allowed_atom_types=(
            EvidenceAtomType.USAGE_AMOUNT,
            EvidenceAtomType.CURRENCY_AMOUNT,
        ),
    )
    state = replace(
        _state_with_inventory(unit),
        need_specs=(
            NeedSpec(
                x_id="x_001",
                needs=(
                    Need(
                        need_id=NeedType.USAGE_AMOUNT,
                        need_type=NeedType.USAGE_AMOUNT,
                        target_value=6400,
                        target_unit="kWh",
                        acceptable_units=("kWh", "MWh"),
                    ),
                ),
            ),
        ),
        agenda=(retrieve_task,),
    )
    runner = LocalInvestigationRunner(
        planner=_NoPlanner(),
        unit_retriever=CandidateUnitRetriever(),
        llm_atomizer=_UnitEchoAtomizer(),
        normalizer=DeterministicNormalizer(),
    )

    updated = runner.run_agenda(state, max_steps=3)
    payload = updated.to_dict()

    assert payload["agenda"] == []
    assert [task["task_id"] for task in payload["completed_tasks"]] == [
        "gap_x_001_usage_amount_001",
        "gap_x_001_usage_amount_001_atomize_001",
        "gap_x_001_usage_amount_001_atomize_001_normalize_001",
    ]
    assert payload["completed_tasks"][2]["metadata"] == {
        "producer": "deterministic_normalizer_v0"
    }
    assert payload["normalization_results"][0]["target_id"] == "atom_from_cycle_001"
    assert payload["normalization_results"][0]["normalized_type"] == NormalizedType.QUANTITY
    assert payload["normalization_results"][0]["normalized"]["value"] == 6400
    assert payload["normalization_results"][0]["normalized"]["unit"] == "kWh"
    assert payload["events"][5] == {
        "run_id": "run_cycle_001",
        "sequence": 6,
        "event_type": "task_planned",
        "payload": {
            "task_ids": ["gap_x_001_usage_amount_001_atomize_001_normalize_001"],
            "source_task_id": "gap_x_001_usage_amount_001_atomize_001",
        },
    }


def test_local_investigation_runner_run_agenda_refreshes_draft_graph_after_normalization():
    from evidence_toolchain import (
        CandidateUnitRetriever,
        DeclaredClaim,
        DeterministicNormalizer,
        EvidenceAtomType,
        EvidenceUnit,
        HardGateResolver,
        InvestigationTask,
        InvestigationTaskType,
        LocalInvestigationRunner,
        Need,
        NeedSpec,
        NeedType,
        ResolutionStatus,
    )

    unit = EvidenceUnit(
        unit_id="unit_usage",
        artifact_id="artifact_pdf_page_1",
        unit_type="text_span",
        producer="pdfplumber_extract",
        text="electricity usage 6.4 MWh",
    )
    claim = DeclaredClaim(
        x_id="x_001",
        fields={"activity": "electricity", "amount": 6400, "unit": "kWh"},
    )
    usage_need = Need(
        need_id=NeedType.USAGE_AMOUNT,
        need_type=NeedType.USAGE_AMOUNT,
        target_value=6400,
        target_unit="kWh",
        acceptable_units=("kWh", "MWh"),
    )
    retrieve_task = InvestigationTask(
        task_id="gap_x_001_usage_amount_001",
        task_type=InvestigationTaskType.RETRIEVE_CANDIDATE_UNITS,
        target_claim_id="x_001",
        target_need_id=NeedType.USAGE_AMOUNT,
        allowed_atom_types=(
            EvidenceAtomType.USAGE_AMOUNT,
            EvidenceAtomType.CURRENCY_AMOUNT,
        ),
    )
    normalizer = DeterministicNormalizer()
    state = replace(
        _state_with_inventory(unit),
        claims=(claim,),
        need_specs=(NeedSpec(x_id="x_001", needs=(usage_need,)),),
        normalization_results=normalizer.normalize_claim_need(usage_need),
        agenda=(retrieve_task,),
    )
    runner = LocalInvestigationRunner(
        planner=_NoPlanner(),
        unit_retriever=CandidateUnitRetriever(),
        llm_atomizer=_UnitEchoAtomizer(),
        normalizer=normalizer,
        resolver=HardGateResolver(),
    )

    updated = runner.run_agenda(state, max_steps=3)
    payload = updated.to_dict()

    assert payload["draft_graph"]["metadata"]["producer"] == "hard_gate_resolver_v0"
    assert payload["draft_graph"]["resolutions"][0]["status"] == (
        ResolutionStatus.SUPPORTED_AFTER_UNIT_NORMALIZATION
    )
    assert payload["draft_graph"]["resolutions"][0]["supporting_atom_ids"] == [
        "atom_from_cycle_001"
    ]
    assert payload["events"][-1] == {
        "run_id": "run_cycle_001",
        "sequence": 9,
        "event_type": "state_updated",
        "payload": {
            "draft_graph_claim_ids": ["x_001"],
            "producer": "hard_gate_resolver_v0",
            "source_task_id": "gap_x_001_usage_amount_001_atomize_001_normalize_001",
        },
    }


def test_local_investigation_runner_run_agenda_can_normalize_queued_atom_candidates():
    from evidence_toolchain import (
        DeterministicNormalizer,
        EvidenceAtomType,
        EvidenceUnit,
        InvestigationTask,
        InvestigationTaskType,
        LocalInvestigationRunner,
        NormalizedType,
    )

    unit = EvidenceUnit(
        unit_id="unit_usage",
        artifact_id="artifact_pdf_page_1",
        unit_type="text_span",
        producer="pdfplumber_extract",
        text="electricity usage 6.4 MWh",
    )
    atomize_task = InvestigationTask(
        task_id="task_atomize_usage",
        task_type=InvestigationTaskType.ATOMIZE_UNIT_CLUSTER,
        target_unit_ids=("unit_usage",),
        allowed_atom_types=(EvidenceAtomType.USAGE_AMOUNT,),
    )
    normalize_task = InvestigationTask(
        task_id="task_normalize_usage",
        task_type=InvestigationTaskType.NORMALIZE_CANDIDATE,
        metadata={"target_atom_ids": ("atom_from_cycle_001",)},
    )
    state = replace(
        _state_with_inventory(unit),
        agenda=(atomize_task, normalize_task),
    )
    runner = LocalInvestigationRunner(
        planner=_NoPlanner(),
        llm_atomizer=_UnitEchoAtomizer(),
        normalizer=DeterministicNormalizer(),
    )

    updated = runner.run_agenda(state, max_steps=2)
    payload = updated.to_dict()

    assert payload["agenda"] == []
    assert [task["task_id"] for task in payload["completed_tasks"]] == [
        "task_atomize_usage",
        "task_normalize_usage",
    ]
    assert payload["completed_tasks"][1]["produced_normalization_result_ids"] == [
        "atom_from_cycle_001"
    ]
    assert payload["completed_tasks"][1]["metadata"] == {
        "producer": "deterministic_normalizer_v0"
    }
    assert payload["normalization_results"] == [
        {
            "target_id": "atom_from_cycle_001",
            "target_kind": "atom",
            "normalized_type": NormalizedType.QUANTITY,
            "normalized": {
                "value": 6400,
                "unit": "kWh",
                "dimension": "energy",
                "source_value": 6.4,
                "source_unit": "MWh",
                "original_text": "electricity usage 6.4 MWh",
                "metadata": {"conversion": "MWh_to_kWh"},
            },
            "producer": "deterministic_normalizer_v0",
            "confidence": 1.0,
            "issues": [],
            "metadata": {},
        }
    ]


def test_local_investigation_runner_run_agenda_does_not_plan_when_agenda_is_empty():
    from evidence_toolchain import LocalInvestigationRunner

    state = _state_with_inventory()
    runner = LocalInvestigationRunner(planner=_NoPlanner())

    updated = runner.run_agenda(state, max_steps=2)

    assert updated is state


def test_local_investigation_runner_run_agenda_stops_on_repeated_task_fingerprint():
    from evidence_toolchain import (
        InvestigationTask,
        InvestigationTaskType,
        LocalInvestigationRunner,
    )

    task_a = InvestigationTask(
        task_id="task_a",
        task_type=InvestigationTaskType.REQUEST_MANUAL_REVIEW,
        target_claim_id="x_001",
        target_need_id="usage_amount",
        reason="same_gap",
    )
    task_b = InvestigationTask(
        task_id="task_b",
        task_type=InvestigationTaskType.REQUEST_MANUAL_REVIEW,
        target_claim_id="x_001",
        target_need_id="usage_amount",
        reason="same_gap",
    )
    state = replace(_state_with_inventory(), agenda=(task_a, task_b))
    runner = LocalInvestigationRunner(planner=_NoPlanner())

    updated = runner.run_agenda(state, max_steps=3)
    payload = updated.to_dict()

    assert [task["task_id"] for task in payload["completed_tasks"]] == ["task_a"]
    assert payload["agenda"][0]["task_id"] == "task_b"
    assert payload["metadata"]["stop_reason"] == "repeated_task_detected"
    assert payload["events"][-1]["event_type"] == "stopped"
    assert payload["events"][-1]["payload"] == {
        "reason": "repeated_task_detected",
        "task_id": "task_b",
    }


def test_local_investigation_runner_run_agenda_stops_when_no_progress_is_made():
    from evidence_toolchain import InvestigationTask, InvestigationTaskType

    task = InvestigationTask(
        task_id="task_stuck",
        task_type=InvestigationTaskType.REQUEST_MANUAL_REVIEW,
    )
    state = replace(_state_with_inventory(), agenda=(task,))

    updated = _StuckRunner().run_agenda(state, max_steps=3)
    payload = updated.to_dict()

    assert payload["agenda"][0]["task_id"] == "task_stuck"
    assert payload["metadata"]["stop_reason"] == "no_progress_detected"
    assert payload["events"][-1]["event_type"] == "stopped"
    assert payload["events"][-1]["payload"] == {
        "reason": "no_progress_detected",
        "task_id": "task_stuck",
    }


def test_local_investigation_runner_run_agenda_stops_on_iteration_budget():
    from evidence_toolchain import (
        CandidateUnitRetriever,
        EvidenceAtomType,
        EvidenceUnit,
        InvestigationBudget,
        InvestigationTask,
        InvestigationTaskType,
        LocalInvestigationRunner,
        Need,
        NeedSpec,
        NeedType,
    )

    unit = EvidenceUnit(
        unit_id="unit_usage",
        artifact_id="artifact_pdf_page_1",
        unit_type="text_span",
        producer="pdfplumber_extract",
        text="전력 사용량 6.4 MWh",
    )
    retrieve_task = InvestigationTask(
        task_id="gap_x_001_usage_amount_001",
        task_type=InvestigationTaskType.RETRIEVE_CANDIDATE_UNITS,
        target_claim_id="x_001",
        target_need_id=NeedType.USAGE_AMOUNT,
        allowed_atom_types=(
            EvidenceAtomType.USAGE_AMOUNT,
            EvidenceAtomType.CURRENCY_AMOUNT,
        ),
    )
    state = replace(
        _state_with_inventory(unit),
        budget=InvestigationBudget(max_iterations=1),
        need_specs=(
            NeedSpec(
                x_id="x_001",
                needs=(
                    Need(
                        need_id=NeedType.USAGE_AMOUNT,
                        need_type=NeedType.USAGE_AMOUNT,
                        target_unit="kWh",
                        acceptable_units=("kWh", "MWh"),
                    ),
                ),
            ),
        ),
        agenda=(retrieve_task,),
    )
    runner = LocalInvestigationRunner(
        planner=_NoPlanner(),
        unit_retriever=CandidateUnitRetriever(),
        llm_atomizer=_UnitEchoAtomizer(),
    )

    updated = runner.run_agenda(state, max_steps=3)
    payload = updated.to_dict()

    assert [task["task_id"] for task in payload["completed_tasks"]] == [
        "gap_x_001_usage_amount_001"
    ]
    assert payload["agenda"][0]["task_type"] == "atomize_unit_cluster"
    assert payload["metadata"]["stop_reason"] == "max_iterations_exhausted"
    assert payload["events"][-1]["event_type"] == "budget_exhausted"
