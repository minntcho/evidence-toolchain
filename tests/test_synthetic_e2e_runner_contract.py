from __future__ import annotations

import json
from pathlib import Path


def test_minimal_e2e_scenario_fixtures_define_csv_and_xlsx_contracts() -> None:
    fixtures = {
        "scenarios/erp_export_basic.yaml": {
            "scenario_id": "erp_export_basic",
            "artifact_id": "export",
            "carrier": "csv",
        },
        "scenarios/supplier_breakdown_workbook_basic.yaml": {
            "scenario_id": "supplier_breakdown_workbook_basic",
            "artifact_id": "breakdown",
            "carrier": "xlsx",
        },
    }

    for fixture_path, expected in fixtures.items():
        text = Path(fixture_path).read_text(encoding="utf-8")

        assert f"scenario_id: {expected['scenario_id']}" in text
        assert f"id: {expected['artifact_id']}" in text
        assert f"carrier: {expected['carrier']}" in text
        assert "expected_predicates:" in text
        assert "id: artifact_ingested" in text
        assert "id: minimum_observation_count" in text
        assert f"artifact_id: {expected['artifact_id']}" in text
        assert "min_count: 1" in text


def test_expected_predicate_schema_is_v0_and_keeps_predicates_small() -> None:
    schema = _load_json("scenarios/contracts/expected_predicates.v0.schema.json")

    assert schema["$id"] == "synthetic.expected_predicates.v0"
    assert schema["required"] == ["predicates"]
    predicate = schema["properties"]["predicates"]["items"]
    assert predicate["required"] == ["id", "artifact_id"]
    assert predicate["properties"]["id"]["enum"] == [
        "artifact_ingested",
        "minimum_observation_count",
    ]
    assert "claim_status" not in json.dumps(schema)
    assert "manual_review" not in json.dumps(schema)


def test_runtime_report_schema_captures_reader_and_predicate_results() -> None:
    schema = _load_json("scenarios/contracts/runtime_report.v0.schema.json")

    assert schema["$id"] == "synthetic.runtime_report.v0"
    assert schema["required"] == [
        "case_id",
        "status",
        "artifacts",
        "predicates",
        "links",
    ]
    assert schema["properties"]["status"]["enum"] == ["passed", "failed"]
    artifact = schema["properties"]["artifacts"]["items"]
    assert artifact["required"] == [
        "artifact_id",
        "path",
        "carrier",
        "reader",
        "reader_status",
        "observation_count",
        "issue_count",
    ]
    assert artifact["properties"]["carrier"]["enum"] == ["csv", "xlsx"]
    predicate = schema["properties"]["predicates"]["items"]
    assert predicate["properties"]["status"]["enum"] == ["passed", "failed"]
    assert "message" in predicate["properties"]
    assert schema["properties"]["links"]["required"] == [
        "manifest",
        "carrier_trace",
        "verification_report",
    ]


def test_synthetic_e2e_runner_contract_doc_sets_v0_program_boundary() -> None:
    doc = Path("docs/testing/synthetic-e2e-runner-contract.md").read_text(
        encoding="utf-8"
    )
    testing_index = Path("docs/testing/README.md").read_text(encoding="utf-8")

    assert "synthetic-e2e-runner-contract.md" in testing_index
    assert "evidence-synthetic run scenarios/erp_export_basic.yaml --out generated" in doc
    assert "evidence-synthetic build" in doc
    assert "evidence-synthetic verify" in doc
    assert "verification_report.json" in doc
    assert "runtime_report.json" in doc
    assert "expected/expected_predicates.json" in doc
    assert "runtime_tmp/input" in doc
    assert "reader runtime sees input/ only" in doc
    assert "csv" in doc
    assert "xlsx" in doc
    for deferred in ("pdf", "scanned_pdf", "eml", "image", "OCR", "VLM"):
        assert deferred in doc


def _load_json(path: str) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
