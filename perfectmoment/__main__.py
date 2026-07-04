"""CLI entrypoint.

    python -m perfectmoment extract <video> --top-n 5 --min-score 0.6 [--fps 2] [--no-faces] [--out ./perfect-moment-out]
"""

import argparse
import sys
from pathlib import Path

from perfectmoment import config, pipeline


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
        video_path = Path(args.video)
        video_stem = video_path.stem
        out_dir = Path(args.out) / video_stem

        result = pipeline.run(
            video_path=video_path,
            out_dir=out_dir,
            top_n=args.top_n,
            min_score=args.min_score,
            fps=args.fps,
            force_no_faces=args.no_faces,
        )

        for warning in result.warnings:
            print(warning)
        print(f"Exported {result.exported_count} frame(s) to {out_dir}")
        print(f"Manifest: {result.manifest_path}")
        print(f"Elapsed: {result.elapsed_seconds:.1f}s")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
