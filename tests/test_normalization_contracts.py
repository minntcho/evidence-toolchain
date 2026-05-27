import json


def test_normalization_vocabularies_are_closed_for_v0():
    from evidence_toolchain import NormalizationTargetKind, NormalizedType

    assert NormalizationTargetKind.ALL == ("atom", "need", "claim")
    assert NormalizationTargetKind.is_core_kind("atom") is True
    assert NormalizationTargetKind.is_core_kind("edge") is False

    assert NormalizedType.ALL == (
        "quantity",
        "period",
        "date",
        "currency",
        "identifier",
        "unknown",
    )
    assert NormalizedType.is_core_type("quantity") is True
    assert NormalizedType.is_core_type("support") is False


def test_normalized_quantity_preserves_source_and_dimension_without_judgment():
    from evidence_toolchain import NormalizedQuantity

    normalized = NormalizedQuantity(
        value=6400,
        unit="kWh",
        dimension="energy",
        source_value=6.4,
        source_unit="MWh",
        original_text="6.4 MWh",
        metadata={"conversion": "MWh_to_kWh"},
    )
    payload = normalized.to_dict()

    assert payload == {
        "value": 6400,
        "unit": "kWh",
        "dimension": "energy",
        "source_value": 6.4,
        "source_unit": "MWh",
        "original_text": "6.4 MWh",
        "metadata": {"conversion": "MWh_to_kWh"},
    }
    assert "relation" not in payload
    assert "status" not in payload
    assert "x_id" not in payload
    json.dumps(payload)


def test_normalized_temporal_currency_and_identifier_values_are_json_shapes():
    from evidence_toolchain import (
        NormalizedCurrency,
        NormalizedDate,
        NormalizedIdentifier,
        NormalizedPeriod,
    )

    period = NormalizedPeriod(
        start_date="2025-03-01",
        end_date="2025-03-31",
        granularity="month",
        original_text="2025년 3월 사용분",
    )
    date = NormalizedDate(
        date="2025-04-20",
        date_role="payment_due_date",
        original_text="납부기한 2025-04-20",
    )
    currency = NormalizedCurrency(
        value=1230000,
        currency="KRW",
        original_text="1,230,000 KRW",
    )
    identifier = NormalizedIdentifier(
        value="OCH-01",
        namespace="site",
        original_text="오창 1공장",
    )

    payload = {
        "period": period.to_dict(),
        "date": date.to_dict(),
        "currency": currency.to_dict(),
        "identifier": identifier.to_dict(),
    }

    assert payload["period"]["start_date"] == "2025-03-01"
    assert payload["period"]["end_date"] == "2025-03-31"
    assert payload["date"]["date_role"] == "payment_due_date"
    assert payload["currency"]["currency"] == "KRW"
    assert payload["identifier"]["namespace"] == "site"
    assert all("relation" not in item for item in payload.values())
    json.dumps(payload)


def test_normalization_result_targets_atom_or_need_without_resolution_edge():
    from evidence_toolchain import (
        NormalizationResult,
        NormalizationTargetKind,
        NormalizedQuantity,
        NormalizedType,
    )
    from evidence_toolchain.issues import EvidenceIssue

    result = NormalizationResult(
        target_id="atom_001",
        target_kind=NormalizationTargetKind.ATOM,
        normalized_type=NormalizedType.QUANTITY,
        normalized=NormalizedQuantity(
            value=6400,
            unit="kWh",
            dimension="energy",
            source_value=6.4,
            source_unit="MWh",
            original_text="6.4 MWh",
        ),
        producer="deterministic_quantity_normalizer",
        confidence=1.0,
        issues=(
            EvidenceIssue(
                code="unit_converted",
                severity="info",
                message="MWh was converted to kWh for comparison.",
            ),
        ),
    )
    payload = result.to_dict()

    assert payload == {
        "target_id": "atom_001",
        "target_kind": "atom",
        "normalized_type": "quantity",
        "normalized": {
            "value": 6400,
            "unit": "kWh",
            "dimension": "energy",
            "source_value": 6.4,
            "source_unit": "MWh",
            "original_text": "6.4 MWh",
            "metadata": {},
        },
        "producer": "deterministic_quantity_normalizer",
        "confidence": 1.0,
        "issues": [
            {
                "code": "unit_converted",
                "severity": "info",
                "message": "MWh was converted to kWh for comparison.",
            }
        ],
        "metadata": {},
    }
    assert "edge_id" not in payload
    assert "relation" not in payload
    assert "status" not in payload
    json.dumps(payload)


def test_normalization_adapter_protocol_describes_tool_boundary():
    from evidence_toolchain import (
        EvidenceAtom,
        EvidenceAtomType,
        Need,
        NeedType,
        NormalizationAdapter,
        NormalizationResult,
        NormalizationTargetKind,
        NormalizedQuantity,
        NormalizedType,
    )

    class FixtureNormalizer:
        producer = "fixture_normalizer"

        def normalize_atom_value(self, atom: EvidenceAtom) -> tuple[NormalizationResult, ...]:
            return (
                NormalizationResult(
                    target_id=atom.atom_id,
                    target_kind=NormalizationTargetKind.ATOM,
                    normalized_type=NormalizedType.QUANTITY,
                    normalized=NormalizedQuantity(
                        value=6400,
                        unit="kWh",
                        dimension="energy",
                        source_value=atom.value,
                        source_unit=atom.unit,
                        original_text=atom.text,
                    ),
                    producer=self.producer,
                ),
            )

        def normalize_claim_need(self, need: Need) -> tuple[NormalizationResult, ...]:
            return (
                NormalizationResult(
                    target_id=need.need_id,
                    target_kind=NormalizationTargetKind.NEED,
                    normalized_type=NormalizedType.QUANTITY,
                    normalized=NormalizedQuantity(
                        value=need.target_value,
                        unit=need.target_unit,
                        dimension="energy",
                    ),
                    producer=self.producer,
                ),
            )

    adapter = FixtureNormalizer()
    atom_results = adapter.normalize_atom_value(
        EvidenceAtom(
            atom_id="atom_001",
            atom_type=EvidenceAtomType.USAGE_AMOUNT,
            source_unit_ids=("unit_001",),
            source_artifact_ids=("artifact_001",),
            producer="regex_atomizer",
            text="6.4 MWh",
            value=6.4,
            unit="MWh",
        )
    )
    need_results = adapter.normalize_claim_need(
        Need(
            need_id="usage_amount",
            need_type=NeedType.USAGE_AMOUNT,
            target_value=6400,
            target_unit="kWh",
        )
    )

    assert isinstance(adapter, NormalizationAdapter)
    assert atom_results[0].target_kind == "atom"
    assert need_results[0].target_kind == "need"
    assert atom_results[0].to_dict()["normalized"]["unit"] == "kWh"
