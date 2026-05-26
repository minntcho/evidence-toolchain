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
