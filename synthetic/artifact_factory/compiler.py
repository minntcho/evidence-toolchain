from __future__ import annotations

from synthetic.artifact_factory.ir import ConfusionEdge, DocumentIntent, ScenarioIR
from synthetic.artifact_factory.plans import ArtifactPlan, BundlePlan
from synthetic.artifact_factory.specs import ScenarioSpec


def compile_scenario_ir(spec: ScenarioSpec) -> ScenarioIR:
    document_ids = _validate_document_ids(spec)
    confusion_edges = tuple(_compile_confusion_edges(spec, document_ids))

    return ScenarioIR(
        scenario_id=spec.scenario_id,
        rng_seed=spec.seed,
        intake_events=tuple(_compile_intake_events(spec)),
        document_intents=tuple(_compile_document_intents(spec)),
        evidence_need=dict(spec.evidence_need),
        confusion_graph=confusion_edges,
        expected_syndrome=dict(spec.expected_syndrome),
    )


def compile_ir_to_bundle_plan(scenario_ir: ScenarioIR) -> BundlePlan:
    artifacts = tuple(
        ArtifactPlan(
            artifact_id=intent.document_id,
            carrier=intent.carrier,
            archetype=intent.archetype,
            role=intent.role,
            evidence_roles_to_realize=(intent.role,),
            logical_requirements={"evidence_need": dict(scenario_ir.evidence_need)},
            confusion_requirements=_confusions_for_artifact(
                intent.document_id,
                scenario_ir.confusion_graph,
            ),
            carrier_profile=intent.carrier_profile,
        )
        for intent in scenario_ir.document_intents
    )
    return BundlePlan(
        scenario_id=scenario_ir.scenario_id,
        artifacts=artifacts,
        expected_syndrome=dict(scenario_ir.expected_syndrome),
    )


def compile_scenario_to_bundle_plan(spec: ScenarioSpec) -> BundlePlan:
    return compile_ir_to_bundle_plan(compile_scenario_ir(spec))


def _validate_document_ids(spec: ScenarioSpec) -> set[str]:
    document_ids: set[str] = set()
    for document in spec.documents:
        if document.document_id in document_ids:
            raise ValueError(f"Duplicate document id: {document.document_id}")
        document_ids.add(document.document_id)
    return document_ids


def _compile_intake_events(spec: ScenarioSpec) -> list[dict[str, object]]:
    lifecycle = spec.intake_story.get("lifecycle", [])
    if not isinstance(lifecycle, (list, tuple)):
        raise ValueError("intake_story.lifecycle must be a sequence")
    return [
        {
            "event_id": str(event_id),
            "ordinal": ordinal,
        }
        for ordinal, event_id in enumerate(lifecycle)
    ]


def _compile_document_intents(spec: ScenarioSpec) -> list[DocumentIntent]:
    return [
        DocumentIntent(
            document_id=document.document_id,
            archetype=document.archetype,
            role=document.role,
            carrier=document.carrier,
            carrier_profile=document.quality_profile,
        )
        for document in spec.documents
    ]


def _compile_confusion_edges(
    spec: ScenarioSpec,
    document_ids: set[str],
) -> list[ConfusionEdge]:
    edges: list[ConfusionEdge] = []
    for confusion in spec.confusions:
        _validate_document_ref(confusion.source, document_ids)
        if confusion.target is not None:
            _validate_document_ref(confusion.target, document_ids)
        for key, value in confusion.params.items():
            if _looks_like_document_ref_key(key):
                _validate_document_ref(str(value), document_ids)
        edges.append(
            ConfusionEdge(
                confusion_type=confusion.confusion_type,
                source=confusion.source,
                target=confusion.target,
                params=dict(confusion.params),
            )
        )
    return edges


def _confusions_for_artifact(
    artifact_id: str,
    confusion_graph: tuple[ConfusionEdge, ...],
) -> tuple[str, ...]:
    matches: list[str] = []
    for edge in confusion_graph:
        if artifact_id in _edge_document_refs(edge):
            matches.append(edge.confusion_type)
    return tuple(matches)


def _edge_document_refs(edge: ConfusionEdge) -> set[str]:
    refs = {edge.source}
    if edge.target is not None:
        refs.add(edge.target)
    for key, value in edge.params.items():
        if _looks_like_impacted_document_ref_key(key):
            refs.add(str(value))
    return refs


def _looks_like_document_ref_key(key: str) -> bool:
    return key == "source" or key.endswith("_source") or key.endswith("_document")


def _looks_like_impacted_document_ref_key(key: str) -> bool:
    return key == "correction_source" or key.endswith("_document")


def _validate_document_ref(ref: str, document_ids: set[str]) -> None:
    if ref not in document_ids:
        raise ValueError(f"Unknown document reference: {ref}")
