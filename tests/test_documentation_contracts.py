import re
from pathlib import Path


def _markdown_labels(*paths: str) -> set[str]:
    labels: set[str] = set()
    link_pattern = re.compile(r"\[([^\]]+)\]\([^)]+\)")
    for path in paths:
        text = Path(path).read_text(encoding="utf-8")
        for line in text.splitlines():
            if line.startswith("#"):
                labels.add(line.lstrip("#").strip())
            labels.update(link_pattern.findall(line))
    return labels


def test_document_heading_and_navigation_labels_are_korean():
    labels = _markdown_labels(
        "README.md",
        "docs/index.md",
        "docs/capability-registry.md",
        "docs/failure-modes.md",
        "docs/adapter-boundary.md",
        "docs/evidence-routing.md",
        "docs/orchestration-boundary.md",
        "docs/investigation-loop-boundary.md",
        "docs/synthetic-evidence.md",
        "docs/ingestion-normalization.md",
        "docs/contracts/evidence-check.md",
        "docs/testing/generated-case-bundle-contract.md",
        "docs/testing/failure-mode-test-strategy.md",
        "docs/testing/README.md",
        "docs/testing/synthetic-evidence-cases.md",
        "synthetic/README.md",
    )

    expected_labels = {
        "Capability 레지스트리",
        "실패 모드",
        "합성 증거 테스트킷",
        "테스트킷 경계",
        "라우팅 원칙",
        "입력",
        "출력",
        "런타임 port",
        "조사 루프 경계",
        "Evidence 파일",
        "Expected 파일",
        "Manifest 계약",
        "Core 언어",
        "Downstream 언어",
        "실패 모드 테스트 전략",
        "테스트 authority 규칙",
        "Review semantics 규칙",
    }
    old_labels = {
        "Capability registry",
        "Failure mode",
        "Synthetic evidence testkit",
        "Testkit boundary",
        "Routing 원칙",
        "Input",
        "Output",
        "Runtime port",
        "Evidence file",
        "Expected file",
        "Manifest contract",
        "Core language",
        "Downstream language",
        "Failure Mode 테스트 전략",
        "Test authority 규칙",
        "Review semantics",
    }

    assert expected_labels <= labels
    assert not (old_labels & labels)


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


def test_architecture_doc_summarizes_current_pipeline_and_legacy_report_path():
    doc = Path("docs/architecture.md").read_text(encoding="utf-8")

    assert "현재 구현 기준의 큰 흐름" in doc
    assert "AttachmentBundle -> RawAttachment -> EvidenceArtifact -> EvidenceUnit -> EvidenceInventory" in doc
    assert "EvidenceInventory -> EvidenceAtom -> NeedSpec -> NormalizationResult -> EvidenceResolutionGraph" in doc
    assert "InvestigationState / InvestigationTask / InvestigationTaskResult" in doc
    assert "ResolutionGapPlanner" in doc
    assert "CandidateUnitRetriever" in doc
    assert "resolver gap을 NeedLedgerEntry와 InvestigationTask로 번역한다." in doc
    assert "retrieve_candidate_units task를 EvidenceInventory 안의 EvidenceUnit 후보 선택으로 접지한다." in doc
    assert "LocalInvestigationRunner는 주입된 CandidateUnitRetriever로 retrieve_candidate_units를 실행할 수 있다." in doc
    assert "LocalInvestigationRunner는 주입된 NormalizationAdapter로 queued normalize_candidate를 실행할 수 있다." in doc
    assert "LocalInvestigationRunner는 atomize_unit_cluster가 만든 atom id를 normalize_candidate follow-up task로 이어 줄 수 있다." in doc
    assert "LocalInvestigationRunner는 주입된 ResolverPort로 draft EvidenceResolutionGraph를 갱신할 수 있다." in doc
    assert "run_resolution_cycle은 deterministic reference controller로 NeedSpec, gap plan, local runner, resolver를 연결한다." in doc
    assert "LocalInvestigationRunner retrieve_candidate_units 자동 실행" not in doc
    assert "provider-backed end-to-end EvidenceInventory -> ResolutionGraph orchestration" in doc
    assert "automatic end-to-end EvidenceInventory -> ResolutionGraph orchestration" not in doc
    assert "기존 `EvidenceDocument -> EvidenceReport` 경로는 compatibility document workflow입니다." in doc
    assert "현재 구현된 것" in doc
    assert "아직 구현하지 않은 것" in doc
    assert "Reader는 EvidenceUnit까지만 만든다." in doc
    assert "Resolver만 support/contradict를 판단한다." in doc
    assert "LLM/VLM은 resolver authority가 아니다." in doc


def test_readme_and_docs_index_point_to_current_architecture_state():
    readme = Path("README.md").read_text(encoding="utf-8")
    docs_index = Path("docs/index.md").read_text(encoding="utf-8")

    for text in (readme, docs_index):
        assert "현재 구현 기준" in text
        assert "AttachmentBundle" in text
        assert "EvidenceInventory" in text
        assert "EvidenceAtom" in text
        assert "NeedSpec" in text
        assert "EvidenceResolutionGraph" in text
        assert "최종 support/contradict 판단은 resolver 경계에 남깁니다." in text


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
    assert "현재 public-ish contract surface" in contracts_text
    for contract_name in (
        "AttachmentBundle",
        "RawAttachment",
        "EvidenceArtifact",
        "EvidenceUnit",
        "EvidenceInventory",
        "EvidenceAtom",
        "NeedSpec",
        "NormalizationResult",
        "EvidenceResolutionGraph",
        "ResolutionGapPlan",
        "ResolutionGapPlanner",
        "EvidenceUnitRetrievalResult",
        "CandidateUnitRetriever",
        "SimpleUnitClusterAtomizer",
        "EvidenceResolutionRun",
        "run_resolution_cycle",
        "ResolverPort",
        "InvestigationState",
        "InvestigationTask",
        "InvestigationTaskResult",
        "AdapterAcceptanceCheck",
        "AdapterAcceptanceReport",
        "AttachmentReaderPort",
        "run_basic_resolution_adapter_acceptance",
        "run_reader_resolution_adapter_acceptance",
    ):
        assert contract_name in contracts_text
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
        "adapter-acceptance.md",
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


def test_adapter_acceptance_doc_describes_reader_backed_real_tool_smoke():
    text = Path("docs/testing/adapter-acceptance.md").read_text(encoding="utf-8")

    assert "run_reader_resolution_adapter_acceptance" in text
    assert "PdfPlumberExtractReader" in text
    assert "reader-backed" in text
    assert "pdfplumber_dependency_missing" in text
    assert "pdf_text_extract_failed" in text
    assert "EvidenceInventory -> EvidenceAtom -> EvidenceResolutionGraph" in text


def test_generated_case_bundle_contract_is_indexed_and_scope_limited():
    doc_path = Path("docs/testing/generated-case-bundle-contract.md")
    testing_index = Path("docs/testing/README.md").read_text(encoding="utf-8")

    assert doc_path.exists()
    assert "generated-case-bundle-contract.md" in testing_index

    text = doc_path.read_text(encoding="utf-8")
    assert "case directory" in text
    assert "evidence.<ext>" in text
    assert "expected.json" in text
    assert "experiment.json" in text
    assert "expected-behavior.json" in text
    assert "run-experiment" in text
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


def test_investigation_loop_boundary_doc_is_indexed_and_keeps_model_authority_bounded():
    doc_path = Path("docs/investigation-loop-boundary.md")
    docs_index = Path("docs/index.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")

    assert doc_path.exists()
    assert "investigation-loop-boundary.md" in docs_index
    assert "조사 루프 경계" in readme

    text = doc_path.read_text(encoding="utf-8")
    assert "LLM/VLM은 판사가 아니라 조사관입니다." in text
    assert "LLM/VLM은 ingestion reader에 들어가지 않는다." in text
    assert "LLM/VLM은 resolver authority가 아니다." in text
    assert "EvidenceInvestigationLoop" in text
    assert "InvestigationState" in text
    assert "InvestigationTask" in text
    assert "InvestigationTaskResult" in text
    assert "NeedLedgerEntry" in text
    assert "InvestigationBudget" in text
    assert "LLMPlannerPort" in text
    assert "VLMObserverPort" in text
    assert "LLMAtomizerPort" in text
    assert "LLMNormalizerPort" in text
    assert "ResolverPort" in text
    assert "FakeLLMPlanner" in text
    assert "FakeVLMObserver" in text
    assert "LocalInvestigationRunner" in text
    assert "ResolutionGapPlanner" in text
    assert "EvidenceResolutionGraph gap을 NeedLedgerEntry와 InvestigationTask로 번역합니다." in text
    assert "`CandidateUnitRetriever`는 retrieve_candidate_units task를 EvidenceUnit 후보 선택으로 접지합니다." in text
    assert "retrieval은 EvidenceAtom이나 ResolutionEdge를 만들지 않습니다." in text
    assert "LocalInvestigationRunner는 `CandidateUnitRetriever`가 주입되면 `retrieve_candidate_units` task를 실행할 수 있습니다." in text
    assert "`run_agenda(max_steps=...)`는 이미 올라온 agenda만 deterministic하게 실행합니다." in text
    assert "run_agenda는 새 planner task를 요청하지 않습니다." in text
    assert "같은 task fingerprint가 다시 나타나면 `repeated_task_detected`로 멈춥니다." in text
    assert "runner가 agenda, completed task, unit, atom, normalization, event를 전혀 바꾸지 못하면 `no_progress_detected`로 멈춥니다." in text
    assert "현재 runner는 `retrieve_candidate_units`를 자동 실행하지 않습니다." not in text
    assert "missing/conflict/ambiguous clue" in text
    assert "model output은 EvidenceUnit, EvidenceAtom, NormalizationResult 중 하나로 내려와야 한다." in text
    assert 'unit_type="visual_observation"' in text
    assert "visual task result에 포함된 produced unit과 atom을" in text
    assert "그래도 resolver edge나 claim status는 만들지 않습니다." in text
    assert "LocalInvestigationRunner는 `NormalizationAdapter`가 주입되고 agenda에 `normalize_candidate`" in text
    assert "이 실행도 resolver edge나 claim status를 만들지 않습니다." in text
    assert "normalizer가 주입된 runner는 `atomize_unit_cluster`가 accepted atom id를 만들면" in text
    assert "이미 같은 atom id를 대상으로 하는 normalize task가 agenda에 있으면 중복으로 만들지 않습니다." in text
    assert "ResolverPort가 주입된 runner는 `normalize_candidate` 완료 뒤 현재 state material로" in text
    assert "주입된 port 결과를 `draft_graph`에 저장하며 `state_updated` event를 남깁니다." in text
    assert "model output atom은 core atom vocabulary와 task의 `allowed_atom_types`를 통과해야 합니다." in text
    assert "source_unit_ids 또는 source_artifact_ids provenance가 없으면 state에 append하지 않습니다." in text
    assert "Controller가 state와 budget을 들고 model/tool port를 호출한다." in text
    assert "모델끼리 직접 서로 호출하지 않는다." in text
    assert "real provider adapter와 LangGraph adapter는 core contract 뒤에 붙인다." in text
    assert "현재 구현은 조사 루프 record contract와 model port contract를 제공합니다." in text
    assert "agenda가 있으면 첫 task 하나를 fake/model port로 실행해" in text
    assert "이 runner는 provider SDK, LangGraph, resolver 구현을 직접 import하지 않습니다." in text
    assert "retrieve_candidate_units -> atomize_unit_cluster -> normalize_candidate" in text
    assert "`run_resolution_cycle`은 이 local runner를 실제 deterministic 부품과 묶는 reference" in text
    assert "fake adapter는 외부 모델을 호출하지 않습니다." in text


def test_ingestion_normalization_doc_is_indexed_and_layered():
    doc_path = Path("docs/ingestion-normalization.md")
    docs_index = Path("docs/index.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")

    assert doc_path.exists()
    assert "ingestion-normalization.md" in docs_index
    assert "첨부 정규화" in readme

    text = doc_path.read_text(encoding="utf-8")
    assert "파일 라우팅은 물리 첨부를 공통 inventory로 낮춘다." in text
    assert "EvidenceUnit은 semantic matching target이 아니다." in text
    assert "EvidenceAtom" in text
    assert "SafetyPolicy는 reader보다 먼저 적용되어야 한다." in text
    assert "FileKindRouter는 route와 근거를 함께 남긴다." in text
    assert "merge_evidence_inventories" in text
    assert "ingest_bundle" in text
    assert "이 merge는 semantic routing이 아니다." in text
    assert "EvidenceAtom은 support/contradict 판정이 아니다." in text
    assert "v0 atom type vocabulary는 사람이 읽을 수 있는 string으로 고정합니다." in text
    assert "currency_amount" in text
    assert "`producer`는 atom을 만든 주체를 보존합니다." in text
    assert "`normalized`는 best-effort helper field다." in text
    assert "AtomizerResult는 EvidenceReport도 아니고 ResolutionGraph도 아닙니다." in text
    assert "SimpleTextAtomizer는 deterministic baseline atomizer입니다." in text
    assert "SimpleTextAtomizer는 LLM/VLM adapter가 아니다." in text
    assert "usage_amount" in text
    assert "service_period" in text
    assert "UnsupportedReader" in text
    assert "PlainTextReader" in text
    assert "DelimitedTableReader" in text
    assert "PdfProfileReader" in text
    assert "PdfPlumberExtractReader" in text
    assert "ImageProfileReader" in text
    assert "SpreadsheetReader" in text
    assert "Image profile은 OCR 또는 VLM extraction이 아니다." in text
    assert "PDF profile은 text extraction이 아니다." in text
    assert "기본 `ingest_attachment` PDF route는 cheap profile을 만들고" in text
    assert "PdfPlumberExtractReader는 EvidenceAtom을 만들지 않는다." in text
    assert "Spreadsheet reader는 수식을 실행하지 않는다." in text
    assert "reader는 EvidenceAtom을 만들지 않는다." in text
    assert "해서는 안 되는 일" in text


def test_experiment_manifest_doc_is_indexed_and_keeps_oracle_out_of_input_contract():
    doc_path = Path("docs/experiment-manifest.md")
    docs_index = Path("docs/index.md").read_text(encoding="utf-8")
    contracts_index = Path("docs/contracts/README.md").read_text(encoding="utf-8")

    assert doc_path.exists()
    assert "experiment-manifest.md" in docs_index
    assert "ExperimentManifest" in contracts_index
    assert "ExperimentAttachmentSpec" in contracts_index

    text = doc_path.read_text(encoding="utf-8")
    assert "실험 manifest" in text
    assert "AttachmentBundle" in text
    assert "DeclaredClaim" in text
    assert "InvestigationBudget" in text
    assert "allowed_capabilities" in text
    assert "ExpectedBehavior oracle은 다음 slice" in text
    assert "Downstream judgment를 encode하지 않는다" in text


def test_experiment_run_trace_doc_is_indexed_and_separates_trace_from_oracle():
    doc_path = Path("docs/experiment-run-trace.md")
    docs_index = Path("docs/index.md").read_text(encoding="utf-8")
    contracts_index = Path("docs/contracts/README.md").read_text(encoding="utf-8")

    assert doc_path.exists()
    assert "experiment-run-trace.md" in docs_index
    assert "ExperimentRunTrace" in contracts_index

    text = doc_path.read_text(encoding="utf-8")
    assert "실행 trace" in text
    assert "ExperimentManifest" in text
    assert "EvidenceResolutionRun" in text
    assert "initial_graph" in text
    assert "gap_plan" in text
    assert "investigation_state" in text
    assert "final_graph" in text
    assert "ExpectedBehavior oracle이 아니다" in text
    assert "Downstream verdict가 아니다" in text


def test_expected_behavior_oracle_doc_is_indexed_and_keeps_policy_out():
    doc_path = Path("docs/expected-behavior-oracle.md")
    docs_index = Path("docs/index.md").read_text(encoding="utf-8")
    contracts_index = Path("docs/contracts/README.md").read_text(encoding="utf-8")

    assert doc_path.exists()
    assert "expected-behavior-oracle.md" in docs_index
    assert "ExperimentExpectedBehavior" in contracts_index
    assert "ExpectedBehaviorReport" in contracts_index

    text = doc_path.read_text(encoding="utf-8")
    assert "ExpectedBehavior oracle" in text
    assert "ExperimentRunTrace" in text
    assert "ExpectedClaimResolution" in text
    assert "ExpectedBehaviorReport" in text
    assert "claim_status" in text
    assert "supporting_atom_types" in text
    assert "test expectation" in text
    assert "runtime authority가 아니다" in text


def test_experiment_cli_runner_doc_is_indexed_and_keeps_provider_authority_out():
    doc_path = Path("docs/experiment-cli-runner.md")
    docs_index = Path("docs/index.md").read_text(encoding="utf-8")

    assert doc_path.exists()
    assert "experiment-cli-runner.md" in docs_index

    text = doc_path.read_text(encoding="utf-8")
    assert "run-experiment" in text
    assert "ExperimentManifest" in text
    assert "ExperimentRunTrace" in text
    assert "ExpectedBehaviorReport" in text
    assert "provider tools" in text
    assert "downstream policy sufficiency" in text


def test_evidence_linking_architecture_doc_is_indexed_and_sets_authority_boundaries():
    doc_path = Path("docs/evidence-linking-architecture.md")
    docs_index = Path("docs/index.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")

    assert doc_path.exists()
    assert "evidence-linking-architecture.md" in docs_index
    assert "X-Y 증거 연결 아키텍처" in readme

    text = doc_path.read_text(encoding="utf-8")
    assert "증빙 처리는 문서 파싱이 아니라 X-Y evidence linking 문제입니다." in text
    assert "File routing은 증빙 의미를 판단하지 않는다." in text
    assert "Reader는 EvidenceUnit까지만 만든다." in text
    assert "Atomizer는 EvidenceAtom 후보만 만든다." in text
    assert "Resolver만 support/contradict를 판단한다." in text
    assert "LLM/VLM은 authority가 아니라 adapter입니다." in text
    assert "조사 루프 경계" in text
    assert "NeedSpec" in text
    assert "DeclaredClaim" in text
    assert "derive_need_spec" in text
    assert "EvidenceResolutionGraph" in text
    assert "HardGateResolver" in text
    assert "EvidenceResolutionRun" in text
    assert "SimpleUnitClusterAtomizer" in text
    assert "run_resolution_cycle" in text
    assert "ResolutionEdge" in text
    assert "ClaimResolution" in text
    assert "ResolutionRelation" in text
    assert "ResolutionStatus" in text
    assert "NormalizationResult" in text
    assert "NormalizedQuantity" in text
    assert "NormalizationAdapter" in text
    assert "DeterministicNormalizer" in text
    assert "정규화는 support/contradict 판단이 아니다." in text
    assert "DeterministicNormalizer는 resolver가 아니다." in text
    assert "DeterministicNormalizer는 optional/reference adapter입니다." in text
    assert "provider/model-backed normalization orchestration" in text
    assert "automatic normalization orchestration" not in text
    assert "core flow는 normalizer를 자동 호출하지 않는다." in text
    assert "LLM/VLM normalizer도 NormalizationAdapter contract를 따라야 합니다." in text
    assert "site/supplier alias와 ambiguous period는 deterministic scope 밖입니다." in text
    assert "현재 구현된 것" in text
    assert "아직 구현하지 않은 것" in text
    assert "NeedSpec 없는 simple resolver로 가지 않는다." in text
    assert "v0 hard-gate edge와 claim resolution을 만듭니다." in text
    assert "이 resolver는 normalizer를 자동 호출하지" in text
    assert "soft score resolver" in text


def test_adapter_boundary_matches_current_resolver_contract_language():
    text = Path("docs/adapter-boundary.md").read_text(encoding="utf-8")
    downstream_section = text.split("## Downstream 언어", 1)[1].split(
        "## Adapter 예시",
        1,
    )[0]

    assert "Core resolver 언어" in text
    assert "EvidenceResolutionGraph" in text
    assert "ResolutionEdge" in text
    assert "ClaimResolution" in text
    assert "resolver의 evidence relation status" in text
    assert "최종 domain authority verdict" in text
    assert "domain claim approval" in downstream_section
    assert "policy sufficiency threshold" in downstream_section
    assert "claim\nsupport\ncontradiction" not in downstream_section


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
            "Capability 레지스트리",
            "Capability는 단순한 function이 아닙니다",
            "문서화된 한계가 없는 capability",
        ],
        "docs/failure-modes.md": [
            "실패 모드",
            "실패 모드는 first-class output입니다",
            "Downstream policy verdict가 되면 안 됩니다",
        ],
        "docs/adapter-boundary.md": [
            "Adapter 경계",
            "Core package는 독립적으로 유지되어야 합니다",
            "Core resolver는 evidence relation status를 만들 수 있지만",
        ],
        "docs/synthetic-evidence.md": [
            "합성 증거 테스트킷",
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

    assert "Capability 레지스트리" in readme
    assert "Adapter 경계" in readme
    assert "합성 증거 테스트킷" in readme
