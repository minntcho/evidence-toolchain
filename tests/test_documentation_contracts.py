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
        "docs/synthetic-artifact-factory.md",
        "docs/ingestion-normalization.md",
        "docs/contracts/evidence-check.md",
        "docs/testing/generated-case-bundle-contract.md",
        "docs/testing/failure-mode-test-strategy.md",
        "docs/testing/README.md",
        "docs/testing/synthetic-evidence-cases.md",
        "synthetic/README.md",
    )

    expected_labels = {
        "Capability ?????",
        "?? ??",
        "?? ?? ????",
        "Synthetic Evidence Artifact Factory",
        "???? ??",
        "??? ??",
        "??",
        "??",
        "??? port",
        "?? ?? ??",
        "Evidence ??",
        "Expected ??",
        "Manifest ??",
        "Core ??",
        "Downstream ??",
        "?? ?? ??? ??",
        "??? authority ??",
        "Review semantics ??",
    }
    old_labels = {
        "Capability registry",
        "Failure mode",
        "Synthetic evidence testkit",
        "Testkit boundary",
        "Routing ??",
        "Input",
        "Output",
        "Runtime port",
        "Evidence file",
        "Expected file",
        "Manifest contract",
        "Core language",
        "Downstream language",
        "Failure Mode ??? ??",
        "Test authority ??",
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

    assert "??? ???? ??-?? ???" in doc
    assert "?? ??? ??? ??? ???" in doc
    assert "purpose-and-boundaries.md" in index
    assert "??? ??" in readme


def test_purpose_doc_keeps_consumer_examples_outside_core_identity():
    doc = Path("docs/purpose-and-boundaries.md").read_text(encoding="utf-8")

    assert "??? ??? ??? ? ?? ???? ???." in doc
    assert "?? ??? ????? ????" in doc


def test_architecture_doc_summarizes_current_pipeline_and_legacy_report_path():
    doc = Path("docs/architecture.md").read_text(encoding="utf-8")

    assert "?? ?? ??? ? ??" in doc
    assert "AttachmentBundle -> RawAttachment -> EvidenceArtifact -> EvidenceUnit -> EvidenceInventory" in doc
    assert "EvidenceInventory -> EvidenceAtom -> NeedSpec -> NormalizationResult -> EvidenceResolutionGraph" in doc
    assert "InvestigationState / InvestigationTask / InvestigationTaskResult" in doc
    assert "ResolutionGapPlanner" in doc
    assert "CandidateUnitRetriever" in doc
    assert "resolver gap? NeedLedgerEntry? InvestigationTask? ????." in doc
    assert "retrieve_candidate_units task? EvidenceInventory ?? EvidenceUnit ?? ???? ????." in doc
    assert "LocalInvestigationRunner? ??? CandidateUnitRetriever? retrieve_candidate_units? ??? ? ??." in doc
    assert "LocalInvestigationRunner? ??? NormalizationAdapter? queued normalize_candidate? ??? ? ??." in doc
    assert "LocalInvestigationRunner? atomize_unit_cluster? ?? atom id? normalize_candidate follow-up task? ?? ? ? ??." in doc
    assert "LocalInvestigationRunner? ??? ResolverPort? draft EvidenceResolutionGraph? ??? ? ??." in doc
    assert "run_resolution_cycle? deterministic reference controller? NeedSpec, gap plan, local runner, resolver? ????." in doc
    assert "LocalInvestigationRunner retrieve_candidate_units ?? ??" not in doc
    assert "provider-backed end-to-end EvidenceInventory -> ResolutionGraph orchestration" in doc
    assert "automatic end-to-end EvidenceInventory -> ResolutionGraph orchestration" not in doc
    assert "?? `EvidenceDocument -> EvidenceReport` ??? compatibility document workflow???." in doc
    assert "?? ??? ?" in doc
    assert "?? ???? ?? ?" in doc
    assert "Reader? EvidenceUnit??? ???." in doc
    assert "Resolver? support/contradict? ????." in doc
    assert "LLM/VLM? resolver authority? ???." in doc


def test_readme_and_docs_index_point_to_current_architecture_state():
    readme = Path("README.md").read_text(encoding="utf-8")
    docs_index = Path("docs/index.md").read_text(encoding="utf-8")

    for text in (readme, docs_index):
        assert "?? ?? ??" in text
        assert "AttachmentBundle" in text
        assert "EvidenceInventory" in text
        assert "EvidenceAtom" in text
        assert "NeedSpec" in text
        assert "EvidenceResolutionGraph" in text
        assert "?? support/contradict ??? resolver ??? ????." in text


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
    assert "?? ??? ??? ???? Downstream ??? ???? ???." in contracts_text
    assert "?? public-ish contract surface" in contracts_text
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
        assert "??? ? ?? ?" in text
        assert "??? ? ?? ?" in text
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
    assert "??? ??? ?? ??? ???? runtime authority? ???? ???." in testing_text
    assert "testing/README.md" in docs_index

    for filename in strategy_docs:
        path = Path("docs/testing") / filename
        assert path.exists(), f"missing {path}"
        text = path.read_text(encoding="utf-8")
        assert "??? assert? ?" in text
        assert "freeze?? ??? ? ?" in text
        assert "??? ? ?? ?" in text


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
    assert "run-convergence" in text
    assert "claim_convergences" in text
    assert "convergence_nonblocking_issue" in text
    assert "convergence_candidate_conflict" in text
    assert "fake `PatchProducer`" in text
    assert "Ground truth" in text
    assert "Expected toolchain behavior" in text
    assert "??? ? ?? ?" in text
    assert "Downstream" in text


def test_orchestration_boundary_doc_is_indexed_and_framework_neutral():
    doc_path = Path("docs/orchestration-boundary.md")
    docs_index = Path("docs/index.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")

    assert doc_path.exists()
    assert "orchestration-boundary.md" in docs_index
    assert "??????? ??" in readme

    text = doc_path.read_text(encoding="utf-8")
    assert "??????? ???? ?? ???" in text
    assert "local runner" in text
    assert "framework adapters" in text
    assert "EvidenceRunState" in text
    assert "EvidenceEvent" in text
    assert "CheckpointStore" in text
    assert "??? ? ?? ?" in text
    assert "Downstream" in text


def test_investigation_loop_boundary_doc_is_indexed_and_keeps_model_authority_bounded():
    doc_path = Path("docs/investigation-loop-boundary.md")
    docs_index = Path("docs/index.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")

    assert doc_path.exists()
    assert "investigation-loop-boundary.md" in docs_index
    assert "?? ?? ??" in readme

    text = doc_path.read_text(encoding="utf-8")
    assert "LLM/VLM? ??? ??? ??????." in text
    assert "LLM/VLM? ingestion reader? ???? ???." in text
    assert "LLM/VLM? resolver authority? ???." in text
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
    assert "EvidenceResolutionGraph gap? NeedLedgerEntry? InvestigationTask? ?????." in text
    assert "`CandidateUnitRetriever`? retrieve_candidate_units task? EvidenceUnit ?? ???? ?????." in text
    assert "retrieval? EvidenceAtom?? ResolutionEdge? ??? ????." in text
    assert "LocalInvestigationRunner? `CandidateUnitRetriever`? ???? `retrieve_candidate_units` task? ??? ? ????." in text
    assert "`run_agenda(max_steps=...)`? ?? ??? agenda? deterministic?? ?????." in text
    assert "run_agenda? ? planner task? ???? ????." in text
    assert "?? task fingerprint? ?? ???? `repeated_task_detected`? ????." in text
    assert "runner? agenda, completed task, unit, atom, normalization, event? ?? ??? ??? `no_progress_detected`? ????." in text
    assert "?? runner? `retrieve_candidate_units`? ?? ???? ????." not in text
    assert "missing/conflict/ambiguous clue" in text
    assert "model output? EvidenceUnit, EvidenceAtom, NormalizationResult ? ??? ???? ??." in text
    assert 'unit_type="visual_observation"' in text
    assert "visual task result? ??? produced unit? atom?" in text
    assert "??? resolver edge? claim status? ??? ????." in text
    assert "LocalInvestigationRunner? `NormalizationAdapter`? ???? agenda? `normalize_candidate`" in text
    assert "? ??? resolver edge? claim status? ??? ????." in text
    assert "normalizer? ??? runner? `atomize_unit_cluster`? accepted atom id? ???" in text
    assert "?? ?? atom id? ???? ?? normalize task? agenda? ??? ???? ??? ????." in text
    assert "ResolverPort? ??? runner? `normalize_candidate` ?? ? ?? state material?" in text
    assert "??? port ??? `draft_graph`? ???? `state_updated` event? ????." in text
    assert "model output atom? core atom vocabulary? task? `allowed_atom_types`? ???? ???." in text
    assert "source_unit_ids ?? source_artifact_ids provenance? ??? state? append?? ????." in text
    assert "Controller? state? budget? ?? model/tool port? ????." in text
    assert "???? ?? ?? ???? ???." in text
    assert "real provider adapter? LangGraph adapter? core contract ?? ???." in text
    assert "?? ??? ?? ?? record contract? model port contract? ?????." in text
    assert "agenda? ??? ? task ??? fake/model port? ???" in text
    assert "? runner? provider SDK, LangGraph, resolver ??? ?? import?? ????." in text
    assert "retrieve_candidate_units -> atomize_unit_cluster -> normalize_candidate" in text
    assert "`run_resolution_cycle`? ? local runner? ?? deterministic ??? ?? reference" in text
    assert "fake adapter? ?? ??? ???? ????." in text


def test_ingestion_normalization_doc_is_indexed_and_layered():
    doc_path = Path("docs/ingestion-normalization.md")
    docs_index = Path("docs/index.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")

    assert doc_path.exists()
    assert "ingestion-normalization.md" in docs_index
    assert "?? ???" in readme

    text = doc_path.read_text(encoding="utf-8")
    assert "?? ???? ?? ??? ?? inventory? ???." in text
    assert "EvidenceUnit? semantic matching target? ???." in text
    assert "EvidenceAtom" in text
    assert "SafetyPolicy? reader?? ?? ????? ??." in text
    assert "FileKindRouter? route? ??? ?? ???." in text
    assert "merge_evidence_inventories" in text
    assert "ingest_bundle" in text
    assert "? merge? semantic routing? ???." in text
    assert "EvidenceAtom? support/contradict ??? ???." in text
    assert "v0 atom type vocabulary? ??? ?? ? ?? string?? ?????." in text
    assert "currency_amount" in text
    assert "`producer`? atom? ?? ??? ?????." in text
    assert "`normalized`? best-effort helper field?." in text
    assert "AtomizerResult? EvidenceReport? ??? ResolutionGraph? ????." in text
    assert "SimpleTextAtomizer? deterministic baseline atomizer???." in text
    assert "SimpleTextAtomizer? LLM/VLM adapter? ???." in text
    assert "usage_amount" in text
    assert "service_period" in text
    assert "UnsupportedReader" in text
    assert "PlainTextReader" in text
    assert "DelimitedTableReader" in text
    assert "PdfProfileReader" in text
    assert "PdfPlumberExtractReader" in text
    assert "ImageProfileReader" in text
    assert "SpreadsheetReader" in text
    assert "Image profile? OCR ?? VLM extraction? ???." in text
    assert "PDF profile? text extraction? ???." in text
    assert "?? `ingest_attachment` PDF route? cheap profile? ???" in text
    assert "PdfPlumberExtractReader? EvidenceAtom? ??? ???." in text
    assert "Spreadsheet reader? ??? ???? ???." in text
    assert "reader? EvidenceAtom? ??? ???." in text
    assert "??? ? ?? ?" in text


def test_experiment_manifest_doc_is_indexed_and_keeps_oracle_out_of_input_contract():
    doc_path = Path("docs/experiment-manifest.md")
    docs_index = Path("docs/index.md").read_text(encoding="utf-8")
    contracts_index = Path("docs/contracts/README.md").read_text(encoding="utf-8")

    assert doc_path.exists()
    assert "experiment-manifest.md" in docs_index
    assert "ExperimentManifest" in contracts_index
    assert "ExperimentAttachmentSpec" in contracts_index

    text = doc_path.read_text(encoding="utf-8")
    assert "?? manifest" in text
    assert "AttachmentBundle" in text
    assert "DeclaredClaim" in text
    assert "InvestigationBudget" in text
    assert "allowed_capabilities" in text
    assert "ExpectedBehavior oracle? ?? slice" in text
    assert "Downstream judgment? encode?? ???" in text


def test_experiment_run_trace_doc_is_indexed_and_separates_trace_from_oracle():
    doc_path = Path("docs/experiment-run-trace.md")
    docs_index = Path("docs/index.md").read_text(encoding="utf-8")
    contracts_index = Path("docs/contracts/README.md").read_text(encoding="utf-8")

    assert doc_path.exists()
    assert "experiment-run-trace.md" in docs_index
    assert "ExperimentRunTrace" in contracts_index

    text = doc_path.read_text(encoding="utf-8")
    assert "?? trace" in text
    assert "ExperimentManifest" in text
    assert "EvidenceResolutionRun" in text
    assert "initial_graph" in text
    assert "gap_plan" in text
    assert "investigation_state" in text
    assert "final_graph" in text
    assert "ExpectedBehavior oracle? ???" in text
    assert "Downstream verdict? ???" in text


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
    assert "ExpectedClaimConvergence" in text
    assert "ExpectedBehaviorReport" in text
    assert "claim_status" in text
    assert "supporting_atom_types" in text
    assert "test expectation" in text
    assert "runtime authority? ???" in text


def test_experiment_cli_runner_doc_is_indexed_and_keeps_provider_authority_out():
    doc_path = Path("docs/experiment-cli-runner.md")
    docs_index = Path("docs/index.md").read_text(encoding="utf-8")

    assert doc_path.exists()
    assert "experiment-cli-runner.md" in docs_index

    text = doc_path.read_text(encoding="utf-8")
    assert "run-experiment" in text
    assert "run-convergence" in text
    assert "ExperimentManifest" in text
    assert "ExperimentRunTrace" in text
    assert "ExpectedBehaviorReport" in text
    assert "ExperimentExpectedBehavior.claim_convergences" in text
    assert "run.report.claim_reports" in text
    assert "does not run the expected-behavior oracle yet" not in text
    assert "provider tools" in text
    assert "downstream policy sufficiency" in text


def test_synthetic_artifact_factory_doc_defines_spec_to_tool_boundary():
    doc_path = Path("docs/synthetic-artifact-factory.md")
    docs_index = Path("docs/index.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")

    assert doc_path.exists()
    assert "synthetic-artifact-factory.md" in docs_index
    assert "Synthetic Evidence Artifact Factory" in readme

    text = doc_path.read_text(encoding="utf-8")
    assert "ScenarioSpec -> ScenarioIR -> BundlePlan -> ToolPlan" in text
    assert "ToolInvocationDAG" in text
    assert "ToolDescriptor" in text
    assert "ArtifactState" in text
    assert "TraceLayer" in text
    assert "ScenarioIR.rng_seed -> BundlePlan.rng_seed -> ToolInvocation.seed" in text
    assert "EvidenceConfusionOperator" in text
    assert "CarrierOperator" in text
    assert "ArtifactVerifier" in text
    assert "Syndrome precondition verifier" in text
    assert "_synthetic/" in text
    assert "evidence-toolchain core? input artifact?" in text
    assert "ScenarioSpec? ?? reportlab, Pillow, OpenCV, openpyxl, email lib? ???? ? ??." in text


def test_evidence_linking_architecture_doc_is_indexed_and_sets_authority_boundaries():
    doc_path = Path("docs/evidence-linking-architecture.md")
    docs_index = Path("docs/index.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")

    assert doc_path.exists()
    assert "evidence-linking-architecture.md" in docs_index
    assert "X-Y ?? ?? ????" in readme

    text = doc_path.read_text(encoding="utf-8")
    assert "?? ??? ?? ??? ??? X-Y evidence linking ?????." in text
    assert "File routing? ?? ??? ???? ???." in text
    assert "Reader? EvidenceUnit??? ???." in text
    assert "Atomizer? EvidenceAtom ??? ???." in text
    assert "Resolver? support/contradict? ????." in text
    assert "LLM/VLM? authority? ??? adapter???." in text
    assert "?? ?? ??" in text
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
    assert "???? support/contradict ??? ???." in text
    assert "DeterministicNormalizer? resolver? ???." in text
    assert "DeterministicNormalizer? optional/reference adapter???." in text
    assert "provider/model-backed normalization orchestration" in text
    assert "automatic normalization orchestration" not in text
    assert "core flow? normalizer? ?? ???? ???." in text
    assert "LLM/VLM normalizer? NormalizationAdapter contract? ??? ???." in text
    assert "site/supplier alias? ambiguous period? deterministic scope ????." in text
    assert "?? ??? ?" in text
    assert "?? ???? ?? ?" in text
    assert "NeedSpec ?? simple resolver? ?? ???." in text
    assert "v0 hard-gate edge? claim resolution? ????." in text
    assert "? resolver? normalizer? ?? ????" in text
    assert "soft score resolver" in text


def test_adapter_boundary_matches_current_resolver_contract_language():
    text = Path("docs/adapter-boundary.md").read_text(encoding="utf-8")
    downstream_section = text.split("## Downstream ??", 1)[1].split(
        "## Adapter ??",
        1,
    )[0]

    assert "Core resolver ??" in text
    assert "EvidenceResolutionGraph" in text
    assert "ResolutionEdge" in text
    assert "ClaimResolution" in text
    assert "resolver? evidence relation status" in text
    assert "?? domain authority verdict" in text
    assert "domain claim approval" in downstream_section
    assert "policy sufficiency threshold" in downstream_section
    assert "claim\nsupport\ncontradiction" not in downstream_section


def test_supporting_architecture_docs_are_localized_and_indexed():
    docs_index = Path("docs/index.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")

    expectations = {
        "docs/evidence-routing.md": [
            "?? ???",
            "?? ????",
            "?? validation judgment? ??? ? ???",
        ],
        "docs/capability-registry.md": [
            "Capability ?????",
            "Capability? ??? function? ????",
            "???? ??? ?? capability",
        ],
        "docs/failure-modes.md": [
            "?? ??",
            "?? ??? first-class output???",
            "Downstream policy verdict? ?? ? ???",
        ],
        "docs/adapter-boundary.md": [
            "Adapter ??",
            "Core package? ????? ????? ???",
            "Core resolver? evidence relation status? ?? ? ???",
        ],
        "docs/synthetic-evidence.md": [
            "?? ?? ????",
            "Synthetic case? runtime authority? ???? ????",
            "truth? expected behavior? ?????",
        ],
    }

    for doc_path, anchors in expectations.items():
        path = Path(doc_path)
        assert path.exists(), f"missing {path}"
        assert path.name in docs_index
        for anchor in anchors:
            assert anchor in path.read_text(encoding="utf-8")

    assert "Capability ?????" in readme
    assert "Adapter ??" in readme
    assert "?? ?? ????" in readme
