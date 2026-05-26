from __future__ import annotations

from dataclasses import replace

from evidence_toolchain.artifacts import EvidenceDocument
from evidence_toolchain.capabilities import CapabilityRunner
from evidence_toolchain.planner import EvidenceToolPlan
from evidence_toolchain.preflight import EvidencePreflight, preflight_document
from evidence_toolchain.routers import ObservationRouter, RuleObservationRouter
from evidence_toolchain.runtime import (
    EvidenceEvent,
    EvidenceRunState,
    EvidenceStep,
    EvidenceToolResult,
)


def run_document(
    document: EvidenceDocument,
    *,
    run_id: str | None = None,
    router: ObservationRouter | None = None,
    capability_runner: CapabilityRunner | None = None,
) -> EvidenceRunState:
    """observation과 planning까지 reference local flow를 실행합니다."""

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

    if capability_runner is not None:
        state = run_capability_steps(state, capability_runner)

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


def run_capability_steps(
    state: EvidenceRunState,
    capability_runner: CapabilityRunner,
) -> EvidenceRunState:
    pending: list[EvidenceStep] = []
    completed = list(state.completed_steps)
    tool_results = list(state.tool_results)
    interrupts = list(state.interrupts)
    selected_fallbacks: list[EvidenceStep] = []
    current = state

    for step in state.pending_steps:
        if not capability_runner.can_run(step, current):
            pending.append(step)
            continue

        current = current.record_event(
            EvidenceEvent(
                run_id=current.run_id,
                sequence=len(current.events) + 1,
                event_type="capability_started",
                payload={
                    "capability": step.capability,
                    "reason": step.reason,
                },
            )
        )
        try:
            result = capability_runner.run(step, current)
        except Exception as error:
            result = _failed_result_from_exception(step, error)
        completed.append(replace(step, status=_step_status_from_result(result.status)))
        tool_results.append(result)
        if result.status == "review_requested":
            interrupts.append(
                {
                    "type": "manual_review",
                    "capability": result.capability,
                    "reason": result.outputs.get("reason", "manual_review_requested"),
                }
            )

        current = replace(
            current,
            completed_steps=tuple(completed),
            pending_steps=tuple(pending),
            tool_results=tuple(tool_results),
            interrupts=tuple(interrupts),
        )
        current = _record_capability_result_event(current, result)
        if result.status == "failed":
            for fallback in _fallback_steps_for_failure(current, result.capability):
                if _has_capability(pending + completed + selected_fallbacks, fallback):
                    continue
                selected_fallbacks.append(fallback)
                current = current.record_event(
                    EvidenceEvent(
                        run_id=current.run_id,
                        sequence=len(current.events) + 1,
                        event_type="fallback_selected",
                        payload={
                            "capability": fallback.capability,
                            "reason": fallback.reason,
                            "source_capability": result.capability,
                        },
                    )
                )
        if result.status == "review_requested":
            current = current.record_event(
                EvidenceEvent(
                    run_id=current.run_id,
                    sequence=len(current.events) + 1,
                    event_type="review_requested",
                    payload={
                        "capability": result.capability,
                        "reason": result.outputs.get("reason", "manual_review_requested"),
                    },
                )
            )

    return replace(current, pending_steps=tuple(pending + selected_fallbacks))


def _step_status_from_result(result_status: str) -> str:
    if result_status == "failed":
        return "failed"
    return "completed"


def _failed_result_from_exception(
    step: EvidenceStep,
    error: Exception,
) -> EvidenceToolResult:
    capability = step.capability or "unknown_capability"
    return EvidenceToolResult(
        capability=capability,
        status="failed",
        errors=(f"{type(error).__name__}: {error}",),
    )


def _record_capability_result_event(
    state: EvidenceRunState,
    result: EvidenceToolResult,
) -> EvidenceRunState:
    event_type = (
        "capability_failed" if result.status == "failed" else "capability_completed"
    )
    payload = {
        "capability": result.capability,
        "status": result.status,
    }
    if result.status == "failed":
        payload["errors"] = list(result.errors)
    return state.record_event(
        EvidenceEvent(
            run_id=state.run_id,
            sequence=len(state.events) + 1,
            event_type=event_type,
            payload=payload,
        )
    )


def _fallback_steps_for_failure(
    state: EvidenceRunState,
    source_capability: str,
) -> tuple[EvidenceStep, ...]:
    if state.plan is None:
        return ()

    return tuple(
        EvidenceStep(
            name="execute_capability",
            status="pending",
            capability=fallback.name,
            reason=fallback.reason,
            metadata={"source_capability": source_capability},
        )
        for fallback in state.plan.fallbacks
    )


def _has_capability(steps: list[EvidenceStep], step: EvidenceStep) -> bool:
    return any(existing.capability == step.capability for existing in steps)
