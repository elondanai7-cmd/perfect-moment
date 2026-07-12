"""Stage 4: face/eye/smile scoring via MediaPipe Tasks FaceLandmarker.

Uses the current Tasks API (mediapipe.tasks.python.vision.FaceLandmarker), NOT
the deprecated legacy Solutions API (mp.solutions.face_mesh) — SKILL.md pitfall
#3. Verified against the real blendshape output on 2026-07-04: category names
are `eyeBlinkLeft`/`eyeBlinkRight`/`mouthSmileLeft`/`mouthSmileRight`, matching
the plan's formulas exactly.

open_eyes = 1 - max(eyeBlinkLeft, eyeBlinkRight)   (blink score is "how closed")
smile     = mean(mouthSmileLeft, mouthSmileRight)

Per-face scores are aggregated per-frame (mean across faces, EXCEPT eyes_open
which also keeps a per-face list -- see below). A frame with zero detected
faces anywhere in the whole clip triggers the --no-faces fallback path
(AC-15), decided by the caller (pipeline.py) based on `no_faces_in_clip`.

Extended expression signals (added 2026-07-05, all verified against real
blendshape output -- MediaPipe exposes 52 categories per face, not just the
4 originally used):

- gaze_deviation: how far the eyes are looking away from the camera, derived
  from eyeLookIn/Out/Up/DownLeft/Right. 0 = looking straight at the lens,
  higher = looking away. For each eye, take the max of its four directional
  blendshapes (only one is meaningfully active at a time), then mean the two
  eyes.
- mouth_open: raw jawOpen score. Combined with smile, distinguishes a closed
  polite smile from a genuine open-mouth laugh (mouth_open high + smile high).
- frown: mean(mouthFrownLeft, mouthFrownRight) -- a negative-expression signal
  a plain "smile" score alone does not capture (someone can score low smile
  without actively frowning; frowning is a distinct, worse case).
- squint: mean(eyeSquintLeft, eyeSquintRight) -- different from eyeBlink;
  squinting (e.g. into direct sun) reads as "eyes technically open" under the
  blink metric but looks worse in a photo than genuinely relaxed open eyes.

`eyes_open_per_face` is kept as a list (not just the frame-mean) because a
group-photo scoring profile should require the WORST face's eyes to be open,
not just the average -- one person blinking in a 5-person group photo is a
real defect an average would paper over.

v2 additions (2026-07-05, research-based -- see .specs/scratchpad/scoring-research.md):

- `duchenne_bonus` (smile * squint): research shows a GENUINE smile involves
  eye-muscle engagement (orbicularis oculi -- the "eye crinkle"), which shows
  up as cheek-squint alongside the mouth smile. A posed/forced smile has high
  `smile` but low `squint`; a genuine one has both. This is a bonus layered on
  top of the plain smile score, not a replacement for it.
- `eyes_open_pct` (property): fraction of faces with eyes_open above 0.5 --
  the input to the group hard-gate (SCORING["GATE_EYES_OPEN_FACE_PCT_MIN_GROUP"]).
- `gaze_deviation_per_face` + `cohesion` (property): a group "peak moment"
  proxy. Cohesion is high when all faces have SIMILAR gaze deviation (all
  looking at the camera together, or all looking toward the same off-camera
  point) -- low variance across faces, not necessarily zero deviation.
- `face_lighting`: mean brightness measured INSIDE the face box, not the
  whole frame (stage 3's brightness check is whole-frame and misses a
  backlit face against a bright background). Distance from a flattering
  mid-tone target is penalized.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python import vision

from perfectmoment import config

IDEAL_FACE_BRIGHTNESS = 140.0  # 0-255, a flattering mid-tone for a face region
FACE_BRIGHTNESS_TOLERANCE = 90.0  # normalization range for the distance-from-ideal penalty


@dataclass(frozen=True)
class FaceBox:
    """Normalized (0-1) bounding box derived from landmark extents, for composition scoring."""

    x_min: float
    y_min: float
    x_max: float
    y_max: float

    @property
    def width(self) -> float:
        return self.x_max - self.x_min

    @property
    def height(self) -> float:
        return self.y_max - self.y_min

    @property
    def center(self) -> tuple[float, float]:
        return ((self.x_min + self.x_max) / 2, (self.y_min + self.y_max) / 2)


@dataclass(frozen=True)
class FaceScore:
    path: Path
    face_count: int
    eyes_open: float  # 0-1, mean across faces, 1 = all eyes open
    smile: float  # 0-1, mean across faces
    face_boxes: list[FaceBox] = field(default_factory=list)
    eyes_open_per_face: list[float] = field(default_factory=list)
    gaze_deviation: float = 0.0  # 0-1, mean across faces, 0 = looking at camera
    gaze_deviation_per_face: list[float] = field(default_factory=list)
    mouth_open: float = 0.0  # 0-1, mean across faces (jawOpen)
    frown: float = 0.0  # 0-1, mean across faces
    squint: float = 0.0  # 0-1, mean across faces
    face_lighting: float = 0.5  # 0-1, mean across faces, 1 = ideal flattering brightness on face

    @property
    def min_eyes_open(self) -> float:
        """Worst-case eyes-open across all faces -- for group-photo scoring,
        where one closed-eyed person should hurt the score, not be averaged away."""
        return min(self.eyes_open_per_face) if self.eyes_open_per_face else 0.0

    @property
    def eyes_open_pct(self) -> float:
        """Fraction of faces with eyes_open > 0.5 -- input to the group hard-gate."""
        if not self.eyes_open_per_face:
            return 0.0
        open_count = sum(1 for e in self.eyes_open_per_face if e > 0.5)
        return open_count / len(self.eyes_open_per_face)

    @property
    def genuine_laugh(self) -> float:
        """High only when smiling, mouth open, AND cheek-squinting together.

        Originally smile * mouth_open with no squint gate -- but talking or
        yawning also scores high on smile + mouth_open (mediapipe's smile
        blendshape fires on any raised mouth corners, not just genuine ones),
        so a mid-sentence open-mouth frame from a dim, blurry clip scored as
        a "genuine laugh" winner (found via a real pilot video, 2026-07-12).
        Requiring squint too -- the actual eye-crinkle marker of authentic
        laughter -- means an open mouth without eye engagement (talking)
        no longer scores as a laugh."""
        return self.smile * self.mouth_open * self.squint

    @property
    def duchenne_bonus(self) -> float:
        """High only when BOTH smiling and cheek-squinting -- the eye-crinkle
        marker of a genuine (Duchenne) smile vs. a posed one."""
        return self.smile * self.squint

    @property
    def cohesion(self) -> float:
        """Group 'peak moment' proxy: high when all faces have SIMILAR gaze
        deviation (low variance -- everyone looking the same way/at camera
        together), regardless of what that shared direction is."""
        if len(self.gaze_deviation_per_face) < 2:
            return 1.0  # single face or no faces: cohesion is not meaningful, don't penalize
        spread = statistics.pstdev(self.gaze_deviation_per_face)
        return max(0.0, 1.0 - spread / 0.5)  # spread of 0.5+ (very mixed directions) -> 0


class FaceLandmarkerModelNotFoundError(RuntimeError):
    pass


def _load_landmarker(model_path: Path, num_faces: int = 5) -> vision.FaceLandmarker:
    if not model_path.exists():
        raise FaceLandmarkerModelNotFoundError(
            f"MediaPipe face model not found at {model_path}. "
            "Run `python scripts/fetch_model.py` first."
        )
    options = vision.FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(model_path)),
        output_face_blendshapes=True,
        output_facial_transformation_matrixes=False,
        num_faces=num_faces,
        running_mode=vision.RunningMode.IMAGE,
    )
    return vision.FaceLandmarker.create_from_options(options)


def _blendshape_value(blendshapes: list, category_name: str) -> float:
    for category in blendshapes:
        if category.category_name == category_name:
            return float(category.score)
    return 0.0


def _face_box_from_landmarks(landmarks) -> FaceBox:
    xs = [lm.x for lm in landmarks]
    ys = [lm.y for lm in landmarks]
    return FaceBox(x_min=min(xs), y_min=min(ys), x_max=max(xs), y_max=max(ys))


def _gaze_deviation_for_eye(blendshapes: list, side: str) -> float:
    """Max of the four directional look-away blendshapes for one eye (Left/Right).
    Only one direction is meaningfully active at a time, so max is the right
    aggregator (mean would dilute a strong single-direction look-away)."""
    directions = ["LookDown", "LookIn", "LookOut", "LookUp"]
    values = [_blendshape_value(blendshapes, f"eye{d}{side}") for d in directions]
    return max(values)


def _face_region_brightness(image_bgr, box: FaceBox) -> float:
    """Mean pixel brightness INSIDE the face bounding box (not the whole frame)."""
    h, w = image_bgr.shape[:2]
    x1, y1 = max(0, int(box.x_min * w)), max(0, int(box.y_min * h))
    x2, y2 = min(w, int(box.x_max * w)), min(h, int(box.y_max * h))
    if x2 <= x1 or y2 <= y1:
        return IDEAL_FACE_BRIGHTNESS  # degenerate box, don't penalize
    region = image_bgr[y1:y2, x1:x2]
    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    return float(gray.mean())


def _face_lighting_score(brightness: float) -> float:
    deviation = abs(brightness - IDEAL_FACE_BRIGHTNESS)
    return max(0.0, 1.0 - deviation / FACE_BRIGHTNESS_TOLERANCE)


def score_frame(image_path: Path, landmarker: vision.FaceLandmarker) -> FaceScore:
    """Detect faces in one frame and compute aggregated expression scores."""
    image = mp.Image.create_from_file(str(image_path))
    result = landmarker.detect(image)

    face_count = len(result.face_landmarks)
    if face_count == 0:
        return FaceScore(path=image_path, face_count=0, eyes_open=0.0, smile=0.0, face_boxes=[])

    image_bgr = cv2.imread(str(image_path))

    eyes_open_scores = []
    smile_scores = []
    gaze_scores = []
    gaze_per_face = []
    mouth_open_scores = []
    frown_scores = []
    squint_scores = []
    lighting_scores = []
    boxes = []
    for face_blendshapes, face_landmarks in zip(result.face_blendshapes, result.face_landmarks):
        blink_left = _blendshape_value(face_blendshapes, "eyeBlinkLeft")
        blink_right = _blendshape_value(face_blendshapes, "eyeBlinkRight")
        smile_left = _blendshape_value(face_blendshapes, "mouthSmileLeft")
        smile_right = _blendshape_value(face_blendshapes, "mouthSmileRight")
        frown_left = _blendshape_value(face_blendshapes, "mouthFrownLeft")
        frown_right = _blendshape_value(face_blendshapes, "mouthFrownRight")
        squint_left = _blendshape_value(face_blendshapes, "eyeSquintLeft")
        squint_right = _blendshape_value(face_blendshapes, "eyeSquintRight")
        jaw_open = _blendshape_value(face_blendshapes, "jawOpen")

        gaze_left = _gaze_deviation_for_eye(face_blendshapes, "Left")
        gaze_right = _gaze_deviation_for_eye(face_blendshapes, "Right")
        gaze_value = (gaze_left + gaze_right) / 2

        box = _face_box_from_landmarks(face_landmarks)

        eyes_open_scores.append(1.0 - max(blink_left, blink_right))
        smile_scores.append((smile_left + smile_right) / 2)
        gaze_scores.append(gaze_value)
        gaze_per_face.append(gaze_value)
        mouth_open_scores.append(jaw_open)
        frown_scores.append((frown_left + frown_right) / 2)
        squint_scores.append((squint_left + squint_right) / 2)
        boxes.append(box)

        if image_bgr is not None:
            brightness = _face_region_brightness(image_bgr, box)
            lighting_scores.append(_face_lighting_score(brightness))
        else:
            lighting_scores.append(0.5)  # unreadable image, neutral fallback

    return FaceScore(
        path=image_path,
        face_count=face_count,
        eyes_open=sum(eyes_open_scores) / len(eyes_open_scores),
        smile=sum(smile_scores) / len(smile_scores),
        face_boxes=boxes,
        eyes_open_per_face=eyes_open_scores,
        gaze_deviation=sum(gaze_scores) / len(gaze_scores),
        gaze_deviation_per_face=gaze_per_face,
        mouth_open=sum(mouth_open_scores) / len(mouth_open_scores),
        frown=sum(frown_scores) / len(frown_scores),
        squint=sum(squint_scores) / len(squint_scores),
        face_lighting=sum(lighting_scores) / len(lighting_scores),
    )


def score_frames(
    image_paths: list[Path],
    model_path: Path = config.FACE_LANDMARKER_MODEL_PATH,
) -> tuple[list[FaceScore], bool]:
    """Score all frames; returns (scores, no_faces_in_clip).

    no_faces_in_clip is True only if NOT ONE frame in the whole clip has a
    detected face — the trigger for the --no-faces / product-lane fallback (AC-15).
    """
    landmarker = _load_landmarker(model_path)
    scores = [score_frame(p, landmarker) for p in image_paths]
    no_faces_in_clip = all(s.face_count == 0 for s in scores)
    return scores, no_faces_in_clip
