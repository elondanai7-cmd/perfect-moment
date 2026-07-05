"""CLI entrypoint.

    python -m perfectmoment extract <video> --top-n 5 --min-score 0.6 [--fps 2] [--no-faces] [--out ./perfect-moment-out]
    python -m perfectmoment batch <folder>  [same flags]   # cull a whole shoot folder

`batch` is the photographer beachhead workflow: point it at a folder of clips
from a shoot; the NIMA model loads ONCE for the whole batch (not per clip),
each video gets its own <out>/<video-stem>/ output + report.html, and a
batch summary prints at the end.
"""

import argparse
import sys
from pathlib import Path

from perfectmoment import config, pipeline

VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="perfectmoment",
        description="Extract the best frames from a video.",
    )
    subparsers = parser.add_subparsers(dest="command")

    def add_common_flags(sub):
        sub.add_argument("--top-n", type=int, default=config.DEFAULT_TOP_N)
        sub.add_argument("--min-score", type=float, default=config.DEFAULT_MIN_SCORE)
        sub.add_argument("--fps", type=float, default=config.DEFAULT_FPS)
        sub.add_argument("--no-faces", action="store_true", help="Skip face/eye scoring (product-lane profile).")
        sub.add_argument("--out", default=config.DEFAULT_OUT_DIR)
        sub.add_argument("--no-report", action="store_true", help="Skip generating the report.html contact sheet.")

    extract = subparsers.add_parser("extract", help="Extract ranked best frames from a video.")
    extract.add_argument("video", help="Path to the input video file.")
    add_common_flags(extract)

    batch = subparsers.add_parser("batch", help="Cull a whole folder of clips (photographer shoot workflow).")
    batch.add_argument("folder", help="Path to a folder containing video files.")
    add_common_flags(batch)

    return parser


def main(argv=None) -> int:
    # Windows' default stdout/stderr encoding (cp1252) crashes on Hebrew or
    # other non-Latin filenames/paths (e.g. a Hebrew-named video or output
    # dir) -- reconfigure to UTF-8 so print() never raises UnicodeEncodeError.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "extract":
        video_path = Path(args.video)
        out_dir = Path(args.out) / video_path.stem

        result = pipeline.run(
            video_path=video_path,
            out_dir=out_dir,
            top_n=args.top_n,
            min_score=args.min_score,
            fps=args.fps,
            force_no_faces=args.no_faces,
            on_progress=print,
            make_report=not args.no_report,
        )

        _print_result(result, out_dir)
        return 0

    if args.command == "batch":
        folder = Path(args.folder)
        if not folder.is_dir():
            print(f"Not a folder: {folder}")
            return 1

        videos = sorted(p for p in folder.iterdir() if p.suffix.lower() in VIDEO_EXTENSIONS)
        if not videos:
            print(f"No video files found in {folder} (looked for: {', '.join(sorted(VIDEO_EXTENSIONS))})")
            return 1

        # Load the NIMA model ONCE for the whole shoot -- per-clip reload
        # would waste ~2.5s x number of clips for nothing.
        from perfectmoment.aesthetics import AestheticScorer

        print(f"Batch: {len(videos)} clip(s) in {folder}")
        print("Loading aesthetic model (once for the whole batch)...")
        scorer = AestheticScorer()

        summary = []
        failures = []
        for i, video_path in enumerate(videos, start=1):
            print(f"\n=== [{i}/{len(videos)}] {video_path.name} ===")
            out_dir = Path(args.out) / video_path.stem
            try:
                result = pipeline.run(
                    video_path=video_path,
                    out_dir=out_dir,
                    top_n=args.top_n,
                    min_score=args.min_score,
                    fps=args.fps,
                    force_no_faces=args.no_faces,
                    scorer=scorer,
                    on_progress=print,
                    make_report=not args.no_report,
                )
                _print_result(result, out_dir)
                summary.append((video_path.name, result))
            except Exception as exc:  # noqa: BLE001 -- one broken clip must not kill the whole shoot
                print(f"FAILED: {exc}")
                failures.append((video_path.name, str(exc)))

        print("\n" + "=" * 50)
        print(f"Batch done: {len(summary)} succeeded, {len(failures)} failed.")
        for name, result in summary:
            flag = "" if result.quality_bar_met else "  [low quality]"
            print(f"  {name}: {result.exported_count} frame(s), {result.elapsed_seconds:.0f}s{flag}")
        for name, error in failures:
            print(f"  {name}: FAILED -- {error}")
        return 0 if not failures else 1

    parser.print_help()
    return 0


def _print_result(result, out_dir: Path) -> None:
    for warning in result.warnings:
        print(warning)
    print(f"Exported {result.exported_count} frame(s) to {out_dir}")
    print(f"Manifest: {result.manifest_path}")
    if result.report_path:
        print(f"Report:   {result.report_path}")
    print(f"Elapsed: {result.elapsed_seconds:.1f}s")


if __name__ == "__main__":
    sys.exit(main())
