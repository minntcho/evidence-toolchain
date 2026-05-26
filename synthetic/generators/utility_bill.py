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
            f"공급자: {truth['supplier']}",
            f"사업장: {truth['site']}",
            f"서비스 기간: {truth['period']}",
            "",
            "사용량 표",
            "활동              수량        단위",
            f"{truth['activity']}       {truth['amount']}       {truth['unit']}",
        ]
    )
