"""CLI entrypoint (stub for step A1 — full wiring lands in A7).

    python -m perfectmoment extract <video> --top-n 5 --min-score 0.6 [--fps 2] [--no-faces] [--out ./perfect-moment-out]
"""

import argparse
import sys

from perfectmoment import config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="perfectmoment",
        description="Extract the best frames from a video.",
    )
    subparsers = parser.add_subparsers(dest="command")

    extract = subparsers.add_parser("extract", help="Extract ranked best frames from a video.")
    extract.add_argument("video", help="Path to the input video file.")
    extract.add_argument("--top-n", type=int, default=config.DEFAULT_TOP_N)
    extract.add_argument("--min-score", type=float, default=config.DEFAULT_MIN_SCORE)
    extract.add_argument("--fps", type=float, default=config.DEFAULT_FPS)
    extract.add_argument("--no-faces", action="store_true", help="Skip face/eye scoring (product-lane profile).")
    extract.add_argument("--out", default=config.DEFAULT_OUT_DIR)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "extract":
        print("NOTE: pipeline not wired yet (lands in step A7). Parsed args:")
        print(vars(args))
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
