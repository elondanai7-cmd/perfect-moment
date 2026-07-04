"""Stage 4: face/eye/smile scoring via MediaPipe Tasks FaceLandmarker.

Uses the current Tasks API (mediapipe.tasks.python.vision.FaceLandmarker), NOT
the deprecated legacy Solutions API (mp.solutions.face_mesh) — SKILL.md pitfall
#3. Verified against the real blendshape output on 2026-07-04: category names
are `eyeBlinkLeft`/`eyeBlinkRight`/`mouthSmileLeft`/`mouthSmileRight`, matching
the plan's formulas exactly.

open_eyes = 1 - max(eyeBlinkLeft, eyeBlinkRight)   (blink score is "how closed")
smile     = mean(mouthSmileLeft, mouthSmileRight)

Per-face scores are aggregated per-frame (mean across faces). A frame with zero
detected faces anywhere in the whole clip triggers the --no-faces fallback path
(AC-15), decided by the caller (pipeline.py) based on `no_faces_in_clip`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python import vision

from perfectmoment import config


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


def score_frame(image_path: Path, landmarker: vision.FaceLandmarker) -> FaceScore:
    """Detect faces in one frame and compute aggregated eyes-open/smile scores."""
    image = mp.Image.create_from_file(str(image_path))
    result = landmarker.detect(image)

    face_count = len(result.face_landmarks)
    if face_count == 0:
        return FaceScore(path=image_path, face_count=0, eyes_open=0.0, smile=0.0, face_boxes=[])

    eyes_open_scores = []
    smile_scores = []
    boxes = []
    for face_blendshapes, face_landmarks in zip(result.face_blendshapes, result.face_landmarks):
        blink_left = _blendshape_value(face_blendshapes, "eyeBlinkLeft")
        blink_right = _blendshape_value(face_blendshapes, "eyeBlinkRight")
        smile_left = _blendshape_value(face_blendshapes, "mouthSmileLeft")
        smile_right = _blendshape_value(face_blendshapes, "mouthSmileRight")

        eyes_open_scores.append(1.0 - max(blink_left, blink_right))
        smile_scores.append((smile_left + smile_right) / 2)
        boxes.append(_face_box_from_landmarks(face_landmarks))

    return FaceScore(
        path=image_path,
        face_count=face_count,
        eyes_open=sum(eyes_open_scores) / len(eyes_open_scores),
        smile=sum(smile_scores) / len(smile_scores),
        face_boxes=boxes,
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
