def _inventory_with_units(*units):
    from evidence_toolchain import EvidenceInventory

    return EvidenceInventory(
        bundle_id="bundle_001",
        attachments=(),
        artifacts=(),
        units=tuple(units),
        route_decisions=(),
    )


def test_run_resolution_cycle_demonstrates_missing_gap_to_supported_graph():
    from evidence_toolchain import (
        DeclaredClaim,
        EvidenceUnit,
        InvestigationTaskType,
        NeedType,
        ResolutionStatus,
        run_resolution_cycle,
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
            unit_id="unit_charge",
            artifact_id="artifact_pdf_page_1",
            unit_type="text_span",
            producer="pdfplumber_extract",
            text="청구금액 1,230,000 KRW",
        ),
        EvidenceUnit(
            unit_id="unit_period",
            artifact_id="artifact_pdf_page_1",
            unit_type="text_span",
            producer="pdfplumber_extract",
            text="사용기간 2025-03-01 ~ 2025-03-31",
        ),
    )
    claim = DeclaredClaim(
        x_id="x_001",
        fields={"amount": 6400, "unit": "kWh", "period": "2025-03"},
    )

    result = run_resolution_cycle(
        inventory=inventory,
        claims=(claim,),
        max_investigation_steps=6,
    )
    payload = result.to_dict()

    assert payload["initial_graph"]["resolutions"][0]["status"] == ResolutionStatus.INSUFFICIENT
    assert payload["initial_graph"]["resolutions"][0]["missing_need_ids"] == [
        NeedType.USAGE_AMOUNT,
        NeedType.SERVICE_PERIOD,
    ]
    assert [task["task_type"] for task in payload["gap_plan"]["tasks"]] == [
        InvestigationTaskType.RETRIEVE_CANDIDATE_UNITS,
        InvestigationTaskType.RETRIEVE_CANDIDATE_UNITS,
    ]

    completed = payload["investigation_state"]["completed_tasks"]
    assert payload["investigation_state"]["agenda"] == []
    assert [task["status"] for task in completed] == [
        "completed",
        "completed",
        "completed",
        "completed",
        "completed",
        "completed",
    ]
    assert completed[0]["metadata"]["selected_unit_ids"] == ["unit_usage", "unit_charge"]
    assert completed[1]["produced_atom_ids"] == [
        "gap_x_001_usage_amount_001_atomize_001_atom_001",
        "gap_x_001_usage_amount_001_atomize_001_atom_002",
    ]

    final_graph = payload["final_graph"]
    assert final_graph["resolutions"][0]["status"] == ResolutionStatus.SUPPORTED_AFTER_UNIT_NORMALIZATION
    assert final_graph["resolutions"][0]["missing_need_ids"] == []
    assert final_graph["resolutions"][0]["supporting_atom_ids"] == [
        "gap_x_001_usage_amount_001_atomize_001_atom_001",
        "gap_x_001_service_period_002_atomize_001_atom_001",
    ]
    assert final_graph["resolutions"][0]["rejected_atom_ids"] == [
        "gap_x_001_usage_amount_001_atomize_001_atom_002"
    ]
    assert payload["stop_reason"] == "agenda_exhausted"
