SITE = 1 << 0
PERIOD = 1 << 1
ACTIVITY = 1 << 2
QUANTITY = 1 << 3
UNIT = 1 << 4


def _usage_schema(*, directly_comparable_mask: int = 0):
    from evidence_toolchain.convergence import EvidenceSchema, SlotDef

    return EvidenceSchema(
        schema_id="utility_usage_record.v1",
        slots=(
            SlotDef(
                "site",
                SITE,
                "identifier",
                directly_comparable=bool(directly_comparable_mask & SITE),
                provenance_required=False,
            ),
            SlotDef(
                "period",
                PERIOD,
                "period",
                comparable=True,
                directly_comparable=bool(directly_comparable_mask & PERIOD),
                provenance_required=False,
            ),
            SlotDef(
                "activity",
                ACTIVITY,
                "identifier",
                directly_comparable=bool(directly_comparable_mask & ACTIVITY),
                provenance_required=False,
            ),
            SlotDef(
                "quantity",
                QUANTITY,
                "quantity",
                comparable=True,
                directly_comparable=bool(directly_comparable_mask & QUANTITY),
                provenance_required=False,
            ),
            SlotDef(
                "unit",
                UNIT,
                "unit",
                comparable=True,
                directly_comparable=bool(directly_comparable_mask & UNIT),
                provenance_required=False,
            ),
        ),
    )


def _candidate(mask_state):
    from evidence_toolchain.convergence import EvidenceCandidate

    return EvidenceCandidate(
        candidate_id="cand_001",
        claim_id="claim_001",
        schema_id="utility_usage_record.v1",
        mask_state=mask_state,
    )


def _capability(name, *, handles_gap_kinds, handles_mask=QUANTITY, input_required_mask=0, cost=10, kind="deterministic"):
    from evidence_toolchain.convergence import CapabilitySpec

    return CapabilitySpec(
        name=name,
        handles_mask=handles_mask,
        input_required_mask=input_required_mask,
        handles_gap_kinds=frozenset(handles_gap_kinds),
        cost=cost,
        kind=kind,
    )


def test_compute_candidate_gap_reports_missing_slots_before_later_gap_kinds():
    from evidence_toolchain.convergence import CandidateMaskState, compute_candidate_gap

    gap = compute_candidate_gap(
        _candidate(CandidateMaskState()),
        _usage_schema(),
    )

    assert gap.missing_mask == SITE | PERIOD | ACTIVITY | QUANTITY | UNIT
    assert gap.unassigned_mask == 0
    assert gap.unnormalized_mask == 0
    assert gap.unaligned_mask == 0


def test_compute_candidate_gap_reports_unassigned_present_slots():
    from evidence_toolchain.convergence import CandidateMaskState, compute_candidate_gap

    gap = compute_candidate_gap(
        _candidate(CandidateMaskState(present_mask=QUANTITY)),
        _usage_schema(),
    )

    assert gap.missing_mask == SITE | PERIOD | ACTIVITY | UNIT
    assert gap.unassigned_mask == QUANTITY
    assert gap.unnormalized_mask == 0
    assert gap.unaligned_mask == 0


def test_compute_candidate_gap_reports_unnormalized_assigned_comparable_slots():
    from evidence_toolchain.convergence import CandidateMaskState, compute_candidate_gap

    gap = compute_candidate_gap(
        _candidate(CandidateMaskState(present_mask=QUANTITY, assigned_mask=QUANTITY)),
        _usage_schema(),
    )

    assert gap.unassigned_mask == 0
    assert gap.unnormalized_mask == QUANTITY
    assert gap.unaligned_mask == 0


def test_compute_candidate_gap_reports_unaligned_once_normalized_or_directly_comparable():
    from evidence_toolchain.convergence import CandidateMaskState, compute_candidate_gap

    normalized_gap = compute_candidate_gap(
        _candidate(
            CandidateMaskState(
                present_mask=QUANTITY,
                assigned_mask=QUANTITY,
                normalized_mask=QUANTITY,
            )
        ),
        _usage_schema(),
    )
    direct_gap = compute_candidate_gap(
        _candidate(CandidateMaskState(present_mask=SITE, assigned_mask=SITE)),
        _usage_schema(directly_comparable_mask=SITE),
    )

    assert normalized_gap.unnormalized_mask == 0
    assert normalized_gap.unaligned_mask == QUANTITY
    assert direct_gap.unnormalized_mask == 0
    assert direct_gap.unaligned_mask == SITE


def test_select_capabilities_uses_gap_kind_not_only_slot_overlap():
    from evidence_toolchain.convergence import CandidateMaskState, compute_candidate_gap, select_capabilities

    candidate = _candidate(CandidateMaskState(present_mask=QUANTITY, assigned_mask=QUANTITY))
    gap = compute_candidate_gap(candidate, _usage_schema())
    assigner = _capability(
        "simple_slot_assigner",
        handles_gap_kinds={"unassigned"},
        handles_mask=QUANTITY,
        cost=1,
    )
    normalizer = _capability(
        "deterministic_normalizer",
        handles_gap_kinds={"unnormalized"},
        handles_mask=QUANTITY,
        input_required_mask=QUANTITY,
        cost=5,
    )

    selected = select_capabilities(candidate, gap, (assigner, normalizer))

    assert selected == (normalizer,)


def test_select_capabilities_uses_aligner_for_unaligned_gap():
    from evidence_toolchain.convergence import CandidateMaskState, compute_candidate_gap, select_capabilities

    candidate = _candidate(
        CandidateMaskState(
            present_mask=QUANTITY,
            assigned_mask=QUANTITY,
            normalized_mask=QUANTITY,
        )
    )
    gap = compute_candidate_gap(candidate, _usage_schema())
    normalizer = _capability("deterministic_normalizer", handles_gap_kinds={"unnormalized"})
    aligner = _capability(
        "simple_aligner",
        handles_gap_kinds={"unaligned"},
        input_required_mask=QUANTITY,
    )

    selected = select_capabilities(candidate, gap, (normalizer, aligner))

    assert selected == (aligner,)


def test_select_capabilities_filters_unsatisfied_input_requirements():
    from evidence_toolchain.convergence import CandidateMaskState, compute_candidate_gap, select_capabilities

    candidate = _candidate(CandidateMaskState(present_mask=QUANTITY, assigned_mask=QUANTITY))
    gap = compute_candidate_gap(candidate, _usage_schema())
    blocked = _capability(
        "period_aware_normalizer",
        handles_gap_kinds={"unnormalized"},
        input_required_mask=QUANTITY | PERIOD,
    )

    selected = select_capabilities(candidate, gap, (blocked,))

    assert selected == ()


def test_select_capabilities_orders_deterministic_lower_cost_before_llm():
    from evidence_toolchain.convergence import CandidateMaskState, compute_candidate_gap, select_capabilities

    candidate = _candidate(CandidateMaskState(present_mask=QUANTITY, assigned_mask=QUANTITY))
    gap = compute_candidate_gap(candidate, _usage_schema())
    llm = _capability(
        "future_llm_normalizer",
        handles_gap_kinds={"unnormalized"},
        input_required_mask=QUANTITY,
        cost=1,
        kind="llm",
    )
    deterministic = _capability(
        "deterministic_normalizer",
        handles_gap_kinds={"unnormalized"},
        input_required_mask=QUANTITY,
        cost=5,
        kind="deterministic",
    )

    selected = select_capabilities(candidate, gap, (llm, deterministic))

    assert selected == (deterministic, llm)
