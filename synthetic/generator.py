from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from synthetic.generators import render_document
from synthetic.manifests import SyntheticCaseManifest


@dataclass(frozen=True)
class GeneratedCase:
    case_id: str
    case_dir: Path
    document_path: Path
    expected_path: Path
    experiment_manifest_path: Path
    expected_behavior_path: Path


def generate_case(manifest: SyntheticCaseManifest, output_dir: str | Path) -> GeneratedCase:
    destination = Path(output_dir)
    case_dir = destination / manifest.case_id
    case_dir.mkdir(parents=True, exist_ok=True)

    document_path = case_dir / "evidence.txt"
    expected_path = case_dir / "expected.json"
    experiment_manifest_path = case_dir / "experiment.json"
    expected_behavior_path = case_dir / "expected-behavior.json"

    document_path.write_text(render_document(manifest), encoding="utf-8")
    expected_path.write_text(
        json.dumps(manifest.to_expected_payload(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    experiment_manifest_path.write_text(
        json.dumps(
            manifest.to_experiment_manifest_payload(),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    expected_behavior_path.write_text(
        json.dumps(
            manifest.to_expected_behavior_payload(),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    return GeneratedCase(
        case_id=manifest.case_id,
        case_dir=case_dir,
        document_path=document_path,
        expected_path=expected_path,
        experiment_manifest_path=experiment_manifest_path,
        expected_behavior_path=expected_behavior_path,
    )
