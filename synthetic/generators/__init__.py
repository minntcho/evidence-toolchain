from __future__ import annotations

from synthetic.generators.meter_log import render_meter_log
from synthetic.generators.receipt import render_receipt
from synthetic.generators.utility_bill import render_utility_bill
from synthetic.manifests import SyntheticCaseManifest


def render_document(manifest: SyntheticCaseManifest) -> str:
    if manifest.document_kind == "utility_bill":
        return render_utility_bill(manifest)
    if manifest.document_kind == "receipt":
        return render_receipt(manifest)
    if manifest.document_kind == "meter_log":
        return render_meter_log(manifest)
    raise ValueError(f"Unsupported synthetic document kind: {manifest.document_kind}")
