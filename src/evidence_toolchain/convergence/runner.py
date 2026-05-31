from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
from pathlib import Path
from typing import Any, Callable

from evidence_toolchain.claims import DeclaredClaim
from evidence_toolchain.convergence.board import (
    ConvergenceBoard,
    ConvergenceEvent,
    PartialFailure,
    ReviewTrigger,
)
from evidence_toolchain.convergence.capabilities import (
    ACTIVITY,
    PERIOD,
    QUANTITY,
    SITE,
    UNIT,
    deterministic_normalizer_spec,
    propose_deterministic_normalization,
    propose_simple_alignment,
    propose_simple_slot_assignment,
    seed_usage_candidate,
    simple_aligner_spec,
    simple_slot_assigner_spec,
    utility_usage_schema,
)
from evidence_toolchain.convergence.candidates import EvidenceCandidate
from evidence_toolchain.convergence.gaps import CandidateGap, compute_candidate_gap
from evidence_toolchain.convergence.patches import CapabilitySpec, MaskPatch
from evidence_toolchain.convergence.reports import (
    ClaimConvergenceReport,
    ConvergenceReport,
)
from evidence_toolchain.convergence.scheduler import select_capabilities
from evidence_toolchain.convergence.schemas import EvidenceSchema
from evidence_toolchain.convergence.validator import apply_patch, validate_patch
from evidence_toolchain.ingestion import EvidenceInventory


PatchProducerFn = Callable[
    [EvidenceCandidate, EvidenceInventory, tuple[DeclaredClaim, ...], EvidenceSchema],
    MaskPatch,
]


@dataclass(frozen=True)
class PatchProducer:
    spec: CapabilitySpec
    produce_patch: PatchProducerFn


@dataclass(frozen=True)
class ConvergenceRun:
    run_id: str
    inventory: EvidenceInventory
    claims: tuple[DeclaredClaim, ...]
    schema_ids: tuple[str, ...]
    final_board: ConvergenceBoard
    report: ConvergenceReport
    stop_reason: str

    def to_dict(self) -> dict[str, Any]:
        return _to_json_compatible(self)


def run_convergence_cycle(
    *,
    inventory: EvidenceInventory,
    claims: tuple[DeclaredClaim, ...],
    schema_registry: EvidenceSchema | None = None,
    capabilities: tuple[CapabilitySpec | PatchProducer, ...] | None = None,
    run_id: str | None = None,
    max_steps: int = 10,
) -> ConvergenceRun:
    active_run_id = run_id or f"convergence_{inventory.bundle_id}"
    schema = schema_registry or utility_usage_schema()
    active_producers = _normalize_patch_producers(capabilities, schema)
    active_capabilities = tuple(producer.spec for producer in active_producers)
    producer_by_name = {
        producer.spec.name: producer
        for producer in active_producers
    }
    board = _seed_board(active_run_id, inventory, claims, schema)
    stop_reason = "max_steps_exhausted"

    for _step in range(max_steps):
        candidate, gap, selected = _next_action(board, schema, active_capabilities)
        if candidate is None or gap is None:
            stop_reason = "converged"
            break

        board = _append_event(
            board,
            "gap_computed",
            candidate_id=candidate.candidate_id,
            metadata=_gap_metadata(gap),
        )

        if not selected:
            stop_reason = "no_eligible_capability"
            board = _append_event(
                board,
                "stopped",
                candidate_id=candidate.candidate_id,
                metadata={"reason": stop_reason},
            )
            break

        capability = selected[0]
        producer = producer_by_name[capability.name]
        board = _append_event(
            board,
            "capability_selected",
            candidate_id=candidate.candidate_id,
            capability_name=capability.name,
        )
        patch = producer.produce_patch(candidate, inventory, claims, schema)
        board = _append_event(
            board,
            "patch_proposed",
            candidate_id=candidate.candidate_id,
            capability_name=capability.name,
            metadata={"touched_mask": patch.touched_mask},
        )
        if not patch.touched_mask:
            stop_reason = "no_progress"
            board = _append_event(
                board,
                "stopped",
                candidate_id=candidate.candidate_id,
                capability_name=capability.name,
                metadata={"reason": stop_reason},
            )
            break

        validation = validate_patch(candidate, patch, capability, schema)

        if not validation.accepted:
            board = _append_event(
                board,
                "patch_rejected",
                candidate_id=candidate.candidate_id,
                capability_name=capability.name,
                metadata={
                    "errors": tuple(error.code for error in validation.errors),
                },
            )
            board = _append_review_trigger(
                board,
                ReviewTrigger(
                    code="patch_rejected",
                    message="PatchValidator rejected a proposed patch.",
                    metadata={
                        "candidate_id": candidate.candidate_id,
                        "capability_name": capability.name,
                        "errors": tuple(error.code for error in validation.errors),
                    },
                ),
            )
            stop_reason = "patch_rejected"
            break

        updated_candidate = apply_patch(candidate, patch, validation)
        board = _replace_candidate(board, updated_candidate)
        board = _append_event(
            board,
            "patch_applied",
            candidate_id=candidate.candidate_id,
            capability_name=capability.name,
            metadata={"touched_mask": patch.touched_mask},
        )
    else:
        stop_reason = "max_steps_exhausted"

    board = _detect_simple_conflicts(board, schema)
    report = _finalize_report(
        run_id=active_run_id,
        inventory=inventory,
        claims=claims,
        board=board,
        schema=schema,
    )
    board = _append_event(
        board,
        "finalized",
        metadata={"stop_reason": stop_reason},
    )
    return ConvergenceRun(
        run_id=active_run_id,
        inventory=inventory,
        claims=claims,
        schema_ids=(schema.schema_id,),
        final_board=board,
        report=report,
        stop_reason=stop_reason,
    )


def _default_capabilities(schema: EvidenceSchema) -> tuple[CapabilitySpec, ...]:
    return (
        simple_slot_assigner_spec(schema),
        deterministic_normalizer_spec(schema),
        simple_aligner_spec(schema),
    )


def _normalize_patch_producers(
    capabilities: tuple[CapabilitySpec | PatchProducer, ...] | None,
    schema: EvidenceSchema,
) -> tuple[PatchProducer, ...]:
    selected = capabilities or _default_capabilities(schema)
    return tuple(
        capability
        if isinstance(capability, PatchProducer)
        else _builtin_patch_producer(capability)
        for capability in selected
    )


def _builtin_patch_producer(spec: CapabilitySpec) -> PatchProducer:
    return PatchProducer(
        spec=spec,
        produce_patch=lambda candidate, inventory, claims, schema: _propose_builtin_patch(
            spec,
            candidate,
            inventory,
            claims,
            schema,
        ),
    )


def _seed_board(
    run_id: str,
    inventory: EvidenceInventory,
    claims: tuple[DeclaredClaim, ...],
    schema: EvidenceSchema,
) -> ConvergenceBoard:
    candidates = _seed_candidates(inventory, claims, schema)
    board = ConvergenceBoard(
        board_id=f"{run_id}_board",
        run_id=run_id,
        inventory=inventory,
        claims=claims,
        candidates=candidates,
        partial_failures=_partial_failures_from_inventory(inventory),
    )
    for candidate in candidates:
        board = _append_event(board, "candidate_seeded", candidate_id=candidate.candidate_id)
    return board


def _seed_candidates(
    inventory: EvidenceInventory,
    claims: tuple[DeclaredClaim, ...],
    schema: EvidenceSchema,
) -> tuple[EvidenceCandidate, ...]:
    row_keys = _candidate_row_keys(inventory)
    candidates: list[EvidenceCandidate] = []
    for claim in claims:
        if row_keys:
            for artifact_id, row in row_keys:
                candidates.append(
                    seed_usage_candidate(
                        inventory,
                        claim,
                        schema=schema,
                        candidate_id=f"cand_{len(candidates) + 1:03d}",
                        metadata={"artifact_id": artifact_id, "row": row},
                    )
                )
        else:
            candidates.append(
                seed_usage_candidate(
                    inventory,
                    claim,
                    schema=schema,
                    candidate_id=f"cand_{len(candidates) + 1:03d}",
                )
            )
    return tuple(candidates)


def _candidate_row_keys(inventory: EvidenceInventory) -> tuple[tuple[str, int], ...]:
    row_keys: set[tuple[str, int]] = set()
    for unit in inventory.units:
        row = unit.locator.get("row")
        header = unit.locator.get("header") or unit.metadata.get("slot")
        if row is None or header is None:
            continue
        if str(header).strip().lower() not in _SEED_HEADERS:
            continue
        row_keys.add((unit.artifact_id, int(row)))
    return tuple(sorted(row_keys))


def _next_action(
    board: ConvergenceBoard,
    schema: EvidenceSchema,
    capabilities: tuple[CapabilitySpec, ...],
) -> tuple[EvidenceCandidate | None, CandidateGap | None, tuple[CapabilitySpec, ...]]:
    for candidate in board.candidates:
        gap = compute_candidate_gap(candidate, schema)
        if not gap.active_mask:
            continue
        return candidate, gap, select_capabilities(candidate, gap, capabilities)
    return None, None, ()


def _propose_builtin_patch(
    capability: CapabilitySpec,
    candidate: EvidenceCandidate,
    inventory: EvidenceInventory,
    claims: tuple[DeclaredClaim, ...],
    schema: EvidenceSchema,
) -> MaskPatch:
    if capability.name == "simple_slot_assigner":
        return propose_simple_slot_assignment(candidate, inventory, schema=schema)
    if capability.name == "deterministic_normalizer":
        return propose_deterministic_normalization(candidate, schema=schema)
    if capability.name == "simple_aligner":
        claim = _claim_for_candidate(candidate, claims)
        return propose_simple_alignment(candidate, claim, schema=schema)
    raise ValueError(f"unsupported convergence capability: {capability.name}")


def _claim_for_candidate(
    candidate: EvidenceCandidate,
    claims: tuple[DeclaredClaim, ...],
) -> DeclaredClaim:
    for claim in claims:
        if claim.x_id == candidate.claim_id:
            return claim
    raise KeyError(f"claim not found for candidate: {candidate.candidate_id}")


def _replace_candidate(
    board: ConvergenceBoard,
    updated_candidate: EvidenceCandidate,
) -> ConvergenceBoard:
    return replace(
        board,
        candidates=tuple(
            updated_candidate
            if candidate.candidate_id == updated_candidate.candidate_id
            else candidate
            for candidate in board.candidates
        ),
    )


def _append_event(
    board: ConvergenceBoard,
    event_type: str,
    *,
    candidate_id: str | None = None,
    capability_name: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> ConvergenceBoard:
    return replace(
        board,
        events=board.events
        + (
            ConvergenceEvent(
                event_type=event_type,
                candidate_id=candidate_id,
                capability_name=capability_name,
                metadata=dict(metadata or {}),
            ),
        ),
    )


def _append_review_trigger(
    board: ConvergenceBoard,
    trigger: ReviewTrigger,
) -> ConvergenceBoard:
    return replace(board, review_triggers=board.review_triggers + (trigger,))


def _finalize_report(
    *,
    run_id: str,
    inventory: EvidenceInventory,
    claims: tuple[DeclaredClaim, ...],
    board: ConvergenceBoard,
    schema: EvidenceSchema,
) -> ConvergenceReport:
    claim_reports = tuple(
        _claim_report(
            claim,
            board.candidates,
            schema,
            board.review_triggers,
            board.partial_failures,
        )
        for claim in claims
    )
    return ConvergenceReport(
        run_id=run_id,
        bundle_id=inventory.bundle_id,
        claim_reports=claim_reports,
    )


def _claim_report(
    claim: DeclaredClaim,
    candidates: tuple[EvidenceCandidate, ...],
    schema: EvidenceSchema,
    review_triggers: tuple[ReviewTrigger, ...],
    partial_failures: tuple[PartialFailure, ...],
) -> ClaimConvergenceReport:
    claim_candidates = tuple(
        candidate for candidate in candidates if candidate.claim_id == claim.x_id
    )
    selected = tuple(
        candidate
        for candidate in claim_candidates
        if candidate.aligned_mask & schema.required_mask == schema.required_mask
    )
    unresolved = tuple(
        _unresolved_gap_labels(compute_candidate_gap(candidate, schema), schema)
        for candidate in claim_candidates
        if candidate not in selected
    )
    unresolved_gaps = tuple(label for labels in unresolved for label in labels)

    if selected:
        candidate = selected[0]
        claim_alignment_status = (
            "supported_after_unit_normalization"
            if candidate.normalized_mask
            else "supported_direct"
        )
        evidence_convergence_status = (
            "needs_review_due_to_candidate_conflict"
            if any(trigger.code == "candidate_conflict" for trigger in review_triggers)
            else "evidence_converged"
        )
    elif any(trigger.code == "patch_rejected" for trigger in review_triggers):
        claim_alignment_status = "not_evaluated"
        evidence_convergence_status = "needs_review_unresolved_gap"
    elif any(
        compute_candidate_gap(candidate, schema).missing_mask
        for candidate in claim_candidates
    ):
        claim_alignment_status = "insufficient"
        evidence_convergence_status = "insufficient_missing_required_slots"
    else:
        claim_alignment_status = "not_evaluated"
        evidence_convergence_status = "needs_review_unresolved_gap"

    return ClaimConvergenceReport(
        claim_id=claim.x_id,
        target_schema_id=schema.schema_id,
        claim_alignment_status=claim_alignment_status,
        evidence_convergence_status=evidence_convergence_status,
        selected_support_set=tuple(candidate.candidate_id for candidate in selected[:1]),
        candidate_ids=tuple(candidate.candidate_id for candidate in claim_candidates),
        unresolved_gaps=unresolved_gaps,
        review_triggers=review_triggers,
        partial_failures=partial_failures,
    )


def _partial_failures_from_inventory(
    inventory: EvidenceInventory,
) -> tuple[PartialFailure, ...]:
    failures: list[PartialFailure] = []
    for issue in inventory.issues:
        if issue.severity == "blocking":
            continue
        failures.append(
            PartialFailure(
                code="nonblocking_failure",
                message=issue.message,
                metadata={
                    "issue_code": issue.code,
                    "issue_severity": issue.severity,
                },
            )
        )
    return tuple(failures)


def _detect_simple_conflicts(
    board: ConvergenceBoard,
    schema: EvidenceSchema,
) -> ConvergenceBoard:
    updated = board
    for claim in board.claims:
        claim_candidates = tuple(
            candidate for candidate in board.candidates if candidate.claim_id == claim.x_id
        )
        selected = tuple(
            candidate
            for candidate in claim_candidates
            if candidate.aligned_mask & schema.required_mask == schema.required_mask
        )
        if not selected:
            continue
        selected_candidate = selected[0]
        for candidate in claim_candidates:
            if candidate.candidate_id == selected_candidate.candidate_id:
                continue
            if _candidate_conflicts(selected_candidate, candidate):
                updated = _append_review_trigger(
                    updated,
                    ReviewTrigger(
                        code="candidate_conflict",
                        message="A second candidate conflicts with the selected support candidate.",
                        metadata={
                            "selected_candidate_id": selected_candidate.candidate_id,
                            "conflicting_candidate_id": candidate.candidate_id,
                        },
                    ),
                )
    return updated


def _candidate_conflicts(
    selected: EvidenceCandidate,
    candidate: EvidenceCandidate,
) -> bool:
    context_bits = (SITE, PERIOD, ACTIVITY)
    if any(_candidate_value(selected, bit) != _candidate_value(candidate, bit) for bit in context_bits):
        return False
    if _candidate_value(selected, UNIT) != _candidate_value(candidate, UNIT):
        return False
    selected_quantity = _candidate_value(selected, QUANTITY)
    candidate_quantity = _candidate_value(candidate, QUANTITY)
    return (
        selected_quantity is not None
        and candidate_quantity is not None
        and selected_quantity != candidate_quantity
    )


def _candidate_value(candidate: EvidenceCandidate, slot_bit: int) -> Any:
    return candidate.normalized_payload_by_slot.get(
        slot_bit,
        candidate.payload_by_slot.get(slot_bit),
    )


def _unresolved_gap_labels(gap: CandidateGap, schema: EvidenceSchema) -> tuple[str, ...]:
    labels: list[str] = []
    for slot in schema.slots:
        if gap.active_mask & slot.bit:
            labels.append(slot.slot_id)
    return tuple(labels)


def _gap_metadata(gap: CandidateGap) -> dict[str, int]:
    return {
        "missing_mask": gap.missing_mask,
        "unassigned_mask": gap.unassigned_mask,
        "unnormalized_mask": gap.unnormalized_mask,
        "unaligned_mask": gap.unaligned_mask,
        "ambiguous_mask": gap.ambiguous_mask,
        "issue_mask": gap.issue_mask,
    }


def _to_json_compatible(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value):
        return {
            item.name: _to_json_compatible(getattr(value, item.name))
            for item in fields(value)
        }
    if isinstance(value, dict):
        return {
            str(key): _to_json_compatible(item)
            for key, item in value.items()
        }
    if isinstance(value, tuple | list):
        return [_to_json_compatible(item) for item in value]
    return value


_SEED_HEADERS = frozenset(
    {
        "site",
        "location",
        "period",
        "service period",
        "activity",
        "fuel",
        "amount",
        "quantity",
        "usage",
        "usage amount",
        "unit",
        "uom",
    }
)
