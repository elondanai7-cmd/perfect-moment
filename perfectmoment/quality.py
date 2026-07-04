"""Stage 3: cheap technical filter — reject blurry/dark/blown-out frames before
any face or aesthetic model runs (those are far more expensive per frame).

Sharpness uses Laplacian variance (SKILL.md pitfall #2: must resize to a fixed
long edge first, since variance is scale-dependent and raw-resolution scores
aren't comparable across frames extracted at different sizes).

Thresholds here (config.BLUR_VARIANCE_MIN, BRIGHTNESS_MIN/MAX) are global
placeholders; step A9 calibrates them per capture source (phone/DSLR/low-light).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from perfectmoment import config


@dataclass(frozen=True)
class QualityScore:
    path: Path
    sharpness: float  # Laplacian variance, higher = sharper
    brightness: float  # mean pixel intensity, 0-255
    passed: bool
    reject_reason: str | None


def _resize_long_edge(image: np.ndarray, long_edge: int) -> np.ndarray:
    """Resize so the longer side equals `long_edge`, preserving aspect ratio.

    Fixes SKILL.md pitfall #2: Laplacian variance must be computed at a
    consistent scale or scores aren't comparable across frames.
    """
    h, w = image.shape[:2]
    current_long_edge = max(h, w)
    if current_long_edge == long_edge:
        return image
    scale = long_edge / current_long_edge
    new_size = (round(w * scale), round(h * scale))
    return cv2.resize(image, new_size, interpolation=cv2.INTER_AREA)


def score_frame(
    image_path: Path,
    blur_variance_min: float = config.BLUR_VARIANCE_MIN,
    brightness_min: int = config.BRIGHTNESS_MIN,
    brightness_max: int = config.BRIGHTNESS_MAX,
    resize_long_edge: int = config.LAPLACIAN_RESIZE_LONG_EDGE,
) -> QualityScore:
    """Compute sharpness + brightness for one frame and decide pass/reject."""
    image = cv2.imread(str(image_path))
    if image is None:
        return QualityScore(
            path=image_path, sharpness=0.0, brightness=0.0,
            passed=False, reject_reason="unreadable image file",
        )

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray_resized = _resize_long_edge(gray, resize_long_edge)

    sharpness = float(cv2.Laplacian(gray_resized, cv2.CV_64F).var())
    brightness = float(gray_resized.mean())

    # Brightness checked first: a flat black/white frame has ~zero Laplacian
    # variance too, and "underexposed"/"blown out" is the more useful diagnosis
    # than "blurry" for a uniform-color frame.
    reject_reason = None
    if brightness < brightness_min:
        reject_reason = f"underexposed (brightness {brightness:.1f} < {brightness_min})"
    elif brightness > brightness_max:
        reject_reason = f"blown out (brightness {brightness:.1f} > {brightness_max})"
    elif sharpness < blur_variance_min:
        reject_reason = f"blurry (sharpness {sharpness:.1f} < {blur_variance_min})"

    return QualityScore(
        path=image_path,
        sharpness=sharpness,
        brightness=brightness,
        passed=reject_reason is None,
        reject_reason=reject_reason,
    )


def filter_frames(image_paths: list[Path]) -> tuple[list[QualityScore], list[QualityScore]]:
    """Score every frame; return (survivors, rejected), both as QualityScore lists."""
    scores = [score_frame(p) for p in image_paths]
    survivors = [s for s in scores if s.passed]
    rejected = [s for s in scores if not s.passed]
    return survivors, rejected
