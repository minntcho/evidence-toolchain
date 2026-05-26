from pathlib import Path


def test_purpose_and_boundaries_doc_is_indexed_and_domain_neutral():
    doc_path = Path("docs/purpose-and-boundaries.md")

    assert doc_path.exists()

    doc = doc_path.read_text(encoding="utf-8")
    index = Path("docs/index.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "도메인 중립적인 증거-입력 일관성" in doc
    assert "최종 도메인 판단을 내리지 않는다" in doc
    assert "purpose-and-boundaries.md" in index
    assert "목적과 경계" in readme


def test_purpose_doc_keeps_consumer_examples_outside_core_identity():
    doc = Path("docs/purpose-and-boundaries.md").read_text(encoding="utf-8")

    assert "소비자 예시는 예시일 뿐 코어 정체성이 아니다." in doc
    assert "코어 용어는 중립적으로 유지한다" in doc


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
    assert "계약 문서는 동작을 정의하지 Downstream 정책을 정의하지 않는다." in contracts_text
    assert "contracts/README.md" in docs_index

    for filename in contract_docs:
        path = Path("docs/contracts") / filename
        assert path.exists(), f"missing {path}"
        text = path.read_text(encoding="utf-8")
        assert "포함할 수 있는 것" in text
        assert "해서는 안 되는 일" in text
        assert "Downstream" in text


def test_testing_strategy_docs_are_indexed_and_preserve_test_authority():
    strategy_docs = [
        "synthetic-evidence-cases.md",
        "router-planner-test-strategy.md",
        "failure-mode-test-strategy.md",
    ]
    docs_index = Path("docs/index.md").read_text(encoding="utf-8")
    testing_index = Path("docs/testing/README.md")

    assert testing_index.exists()

    testing_text = testing_index.read_text(encoding="utf-8")
    assert "테스트 문서는 검증 전략을 설명하지 runtime authority를 정의하지 않는다." in testing_text
    assert "testing/README.md" in docs_index

    for filename in strategy_docs:
        path = Path("docs/testing") / filename
        assert path.exists(), f"missing {path}"
        text = path.read_text(encoding="utf-8")
        assert "강하게 assert할 것" in text
        assert "freeze하지 말아야 할 것" in text
        assert "해서는 안 되는 일" in text


def test_generated_case_bundle_contract_is_indexed_and_scope_limited():
    doc_path = Path("docs/testing/generated-case-bundle-contract.md")
    testing_index = Path("docs/testing/README.md").read_text(encoding="utf-8")

    assert doc_path.exists()
    assert "generated-case-bundle-contract.md" in testing_index

    text = doc_path.read_text(encoding="utf-8")
    assert "case directory" in text
    assert "evidence.<ext>" in text
    assert "expected.json" in text
    assert "Ground truth" in text
    assert "Expected toolchain behavior" in text
    assert "해서는 안 되는 일" in text
    assert "Downstream" in text


def test_orchestration_boundary_doc_is_indexed_and_framework_neutral():
    doc_path = Path("docs/orchestration-boundary.md")
    docs_index = Path("docs/index.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")

    assert doc_path.exists()
    assert "orchestration-boundary.md" in docs_index
    assert "오케스트레이션 경계" in readme

    text = doc_path.read_text(encoding="utf-8")
    assert "오케스트레이션 중립적인 증거 의미론" in text
    assert "local runner" in text
    assert "framework adapters" in text
    assert "EvidenceRunState" in text
    assert "EvidenceEvent" in text
    assert "CheckpointStore" in text
    assert "해서는 안 되는 일" in text
    assert "Downstream" in text


def test_supporting_architecture_docs_are_localized_and_indexed():
    docs_index = Path("docs/index.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")

    expectations = {
        "docs/evidence-routing.md": [
            "증거 라우팅",
            "먼저 관찰한다",
            "최종 validation judgment를 내리면 안 됩니다",
        ],
        "docs/capability-registry.md": [
            "Capability registry",
            "Capability는 단순한 function이 아닙니다",
            "문서화된 한계가 없는 capability",
        ],
        "docs/failure-modes.md": [
            "Failure mode",
            "Failure mode는 first-class output입니다",
            "Downstream policy verdict가 되면 안 됩니다",
        ],
        "docs/adapter-boundary.md": [
            "Adapter 경계",
            "Core package는 독립적으로 유지되어야 합니다",
            "Core는 최종 validation status를 결정하면 안 됩니다",
        ],
        "docs/synthetic-evidence.md": [
            "Synthetic evidence testkit",
            "Synthetic case는 runtime authority를 정의하지 않습니다",
            "truth와 expected behavior를 분리합니다",
        ],
    }

    for doc_path, anchors in expectations.items():
        path = Path(doc_path)
        assert path.exists(), f"missing {path}"
        assert path.name in docs_index
        for anchor in anchors:
            assert anchor in path.read_text(encoding="utf-8")

    assert "Capability registry" in readme
    assert "Adapter 경계" in readme
    assert "Synthetic evidence testkit" in readme
