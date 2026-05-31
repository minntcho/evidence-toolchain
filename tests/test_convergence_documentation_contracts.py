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

    assert "Evidence Convergence Kernel? ?? ?? ?? reasoning? ???? ???." in combined
    assert "MVP? ? `EvidenceObservation` ??? ??? ????." in combined
    assert "MVP observation = EvidenceUnit" in combined
    assert "MVP observation store = EvidenceInventory" in combined

    assert "Capability? candidate state? ?? ???? ???." in combined
    assert "PatchValidator? patch? ??? ? ??." in combined
    assert "Convergence pass? downstream verdict? ???" in combined

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
    assert "SSOT? ?? ??? ?????." in ssot_doc
    assert "Strategies produce views." in ssot_doc
    assert "Views do not mutate the snapshot." in ssot_doc
    assert "EvidenceResolutionGraph? ConvergenceReport? strategy-specific materialized view?." in ssot_doc
    assert "Projection? ??? adapter?." in ssot_doc
    assert "downstream verdict? core authority? ???." in ssot_doc
    assert "`EvidenceCaseSnapshot` is the code-level SSOT wrapper." in ssot_doc
    assert "`EvidenceInventory` remains the observation store." in ssot_doc
    assert "Strategy outputs reference `case_snapshot_id`." in ssot_doc


def test_convergence_docs_preserve_expected_behavior_view_boundary():
    test_plan = Path("docs/convergence/08-test-plan.md").read_text(encoding="utf-8")

    assert "ExperimentExpectedBehavior.claim_convergences" in test_plan
    assert "ExperimentRunTrace.run.report.claim_reports" in test_plan
    assert "They do not project the convergence report into an" in test_plan
    assert "they do not compare `downstream_verdict`" in test_plan
    assert "convergence_clean_support" in test_plan
    assert "convergence_nonblocking_issue" in test_plan
    assert "convergence_candidate_conflict" in test_plan
    assert "expected unresolved_gaps: quantity" in test_plan
    assert "fake `PatchProducer`" in test_plan
