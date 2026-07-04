"""Stage 6: composition scoring + weighted compose + dedupe/diversity ranking.

Composition sub-score is computed HERE (not in faces.py) from the FaceBox
objects faces.py emits, per the plan's Architecture Overview: face size
(bigger = more prominent subject) + centering distance from rule-of-thirds
points. For --no-faces / product-lane frames (no boxes), composition falls
back to a neutral 0.5 so the weighted formula still works (WEIGHTS_PRODUCT
excludes face_quality entirely, so composition's neutral value there mostly
affects nothing — kept only for a single manifest schema across both lanes).

final = 0.3*blur_norm + 0.4*face_quality + 0.3*aesthetic_norm   (portrait profile)
final = 0.5*blur_norm + 0.5*aesthetic_norm                        (product profile, no faces)

Dedupe: perceptual hash (phash) with hamming distance <= config.DEDUPE_PHASH_HAMMING_MAX
collapses near-identical burst-neighbor frames so the top-N isn't N copies of
the same instant (SKILL.md pitfall #7).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import imagehash
from PIL import Image

from perfectmoment import config
from perfectmoment.faces import FaceBox, FaceScore
from perfectmoment.quality import QualityScore

# Rule-of-thirds intersection points, normalized 0-1.
RULE_OF_THIRDS_POINTS = [(1 / 3, 1 / 3), (2 / 3, 1 / 3), (1 / 3, 2 / 3), (2 / 3, 2 / 3)]


@dataclass(frozen=True)
class RankedFrame:
    path: Path
    timestamp_seconds: float
    sharpness: float
    brightness: float
    face_count: int
    eyes_open: float
    smile: float
    composition: float
    aesthetic_norm: float
    blur_norm: float
    final: float
    low_quality: bool = False


def _normalize(value: float, lo: float, hi: float) -> float:
    """Clamp-normalize value into [0, 1] given an expected [lo, hi] range."""
    if hi <= lo:
        return 0.5
    return max(0.0, min(1.0, (value - lo) / (hi - lo)))


def composition_score(face_boxes: list[FaceBox]) -> float:
    """Face size (prominence) + rule-of-thirds centering distance, averaged across faces.

    Returns 0.5 (neutral) when there are no faces, so the product-lane / --no-faces
    path still produces a valid manifest field even though this term is excluded
    from that profile's weighted formula.
    """
    if not face_boxes:
        return 0.5

    scores = []
    for box in face_boxes:
        # Size term: bigger face (closer to camera / more prominent subject) scores higher.
        area = box.width * box.height
        size_score = _normalize(area, lo=0.0, hi=0.5)  # a face filling half the frame is already excellent

        # Centering term: distance from the nearest rule-of-thirds point (smaller = better).
        cx, cy = box.center
        min_dist = min(((cx - px) ** 2 + (cy - py) ** 2) ** 0.5 for px, py in RULE_OF_THIRDS_POINTS)
        # Max possible distance in unit square is sqrt(2)/... use a practical normalization cap.
        centering_score = 1.0 - _normalize(min_dist, lo=0.0, hi=0.5)

        scores.append((size_score + centering_score) / 2)

    return sum(scores) / len(scores)


def phash_of(image_path: Path) -> imagehash.ImageHash:
    with Image.open(image_path) as img:
        return imagehash.phash(img)


def dedupe_by_similarity(
    candidates: list[RankedFrame],
    hashes: dict[Path, imagehash.ImageHash],
    hamming_max: int = config.DEDUPE_PHASH_HAMMING_MAX,
) -> list[RankedFrame]:
    """Greedily keep the highest-`final`-scoring frame from each near-duplicate cluster.

    candidates must already be sorted by `final` descending. Walks the list and
    drops any frame whose phash is within `hamming_max` of an already-kept frame.
    """
    kept: list[RankedFrame] = []
    for candidate in candidates:
        candidate_hash = hashes[candidate.path]
        is_near_duplicate = any(
            (candidate_hash - hashes[k.path]) <= hamming_max for k in kept
        )
        if not is_near_duplicate:
            kept.append(candidate)
    return kept


def compose_and_rank(
    quality_scores: list[QualityScore],
    face_scores: dict[Path, FaceScore],
    aesthetic_scores: dict[Path, float],
    no_faces_profile: bool = False,
    min_score: float = config.DEFAULT_MIN_SCORE,
) -> tuple[list[RankedFrame], bool]:
    """Combine all sub-scores into ranked, deduped candidates.

    Returns (ranked_frames, quality_bar_met). quality_bar_met is False when no
    candidate's final score reaches `min_score` (AC-14 graceful-degrade trigger) --
    the caller still gets ranked frames back, just flagged low_quality.
    """
    weights = config.WEIGHTS_PRODUCT if no_faces_profile else config.WEIGHTS_PORTRAIT

    ranked: list[RankedFrame] = []
    for qs in quality_scores:
        if not qs.passed:
            continue
        face = face_scores.get(qs.path)
        aesthetic_raw = aesthetic_scores.get(qs.path, 0.0)

        blur_norm = _normalize(qs.sharpness, lo=0.0, hi=1000.0)
        aesthetic_norm = _normalize(aesthetic_raw, lo=1.0, hi=10.0)
        face_quality = ((face.eyes_open + face.smile) / 2) if face and face.face_count > 0 else 0.0
        composition = composition_score(face.face_boxes if face else [])

        if no_faces_profile:
            final = weights["blur"] * blur_norm + weights["aesthetic"] * aesthetic_norm
        else:
            final = (
                weights["blur"] * blur_norm
                + weights["face_quality"] * face_quality
                + weights["aesthetic"] * aesthetic_norm
            )

        ranked.append(
            RankedFrame(
                path=qs.path,
                timestamp_seconds=0.0,  # filled in by caller (pipeline.py) from ExtractedFrame
                sharpness=qs.sharpness,
                brightness=qs.brightness,
                face_count=face.face_count if face else 0,
                eyes_open=face.eyes_open if face else 0.0,
                smile=face.smile if face else 0.0,
                composition=composition,
                aesthetic_norm=aesthetic_norm,
                blur_norm=blur_norm,
                final=final,
            )
        )

    # Deterministic tiebreak: sort by final desc, then by path name (stable, no RNG).
    ranked.sort(key=lambda r: (-r.final, str(r.path)))

    hashes = {r.path: phash_of(r.path) for r in ranked}
    deduped = dedupe_by_similarity(ranked, hashes)

    quality_bar_met = any(r.final >= min_score for r in deduped)
    if not quality_bar_met:
        deduped = [r.__class__(**{**r.__dict__, "low_quality": True}) for r in deduped]
    else:
        deduped = [
            r.__class__(**{**r.__dict__, "low_quality": r.final < min_score}) for r in deduped
        ]

    return deduped, quality_bar_met
