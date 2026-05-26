from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from synthetic.generators import render_document
from synthetic.manifests import SyntheticCaseManifest


@dataclass(frozen=True)
class GeneratedCase:
    case_id: str
    document_path: Path
    expected_path: Path


def generate_case(manifest: SyntheticCaseManifest, output_dir: str | Path) -> GeneratedCase:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)

    document_path = destination / f"{manifest.case_id}.txt"
    expected_path = destination / f"{manifest.case_id}.expected.json"

    document_path.write_text(render_document(manifest), encoding="utf-8")
    expected_path.write_text(
        json.dumps(manifest.to_expected_payload(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    return GeneratedCase(
        case_id=manifest.case_id,
        document_path=document_path,
        expected_path=expected_path,
    )
