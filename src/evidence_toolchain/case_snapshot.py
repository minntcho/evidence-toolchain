from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any

from evidence_toolchain.claims import DeclaredClaim
from evidence_toolchain.ingestion import EvidenceInventory, RawAttachment


@dataclass(frozen=True)
class EvidenceCaseSnapshot:
    """Code-level SSOT wrapper for one fixed evidence case."""

    snapshot_id: str
    inventory: EvidenceInventory
    claims: tuple[DeclaredClaim, ...]
    schema_bindings: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def identity_payload(self) -> dict[str, Any]:
        return evidence_case_identity_payload(
            inventory=self.inventory,
            claims=self.claims,
            schema_bindings=self.schema_bindings,
        )

    def to_dict(self) -> dict[str, Any]:
        return _to_json_compatible(self)


def build_evidence_case_snapshot(
    *,
    inventory: EvidenceInventory,
    claims: tuple[DeclaredClaim, ...],
    schema_bindings: tuple[str, ...] = (),
    metadata: dict[str, Any] | None = None,
    snapshot_id: str | None = None,
) -> EvidenceCaseSnapshot:
    active_schema_bindings = tuple(schema_bindings)
    identity_payload = evidence_case_identity_payload(
        inventory=inventory,
        claims=tuple(claims),
        schema_bindings=active_schema_bindings,
    )
    active_snapshot_id = snapshot_id or f"case_snapshot:{_payload_digest(identity_payload)}"
    return EvidenceCaseSnapshot(
        snapshot_id=active_snapshot_id,
        inventory=inventory,
        claims=tuple(claims),
        schema_bindings=active_schema_bindings,
        metadata=dict(metadata or {}),
    )


def evidence_case_identity_payload(
    *,
    inventory: EvidenceInventory,
    claims: tuple[DeclaredClaim, ...],
    schema_bindings: tuple[str, ...] = (),
) -> dict[str, Any]:
    return {
        "version": "evidence_case_snapshot.v1",
        "inventory": _identity_value(inventory),
        "claims": _identity_value(tuple(claims)),
        "schema_bindings": _identity_value(tuple(schema_bindings)),
    }


def strategy_view_metadata(
    *,
    snapshot: EvidenceCaseSnapshot,
    strategy_id: str,
    strategy_version: str,
    run_id: str,
    view_kind: str,
) -> dict[str, str]:
    return {
        "case_snapshot_id": snapshot.snapshot_id,
        "strategy_id": strategy_id,
        "strategy_version": strategy_version,
        "run_id": run_id,
        "view_kind": view_kind,
    }


def _payload_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _identity_value(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value):
        return {
            item.name: _identity_value(getattr(value, item.name))
            for item in fields(value)
            if not _is_local_attachment_path(value, item.name)
        }
    if isinstance(value, dict):
        return {
            str(key): _identity_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, tuple | list):
        return [_identity_value(item) for item in value]
    return value


def _is_local_attachment_path(value: Any, field_name: str) -> bool:
    return isinstance(value, RawAttachment) and field_name == "path"


def _to_json_compatible(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value):
        return {
            item.name: _to_json_compatible(getattr(value, item.name))
            for item in fields(value)
        }
    if isinstance(value, dict):
        return {
            str(key): _to_json_compatible(item)
            for key, item in value.items()
        }
    if isinstance(value, tuple | list):
        return [_to_json_compatible(item) for item in value]
    return value
