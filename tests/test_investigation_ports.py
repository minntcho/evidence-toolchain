import json
from pathlib import Path


def _empty_state():
    from evidence_toolchain import EvidenceInventory, InvestigationState

    return InvestigationState(
        run_id="run_001",
        inventory=EvidenceInventory(
            bundle_id="bundle_001",
            attachments=(),
            artifacts=(),
            units=(),
            route_decisions=(),
        ),
        claims=(),
        need_specs=(),
        atoms=(),
        normalization_results=(),
    )


def test_llm_planner_port_returns_investigation_plan_contract():
    from evidence_toolchain import (
        FakeLLMPlanner,
        InvestigationPlan,
        InvestigationTask,
        InvestigationTaskType,
        LLMPlannerPort,
    )

    task = InvestigationTask(
        task_id="task_001",
        task_type=InvestigationTaskType.RETRIEVE_CANDIDATE_UNITS,
        target_claim_id="x_001",
        target_need_id="usage_amount",
        reason="usage_amount need가 missing 상태",
    )
    plan = InvestigationPlan(
        tasks=(task,),
        stop_reason=None,
        producer="fake_llm_planner",
        metadata={"source": "unit-test"},
    )
    planner = FakeLLMPlanner(plan=plan)

    assert isinstance(planner, LLMPlannerPort)
    result = planner.plan_next_tasks(_empty_state())
    payload = result.to_dict()

    assert payload == {
        "tasks": [
            {
                "task_id": "task_001",
                "task_type": "retrieve_candidate_units",
                "target_claim_id": "x_001",
                "target_need_id": "usage_amount",
                "target_artifact_ids": [],
                "target_unit_ids": [],
                "question": None,
                "allowed_atom_types": [],
                "reason": "usage_amount need가 missing 상태",
                "metadata": {},
            }
        ],
        "stop_reason": None,
        "producer": "fake_llm_planner",
        "issues": [],
        "metadata": {"source": "unit-test"},
    }
    json.dumps(payload, ensure_ascii=False)


def test_fake_vlm_observer_returns_task_result_without_authorizing_resolution():
    from evidence_toolchain import (
        FakeVLMObserver,
        InvestigationTask,
        InvestigationTaskResult,
        InvestigationTaskStatus,
        InvestigationTaskType,
        VLMObserverPort,
    )

    task = InvestigationTask(
        task_id="task_visual",
        task_type=InvestigationTaskType.INSPECT_VISUAL_ARTIFACT,
        target_artifact_ids=("artifact_image_001",),
        question="사용량 후보를 찾아라.",
        allowed_atom_types=("usage_amount", "currency_amount"),
    )
    result = InvestigationTaskResult(
        task_id="task_visual",
        status=InvestigationTaskStatus.COMPLETED,
        produced_unit_ids=("unit_visual_001",),
        produced_atom_ids=("atom_usage_001",),
        metadata={"producer": "fake_vlm_observer"},
    )
    observer = FakeVLMObserver(result=result)

    assert isinstance(observer, VLMObserverPort)
    payload = observer.inspect(task, artifact_bytes=b"fake-image").to_dict()

    assert payload["status"] == "completed"
    assert payload["produced_atom_ids"] == ["atom_usage_001"]
    assert "relation" not in payload
    assert "status_authority" not in payload


def test_fake_llm_atomizer_and_normalizer_ports_return_existing_contracts():
    from evidence_toolchain import (
        AtomizerResult,
        EvidenceAtom,
        EvidenceAtomType,
        EvidenceUnit,
        FakeLLMAtomizer,
        FakeLLMNormalizer,
        InvestigationTask,
        InvestigationTaskType,
        LLMAtomizerPort,
        LLMNormalizerPort,
        NormalizationResult,
        NormalizationTargetKind,
        NormalizedQuantity,
        NormalizedType,
    )

    task = InvestigationTask(
        task_id="task_atomize",
        task_type=InvestigationTaskType.ATOMIZE_UNIT_CLUSTER,
        target_unit_ids=("unit_001",),
        allowed_atom_types=(EvidenceAtomType.USAGE_AMOUNT,),
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
    atomizer = FakeLLMAtomizer(result=AtomizerResult(bundle_id="bundle_001", atoms=(atom,)))
    normalization = NormalizationResult(
        target_id="atom_001",
        target_kind=NormalizationTargetKind.ATOM,
        normalized_type=NormalizedType.QUANTITY,
        normalized=NormalizedQuantity(value=6400, unit="kWh", dimension="energy"),
        producer="fake_llm_normalizer",
    )
    normalizer = FakeLLMNormalizer(results=(normalization,))

    assert isinstance(atomizer, LLMAtomizerPort)
    assert isinstance(normalizer, LLMNormalizerPort)
    assert atomizer.atomize(task, units=(unit,)).atoms == (atom,)
    assert normalizer.normalize(task, atoms=(atom,)) == (normalization,)


def test_resolver_port_accepts_hard_gate_resolver_contract_without_runner_coupling():
    from evidence_toolchain import (
        EvidenceInventory,
        HardGateResolver,
        ResolverPort,
    )

    resolver = HardGateResolver()

    assert isinstance(resolver, ResolverPort)
    graph = resolver.resolve(
        bundle_id=EvidenceInventory(
            bundle_id="bundle_001",
            attachments=(),
            artifacts=(),
            units=(),
            route_decisions=(),
        ).bundle_id,
        claims=(),
        need_specs=(),
        atoms=(),
        normalization_results=(),
    )
    assert graph.to_dict()["metadata"]["producer"] == "hard_gate_resolver_v0"


def test_investigation_ports_do_not_import_real_provider_or_framework_packages():
    source = Path("src/evidence_toolchain/investigation_ports.py").read_text(encoding="utf-8")

    forbidden_snippets = (
        "openai",
        "langgraph",
        "requests",
        "httpx",
        "HardGateResolver",
        "LocalInvestigationRunner",
    )
    for forbidden in forbidden_snippets:
        assert forbidden not in source
