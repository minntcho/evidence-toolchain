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
            f"가맹점: {truth['supplier']}",
            f"일자: {truth['period']}-15",
            f"디젤 수량: {truth['amount']} {truth['unit']}",
            "단가: 1.49",
            "합계: 62.58",
        ]
    )
