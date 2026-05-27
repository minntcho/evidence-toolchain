import json


def test_declared_claim_preserves_x_identity_without_evidence_judgment():
    from evidence_toolchain import DeclaredClaim

    claim = DeclaredClaim(
        x_id="x_001",
        claim_type="activity_usage",
        fields={
            "activity": "electricity",
            "amount": 6400,
            "unit": "kWh",
            "period": "2025-03",
            "site": "OCH-01",
        },
        metadata={"uploaded_by": "reviewer_001"},
    )
    payload = claim.to_dict()

    assert payload == {
        "x_id": "x_001",
        "claim_type": "activity_usage",
        "fields": {
            "activity": "electricity",
            "amount": 6400,
            "unit": "kWh",
            "period": "2025-03",
            "site": "OCH-01",
        },
        "metadata": {"uploaded_by": "reviewer_001"},
    }
    assert "atom_id" not in payload
    assert "relation" not in payload
    assert "status" not in payload
    json.dumps(payload)


def test_derive_need_spec_lowers_claim_into_llm_readable_needs():
    from evidence_toolchain import DeclaredClaim, NeedType, derive_need_spec

    claim = DeclaredClaim(
        x_id="x_001",
        claim_type="activity_usage",
        fields={
            "activity": "electricity",
            "activity_aliases": ("전력", "전기"),
            "amount": 6400,
            "unit": "kWh",
            "period": "2025-03",
            "site": "OCH-01",
            "site_aliases": ("오창 1공장", "Ochang Plant 1"),
            "supplier": "한국전력 예시",
        },
    )

    need_spec = derive_need_spec(claim)
    payload = need_spec.to_dict()

    assert payload["x_id"] == "x_001"
    assert [need["need_id"] for need in payload["needs"]] == [
        "activity_identity",
        "usage_amount",
        "service_period",
        "site_identity",
        "supplier_identity",
    ]
    assert [need["need_type"] for need in payload["needs"]] == [
        NeedType.ACTIVITY_IDENTITY,
        NeedType.USAGE_AMOUNT,
        NeedType.SERVICE_PERIOD,
        NeedType.SITE_IDENTITY,
        NeedType.SUPPLIER_IDENTITY,
    ]

    amount_need = need_spec.require_need("usage_amount")
    assert amount_need.required is True
    assert amount_need.target_value == 6400
    assert amount_need.target_unit == "kWh"
    assert amount_need.acceptable_units == ("kWh", "MWh")
    assert "사용량" in amount_need.preferred_labels

    period_need = need_spec.require_need("service_period")
    assert period_need.target_period == "2025-03"
    assert "사용기간" in period_need.preferred_labels
    assert "납부기한" in need_spec.disqualifiers
    assert "KRW" in need_spec.disqualifiers

    site_need = need_spec.require_need("site_identity")
    assert site_need.target_text == "OCH-01"
    assert site_need.acceptable_aliases == ("오창 1공장", "Ochang Plant 1")

    supplier_need = need_spec.require_need("supplier_identity")
    assert supplier_need.required is False
    assert supplier_need.target_text == "한국전력 예시"


def test_need_spec_is_not_resolution_or_atom_output():
    from evidence_toolchain import DeclaredClaim, derive_need_spec

    need_spec = derive_need_spec(
        DeclaredClaim(
            x_id="x_002",
            fields={"amount": 500, "unit": "L", "period": "2025-03"},
        )
    )
    payload = need_spec.to_dict()

    assert payload["producer"] == "default_need_spec_deriver"
    assert "atoms" not in payload
    assert "edges" not in payload
    assert "resolution" not in payload
    assert "supporting_y" not in payload
    assert all("source_unit_ids" not in need for need in payload["needs"])
    assert all("relation" not in need for need in payload["needs"])
    json.dumps(payload)
