import argparse
from pathlib import Path

from .convert2bids import convert
from .validate import print_validation_report, validate_bids


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert TUEP v2.0.1 to BIDS.")
    parser.add_argument(
        "--input",
        required=True,
        help="Path to TUEP v2.0.1 root (containing 00_epilepsy).",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output directory for BIDS dataset.",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Run post-conversion validation on the output directory.",
    )
    args = parser.parse_args()

    out_dir = Path(args.output)
    convert(Path(args.input), out_dir)
    if args.validate:
        errors = validate_bids(out_dir)
        print_validation_report(out_dir, errors)
        if errors:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
