import json


def _inventory_with_units(*units):
    from evidence_toolchain.ingestion import (
        EvidenceArtifact,
        EvidenceInventory,
        RawAttachment,
        RouteDecision,
        SafetyDecision,
    )

    attachment = RawAttachment(
        attachment_id="raw_001",
        original_filename="bill.txt",
        path="bill.txt",
        byte_size=0,
        sha256="0" * 64,
        extension=".txt",
    )
    artifact = EvidenceArtifact(
        artifact_id="artifact_001",
        artifact_type="file",
        parent_id="raw_001",
        media_type="text/plain",
        source_locator={"file_name": "bill.txt"},
    )
    return EvidenceInventory(
        bundle_id="bundle_001",
        attachments=(attachment,),
        artifacts=(artifact,),
        units=units,
        route_decisions=(
            RouteDecision(
                attachment_id="raw_001",
                route="plain_text",
                confidence=0.9,
                matched_by=("extension:.txt",),
            ),
        ),
        safety_decisions=(
            SafetyDecision(
                attachment_id="raw_001",
                allowed=True,
                checked_by=("max_file_size:52428800",),
            ),
        ),
    )


def test_simple_text_atomizer_extracts_amount_currency_and_period_candidates():
    from evidence_toolchain import EvidenceAtomType
    from evidence_toolchain.atomizers import SimpleTextAtomizer
    from evidence_toolchain.ingestion import EvidenceUnit

    unit = EvidenceUnit(
        unit_id="unit_001",
        artifact_id="artifact_001",
        unit_type="text_span",
        producer="plain_text_reader",
        text="사용량 6.4 MWh\n청구금액 1,230,000 KRW\n사용기간 2025-03-01 ~ 2025-03-31",
        locator={"line": 1},
    )

    result = SimpleTextAtomizer().atomize(_inventory_with_units(unit))
    payload = result.to_dict()

    assert payload["bundle_id"] == "bundle_001"
    assert [atom["atom_type"] for atom in payload["atoms"]] == [
        EvidenceAtomType.USAGE_AMOUNT,
        EvidenceAtomType.CURRENCY_AMOUNT,
        EvidenceAtomType.SERVICE_PERIOD,
    ]
    usage_atom, currency_atom, period_atom = payload["atoms"]

    assert usage_atom == {
        "atom_id": "atom_bundle_001_001",
        "atom_type": "usage_amount",
        "source_unit_ids": ["unit_001"],
        "source_artifact_ids": ["artifact_001"],
        "producer": "simple_text_atomizer",
        "text": "사용량 6.4 MWh",
        "label": "사용량",
        "value": 6.4,
        "unit": "MWh",
        "normalized": None,
        "normalization_hint": {
            "dimension": "energy",
            "compatible_units": ["kWh", "MWh"],
        },
        "confidence": 0.7,
        "metadata": {"matched_pattern": "usage_amount_with_unit"},
        "issues": [],
    }
    assert currency_atom["atom_type"] == "currency_amount"
    assert currency_atom["label"] == "청구금액"
    assert currency_atom["value"] == 1230000
    assert currency_atom["unit"] == "KRW"
    assert currency_atom["normalization_hint"] == {
        "dimension": "currency",
        "compatible_units": ["KRW"],
    }
    assert period_atom["atom_type"] == "service_period"
    assert period_atom["label"] == "사용기간"
    assert period_atom["value"] == {
        "start": "2025-03-01",
        "end": "2025-03-31",
    }
    assert all("x_id" not in atom and "relation" not in atom for atom in payload["atoms"])
    json.dumps(payload)


def test_simple_text_atomizer_reads_text_span_and_table_cell_units_only():
    from evidence_toolchain.atomizers import SimpleTextAtomizer
    from evidence_toolchain.ingestion import EvidenceUnit

    table_cell = EvidenceUnit(
        unit_id="unit_cell_001",
        artifact_id="artifact_001",
        unit_type="table_cell",
        producer="delimited_table_reader",
        text="납부기한 2025-04-20",
        locator={"row": 2, "column": 4, "header": "납부기한"},
    )
    ignored_metadata = EvidenceUnit(
        unit_id="unit_meta_001",
        artifact_id="artifact_001",
        unit_type="metadata",
        producer="pdf_profile_reader",
        text="사용량 9.9 MWh",
    )

    result = SimpleTextAtomizer().atomize(
        _inventory_with_units(table_cell, ignored_metadata)
    )
    payload = result.to_dict()

    assert [atom["atom_type"] for atom in payload["atoms"]] == ["date"]
    assert payload["atoms"][0]["text"] == "납부기한 2025-04-20"
    assert payload["atoms"][0]["label"] == "납부기한"
    assert payload["atoms"][0]["value"] == "2025-04-20"
    assert payload["atoms"][0]["source_unit_ids"] == ["unit_cell_001"]


def test_atomize_inventory_uses_simple_text_atomizer_by_default():
    from evidence_toolchain import atomize_inventory
    from evidence_toolchain.ingestion import EvidenceUnit

    unit = EvidenceUnit(
        unit_id="unit_001",
        artifact_id="artifact_001",
        unit_type="text_span",
        producer="plain_text_reader",
        text="전력 사용량 6400 kWh",
    )

    result = atomize_inventory(_inventory_with_units(unit))
    payload = result.to_dict()

    assert payload["atoms"][0]["atom_type"] == "usage_amount"
    assert payload["atoms"][0]["producer"] == "simple_text_atomizer"
