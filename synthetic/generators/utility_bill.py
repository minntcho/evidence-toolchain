from __future__ import annotations

from synthetic.generators.image_degradation import degradation_note
from synthetic.manifests import SyntheticCaseManifest


def render_utility_bill(manifest: SyntheticCaseManifest) -> str:
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
            f"Supplier: {truth['supplier']}",
            f"Site: {truth['site']}",
            f"Service period: {truth['period']}",
            "",
            "Usage table",
            "Activity          Amount      Unit",
            f"{truth['activity']}       {truth['amount']}       {truth['unit']}",
        ]
    )
