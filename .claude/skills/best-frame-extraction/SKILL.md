---
name: best-frame-extraction
description: Technical patterns for building a $0-cost, CPU-only pipeline that extracts the single best (or top-N) frame(s) from a video — sharpness, face/eye/smile quality, and aesthetic scoring. Use when building or extending "The Perfect Moment" or any similar video-to-photo / best-frame / photo-culling feature.
---

# Best-Frame Extraction Pipeline

Reusable technical playbook for turning a video into the best still photo(s), at $0/month
running cost, on a CPU-only machine (Windows laptop-feasible). Covers extraction, scoring,
ranking, and known pitfalls.

## Pipeline overview (5 stages)

```
video file
   │
   ▼
1. FRAME EXTRACTION (ffmpeg)          → candidate frames (100s–1000s)
   │
   ▼
2. CHEAP FILTER: blur / exposure       → drop obviously bad frames (fast, OpenCV)
   │
   ▼
3. FACE/EYE/SMILE SCORING (MediaPipe)  → drop closed-eyes, bad expressions; boost open-eye+smile
   │
   ▼
4. AESTHETIC/COMPOSITION SCORE (NIMA)  → rank remaining candidates
   │
   ▼
5. RANK + DEDUPE (perceptual hash)     → return top-1 or top-N, not near-duplicates
```

Run stages in this order because each stage is progressively more expensive. Stage 1
can emit hundreds of frames per minute of video; stage 2 is near-free per frame (<5ms);
stage 3 is cheap (~10-30ms/frame on CPU with BlazeFace); stage 4 (NIMA/InceptionResNetV2)
is the most expensive (~50-150ms/frame on CPU) — only run it on survivors of 2+3, never
on the raw frame dump. Never run NIMA on every frame of a video; it will be your
bottleneck.

## Stage 1: Frame extraction (FFmpeg)

Two extraction strategies, use both depending on source:

**A. Scene-change based** (good for footage with camera cuts / distinct moments):
```
ffmpeg -i input.mp4 -vf "select='gt(scene,0.35)'" -vsync vfr -qscale:v 2 out_%04d.jpg
```
- `scene` threshold range is [0, 1]; typical useful range 0.2–0.4. Lower = more frames.
- Alternative `scdet` filter gives richer scene-change metadata to stdout.

**B. Fixed-interval / dense sampling** (good for continuous handheld/phone video where
the "moment" isn't a scene cut, e.g. someone blowing candles, a jump, a laugh):
```
ffmpeg -i input.mp4 -vf "fps=5" -qscale:v 2 out_%04d.jpg
```
Sample 3–10 fps depending on how fast the target action is (fast motion e.g. a jump
needs 8-10fps; posed group photos need 2-3fps).

**C. I-frame / keyframe extraction** (cheapest, lowest frame count, good first pass on
long videos to find candidate regions before dense-sampling just those windows):
```
ffmpeg -i input.mp4 -vf "select=eq(pict_type\,PICT_TYPE_I)" -vsync vfr out_%04d.jpg
```

Recommended default for "best moment in a short clip" (event photography use case):
run B at 5fps for clips under ~15s (weddings/kids moments are usually short bursts),
fall back to A+windowed-B for longer continuous footage to avoid extracting thousands
of frames.

Always extract at `-qscale:v 2` (near-lossless jpeg) or PNG if disk allows — don't let
ffmpeg's jpeg compression introduce artifacts that corrupt the blur/aesthetic scores
downstream.

## Stage 2: Cheap technical-quality filter (OpenCV)

**Blur detection — variance of Laplacian** (the industry-standard cheap blur metric):
```python
import cv2
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
score = cv2.Laplacian(gray, cv2.CV_64F).var()
```
- Higher variance = sharper. Lower = blurrier.
- Threshold is dataset-dependent — do NOT hardcode a single global number. Typical
  literature range is 100–1000; calibrate per-source (phone footage, especially in
  low light, sits lower than DSLR footage) by sampling a few dozen known-sharp and
  known-blurry frames from your actual target footage and picking the split point.
- Cheap: run this on 100% of extracted frames before anything else — it's the fastest
  possible reject filter (single-digit ms per frame on CPU).
- Also check basic exposure (mean pixel brightness) to reject blown-out/black frames —
  trivial `np.mean(gray)` check with reasonable bounds (~25–230 on 0–255 scale).

**Pitfall**: Laplacian variance is scale-dependent — resize all frames to a consistent
resolution before scoring (e.g. downscale longest edge to 800px) or the variance
comparison across frames of different sizes is meaningless.

## Stage 3: Face / eye / smile scoring (MediaPipe)

Use MediaPipe Face Landmarker (the current 2023+ Tasks API — NOT the deprecated
`mp.solutions.face_mesh` legacy solution, which is still installable but frozen):

```python
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

base_options = python.BaseOptions(model_asset_path='face_landmarker.task')
options = vision.FaceLandmarkerOptions(
    base_options=base_options,
    output_face_blendshapes=True,
    num_faces=5)
detector = vision.FaceLandmarker.create_from_options(options)
result = detector.detect(mp_image)
```

- `output_face_blendshapes=True` gives you 52 named blendshape scores per face directly
  — including `eyeBlinkLeft`/`eyeBlinkRight` (use to detect closed eyes — high score =
  closed) and `mouthSmileLeft`/`mouthSmileRight` (use to detect/rank smiles). This is
  simpler and more robust than hand-rolling Eye Aspect Ratio (EAR) math, and it's free
  and runs on CPU.
- If you need EAR instead (e.g. for finer-grained blink timing), landmarks 33/160/158/
  133/153/144 (left eye) and mirror indices for the right eye give the 6 points for the
  standard EAR formula; threshold ~0.2–0.25 = closed.
- Mouth-corner landmarks 61 and 291 (left/right mouth corner) rising above the lip
  center is a fallback smile heuristic if you don't want blendshapes.
- Face detector itself (BlazeFace, used under the hood) is fast — ~10–30ms/frame CPU —
  so run it on every frame that survives Stage 2.
- Score composition per frame: for each detected face, compute
  `open_eyes_score = 1 - max(eyeBlinkLeft, eyeBlinkRight)`, `smile_score =
  (mouthSmileLeft+mouthSmileRight)/2`. Aggregate across all faces in frame (e.g. mean,
  or min if you want "nobody blinking" strictness) into a single per-frame face-quality
  score.
- Frames with zero faces detected aren't automatically bad — for non-portrait shots
  (product/pet/landscape wedge) skip face scoring and weight Stage 4 higher.

## Stage 4: Aesthetic / composition scoring (NIMA)

NIMA (Neural Image Assessment, Google 2017) predicts a 1–10 aesthetic distribution from
a single image, trained on the AVA dataset. It is the standard free/open aesthetic
scorer and multiple pretrained-weight ports exist (Keras/TF and PyTorch), typically
using InceptionResNetV2 or MobileNet backbones. Runs fine on CPU for single-image
inference at low volume (50–150ms/frame with InceptionResNetV2; MobileNet variant is
faster, ~15-40ms/frame, and often used in production for that reason — worth using
MobileNet weights over InceptionResNetV2 if throughput matters more than the last bit
of accuracy).

```python
# conceptual — actual code depends on which pretrained-weights repo you vendor
predictions = nima_model.predict(preprocessed_image)  # -> 10-class probability vector
mean_score = sum((i+1) * p for i, p in enumerate(predictions))
```

Alternative/complementary no-reference IQA metrics (useful as secondary signals or if
you want to avoid vendoring a NIMA checkpoint):
- `pyiqa` (`pip install pyiqa`) — PyTorch toolbox exposing many NR-IQA metrics including
  NIMA, NIQE, BRISQUE, MUSIQ, TOPIQ in one API; runs CPU or GPU, `device='cpu'` at init.
  This is the easiest single-dependency way to get NIMA-quality scoring without hunting
  down weights yourself.
- `brisque` (PyPI `brisque`, or OpenCV-contrib's `cv2.quality.QualityBRISQUE`) — classical
  (non-deep-learning) no-reference quality score, very cheap, decent as a pre-filter
  before NIMA but weaker at judging "is this a good photo" (it mostly judges technical
  distortion, not composition/aesthetics).

Practical recommendation for MVP: install `pyiqa`, run its `nima` metric CPU-mode only
on frames that already passed Stages 2+3 (i.e. sharp enough + good face state). This
avoids vendoring/managing model weights by hand.

## Stage 5: Rank + dedupe

- Combine scores into a single weighted rank: e.g.
  `final = 0.3*blur_norm + 0.4*face_quality + 0.3*aesthetic_norm` (weights are a product
  decision, not a technical one — tune per wedge: portraits weight face_quality higher,
  product/pet shots weight aesthetic+blur higher).
- Before returning top-N, dedupe visually near-identical frames (burst sequences
  produce many frames within a few % of each other) using perceptual hashing —
  `imagehash` (PyPI, wraps PIL) with `phash`, hamming distance threshold ~5-8 to treat
  as duplicate — otherwise "top 5 frames" ends up being 5 nearly-identical frames from
  the same instant.

## Known pitfalls

1. **Don't run the expensive model on every frame.** Cascade cheap→expensive (Stage
   2 → 3 → 4) or CPU cost balloons on longer clips.
2. **Blur threshold is not a universal constant.** Calibrate per capture source
   (phone vs DSLR vs low-light) — a fixed global Laplacian-variance cutoff will
   misclassify across sources.
3. **Legacy MediaPipe API deprecation.** `mp.solutions.face_mesh` / `face_detection`
   (the old "Solutions" API) still installs and runs but is frozen; new work should
   target the Tasks API (`mediapipe.tasks.python.vision.FaceLandmarker`) for
   blendshapes and future support.
2026 note: re-check MediaPipe's current package/task names before starting — Google
   has been actively restructuring this API since 2023.
4. **JPEG re-compression artifacts** from ffmpeg extraction can distort blur/aesthetic
   scores if quality is set too low. Use `-qscale:v 2` or PNG for the scoring pass;
   you can always re-compress the final chosen frame for delivery.
5. **No single face ≠ bad frame.** Don't hard-reject frames with 0 or >1 detected faces
   for non-portrait use cases (product shots, pets, landscapes) — gate face scoring
   behind a use-case flag.
6. **GPU dependencies creep in silently.** Many aesthetic-scoring repos default to
   assuming CUDA. Explicitly pin `device='cpu'` / verify wheel is CPU-only when
   installing pyiqa/torch (`pip install torch --index-url
   https://download.pytorch.org/whl/cpu` on Windows to avoid pulling a multi-GB CUDA
   build).
7. **Near-duplicate top-N results.** Always dedupe with perceptual hashing before
   presenting "top 5 best frames" — raw ranking alone will cluster around the single
   best moment's neighboring frames.

## Minimal dependency list (all free, CPU-capable)

- `ffmpeg` (system binary, not a pip package)
- `opencv-python` (blur/exposure filtering, optional BRISQUE via opencv-contrib)
- `mediapipe` (face/eye/smile — Tasks API, `face_landmarker.task` model file is
  downloaded free from Google's model zoo)
- `pyiqa` + `torch` (CPU wheel) for NIMA/aesthetic scoring
- `imagehash` + `Pillow` for dedupe
- Everything above runs with no paid API calls and no GPU requirement, satisfying a
  $0/month constraint at low-to-moderate volume. Watch wall-clock time on CPU as the
  scaling constraint, not cost.

## When to reach for paid vision APIs (post-MVP, revenue-gated)

Only once there's revenue to justify it: Google Cloud Vision / AWS Rekognition for
higher-accuracy face/expression detection at scale, or a hosted aesthetic model
(e.g. a fine-tuned CLIP-based scorer) if the classical NIMA approach's ranking quality
plateaus. Don't reach for these before the free pipeline's accuracy is empirically
shown to be the bottleneck — the free stack above is materially good enough for MVP
validation.
