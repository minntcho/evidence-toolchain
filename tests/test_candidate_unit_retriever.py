from pathlib import Path


def _inventory_with_units(*units):
    from evidence_toolchain import EvidenceInventory

    return EvidenceInventory(
        bundle_id="bundle_001",
        attachments=(),
        artifacts=(),
        units=tuple(units),
        route_decisions=(),
    )


def test_candidate_unit_retriever_selects_usage_and_currency_context_without_atomizing():
    from evidence_toolchain import (
        CandidateUnitRetriever,
        EvidenceAtomType,
        EvidenceUnit,
        InvestigationTask,
        InvestigationTaskStatus,
        InvestigationTaskType,
        Need,
        NeedSpec,
        NeedType,
    )

    inventory = _inventory_with_units(
        EvidenceUnit(
            unit_id="unit_usage",
            artifact_id="artifact_pdf_page_1",
            unit_type="text_span",
            producer="pdfplumber_extract",
            text="전력 사용량 6.4 MWh",
        ),
        EvidenceUnit(
            unit_id="unit_money",
            artifact_id="artifact_pdf_page_1",
            unit_type="text_span",
            producer="pdfplumber_extract",
            text="청구금액 1,230,000 KRW",
        ),
        EvidenceUnit(
            unit_id="unit_payment_due",
            artifact_id="artifact_pdf_page_1",
            unit_type="text_span",
            producer="pdfplumber_extract",
            text="납부기한 2025-04-20",
        ),
    )
    need_spec = NeedSpec(
        x_id="x_001",
        needs=(
            Need(
                need_id=NeedType.USAGE_AMOUNT,
                need_type=NeedType.USAGE_AMOUNT,
                target_value=6400,
                target_unit="kWh",
                acceptable_units=("kWh", "MWh"),
                preferred_labels=("사용량", "전력량"),
            ),
        ),
        disqualifiers=("납부기한",),
    )
    task = InvestigationTask(
        task_id="gap_x_001_usage_amount_001",
        task_type=InvestigationTaskType.RETRIEVE_CANDIDATE_UNITS,
        target_claim_id="x_001",
        target_need_id=NeedType.USAGE_AMOUNT,
        allowed_atom_types=(
            EvidenceAtomType.USAGE_AMOUNT,
            EvidenceAtomType.CURRENCY_AMOUNT,
        ),
    )

    result = CandidateUnitRetriever().retrieve(
        task=task,
        inventory=inventory,
        need_spec=need_spec,
    )
    payload = result.to_dict()

    assert payload["selected_unit_ids"] == ["unit_usage", "unit_money"]
    assert payload["rejected_unit_ids"] == ["unit_payment_due"]
    assert "사용량" in payload["matched_clues"]
    assert "MWh" in payload["matched_clues"]
    assert "KRW" in payload["matched_clues"]
    assert payload["metadata"]["producer"] == "candidate_unit_retriever_v0"

    task_result = result.to_task_result()
    assert task_result.status == InvestigationTaskStatus.COMPLETED
    assert task_result.produced_units == ()
    assert task_result.produced_atoms == ()
    assert task_result.metadata["selected_unit_ids"] == ["unit_usage", "unit_money"]
    assert task_result.metadata["next_task_type"] == InvestigationTaskType.ATOMIZE_UNIT_CLUSTER

    atomize_task = result.to_atomize_task(source_task=task)
    assert atomize_task is not None
    assert atomize_task.task_id == "gap_x_001_usage_amount_001_atomize_001"
    assert atomize_task.task_type == InvestigationTaskType.ATOMIZE_UNIT_CLUSTER
    assert atomize_task.target_unit_ids == ("unit_usage", "unit_money")
    assert atomize_task.allowed_atom_types == (
        EvidenceAtomType.USAGE_AMOUNT,
        EvidenceAtomType.CURRENCY_AMOUNT,
    )
    assert atomize_task.reason == "candidate_units_retrieved"


def test_candidate_unit_retriever_selects_period_and_date_clues_for_service_period_need():
    from evidence_toolchain import (
        CandidateUnitRetriever,
        EvidenceAtomType,
        EvidenceUnit,
        InvestigationTask,
        InvestigationTaskType,
        Need,
        NeedSpec,
        NeedType,
    )

    inventory = _inventory_with_units(
        EvidenceUnit(
            unit_id="unit_period",
            artifact_id="artifact_pdf_page_1",
            unit_type="text_span",
            producer="pdfplumber_extract",
            text="사용기간 2025-03-01 ~ 2025-03-31",
        ),
        EvidenceUnit(
            unit_id="unit_bill_date",
            artifact_id="artifact_pdf_page_1",
            unit_type="text_span",
            producer="pdfplumber_extract",
            text="청구일 2025-04-05",
        ),
        EvidenceUnit(
            unit_id="unit_usage",
            artifact_id="artifact_pdf_page_1",
            unit_type="text_span",
            producer="pdfplumber_extract",
            text="전력 사용량 6.4 MWh",
        ),
    )
    need_spec = NeedSpec(
        x_id="x_001",
        needs=(
            Need(
                need_id=NeedType.SERVICE_PERIOD,
                need_type=NeedType.SERVICE_PERIOD,
                target_period="2025-03",
                preferred_labels=("사용기간", "사용월"),
            ),
        ),
    )
    task = InvestigationTask(
        task_id="gap_x_001_service_period_002",
        task_type=InvestigationTaskType.RETRIEVE_CANDIDATE_UNITS,
        target_claim_id="x_001",
        target_need_id=NeedType.SERVICE_PERIOD,
        allowed_atom_types=(
            EvidenceAtomType.SERVICE_PERIOD,
            EvidenceAtomType.DATE,
        ),
    )

    result = CandidateUnitRetriever().retrieve(
        task=task,
        inventory=inventory,
        need_spec=need_spec,
    )
    payload = result.to_dict()

    assert payload["selected_unit_ids"] == ["unit_period", "unit_bill_date"]
    assert payload["rejected_unit_ids"] == []
    assert "사용기간" in payload["matched_clues"]
    assert "청구일" in payload["matched_clues"]
    assert result.to_atomize_task(source_task=task).target_unit_ids == (
        "unit_period",
        "unit_bill_date",
    )


def test_candidate_unit_retriever_reports_no_new_clue_when_no_units_match():
    from evidence_toolchain import (
        CandidateUnitRetriever,
        EvidenceUnit,
        InvestigationTask,
        InvestigationTaskStatus,
        InvestigationTaskType,
        Need,
        NeedSpec,
        NeedType,
    )

    inventory = _inventory_with_units(
        EvidenceUnit(
            unit_id="unit_noise",
            artifact_id="artifact_pdf_page_1",
            unit_type="text_span",
            producer="pdfplumber_extract",
            text="고객센터 1234-5678",
        )
    )
    need_spec = NeedSpec(
        x_id="x_001",
        needs=(
            Need(
                need_id=NeedType.SITE_IDENTITY,
                need_type=NeedType.SITE_IDENTITY,
                target_text="OCH-01",
            ),
        ),
    )
    task = InvestigationTask(
        task_id="gap_x_001_site_identity_001",
        task_type=InvestigationTaskType.RETRIEVE_CANDIDATE_UNITS,
        target_claim_id="x_001",
        target_need_id=NeedType.SITE_IDENTITY,
    )

    result = CandidateUnitRetriever().retrieve(
        task=task,
        inventory=inventory,
        need_spec=need_spec,
    )

    assert result.selected_unit_ids == ()
    assert result.to_task_result().status == InvestigationTaskStatus.NO_NEW_CLUE
    assert "next_task_type" not in result.to_task_result().metadata
    assert result.to_atomize_task(source_task=task) is None
    assert result.issues[0].code == "candidate_unit_retrieval_no_units_selected"


def test_candidate_unit_retriever_does_not_import_resolver_provider_or_frameworks():
    source = Path("src/evidence_toolchain/investigation_retrieval.py").read_text(
        encoding="utf-8"
    )

    forbidden_snippets = (
        "HardGateResolver",
        "DeterministicNormalizer",
        "EvidenceAtom(",
        "NormalizationResult(",
        "openai",
        "langgraph",
        "requests",
        "httpx",
    )
    for forbidden in forbidden_snippets:
        assert forbidden not in source
