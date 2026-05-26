from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from synthetic.generator import generate_case
from synthetic.manifests import load_manifest


DEFAULT_CASES = [
    "utility_bill_basic",
    "scanned_utility_bill_rotated",
    "handwritten_meter_log",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate synthetic evidence cases.")
    parser.add_argument(
        "--output-dir",
        default="tests/fixtures/generated",
        help="Directory for generated documents and expected manifests.",
    )
    parser.add_argument(
        "case_ids",
        nargs="*",
        default=DEFAULT_CASES,
        help="Synthetic case ids to generate.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    generated = [
        generate_case(load_manifest(case_id), output_dir)
        for case_id in args.case_ids
    ]

    for item in generated:
        print(f"{item.case_id}: {item.document_path}")
    print(f"generated {len(generated)} evidence cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
