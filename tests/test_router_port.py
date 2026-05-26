def test_rule_observation_router_matches_existing_planner(tmp_path):
    from evidence_toolchain.artifacts import EvidenceDocument
    from evidence_toolchain.preflight import preflight_document
    from evidence_toolchain.routers import RuleObservationRouter

    document_path = tmp_path / "utility_bill.txt"
    document_path.write_text(
        "\n".join(
            [
                "ETC-case_id: utility_bill_basic",
                "ETC-document_kind: utility_bill",
                "ETC-quality: clean",
                "ETC-text_layer: true",
                "",
                "사용량 6.4 MWh",
            ]
        ),
        encoding="utf-8",
    )

    document = EvidenceDocument.from_path(document_path)
    plan = RuleObservationRouter().route(document, preflight_document(document))

    assert plan.observation.document_class == "utility_bill"
    assert [step.name for step in plan.selected_capabilities] == [
        "docling_parse",
        "table_structure_extract",
        "utility_bill_extract",
    ]


def test_local_runner_accepts_router_port_for_model_assisted_routing(tmp_path):
    from evidence_toolchain.artifacts import EvidenceDocument
    from evidence_toolchain.observations import EvidenceObservation
    from evidence_toolchain.planner import CapabilityStep, EvidenceToolPlan
    from evidence_toolchain.runners import run_document

    class StaticModelRouter:
        def route(self, document, preflight):
            assert preflight.sample_text == "사용량 6.4 MWh"
            return EvidenceToolPlan(
                document_id=document.document_id,
                observation=EvidenceObservation(
                    document_id=document.document_id,
                    document_class="model_routed_utility_bill",
                    has_text_layer=preflight.has_text_layer,
                    quality="model_observed",
                    signals=["model_router_used"],
                ),
                selected_capabilities=[
                    CapabilityStep(
                        name="manual_review_request",
                        reason="model_router_forced_review",
                    )
                ],
            )

    document_path = tmp_path / "utility_bill.txt"
    document_path.write_text(
        "\n".join(
            [
                "ETC-case_id: utility_bill_basic",
                "ETC-document_kind: utility_bill",
                "ETC-quality: clean",
                "ETC-text_layer: true",
                "",
                "사용량 6.4 MWh",
            ]
        ),
        encoding="utf-8",
    )

    state = run_document(
        EvidenceDocument.from_path(document_path),
        router=StaticModelRouter(),
    )

    assert state.observation.document_class == "model_routed_utility_bill"
    assert [step.capability for step in state.pending_steps] == [
        "manual_review_request"
    ]
    assert state.events[2].payload["document_class"] == "model_routed_utility_bill"
    assert state.events[3].payload["selected_capabilities"] == [
        "manual_review_request"
    ]
