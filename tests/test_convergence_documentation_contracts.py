import re
from pathlib import Path


CONVERGENCE_DOCS = (
    "00-north-star.md",
    "01-mvp-scope.md",
    "02-core-concepts.md",
    "03-candidate-mask-state.md",
    "04-mask-patch-and-validator.md",
    "05-gap-scheduler-and-capabilities.md",
    "06-runner-and-report.md",
    "07-integration-with-existing-architecture.md",
    "08-test-plan.md",
    "09-ssot-and-strategy-boundary.md",
    "future-extensions.md",
)


def _read_convergence_docs() -> dict[str, str]:
    return {
        filename: (Path("docs/convergence") / filename).read_text(encoding="utf-8")
        for filename in CONVERGENCE_DOCS
    }


def test_convergence_docs_are_indexed_and_preserve_mvp_boundary():
    docs_index = Path("docs/index.md").read_text(encoding="utf-8")
    convergence_docs = _read_convergence_docs()
    combined = "\n".join(convergence_docs.values())

    for filename in CONVERGENCE_DOCS:
        assert Path("docs/convergence", filename).exists()
        assert f"convergence/{filename}" in docs_index

    assert "Evidence Convergence Kernel은 전체 증빙 다발 reasoning을 해결하지 않는다." in combined
    assert "MVP는 새 `EvidenceObservation` 모델을 만들지 않습니다." in combined
    assert "MVP observation = EvidenceUnit" in combined
    assert "MVP observation store = EvidenceInventory" in combined

    assert "Capability는 candidate state를 직접 변경하지 않는다." in combined
    assert "PatchValidator만 patch를 적용할 수 있다." in combined
    assert "Convergence pass는 downstream verdict가 아니다" in combined

    assert "EvidenceBundleGraph" in combined
    assert "SupportSetSelector" in combined
    assert "DefeaterResolver" in combined
    assert "SourcePrecedencePolicy" in combined


def test_convergence_docs_define_visual_and_schema_contracts_without_pr_local_terms():
    convergence_docs = _read_convergence_docs()
    combined = "\n".join(convergence_docs.values())

    assert "```mermaid" in convergence_docs["00-north-star.md"]
    assert "```mermaid" in convergence_docs["03-candidate-mask-state.md"]
    assert (
        "```mermaid" in convergence_docs["04-mask-patch-and-validator.md"]
        or "```mermaid" in convergence_docs["06-runner-and-report.md"]
    )
    assert combined.count("```mermaid") >= 3

    candidate_state = convergence_docs["03-candidate-mask-state.md"]
    assert "directly_comparable: bool = False" in candidate_state
    assert "directly_comparable_mask" in candidate_state
    assert "aligned_mask & ~(normalized_mask | directly_comparable_mask) == 0" in combined

    assert re.search(r"\bPR\d+\b", combined) is None
    assert re.search(r"\bPRs?\b", combined) is None


def test_convergence_docs_define_snapshot_ssot_and_strategy_views():
    docs_index = Path("docs/index.md").read_text(encoding="utf-8")
    ssot_doc = Path(
        "docs/convergence/09-ssot-and-strategy-boundary.md"
    ).read_text(encoding="utf-8")

    assert "convergence/09-ssot-and-strategy-boundary.md" in docs_index
    assert "SSOT는 증빙 케이스 스냅샷이다." in ssot_doc
    assert "Strategies produce views." in ssot_doc
    assert "Views do not mutate the snapshot." in ssot_doc
    assert "EvidenceResolutionGraph와 ConvergenceReport는 strategy-specific materialized view다." in ssot_doc
    assert "Projection은 명시적 adapter다." in ssot_doc
    assert "downstream verdict는 core authority가 아니다." in ssot_doc
    assert "`EvidenceCaseSnapshot` is the code-level SSOT wrapper." in ssot_doc
    assert "`EvidenceInventory` remains the observation store." in ssot_doc
    assert "Strategy outputs reference `case_snapshot_id`." in ssot_doc


def test_convergence_docs_preserve_expected_behavior_view_boundary():
    test_plan = Path("docs/convergence/08-test-plan.md").read_text(encoding="utf-8")

    assert "ExperimentExpectedBehavior.claim_convergences" in test_plan
    assert "ExperimentRunTrace.run.report.claim_reports" in test_plan
    assert "They do not project the convergence report into an" in test_plan
    assert "they do not compare `downstream_verdict`" in test_plan
