"""A9 calibration harness.

This is the TOOL for per-source calibration, not calibrated values themselves --
real calibration (per plan step A9) requires real phone/DSLR/low-light event
footage, which this repo does not have yet. Running this script against
synthetic test patterns would produce meaningless numbers; it is built now so
that calibration is a single command once real clips are available.

Usage:
    python scripts/calibrate.py known_sharp/*.jpg known_blurry/*.jpg --labels sharp sharp sharp blurry blurry

Simplest real workflow (once you have real footage):
    1. From a real event clip, manually pick ~10 frames you'd call "sharp,
       keep" and ~10 you'd call "blurry, reject".
    2. Save them into two folders: calibration/sharp/ and calibration/blurry/.
    3. Run:
           python scripts/calibrate.py --sharp-dir calibration/sharp --blurry-dir calibration/blurry
    4. The script prints a suggested BLUR_VARIANCE_MIN split point and the
       score distributions -- update perfectmoment/config.py by hand with the
       suggested value (kept manual and reviewable, not auto-written, so a
       human eyeballs the split before it goes live).
"""

from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from perfectmoment import quality  # noqa: E402


def load_scores(image_dir: Path) -> list[float]:
    paths = sorted(list(image_dir.glob("*.jpg")) + list(image_dir.glob("*.jpeg")) + list(image_dir.glob("*.png")))
    if not paths:
        raise SystemExit(f"No images found in {image_dir}")
    return [quality.score_frame(p).sharpness for p in paths]


def suggest_split_point(sharp_scores: list[float], blurry_scores: list[float]) -> float:
    """Midpoint between the lowest 'sharp' score and the highest 'blurry' score.

    If the sets overlap (lowest sharp < highest blurry), there is no clean
    split -- the script reports this honestly rather than picking a number
    that will misclassify real footage.
    """
    min_sharp = min(sharp_scores)
    max_blurry = max(blurry_scores)
    if min_sharp <= max_blurry:
        raise ValueError(
            f"No clean separation: lowest sharp-labeled score ({min_sharp:.1f}) is <= "
            f"highest blurry-labeled score ({max_blurry:.1f}). The sample set overlaps -- "
            "collect more/better-labeled examples before trusting a threshold."
        )
    return (min_sharp + max_blurry) / 2


def main() -> None:
    parser = argparse.ArgumentParser(description="A9 per-source blur threshold calibration harness.")
    parser.add_argument("--sharp-dir", required=True, type=Path, help="Directory of frames labeled 'keep, sharp enough'.")
    parser.add_argument("--blurry-dir", required=True, type=Path, help="Directory of frames labeled 'reject, too blurry'.")
    args = parser.parse_args()

    sharp_scores = load_scores(args.sharp_dir)
    blurry_scores = load_scores(args.blurry_dir)

    print(f"Sharp-labeled  (n={len(sharp_scores)}): min={min(sharp_scores):.1f} max={max(sharp_scores):.1f} mean={statistics.mean(sharp_scores):.1f}")
    print(f"Blurry-labeled (n={len(blurry_scores)}): min={min(blurry_scores):.1f} max={max(blurry_scores):.1f} mean={statistics.mean(blurry_scores):.1f}")

    try:
        split = suggest_split_point(sharp_scores, blurry_scores)
        print(f"\nSuggested BLUR_VARIANCE_MIN: {split:.1f}")
        print("Review this by eye, then update perfectmoment/config.py manually.")
    except ValueError as exc:
        print(f"\nCannot suggest a threshold yet: {exc}")


if __name__ == "__main__":
    main()
