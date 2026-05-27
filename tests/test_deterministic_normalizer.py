import json


def test_deterministic_normalizer_converts_energy_atom_to_canonical_kwh():
    from evidence_toolchain import (
        DeterministicNormalizer,
        EvidenceAtom,
        EvidenceAtomType,
        NormalizationAdapter,
        NormalizedType,
    )

    normalizer = DeterministicNormalizer()
    results = normalizer.normalize_atom_value(
        EvidenceAtom(
            atom_id="atom_usage_001",
            atom_type=EvidenceAtomType.USAGE_AMOUNT,
            source_unit_ids=("unit_001",),
            source_artifact_ids=("artifact_001",),
            producer="simple_text_atomizer",
            text="사용량 6.4 MWh",
            value=6.4,
            unit="MWh",
        )
    )
    payload = results[0].to_dict()

    assert isinstance(normalizer, NormalizationAdapter)
    assert payload == {
        "target_id": "atom_usage_001",
        "target_kind": "atom",
        "normalized_type": NormalizedType.QUANTITY,
        "normalized": {
            "value": 6400,
            "unit": "kWh",
            "dimension": "energy",
            "source_value": 6.4,
            "source_unit": "MWh",
            "original_text": "사용량 6.4 MWh",
            "metadata": {"conversion": "MWh_to_kWh"},
        },
        "producer": "deterministic_normalizer_v0",
        "confidence": 1.0,
        "issues": [],
        "metadata": {},
    }
    assert "relation" not in payload
    assert "status" not in payload
    json.dumps(payload)


def test_deterministic_normalizer_converts_claim_usage_need_to_quantity():
    from evidence_toolchain import DeterministicNormalizer, Need, NeedType, NormalizedType

    results = DeterministicNormalizer().normalize_claim_need(
        Need(
            need_id="usage_amount",
            need_type=NeedType.USAGE_AMOUNT,
            target_value=6400,
            target_unit="kWh",
        )
    )
    payload = results[0].to_dict()

    assert payload["target_id"] == "usage_amount"
    assert payload["target_kind"] == "need"
    assert payload["normalized_type"] == NormalizedType.QUANTITY
    assert payload["normalized"] == {
        "value": 6400,
        "unit": "kWh",
        "dimension": "energy",
        "source_value": 6400,
        "source_unit": "kWh",
        "original_text": None,
        "metadata": {},
    }
    assert "edge_id" not in payload
    assert "relation" not in payload


def test_deterministic_normalizer_keeps_currency_separate_from_quantity():
    from evidence_toolchain import DeterministicNormalizer, EvidenceAtom, EvidenceAtomType, NormalizedType

    results = DeterministicNormalizer().normalize_atom_value(
        EvidenceAtom(
            atom_id="atom_currency_001",
            atom_type=EvidenceAtomType.CURRENCY_AMOUNT,
            source_unit_ids=("unit_002",),
            source_artifact_ids=("artifact_001",),
            producer="simple_text_atomizer",
            text="청구금액 1,230,000 KRW",
            value=1230000,
            unit="KRW",
        )
    )
    payload = results[0].to_dict()

    assert payload["target_kind"] == "atom"
    assert payload["normalized_type"] == NormalizedType.CURRENCY
    assert payload["normalized"] == {
        "value": 1230000,
        "currency": "KRW",
        "original_text": "청구금액 1,230,000 KRW",
        "metadata": {},
    }
    assert payload["issues"] == []
    assert payload["normalized_type"] != NormalizedType.QUANTITY


def test_deterministic_normalizer_converts_month_need_to_period():
    from evidence_toolchain import DeterministicNormalizer, Need, NeedType, NormalizedType

    results = DeterministicNormalizer().normalize_claim_need(
        Need(
            need_id="service_period",
            need_type=NeedType.SERVICE_PERIOD,
            target_period="2025-03",
        )
    )
    payload = results[0].to_dict()

    assert payload["target_id"] == "service_period"
    assert payload["target_kind"] == "need"
    assert payload["normalized_type"] == NormalizedType.PERIOD
    assert payload["normalized"] == {
        "start_date": "2025-03-01",
        "end_date": "2025-03-31",
        "granularity": "month",
        "original_text": "2025-03",
        "metadata": {},
    }


def test_deterministic_normalizer_converts_period_and_date_atoms():
    from evidence_toolchain import DeterministicNormalizer, EvidenceAtom, EvidenceAtomType, NormalizedType

    normalizer = DeterministicNormalizer()
    period_results = normalizer.normalize_atom_value(
        EvidenceAtom(
            atom_id="atom_period_001",
            atom_type=EvidenceAtomType.SERVICE_PERIOD,
            source_unit_ids=("unit_003",),
            source_artifact_ids=("artifact_001",),
            producer="simple_text_atomizer",
            text="사용기간 2025-03-01 ~ 2025-03-31",
            value={"start": "2025-03-01", "end": "2025-03-31"},
        )
    )
    date_results = normalizer.normalize_atom_value(
        EvidenceAtom(
            atom_id="atom_date_001",
            atom_type=EvidenceAtomType.DATE,
            source_unit_ids=("unit_004",),
            source_artifact_ids=("artifact_001",),
            producer="simple_text_atomizer",
            text="납부기한 2025-04-20",
            label="납부기한",
            value="2025-04-20",
        )
    )

    period_payload = period_results[0].to_dict()
    date_payload = date_results[0].to_dict()

    assert period_payload["normalized_type"] == NormalizedType.PERIOD
    assert period_payload["normalized"]["start_date"] == "2025-03-01"
    assert period_payload["normalized"]["end_date"] == "2025-03-31"
    assert date_payload["normalized_type"] == NormalizedType.DATE
    assert date_payload["normalized"]["date"] == "2025-04-20"
    assert date_payload["normalized"]["date_role"] == "payment_due_date"


def test_deterministic_normalizer_returns_no_result_for_ambiguous_identifier():
    from evidence_toolchain import DeterministicNormalizer, Need, NeedType

    results = DeterministicNormalizer().normalize_claim_need(
        Need(
            need_id="site_identity",
            need_type=NeedType.SITE_IDENTITY,
            target_text="OCH-01",
            acceptable_aliases=("오창 1공장",),
        )
    )

    assert results == ()
