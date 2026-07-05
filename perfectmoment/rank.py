"""Stage 6: two-pass, evidence-based "professional photographer" ranking.

Research: .specs/scratchpad/scoring-research.md (33 sources -- Narrative
Select / Aftershoot / FilterPixel docs, Google Top Shot patent US10671895,
NIMA paper, Duchenne-smile & gaze studies, pro culling guides).

PASS 1 -- hard gates (reject obvious technical failures, matching how real
culling tools work, e.g. Aftershoot's separate "Warnings" bucket for closed
eyes): a gated frame gets `gated=True` + a named `gate_reason` and is ranked
BELOW every non-gated frame, but is NEVER deleted -- this preserves the
AC-14 "never return empty" contract (a clip where every frame technically
fails still returns its least-bad frame, flagged, not nothing).

  - eyes closed: portrait -> eyes_open < SCORING["GATE_EYES_OPEN_MIN_PORTRAIT"];
    group -> eyes_open_pct < SCORING["GATE_EYES_OPEN_FACE_PCT_MIN_GROUP"]
    ("one blink ruins the shot" -- worst-face logic, not an average)
  - severe blur: RELATIVE to the clip's own sharpness distribution (bottom
    SCORING["GATE_BLUR_RELATIVE_PERCENTILE"]), not a fixed global constant --
    a real handheld phone clip can be uniformly softer than a studio shot
    (see the A8 test-log and the 2026-07-05 real-video finding: sharpness
    12-55 for an entire clip, all below the old fixed constant of 100).
  - severe exposure is already hard-rejected in stage 3 (quality.py) before a
    frame ever reaches this module, so it is not re-gated here.

PASS 2 -- weighted rank of non-gated candidates, using config.SCORING's
per-scene weights. Key research finding implemented directly: "a slightly
soft great moment beats a tack-sharp boring one" -- sharpness uses a sqrt
curve (diminishing returns near the top, high sensitivity near the bottom),
so a soft-but-clearly-above-gate frame isn't punished much for not being the
absolute sharpest, while expression/gaze/composition still separate the winners.

Composition (headroom + rule-of-thirds + face size) and dedupe (perceptual
hash, SKILL.md pitfall #7) are unchanged from v1.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from pathlib import Path

import imagehash
from PIL import Image

from perfectmoment import config
from perfectmoment.faces import FaceBox, FaceScore
from perfectmoment.quality import QualityScore

# Rule-of-thirds intersection points, normalized 0-1.
RULE_OF_THIRDS_POINTS = [(1 / 3, 1 / 3), (2 / 3, 1 / 3), (1 / 3, 2 / 3), (2 / 3, 2 / 3)]

IDEAL_HEADROOM = 0.12  # normalized space above the head that reads as "well-framed"
IDEAL_FRAME_BRIGHTNESS = 140.0  # mid-tone target, matches faces.IDEAL_FACE_BRIGHTNESS
FRAME_BRIGHTNESS_TOLERANCE = 100.0


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
    scene: str = "landscape"  # portrait / group / landscape (see classify_scene)
    gated: bool = False
    gate_reason: str | None = None
    reason: str = ""  # human-readable, FilterPixel-style "why this frame scored as it did"
    eyes_open_pct: float = 0.0  # group: fraction of faces with eyes open
    duchenne_bonus: float = 0.0
    cohesion: float = 1.0  # group only
    gaze_deviation: float = 0.0
    face_lighting: float = 0.5


def _normalize(value: float, lo: float, hi: float) -> float:
    """Clamp-normalize value into [0, 1] given an expected [lo, hi] range."""
    if hi <= lo:
        return 0.5
    return max(0.0, min(1.0, (value - lo) / (hi - lo)))


def _percentile(values: list[float], p: float) -> float:
    """Simple percentile (no numpy/scipy dependency -- keeps the $0/free-stack promise)."""
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(p * (len(ordered) - 1))))
    return ordered[index]


def _headroom_score(box: FaceBox) -> float:
    """Distance of box.y_min from an ideal headroom margin -- too little crops
    the subject, too much wastes the frame. Symmetric penalty around the ideal."""
    deviation = abs(box.y_min - IDEAL_HEADROOM)
    return 1.0 - _normalize(deviation, lo=0.0, hi=0.3)


def composition_score(face_boxes: list[FaceBox]) -> float:
    """Face size (prominence) + rule-of-thirds centering + headroom, averaged across faces.

    Returns 0.5 (neutral) when there are no faces (landscape scene).
    """
    if not face_boxes:
        return 0.5

    scores = []
    for box in face_boxes:
        area = box.width * box.height
        size_score = _normalize(area, lo=0.0, hi=0.5)

        cx, cy = box.center
        min_dist = min(((cx - px) ** 2 + (cy - py) ** 2) ** 0.5 for px, py in RULE_OF_THIRDS_POINTS)
        centering_score = 1.0 - _normalize(min_dist, lo=0.0, hi=0.5)

        headroom_score = _headroom_score(box)
        scores.append((size_score + centering_score + headroom_score) / 3)

    return sum(scores) / len(scores)


def classify_scene(face_count: int) -> str:
    """portrait (1 face) / group (2+ faces) / landscape (0 faces)."""
    if face_count == 0:
        return "landscape"
    if face_count >= config.GROUP_FACE_COUNT_MIN:
        return "group"
    return "portrait"


def sharpness_score(sharpness: float) -> float:
    """Diminishing-returns sharpness score: sqrt curve over the raw normalized
    value. Research finding: 'a slightly soft great moment beats a tack-sharp
    boring one' -- once a frame clears the pass-1 blur gate, further sharpness
    gains matter less and less, while it stays sensitive near the gate floor."""
    raw = _normalize(sharpness, lo=0.0, hi=1000.0)
    return raw ** 0.5


def expression_component(face: FaceScore) -> float:
    """Smile/laugh with a genuine-smile (Duchenne) bonus and a frown penalty.
    Distinct from eyes/gaze, which are separate weighted terms in v2."""
    base = max(face.smile, face.genuine_laugh)
    boosted = base + 0.3 * face.duchenne_bonus
    penalized = boosted - 0.3 * face.frown
    return max(0.0, min(1.0, penalized))


def _frame_lighting_score(brightness: float) -> float:
    deviation = abs(brightness - IDEAL_FRAME_BRIGHTNESS)
    return max(0.0, 1.0 - deviation / FRAME_BRIGHTNESS_TOLERANCE)


def _frame_exposure_score(brightness: float) -> float:
    """How far from clipping (0 or 255) -- broader tolerance than the lighting
    'flattering mid-tone' target, since exposure is about avoiding clipping,
    not aesthetics."""
    return 1.0 - _normalize(abs(brightness - 127.5), lo=0.0, hi=127.5)


def _gate_reason(scene: str, face: FaceScore | None, is_blur_gated: bool) -> str | None:
    if scene == "portrait" and face is not None:
        if face.eyes_open < config.SCORING["GATE_EYES_OPEN_MIN_PORTRAIT"]:
            return f"eyes closed (eyes_open={face.eyes_open:.2f})"
    elif scene == "group" and face is not None:
        if face.eyes_open_pct < config.SCORING["GATE_EYES_OPEN_FACE_PCT_MIN_GROUP"]:
            return f"one or more faces have closed eyes ({face.eyes_open_pct:.0%} open)"
    if is_blur_gated:
        return "severe blur relative to this clip's own sharpness range"
    return None


def _build_reason_string(scene: str, gated: bool, gate_reason: str | None, expr: float, gaze_dev: float, blur_s: float) -> str:
    if gated:
        return f"gated: {gate_reason}"
    if scene == "landscape":
        return "sharp" if blur_s > 0.6 else "soft but above the blur gate"
    parts = []
    parts.append("genuine smile" if expr > 0.6 else ("neutral expression" if expr > 0.3 else "weak expression"))
    parts.append("gaze at camera" if gaze_dev < 0.25 else "gaze away from camera")
    parts.append("sharp" if blur_s > 0.6 else "soft but above the blur gate")
    return ", ".join(parts)


def phash_of(image_path: Path) -> imagehash.ImageHash:
    with Image.open(image_path) as img:
        return imagehash.phash(img)


def dedupe_by_similarity(
    candidates: list[RankedFrame],
    hashes: dict[Path, imagehash.ImageHash],
    hamming_max: int = config.DEDUPE_PHASH_HAMMING_MAX,
) -> list[RankedFrame]:
    """Greedily keep the highest-`final`-scoring frame from each near-duplicate cluster."""
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
    """Two-pass compose: hard-gate obvious failures, then weighted-rank survivors.

    Scene is classified PER FRAME (portrait/group/landscape) unless
    `no_faces_profile` is True (explicit --no-faces CLI override), which
    forces the landscape profile for every frame regardless of detected faces.

    Returns (ranked_frames, quality_bar_met). Gated frames are always ranked
    below non-gated ones but are included in the returned list -- if EVERY
    frame is gated, the least-bad gated frame is still returned (AC-14).
    """
    candidates = [qs for qs in quality_scores if qs.passed]
    clip_sharpness_values = [qs.sharpness for qs in candidates]
    # No blur gate when the clip has no real sharpness SPREAD (all frames
    # equally sharp/soft, e.g. a short handheld clip with uniform motion blur)
    # -- "relatively worse" is meaningless without variance, and a naive
    # percentile would otherwise gate the entire clip (found via a unit test
    # with two identical-sharpness frames; same failure mode as the earlier
    # A8 all-frames-rejected bug, one layer up).
    has_sharpness_spread = len(set(clip_sharpness_values)) > 1
    blur_gate_threshold = (
        _percentile(clip_sharpness_values, config.SCORING["GATE_BLUR_RELATIVE_PERCENTILE"])
        if has_sharpness_spread
        else float("-inf")
    )

    ranked: list[RankedFrame] = []
    for qs in candidates:
        face = face_scores.get(qs.path)
        aesthetic_raw = aesthetic_scores.get(qs.path, 0.0)

        blur_norm = _normalize(qs.sharpness, lo=0.0, hi=1000.0)
        blur_s = sharpness_score(qs.sharpness)
        aesthetic_norm = _normalize(aesthetic_raw, lo=1.0, hi=10.0)
        composition = composition_score(face.face_boxes if face else [])

        face_count = face.face_count if face else 0
        scene = "landscape" if no_faces_profile else classify_scene(face_count)
        is_group = scene == "group"

        # --- Pass 1: hard gates ---
        is_blur_gated = qs.sharpness <= blur_gate_threshold
        gate_reason = _gate_reason(scene, face, is_blur_gated)
        gated = gate_reason is not None

        # --- Pass 2: weighted scoring (still computed even if gated, so a
        # forced "least-bad" selection among all-gated frames is meaningful) ---
        w = config.SCORING[scene.upper()]
        if scene == "portrait":
            expr = expression_component(face)
            gaze_component = 1.0 - face.gaze_deviation
            final = (
                w["expression"] * expr
                + w["gaze"] * gaze_component
                + w["sharpness"] * blur_s
                + w["composition"] * composition
                + w["lighting"] * face.face_lighting
            )
        elif scene == "group":
            expr = expression_component(face)
            eyes_component = face.min_eyes_open
            final = (
                w["eyes_open"] * eyes_component
                + w["expression"] * expr
                + w["cohesion"] * face.cohesion
                + w["sharpness"] * blur_s
                + w["composition"] * composition
            )
        else:  # landscape
            expr = 0.0
            gaze_component = 0.0
            final = (
                w["sharpness"] * blur_s
                + w["composition"] * composition
                + w["lighting"] * _frame_lighting_score(qs.brightness)
                + w["exposure"] * _frame_exposure_score(qs.brightness)
            )

        # Gated frames rank below ALL non-gated frames regardless of their
        # computed `final` -- push them into a separate, lower score band.
        rank_key_final = (final - 10.0) if gated else final

        reason = _build_reason_string(scene, gated, gate_reason, expr, face.gaze_deviation if face else 1.0, blur_s)

        ranked.append(
            RankedFrame(
                path=qs.path,
                timestamp_seconds=0.0,  # filled in by caller (pipeline.py)
                sharpness=qs.sharpness,
                brightness=qs.brightness,
                face_count=face_count,
                eyes_open=face.eyes_open if face else 0.0,
                smile=face.smile if face else 0.0,
                composition=composition,
                aesthetic_norm=aesthetic_norm,
                blur_norm=blur_norm,
                final=rank_key_final,
                scene=scene,
                gated=gated,
                gate_reason=gate_reason,
                reason=reason,
                eyes_open_pct=face.eyes_open_pct if face else 0.0,
                duchenne_bonus=face.duchenne_bonus if face else 0.0,
                cohesion=face.cohesion if face else 1.0,
                gaze_deviation=face.gaze_deviation if face else 0.0,
                face_lighting=face.face_lighting if face else 0.5,
            )
        )

    # Deterministic tiebreak: sort by (rank_key) final desc, then path name.
    ranked.sort(key=lambda r: (-r.final, str(r.path)))

    hashes = {r.path: phash_of(r.path) for r in ranked}
    deduped = dedupe_by_similarity(ranked, hashes)

    # quality_bar_met uses the TRUE final score (undo the gate rank-key
    # penalty) so a gated-but-decent frame doesn't spuriously fail the bar,
    # and so min_score comparisons remain meaningful across gated/non-gated.
    def true_final(r: RankedFrame) -> float:
        return r.final + 10.0 if r.gated else r.final

    quality_bar_met = any(true_final(r) >= min_score for r in deduped)
    deduped = [
        r.__class__(**{**r.__dict__, "final": true_final(r), "low_quality": (not quality_bar_met) or true_final(r) < min_score})
        for r in deduped
    ]

    return deduped, quality_bar_met
