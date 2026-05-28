import json


def test_experiment_manifest_loads_json_and_builds_attachment_bundle(tmp_path):
    from evidence_toolchain import load_experiment_manifest

    evidence_path = tmp_path / "evidence.txt"
    evidence_path.write_text("electricity usage 6.4 MWh\n", encoding="utf-8")
    manifest_path = tmp_path / "experiment.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "experiment_manifest_v0",
                "experiment_id": "experiment_001",
                "bundle_id": "bundle_001",
                "attachments": [
                    {
                        "attachment_id": "raw_evidence",
                        "path": "evidence.txt",
                        "declared_media_type": "text/plain",
                    }
                ],
                "claims": [
                    {
                        "x_id": "x_001",
                        "fields": {
                            "amount": 6400,
                            "unit": "kWh",
                            "period": "2025-03",
                        },
                    }
                ],
                "budget": {
                    "max_iterations": 6,
                    "max_model_calls": 2,
                    "max_new_units": 10,
                    "max_new_atoms": 10,
                },
                "allowed_capabilities": [
                    "pdfplumber_extract",
                    "manual_review_request",
                ],
                "metadata": {"purpose": "deterministic demo"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    manifest = load_experiment_manifest(manifest_path)
    payload = manifest.to_dict()
    bundle = manifest.to_attachment_bundle(base_dir=tmp_path)

    assert payload["schema_version"] == "experiment_manifest_v0"
    assert payload["experiment_id"] == "experiment_001"
    assert payload["claims"][0]["fields"]["unit"] == "kWh"
    assert payload["budget"]["max_iterations"] == 6
    assert payload["allowed_capabilities"] == [
        "pdfplumber_extract",
        "manual_review_request",
    ]
    assert bundle.bundle_id == "bundle_001"
    assert bundle.metadata["experiment_id"] == "experiment_001"
    assert bundle.attachments[0].attachment_id == "raw_evidence"
    assert bundle.attachments[0].declared_media_type == "text/plain"
    assert bundle.attachments[0].sha256
