from pathlib import Path


def test_purpose_and_boundaries_doc_is_indexed_and_domain_neutral():
    doc_path = Path("docs/purpose-and-boundaries.md")

    assert doc_path.exists()

    doc = doc_path.read_text(encoding="utf-8")
    index = Path("docs/index.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "domain-neutral evidence-input consistency" in doc
    assert "does not make final domain decisions" in doc
    assert "purpose-and-boundaries.md" in index
    assert "Purpose and boundaries" in readme


def test_purpose_doc_keeps_consumer_examples_outside_core_identity():
    doc = Path("docs/purpose-and-boundaries.md").read_text(encoding="utf-8")

    assert "Consumer examples are examples, not core identity." in doc
    assert "Core terms stay neutral" in doc


def test_contract_docs_are_indexed_and_define_allowed_boundaries():
    contract_docs = [
        "evidence-document.md",
        "declared-input.md",
        "extracted-field.md",
        "evidence-check.md",
        "evidence-report.md",
    ]
    docs_index = Path("docs/index.md").read_text(encoding="utf-8")
    contracts_index = Path("docs/contracts/README.md")

    assert contracts_index.exists()

    contracts_text = contracts_index.read_text(encoding="utf-8")
    assert "Contract documents define behavior, not downstream policy." in contracts_text
    assert "contracts/README.md" in docs_index

    for filename in contract_docs:
        path = Path("docs/contracts") / filename
        assert path.exists(), f"missing {path}"
        text = path.read_text(encoding="utf-8")
        assert "May" in text
        assert "Must not" in text
        assert "Downstream" in text
