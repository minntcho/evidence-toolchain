import re
from pathlib import Path


def test_convergence_docs_define_visual_and_schema_contracts_without_pr_local_terms():
    convergence_docs = {
        path.name: path.read_text(encoding="utf-8")
        for path in Path("docs/convergence").glob("*.md")
    }
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
