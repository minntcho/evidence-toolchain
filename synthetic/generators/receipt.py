from __future__ import annotations

from synthetic.generators.image_degradation import degradation_note
from synthetic.manifests import SyntheticCaseManifest


def render_receipt(manifest: SyntheticCaseManifest) -> str:
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
            f"Merchant: {truth['supplier']}",
            f"Date: {truth['period']}-15",
            f"Diesel quantity: {truth['amount']} {truth['unit']}",
            "Unit price: 1.49",
            "Total: 62.58",
        ]
    )
