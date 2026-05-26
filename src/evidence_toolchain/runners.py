from __future__ import annotations

from evidence_toolchain.artifacts import EvidenceDocument
from evidence_toolchain.planner import EvidenceToolPlan, plan_document
from evidence_toolchain.runtime import EvidenceEvent, EvidenceRunState, EvidenceStep


def run_document(
    document: EvidenceDocument,
    *,
    run_id: str | None = None,
) -> EvidenceRunState:
    """Run the reference local flow through observation and planning."""

    resolved_run_id = run_id or document.document_id
    plan = plan_document(document)
    state = EvidenceRunState(
        run_id=resolved_run_id,
        document=document,
        observation=plan.observation,
        plan=plan,
        pending_steps=_pending_capability_steps(plan),
        issues=tuple(plan.issues),
    )

    for event in _initial_events(resolved_run_id, document, plan):
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
            sequence=3,
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
