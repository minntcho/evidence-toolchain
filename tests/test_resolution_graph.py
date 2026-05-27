import json


def test_resolution_relation_and_status_vocabulary_are_closed_for_v0():
    from evidence_toolchain import ResolutionRelation, ResolutionStatus

    assert ResolutionRelation.ALL == (
        "supports",
        "supports_after_unit_normalization",
        "supports_by_aggregation",
        "supports_by_derivation",
        "contradicts",
        "contextualizes",
        "rejected_for_need",
        "needs_review",
    )
    assert ResolutionStatus.ALL == (
        "supported_direct",
        "supported_after_unit_normalization",
        "supported_by_aggregation",
        "supported_by_derivation",
        "contradicted",
        "partial_support",
        "ambiguous",
        "insufficient",
        "needs_review",
    )
    assert ResolutionRelation.is_core_relation("supports") is True
    assert ResolutionRelation.is_core_relation("usage_amount") is False
    assert ResolutionStatus.is_core_status("needs_review") is True
    assert ResolutionStatus.is_core_status("support_edge") is False


def test_resolution_edge_links_claim_need_and_atom_with_provenance():
    from evidence_toolchain import ResolutionEdge, ResolutionRelation
    from evidence_toolchain.issues import EvidenceIssue

    edge = ResolutionEdge(
        edge_id="edge_001",
        x_id="x_001",
        atom_id="atom_001",
        relation=ResolutionRelation.SUPPORTS_AFTER_UNIT_NORMALIZATION,
        need_id="usage_amount",
        basis=("문서에서 6.4 MWh를 발견", "6.4 MWh = 6400 kWh"),
        confidence=0.91,
        metadata={"hard_gate": "unit_dimension_compatible"},
        issues=(
            EvidenceIssue(
                code="needs_unit_normalization",
                severity="info",
                message="MWh evidence is compatible with kWh claim after unit conversion.",
            ),
        ),
    )
    payload = edge.to_dict()

    assert payload == {
        "edge_id": "edge_001",
        "x_id": "x_001",
        "atom_id": "atom_001",
        "relation": "supports_after_unit_normalization",
        "need_id": "usage_amount",
        "basis": ["문서에서 6.4 MWh를 발견", "6.4 MWh = 6400 kWh"],
        "confidence": 0.91,
        "metadata": {"hard_gate": "unit_dimension_compatible"},
        "issues": [
            {
                "code": "needs_unit_normalization",
                "severity": "info",
                "message": "MWh evidence is compatible with kWh claim after unit conversion.",
            }
        ],
    }
    assert "status" not in payload
    assert "supporting_y" not in payload
    json.dumps(payload)


def test_claim_resolution_collects_resolution_state_without_running_solver():
    from evidence_toolchain import ClaimResolution, ResolutionStatus

    resolution = ClaimResolution(
        x_id="x_001",
        status=ResolutionStatus.SUPPORTED_AFTER_UNIT_NORMALIZATION,
        edge_ids=("edge_001",),
        supporting_atom_ids=("atom_001",),
        rejected_atom_ids=("atom_002",),
        missing_need_ids=(),
        basis=("사용량 atom이 단위 변환 후 claim amount와 일치",),
        remaining_gaps=(),
        metadata={"resolver": "manual_fixture"},
    )
    payload = resolution.to_dict()

    assert payload == {
        "x_id": "x_001",
        "status": "supported_after_unit_normalization",
        "edge_ids": ["edge_001"],
        "supporting_atom_ids": ["atom_001"],
        "rejected_atom_ids": ["atom_002"],
        "missing_need_ids": [],
        "basis": ["사용량 atom이 단위 변환 후 claim amount와 일치"],
        "remaining_gaps": [],
        "issues": [],
        "metadata": {"resolver": "manual_fixture"},
    }
    assert "needs" not in payload
    assert "atoms" not in payload
    json.dumps(payload)


def test_evidence_resolution_graph_groups_edges_and_claim_resolutions_only():
    from evidence_toolchain import (
        ClaimResolution,
        EvidenceResolutionGraph,
        ResolutionEdge,
        ResolutionRelation,
        ResolutionStatus,
    )

    edge = ResolutionEdge(
        edge_id="edge_001",
        x_id="x_001",
        atom_id="atom_001",
        relation=ResolutionRelation.SUPPORTS,
        need_id="usage_amount",
        basis=("사용량 값이 직접 일치",),
    )
    resolution = ClaimResolution(
        x_id="x_001",
        status=ResolutionStatus.SUPPORTED_DIRECT,
        edge_ids=("edge_001",),
        supporting_atom_ids=("atom_001",),
    )
    graph = EvidenceResolutionGraph(
        bundle_id="bundle_001",
        claim_ids=("x_001",),
        atom_ids=("atom_001", "atom_002"),
        edges=(edge,),
        resolutions=(resolution,),
        metadata={"producer": "resolution_contract_fixture"},
    )
    payload = graph.to_dict()

    assert payload["bundle_id"] == "bundle_001"
    assert payload["claim_ids"] == ["x_001"]
    assert payload["atom_ids"] == ["atom_001", "atom_002"]
    assert payload["edges"][0]["relation"] == "supports"
    assert payload["resolutions"][0]["status"] == "supported_direct"
    assert payload["issues"] == []
    assert payload["metadata"]["producer"] == "resolution_contract_fixture"
    assert "EvidenceUnit" not in json.dumps(payload)
    assert "NeedSpec" not in json.dumps(payload)
    json.dumps(payload)
