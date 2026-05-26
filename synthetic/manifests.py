from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


MANIFEST_DIR = Path(__file__).parent / "manifests"


@dataclass(frozen=True)
class ExpectedBehavior:
    plan_includes: list[str]
    fallbacks_include: list[str]
    issues_include: list[str]


@dataclass(frozen=True)
class SyntheticCaseManifest:
    case_id: str
    document_kind: str
    title: str
    quality: str
    text_layer: bool
    signals: list[str]
    ground_truth: dict[str, object]
    expected_behavior: ExpectedBehavior

    def to_expected_payload(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "document_kind": self.document_kind,
            "artifact": {
                "path": "evidence.txt",
                "format": "txt",
                "media_type": "text/plain",
                "document_kind": self.document_kind,
            },
            "ground_truth": self.ground_truth,
            "expected_observation": {
                "document_class": self.document_kind,
                "has_text_layer": self.text_layer,
                "quality": self.quality,
                "signals": self.signals,
            },
            "expected_behavior": {
                "plan_includes": self.expected_behavior.plan_includes,
                "fallbacks_include": self.expected_behavior.fallbacks_include,
                "issues_include": self.expected_behavior.issues_include,
            },
            "expected_plan": {
                "selected_capabilities": self.expected_behavior.plan_includes,
                "fallbacks": self.expected_behavior.fallbacks_include,
                "issues": self.expected_behavior.issues_include,
            },
        }


def load_manifest(case_id: str) -> SyntheticCaseManifest:
    path = MANIFEST_DIR / f"{case_id}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return _manifest_from_dict(data)


def load_manifests() -> list[SyntheticCaseManifest]:
    return [_manifest_from_dict(json.loads(path.read_text(encoding="utf-8"))) for path in sorted(MANIFEST_DIR.glob("*.json"))]


def _manifest_from_dict(data: dict[str, object]) -> SyntheticCaseManifest:
    expected = data["expected_behavior"]
    if not isinstance(expected, dict):
        raise ValueError("expected_behavior는 object여야 합니다")

    return SyntheticCaseManifest(
        case_id=str(data["case_id"]),
        document_kind=str(data["document_kind"]),
        title=str(data["title"]),
        quality=str(data["quality"]),
        text_layer=bool(data["text_layer"]),
        signals=[str(item) for item in data.get("signals", [])],
        ground_truth=dict(data["ground_truth"]),
        expected_behavior=ExpectedBehavior(
            plan_includes=[str(item) for item in expected.get("plan_includes", [])],
            fallbacks_include=[str(item) for item in expected.get("fallbacks_include", [])],
            issues_include=[str(item) for item in expected.get("issues_include", [])],
        ),
    )
