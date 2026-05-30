from __future__ import annotations

from evidence_toolchain import EvidenceIssue, RawAttachment


def test_public_import_surface_for_mobile_workflow_smoke() -> None:
    assert RawAttachment.__name__ == "RawAttachment"
    assert EvidenceIssue.__name__ == "EvidenceIssue"
