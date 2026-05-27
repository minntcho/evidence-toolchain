from pathlib import Path

from evidence_toolchain.atomizers import atomize_inventory
from evidence_toolchain.ingestion import EvidenceArtifact, EvidenceInventory, EvidenceUnit


CORE_FLOW_MODULES = (
    "src/evidence_toolchain/ingestion.py",
    "src/evidence_toolchain/file_routing.py",
    "src/evidence_toolchain/readers.py",
    "src/evidence_toolchain/atomizers.py",
    "src/evidence_toolchain/claims.py",
    "src/evidence_toolchain/resolution.py",
)


def test_core_flow_modules_do_not_auto_call_deterministic_normalizer():
    forbidden_snippets = (
        "DeterministicNormalizer",
        "from evidence_toolchain.normalizers",
        "import evidence_toolchain.normalizers",
    )

    for module_path in CORE_FLOW_MODULES:
        source = Path(module_path).read_text(encoding="utf-8")
        for forbidden in forbidden_snippets:
            assert forbidden not in source, f"{module_path} must not auto-wire {forbidden}"


def test_atomizer_output_keeps_normalization_as_hint_not_result():
    inventory = EvidenceInventory(
        bundle_id="bundle_001",
        attachments=(),
        artifacts=(
            EvidenceArtifact(
                artifact_id="artifact_page_1",
                artifact_type="pdf_page",
                parent_id=None,
                media_type="application/pdf-page",
                source_locator={"page": 1},
            ),
        ),
        units=(
            EvidenceUnit(
                unit_id="unit_001",
                artifact_id="artifact_page_1",
                unit_type="text_span",
                producer="test_reader",
                text="사용량 6.4 MWh",
            ),
        ),
        route_decisions=(),
    )

    result = atomize_inventory(inventory)

    assert len(result.atoms) == 1
    atom_payload = result.atoms[0].to_dict()
    assert atom_payload["normalization_hint"] == {
        "dimension": "energy",
        "compatible_units": ["kWh", "MWh"],
    }
    assert atom_payload["normalized"] is None
    assert "normalized_type" not in atom_payload
    assert "target_kind" not in atom_payload
