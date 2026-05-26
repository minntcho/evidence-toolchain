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
            f"기록 출처: {truth['supplier']}",
            "수기 계량기 기록",
            "일자        시작값      종료값      사용량",
            f"{truth['period']}  10420       11600       {truth['amount']} {truth['unit']}",
            "",
            "운영자 이니셜은 수기로 보입니다.",
        ]
    )
