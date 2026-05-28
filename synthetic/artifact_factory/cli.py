from __future__ import annotations

import argparse
from pathlib import Path

from synthetic.artifact_factory.e2e import build_synthetic_case, verify_generated_case


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="evidence-synthetic")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("scenario")
    build_parser.add_argument("--out", required=True)

    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("case_dir")

    args = parser.parse_args(argv)
    if args.command == "build":
        build_synthetic_case(Path(args.scenario), Path(args.out))
        return 0
    if args.command == "verify":
        report = verify_generated_case(Path(args.case_dir))
        return 0 if report.status == "passed" else 1
    raise AssertionError(f"Unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
