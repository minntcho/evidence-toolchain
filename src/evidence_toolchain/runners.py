from __future__ import annotations

from evidence_toolchain.artifacts import EvidenceDocument
from evidence_toolchain.planner import EvidenceToolPlan
from evidence_toolchain.preflight import EvidencePreflight, preflight_document
from evidence_toolchain.routers import ObservationRouter, RuleObservationRouter
from evidence_toolchain.runtime import EvidenceEvent, EvidenceRunState, EvidenceStep


def run_document(
    document: EvidenceDocument,
    *,
    run_id: str | None = None,
    router: ObservationRouter | None = None,
) -> EvidenceRunState:
    """Run the reference local flow through observation and planning."""

    resolved_run_id = run_id or document.document_id
    preflight = preflight_document(document)
    active_router = router or RuleObservationRouter()
    plan = active_router.route(document, preflight)
    state = EvidenceRunState(
        run_id=resolved_run_id,
        document=document,
        preflight=preflight,
        observation=plan.observation,
        plan=plan,
        pending_steps=_pending_capability_steps(plan),
        issues=tuple(plan.issues),
    )

    for event in _initial_events(resolved_run_id, document, preflight, plan):
        state = state.record_event(event)

    return state


def _pending_capability_steps(plan: EvidenceToolPlan) -> tuple[EvidenceStep, ...]:
    return tuple(
        EvidenceStep(
            name="execute_capability",
            status="pending",
            capability=step.name,
            reason=step.reason,
        )
        for step in plan.selected_capabilities
    )


def _initial_events(
    run_id: str,
    document: EvidenceDocument,
    preflight: EvidencePreflight,
    plan: EvidenceToolPlan,
) -> tuple[EvidenceEvent, ...]:
    observation = plan.observation
    return (
        EvidenceEvent(
            run_id=run_id,
            sequence=1,
            event_type="document_received",
            payload={
                "document_id": document.document_id,
                "file_name": document.file_name,
                "media_type": document.media_type,
            },
        ),
        EvidenceEvent(
            run_id=run_id,
            sequence=2,
            event_type="preflight_completed",
            payload={
                "format": preflight.format,
                "media_type": preflight.media_type,
                "has_text_layer": preflight.has_text_layer,
                "signals": list(preflight.signals),
                "detected_rotation": preflight.detected_rotation,
            },
        ),
        EvidenceEvent(
            run_id=run_id,
            sequence=3,
            event_type="observation_created",
            payload={
                "document_class": observation.document_class,
                "has_text_layer": observation.has_text_layer,
                "quality": observation.quality,
                "signals": observation.signals,
            },
        ),
        EvidenceEvent(
            run_id=run_id,
            sequence=4,
            event_type="plan_created",
            payload={
                "selected_capabilities": [
                    step.name for step in plan.selected_capabilities
                ],
                "fallbacks": [step.name for step in plan.fallbacks],
                "issues": [issue.code for issue in plan.issues],
            },
        ),
    )
