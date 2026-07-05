"""Default thresholds, weights, and paths. Calibrated per-source in step A9."""

from pathlib import Path

# Sampling
DEFAULT_FPS = 2

# Output
DEFAULT_OUT_DIR = "./perfect-moment-out"
SCORING_LONG_EDGE = 1280  # downscale target for scoring-stage frames (stage 2)
FULL_RES_REEXTRACT = True

# Quality filter (stage 3) — placeholder global defaults; A9 calibrates per source
LAPLACIAN_RESIZE_LONG_EDGE = 800  # resize before Laplacian variance (must be consistent for comparable scores)
BLUR_VARIANCE_MIN = 100.0  # placeholder; calibrate per-source in A9
BRIGHTNESS_MIN = 25
BRIGHTNESS_MAX = 230

# Face/eye scoring (stage 4)
FACE_LANDMARKER_MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "face_landmarker.task"

# Aesthetic scoring (stage 5)
NIMA_BACKBONE = "nima"  # pyiqa metric name; MobileNet-backbone variant considered if timing requires it
NIMA_DEVICE = "cpu"

# ---------------------------------------------------------------------------
# Ranking model (stage 6) v2 -- evidence-based "professional photographer"
# scoring. Research: .specs/scratchpad/scoring-research.md (33 sources:
# Narrative Select / Aftershoot / FilterPixel docs, Google Top Shot patent
# US10671895, NIMA paper, Duchenne-smile & gaze studies, pro culling guides).
#
# Two-pass model, matching how professional culling tools actually work:
#   PASS 1 (hard gates): reject obvious technical failures outright --
#     closed eyes, severe blur (relative to the clip's OWN sharpness spread,
#     not a fixed global constant -- real phone footage can be uniformly
#     softer than a studio shot, see A8/A9 notes), severe exposure.
#     Gated frames are ranked BELOW all non-gated frames but never deleted
#     (preserves the AC-14 "never return empty" contract).
#   PASS 2 (weighted rank): survivors are ranked by scene-specific weights.
#     Research finding: "a slightly soft great moment beats a tack-sharp
#     boring one" -- sharpness gets diminishing returns above its floor
#     (sqrt curve), while expression/moment dominates the ranking.
# ---------------------------------------------------------------------------

# Group photos: 2+ faces. Portrait: exactly 1 face. Landscape/product: 0 faces.
GROUP_FACE_COUNT_MIN = 2

SCORING = {
    # --- Pass 1: hard gates ---
    "GATE_EYES_OPEN_MIN_PORTRAIT": 0.35,  # below this eyes_open -> gated (Narrative/Aftershoot treat closed eyes as nearly-automatic reject)
    "GATE_EYES_OPEN_FACE_PCT_MIN_GROUP": 0.8,  # group: gate unless >=80% of faces have eyes open ("one blink ruins the shot")
    "GATE_BLUR_RELATIVE_PERCENTILE": 0.15,  # gate the bottom 15% of the CLIP'S OWN sharpness distribution, not a fixed constant

    # --- Pass 2: weighted profiles (weights sum to 1.0 per scene) ---
    "PORTRAIT": {
        "expression": 0.30,      # research: expression dominates once technical floor is cleared
        "gaze": 0.25,            # direct gaze strongly preferred in formal/portrait shots
        "sharpness": 0.20,       # floor + diminishing returns (see sharpness_score)
        "composition": 0.15,
        "lighting": 0.10,        # face-region lighting balance
    },
    "GROUP": {
        "eyes_open": 0.35,       # dominates: worst-face rule, not the mean (see faces.FaceScore.min_eyes_open)
        "expression": 0.25,      # predominant group mood (mean smile/genuine-laugh)
        "cohesion": 0.20,        # peak-moment proxy: are people looking the same way / at camera together
        "sharpness": 0.12,
        "composition": 0.08,
    },
    "LANDSCAPE": {
        "sharpness": 0.35,       # no expression to compensate -- technical quality is primary
        "composition": 0.30,
        "lighting": 0.20,
        "exposure": 0.15,
    },
}

DEDUPE_PHASH_HAMMING_MAX = 6

# CLI defaults
DEFAULT_TOP_N = 5
DEFAULT_MIN_SCORE = 0.6
