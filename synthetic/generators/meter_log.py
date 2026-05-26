from __future__ import annotations

from synthetic.generators.image_degradation import degradation_note
from synthetic.manifests import SyntheticCaseManifest


def render_meter_log(manifest: SyntheticCaseManifest) -> str:
    truth = manifest.ground_truth
    return "\n".join(
        [
            f"ETC-case_id: {manifest.case_id}",
            f"ETC-document_kind: {manifest.document_kind}",
            f"ETC-quality: {manifest.quality}",
            f"ETC-text_layer: {str(manifest.text_layer).lower()}",
            f"ETC-signals: {', '.join(manifest.signals)}",
            "",
            manifest.title,
            degradation_note(manifest),
            "",
            "Handwritten meter log",
            "Date        Opening     Closing     Usage",
            f"{truth['period']}  10420       11600       {truth['amount']} {truth['unit']}",
            "",
            "Operator initials appear handwritten.",
        ]
    )
