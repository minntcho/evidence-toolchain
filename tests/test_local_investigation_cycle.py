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


def test_local_investigation_runner_run_agenda_does_not_plan_when_agenda_is_empty():
    from evidence_toolchain import LocalInvestigationRunner

    state = _state_with_inventory()
    runner = LocalInvestigationRunner(planner=_NoPlanner())

    updated = runner.run_agenda(state, max_steps=2)

    assert updated is state
