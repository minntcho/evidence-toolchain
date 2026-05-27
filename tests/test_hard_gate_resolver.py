import json


def test_hard_gate_resolver_supports_usage_after_unit_normalization_and_period():
    from evidence_toolchain import (
        DeclaredClaim,
        EvidenceAtom,
        EvidenceAtomType,
        HardGateResolver,
        Need,
        NeedSpec,
        NeedType,
        NormalizationResult,
        NormalizationTargetKind,
        NormalizedPeriod,
        NormalizedQuantity,
        NormalizedType,
        ResolutionRelation,
        ResolutionStatus,
    )

    claim = DeclaredClaim(x_id="x_001", fields={"amount": 6400, "unit": "kWh", "period": "2025-03"})
    need_spec = NeedSpec(
        x_id="x_001",
        needs=(
            Need(
                need_id=NeedType.USAGE_AMOUNT,
                need_type=NeedType.USAGE_AMOUNT,
                target_value=6400,
                target_unit="kWh",
            ),
            Need(
                need_id=NeedType.SERVICE_PERIOD,
                need_type=NeedType.SERVICE_PERIOD,
                target_period="2025-03",
            ),
        ),
    )
    usage_atom = EvidenceAtom(
        atom_id="atom_usage",
        atom_type=EvidenceAtomType.USAGE_AMOUNT,
        source_unit_ids=("unit_usage",),
        source_artifact_ids=("artifact_pdf_page_1",),
        producer="simple_text_atomizer",
        text="사용량 6.4 MWh",
        value=6.4,
        unit="MWh",
    )
    period_atom = EvidenceAtom(
        atom_id="atom_period",
        atom_type=EvidenceAtomType.SERVICE_PERIOD,
        source_unit_ids=("unit_period",),
        source_artifact_ids=("artifact_pdf_page_1",),
        producer="simple_text_atomizer",
        text="사용기간 2025-03-01 ~ 2025-03-31",
        value={"start": "2025-03-01", "end": "2025-03-31"},
    )
    normalizations = (
        NormalizationResult(
            target_id=NeedType.USAGE_AMOUNT,
            target_kind=NormalizationTargetKind.NEED,
            normalized_type=NormalizedType.QUANTITY,
            normalized=NormalizedQuantity(
                value=6400,
                unit="kWh",
                dimension="energy",
                source_value=6400,
                source_unit="kWh",
            ),
            producer="test_normalizer",
        ),
        NormalizationResult(
            target_id=NeedType.SERVICE_PERIOD,
            target_kind=NormalizationTargetKind.NEED,
            normalized_type=NormalizedType.PERIOD,
            normalized=NormalizedPeriod(
                start_date="2025-03-01",
                end_date="2025-03-31",
                granularity="month",
            ),
            producer="test_normalizer",
        ),
        NormalizationResult(
            target_id="atom_usage",
            target_kind=NormalizationTargetKind.ATOM,
            normalized_type=NormalizedType.QUANTITY,
            normalized=NormalizedQuantity(
                value=6400,
                unit="kWh",
                dimension="energy",
                source_value=6.4,
                source_unit="MWh",
                original_text="사용량 6.4 MWh",
                metadata={"conversion": "MWh_to_kWh"},
            ),
            producer="test_normalizer",
        ),
        NormalizationResult(
            target_id="atom_period",
            target_kind=NormalizationTargetKind.ATOM,
            normalized_type=NormalizedType.PERIOD,
            normalized=NormalizedPeriod(
                start_date="2025-03-01",
                end_date="2025-03-31",
                granularity="month",
                original_text="사용기간 2025-03-01 ~ 2025-03-31",
            ),
            producer="test_normalizer",
        ),
    )

    graph = HardGateResolver().resolve(
        bundle_id="bundle_001",
        claims=(claim,),
        need_specs=(need_spec,),
        atoms=(usage_atom, period_atom),
        normalization_results=normalizations,
    )
    payload = graph.to_dict()

    assert payload["metadata"]["producer"] == "hard_gate_resolver_v0"
    assert payload["claim_ids"] == ["x_001"]
    assert payload["atom_ids"] == ["atom_usage", "atom_period"]
    assert [edge["relation"] for edge in payload["edges"]] == [
        ResolutionRelation.SUPPORTS_AFTER_UNIT_NORMALIZATION,
        ResolutionRelation.SUPPORTS,
    ]
    assert payload["edges"][0]["need_id"] == NeedType.USAGE_AMOUNT
    assert payload["edges"][0]["metadata"]["hard_gate"] == "quantity_equal_after_normalization"
    assert payload["resolutions"][0]["status"] == ResolutionStatus.SUPPORTED_AFTER_UNIT_NORMALIZATION
    assert payload["resolutions"][0]["supporting_atom_ids"] == ["atom_usage", "atom_period"]
    assert payload["resolutions"][0]["missing_need_ids"] == []
    json.dumps(payload)


def test_hard_gate_resolver_rejects_currency_for_usage_need_and_marks_missing():
    from evidence_toolchain import (
        DeclaredClaim,
        EvidenceAtom,
        EvidenceAtomType,
        HardGateResolver,
        Need,
        NeedSpec,
        NeedType,
        NormalizationResult,
        NormalizationTargetKind,
        NormalizedCurrency,
        NormalizedQuantity,
        NormalizedType,
        ResolutionRelation,
        ResolutionStatus,
    )

    claim = DeclaredClaim(x_id="x_002", fields={"amount": 6400, "unit": "kWh"})
    need_spec = NeedSpec(
        x_id="x_002",
        needs=(
            Need(
                need_id=NeedType.USAGE_AMOUNT,
                need_type=NeedType.USAGE_AMOUNT,
                target_value=6400,
                target_unit="kWh",
            ),
        ),
    )
    currency_atom = EvidenceAtom(
        atom_id="atom_currency",
        atom_type=EvidenceAtomType.CURRENCY_AMOUNT,
        source_unit_ids=("unit_currency",),
        source_artifact_ids=("artifact_pdf_page_1",),
        producer="simple_text_atomizer",
        text="청구금액 1,230,000 KRW",
        value=1230000,
        unit="KRW",
    )

    graph = HardGateResolver().resolve(
        bundle_id="bundle_001",
        claims=(claim,),
        need_specs=(need_spec,),
        atoms=(currency_atom,),
        normalization_results=(
            NormalizationResult(
                target_id=NeedType.USAGE_AMOUNT,
                target_kind=NormalizationTargetKind.NEED,
                normalized_type=NormalizedType.QUANTITY,
                normalized=NormalizedQuantity(value=6400, unit="kWh", dimension="energy"),
                producer="test_normalizer",
            ),
            NormalizationResult(
                target_id="atom_currency",
                target_kind=NormalizationTargetKind.ATOM,
                normalized_type=NormalizedType.CURRENCY,
                normalized=NormalizedCurrency(value=1230000, currency="KRW"),
                producer="test_normalizer",
            ),
        ),
    )
    payload = graph.to_dict()

    assert payload["edges"][0]["relation"] == ResolutionRelation.REJECTED_FOR_NEED
    assert payload["edges"][0]["metadata"]["reason"] == "currency_value_not_usage_quantity"
    assert payload["resolutions"][0]["status"] == ResolutionStatus.INSUFFICIENT
    assert payload["resolutions"][0]["supporting_atom_ids"] == []
    assert payload["resolutions"][0]["rejected_atom_ids"] == ["atom_currency"]
    assert payload["resolutions"][0]["missing_need_ids"] == [NeedType.USAGE_AMOUNT]


def test_hard_gate_resolver_does_not_import_or_call_deterministic_normalizer():
    from pathlib import Path

    source = Path("src/evidence_toolchain/resolution.py").read_text(encoding="utf-8")

    assert "DeterministicNormalizer" not in source
    assert "from evidence_toolchain.normalizers" not in source
    assert "import evidence_toolchain.normalizers" not in source
