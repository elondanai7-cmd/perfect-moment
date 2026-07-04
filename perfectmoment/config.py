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

# Ranking weights (stage 6) — two profiles per Architecture Overview §2
WEIGHTS_PORTRAIT = {"blur": 0.3, "face_quality": 0.4, "aesthetic": 0.3}
WEIGHTS_PRODUCT = {"blur": 0.5, "aesthetic": 0.5}  # --no-faces profile, no face_quality term

DEDUPE_PHASH_HAMMING_MAX = 6

# CLI defaults
DEFAULT_TOP_N = 5
DEFAULT_MIN_SCORE = 0.6
