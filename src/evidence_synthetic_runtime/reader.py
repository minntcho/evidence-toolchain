from __future__ import annotations

from pathlib import Path

from evidence_toolchain.file_routing import ingest_attachment
from evidence_toolchain.ingestion import EvidenceInventory, RawAttachment


def run_runtime_artifact(
    *,
    bundle_id: str,
    attachment_id: str,
    path: str | Path,
) -> dict[str, object]:
    inventory = ingest_attachment(
        bundle_id,
        RawAttachment.from_path(path, attachment_id=attachment_id),
    )
    observation_count = len(inventory.units)
    return {
        "reader": _reader_from_inventory(inventory),
        "reader_status": "ingested" if observation_count > 0 else "failed",
        "observation_count": observation_count,
        "issue_count": len(inventory.issues),
    }


def _reader_from_inventory(inventory: EvidenceInventory) -> str:
    for unit in inventory.units:
        return unit.producer
    for artifact in inventory.artifacts:
        reader = artifact.metadata.get("reader")
        if reader is not None:
            return str(reader)
    return "unknown"
