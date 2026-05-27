import json


def test_evidence_atom_preserves_semantic_candidate_provenance():
    from evidence_toolchain import EvidenceAtom, EvidenceAtomType
    from evidence_toolchain.issues import EvidenceIssue

    atom = EvidenceAtom(
        atom_id="atom_001",
        atom_type=EvidenceAtomType.USAGE_AMOUNT,
        source_unit_ids=("unit_pdf_page_1_text", "unit_pdf_page_1_word_2"),
        source_artifact_ids=("artifact_pdf_page_1",),
        producer="regex_atomizer",
        text="사용량 6.4 MWh",
        label="사용량",
        value=6.4,
        unit="MWh",
        normalized={"value": 6400, "unit": "kWh"},
        normalization_hint={
            "dimension": "energy",
            "compatible_units": ["kWh", "MWh"],
        },
        confidence=0.86,
        metadata={"activity_hint": "electricity"},
        issues=(
            EvidenceIssue(
                code="normalized_is_best_effort",
                severity="info",
                message="Normalized values are helper fields, not final matching authority.",
            ),
        ),
    )
    payload = atom.to_dict()

    assert payload == {
        "atom_id": "atom_001",
        "atom_type": "usage_amount",
        "source_unit_ids": ["unit_pdf_page_1_text", "unit_pdf_page_1_word_2"],
        "source_artifact_ids": ["artifact_pdf_page_1"],
        "producer": "regex_atomizer",
        "text": "사용량 6.4 MWh",
        "label": "사용량",
        "value": 6.4,
        "unit": "MWh",
        "normalized": {"value": 6400, "unit": "kWh"},
        "normalization_hint": {
            "dimension": "energy",
            "compatible_units": ["kWh", "MWh"],
        },
        "confidence": 0.86,
        "metadata": {"activity_hint": "electricity"},
        "issues": [
            {
                "code": "normalized_is_best_effort",
                "severity": "info",
                "message": "Normalized values are helper fields, not final matching authority.",
            }
        ],
    }
    assert "x_id" not in payload
    assert "relation" not in payload
    assert "atom_status" not in payload
    json.dumps(payload)


def test_evidence_atom_type_vocabulary_is_llm_readable_and_closed_for_v0():
    from evidence_toolchain.atoms import EvidenceAtomType

    expected_types = (
        "document_type",
        "activity_identity",
        "usage_amount",
        "service_period",
        "site_identity",
        "supplier_identity",
        "meter_reading",
        "meter_delta",
        "line_item",
        "currency_amount",
        "date",
        "identifier",
        "table_row",
        "note",
        "unknown",
    )

    assert EvidenceAtomType.ALL == expected_types
    assert EvidenceAtomType.is_core_type("usage_amount") is True
    assert EvidenceAtomType.is_core_type("support_edge") is False


def test_atomizer_result_groups_atoms_without_resolution_edges():
    from evidence_toolchain import AtomizerResult, EvidenceAtom, EvidenceAtomType
    from evidence_toolchain.issues import EvidenceIssue

    amount_atom = EvidenceAtom(
        atom_id="atom_amount_001",
        atom_type=EvidenceAtomType.USAGE_AMOUNT,
        source_unit_ids=("unit_001",),
        source_artifact_ids=("artifact_001",),
        producer="table_atomizer",
        text="6.4 MWh",
        value=6.4,
        unit="MWh",
    )
    currency_atom = EvidenceAtom(
        atom_id="atom_currency_001",
        atom_type=EvidenceAtomType.CURRENCY_AMOUNT,
        source_unit_ids=("unit_002",),
        source_artifact_ids=("artifact_001",),
        producer="table_atomizer",
        text="1,230,000 KRW",
        value=1230000,
        unit="KRW",
    )
    result = AtomizerResult(
        bundle_id="bundle_001",
        atoms=(amount_atom, currency_atom),
        issues=(
            EvidenceIssue(
                code="atomizer_result_is_candidate_only",
                severity="info",
                message="Atomizer results do not decide support or contradiction.",
            ),
        ),
    )
    payload = result.to_dict()

    assert payload["bundle_id"] == "bundle_001"
    assert [atom["atom_type"] for atom in payload["atoms"]] == [
        "usage_amount",
        "currency_amount",
    ]
    assert payload["issues"][0]["code"] == "atomizer_result_is_candidate_only"
    assert all("relation" not in atom for atom in payload["atoms"])
    assert all("x_id" not in atom for atom in payload["atoms"])
    json.dumps(payload)


def test_readers_stay_below_evidence_atom_layer():
    from pathlib import Path

    source = Path("src/evidence_toolchain/readers.py").read_text(encoding="utf-8")

    assert "EvidenceAtom" not in source
    assert "AtomizerResult" not in source
