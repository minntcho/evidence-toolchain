from __future__ import annotations

from synthetic.manifests import SyntheticCaseManifest


def degradation_note(manifest: SyntheticCaseManifest) -> str:
    if not manifest.signals:
        return "No synthetic degradation applied."
    return "Synthetic degradation signals: " + ", ".join(manifest.signals) + "."
