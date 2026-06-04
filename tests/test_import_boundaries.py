from pathlib import Path
import tomllib


def test_core_package_does_not_import_synthetic_testkit():
    core_files = [
        path
        for path in Path("src/evidence_toolchain").rglob("*.py")
        if "__pycache__" not in path.parts
    ]

    assert core_files
    for path in core_files:
        source = path.read_text(encoding="utf-8")
        assert "import synthetic" not in source
        assert "from synthetic" not in source


def test_pdfplumber_is_optional_pdf_extra_not_required_core_dependency():
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert "pdfplumber>=0.11" not in pyproject["project"].get("dependencies", [])
    assert pyproject["project"]["optional-dependencies"]["pdf"] == [
        "pdfplumber>=0.11"
    ]


def test_convergence_public_api_is_explicit_and_runner_visible():
    import evidence_toolchain.convergence as convergence

    assert convergence.__all__ == [
        "CapabilitySpec",
        "CandidateGap",
        "CandidateMaskState",
        "ClaimConvergenceReport",
        "ConvergenceReport",
        "ConvergenceRun",
        "EvidenceCandidate",
        "EvidenceSchema",
        "MaskPatch",
        "PatchProducer",
        "PatchValidationError",
        "PatchValidationResult",
        "SlotDef",
        "apply_patch",
        "compute_candidate_gap",
        "mask_has_unknown_bits",
        "provenance_present_mask",
        "run_convergence_cycle",
        "select_capabilities",
        "validate_candidate_state",
        "validate_patch",
    ]


def test_top_level_package_does_not_export_convergence_kernel_symbols():
    import evidence_toolchain

    forbidden = {
        "CandidateMaskState",
        "ClaimConvergenceReport",
        "ConvergenceReport",
        "ConvergenceRun",
        "EvidenceCandidate",
        "MaskPatch",
        "PatchProducer",
        "run_convergence_cycle",
    }

    assert forbidden.isdisjoint(evidence_toolchain.__all__)
    assert "run_convergence_adapter_acceptance" in evidence_toolchain.__all__


def test_convergence_kernel_imports_do_not_depend_on_resolution_or_harness():
    convergence_files = [
        path
        for path in Path("src/evidence_toolchain/convergence").rglob("*.py")
        if "__pycache__" not in path.parts
    ]
    forbidden_tokens = (
        "EvidenceResolutionGraph",
        "evidence_toolchain.adapter_acceptance",
        "evidence_toolchain.cli",
        "evidence_toolchain.resolution",
        "evidence_toolchain.resolution_cycle",
    )

    assert convergence_files
    for path in convergence_files:
        source = path.read_text(encoding="utf-8")
        for token in forbidden_tokens:
            assert token not in source, f"{path} imports or mentions {token}"
