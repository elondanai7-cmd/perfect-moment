"""Pick THE single best frame from a video, using the existing scoring engine.

This is a thin wrapper on top of the full pipeline (perfectmoment.pipeline) --
it does not introduce a new scoring model, it just runs the same engine with
top_n=1 and prints the full reasoning (every sub-score for every candidate
frame, not just the winner) so the decision is transparent, not a black box.

Usage:
    python scripts/pick_best_frame.py "<video path>" [--out ./out]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from perfectmoment import config, pipeline  # noqa: E402


def main() -> None:
    # Windows' default stdout/stderr encoding (cp1252) crashes on Hebrew or
    # other non-Latin filenames/paths -- reconfigure to UTF-8.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Pick the single best frame from a video.")
    parser.add_argument("video", help="Path to the input video file.")
    parser.add_argument("--out", default=config.DEFAULT_OUT_DIR)
    parser.add_argument("--min-score", type=float, default=config.DEFAULT_MIN_SCORE)
    args = parser.parse_args()

    video_path = Path(args.video)
    out_dir = Path(args.out) / video_path.stem

    result = pipeline.run(video_path, out_dir, top_n=1, min_score=args.min_score)

    for w in result.warnings:
        print(w)

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    frames = manifest["frames"]

    if not frames:
        print("No frame could be selected (unexpected -- check warnings above).")
        return

    winner = frames[0]
    print()
    print("=" * 60)
    print(f"WINNER: {out_dir / winner['output_file']}")
    print("=" * 60)
    print(f"scene            = {winner['scene']} (weights: perfectmoment/config.py SCORING['{winner['scene'].upper()}'])")
    print(f"final score      = {winner['final']:.3f}")
    print(f"reason           = {winner['reason']}")
    print(f"gated            = {winner['gated']}" + (f" ({winner['gate_reason']})" if winner['gated'] else ""))
    print(f"  sharpness      = {winner['sharpness']:.1f}   blur_norm = {winner['blur_norm']:.3f}")
    print(f"  face_count     = {winner['face_count']}")
    print(f"  eyes_open      = {winner['eyes_open']:.3f}")
    print(f"  smile          = {winner['smile']:.3f}  (duchenne_bonus={winner['duchenne_bonus']:.3f})")
    print(f"  gaze_deviation = {winner['gaze_deviation']:.3f}  (0 = looking at camera)")
    print(f"  composition    = {winner['composition']:.3f}")
    print(f"  face_lighting  = {winner['face_lighting']:.3f}")
    print(f"  aesthetic_norm = {winner['aesthetic_norm']:.3f}")
    print(f"  low_quality    = {winner['low_quality']}")
    print(f"  timestamp      = {winner['timestamp_seconds']:.2f}s into the clip")


if __name__ == "__main__":
    main()
