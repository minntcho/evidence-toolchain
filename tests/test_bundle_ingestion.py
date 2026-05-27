import json


def test_ingest_bundle_merges_attachment_inventories_in_input_order(tmp_path):
    from evidence_toolchain.file_routing import ingest_bundle
    from evidence_toolchain.ingestion import AttachmentBundle, RawAttachment

    text_path = tmp_path / "usage.txt"
    text_path.write_text("사용량 6.4 MWh\n", encoding="utf-8")
    csv_path = tmp_path / "usage.csv"
    csv_path.write_text("site,amount\nOCH-01,6400\n", encoding="utf-8")
    bin_path = tmp_path / "raw.bin"
    bin_path.write_bytes(b"\x00\x01")

    bundle = AttachmentBundle(
        bundle_id="bundle_001",
        attachments=(
            RawAttachment.from_path(text_path, attachment_id="raw_txt"),
            RawAttachment.from_path(csv_path, attachment_id="raw_csv"),
            RawAttachment.from_path(bin_path, attachment_id="raw_bin"),
        ),
    )

    inventory = ingest_bundle(bundle)
    payload = inventory.to_dict()

    assert payload["bundle_id"] == "bundle_001"
    assert [attachment["attachment_id"] for attachment in payload["attachments"]] == [
        "raw_txt",
        "raw_csv",
        "raw_bin",
    ]
    assert [decision["route"] for decision in payload["route_decisions"]] == [
        "plain_text",
        "delimited_table",
        "unknown",
    ]
    assert [decision["attachment_id"] for decision in payload["safety_decisions"]] == [
        "raw_txt",
        "raw_csv",
        "raw_bin",
    ]
    assert [artifact["parent_id"] for artifact in payload["artifacts"]] == [
        "raw_txt",
        "raw_csv",
        "raw_bin",
    ]
    assert [unit["producer"] for unit in payload["units"]] == [
        "plain_text_reader",
        "delimited_table_reader",
        "delimited_table_reader",
        "delimited_table_reader",
    ]
    assert payload["issues"][-1]["code"] == "unsupported_media_type"
    assert "atom_type" not in payload["units"][0]
    json.dumps(payload)


def test_ingest_bundle_applies_shared_safety_policy_to_every_attachment(tmp_path):
    from evidence_toolchain.file_routing import SafetyLimits, SafetyPolicy, ingest_bundle
    from evidence_toolchain.ingestion import AttachmentBundle, RawAttachment

    small_path = tmp_path / "small.txt"
    small_path.write_text("ok\n", encoding="utf-8")
    large_path = tmp_path / "large.txt"
    large_path.write_text("too large\n", encoding="utf-8")

    bundle = AttachmentBundle(
        bundle_id="bundle_001",
        attachments=(
            RawAttachment.from_path(small_path, attachment_id="raw_small"),
            RawAttachment.from_path(large_path, attachment_id="raw_large"),
        ),
    )

    inventory = ingest_bundle(
        bundle,
        safety_policy=SafetyPolicy(SafetyLimits(max_file_size_bytes=4)),
    )
    payload = inventory.to_dict()

    assert [decision["allowed"] for decision in payload["safety_decisions"]] == [
        True,
        False,
    ]
    assert payload["artifacts"][1]["artifact_type"] == "unsupported_attachment"
    assert payload["issues"][0]["code"] == "plain_text_low_provenance"
    assert payload["issues"][1]["code"] == "file_too_large"


def test_merge_evidence_inventories_allows_empty_bundle_inventory():
    from evidence_toolchain.ingestion import EvidenceInventory, merge_evidence_inventories

    inventory = merge_evidence_inventories(bundle_id="bundle_empty", inventories=())
    payload = inventory.to_dict()

    assert payload == {
        "bundle_id": "bundle_empty",
        "attachments": [],
        "artifacts": [],
        "units": [],
        "route_decisions": [],
        "safety_decisions": [],
        "issues": [],
    }
    assert isinstance(inventory, EvidenceInventory)
