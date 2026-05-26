from __future__ import annotations

from synthetic.manifests import SyntheticCaseManifest


def degradation_note(manifest: SyntheticCaseManifest) -> str:
    if not manifest.signals:
        return "적용된 synthetic degradation이 없습니다."
    return "적용된 synthetic degradation signal: " + ", ".join(manifest.signals) + "."
