from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
from pathlib import Path
from typing import Any

from evidence_toolchain.claims import DeclaredClaim
from evidence_toolchain.convergence.board import ConvergenceBoard, ConvergenceEvent
from evidence_toolchain.convergence.capabilities import (
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
    capabilities: tuple[CapabilitySpec, ...] | None = None,
    run_id: str | None = None,
    max_steps: int = 10,
) -> ConvergenceRun:
    active_run_id = run_id or f"convergence_{inventory.bundle_id}"
    schema = schema_registry or utility_usage_schema()
    active_capabilities = capabilities or _default_capabilities(schema)
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
        board = _append_event(
            board,
            "capability_selected",
            candidate_id=candidate.candidate_id,
            capability_name=capability.name,
        )
        patch = _propose_patch(capability, candidate, inventory, claims, schema)
        board = _append_event(
            board,
            "patch_proposed",
            candidate_id=candidate.candidate_id,
            capability_name=capability.name,
            metadata={"touched_mask": patch.touched_mask},
        )
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

    report = _finalize_report(
        run_id=active_run_id,
        inventory=inventory,
        claims=claims,
        candidates=board.candidates,
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


def _seed_board(
    run_id: str,
    inventory: EvidenceInventory,
    claims: tuple[DeclaredClaim, ...],
    schema: EvidenceSchema,
) -> ConvergenceBoard:
    candidates = tuple(
        seed_usage_candidate(
            inventory,
            claim,
            schema=schema,
            candidate_id=f"cand_{index:03d}",
        )
        for index, claim in enumerate(claims, start=1)
    )
    board = ConvergenceBoard(
        board_id=f"{run_id}_board",
        run_id=run_id,
        inventory=inventory,
        claims=claims,
        candidates=candidates,
    )
    for candidate in candidates:
        board = _append_event(board, "candidate_seeded", candidate_id=candidate.candidate_id)
    return board


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


def _propose_patch(
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


def _finalize_report(
    *,
    run_id: str,
    inventory: EvidenceInventory,
    claims: tuple[DeclaredClaim, ...],
    candidates: tuple[EvidenceCandidate, ...],
    schema: EvidenceSchema,
) -> ConvergenceReport:
    claim_reports = tuple(
        _claim_report(claim, candidates, schema)
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
        evidence_convergence_status = "evidence_converged"
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
