from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvidenceIssue:
    """evidence 처리 중 보존해야 하는 issue 또는 review signal입니다."""

    code: str
    severity: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
        }
