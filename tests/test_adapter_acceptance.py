import json


def test_basic_resolution_adapter_acceptance_passes_reference_adapters():
    from evidence_toolchain import (
        DeterministicNormalizer,
        HardGateResolver,
        SimpleUnitClusterAtomizer,
        run_basic_resolution_adapter_acceptance,
    )

    report = run_basic_resolution_adapter_acceptance(
        adapter_name="reference_text_resolution",
        llm_atomizer=SimpleUnitClusterAtomizer(bundle_id="acceptance_bundle_001"),
        normalizer=DeterministicNormalizer(),
        resolver=HardGateResolver(),
    )
    payload = report.to_dict()

    assert payload["adapter_name"] == "reference_text_resolution"
    assert payload["passed"] is True
    assert [check["name"] for check in payload["checks"]] == [
        "llm_atomizer_port",
        "normalization_adapter_port",
        "resolver_port",
        "trace_json_serializable",
        "expected_behavior.claim_status",
        "expected_behavior.missing_need_ids",
        "expected_behavior.supporting_atom_types",
        "expected_behavior.rejected_atom_types",
    ]
    assert payload["trace"]["run"]["final_graph"]["resolutions"][0]["status"] == (
        "supported_after_unit_normalization"
    )
    assert payload["expected_behavior_report"]["passed"] is True
    json.dumps(payload, ensure_ascii=False)


def test_basic_resolution_adapter_acceptance_reports_failed_expected_behavior():
    from evidence_toolchain import (
        AtomizerResult,
        DeterministicNormalizer,
        HardGateResolver,
        run_basic_resolution_adapter_acceptance,
    )

    class EmptyAtomizer:
        producer = "empty_atomizer"

        def atomize(self, task, units):
            del task, units
            return AtomizerResult(bundle_id="acceptance_bundle_001", atoms=())

    report = run_basic_resolution_adapter_acceptance(
        adapter_name="empty_atomizer",
        llm_atomizer=EmptyAtomizer(),
        normalizer=DeterministicNormalizer(),
        resolver=HardGateResolver(),
    )
    payload = report.to_dict()

    assert payload["passed"] is False
    assert payload["trace"]["run"]["final_graph"]["resolutions"][0]["status"] == (
        "insufficient"
    )
    failed_checks = [
        check for check in payload["checks"] if check["passed"] is False
    ]
    assert [check["name"] for check in failed_checks] == [
        "expected_behavior.claim_status",
        "expected_behavior.missing_need_ids",
        "expected_behavior.supporting_atom_types",
        "expected_behavior.rejected_atom_types",
    ]
    assert failed_checks[0]["expected"] == "supported_after_unit_normalization"
    assert failed_checks[0]["actual"] == "insufficient"


def test_adapter_acceptance_helper_stays_provider_and_framework_neutral():
    from pathlib import Path

    source = Path("src/evidence_toolchain/adapter_acceptance.py").read_text(
        encoding="utf-8"
    )

    for forbidden in ("openai", "langgraph", "requests", "httpx"):
        assert forbidden not in source
