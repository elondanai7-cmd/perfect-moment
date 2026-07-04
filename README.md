# The Perfect Moment

AI pipeline that takes a video and surfaces the best frames — sharp, eyes open,
good expression, well composed — as ranked, print-worthy stills. Runs entirely
on CPU, $0/month, no paid APIs.

Full plan: `.specs/tasks/todo/perfect-moment-startup-plan.feature.md`
Technical skill reference: `.claude/skills/best-frame-extraction/SKILL.md`

## Install

1. **ffmpeg** — must be on PATH.
   - Windows: `winget install ffmpeg`, then restart your terminal.
   - Verify: `ffmpeg -version` and `ffprobe -version` both print a version.

2. **CPU-only torch** — install this FIRST to avoid pulling a multi-GB CUDA build:
   ```
   pip install torch --index-url https://download.pytorch.org/whl/cpu
   ```

3. **Everything else:**
   ```
   pip install -r requirements.txt
   ```

4. **Download the face landmark model** (one-time, gitignored, ~a few MB):
   ```
   python scripts/fetch_model.py
   ```

Verified working on Python 3.14 (Windows) as of 2026-07-04 — no compatibility
issues found with any of the pinned versions in `requirements.txt`.

## Run

```
python -m perfectmoment extract <video_path> --top-n 5 --min-score 0.6 --out ./perfect-moment-out
```

Flags:
- `--top-n` (default 5) — how many ranked stills to export.
- `--min-score` (default 0.6) — quality bar on the weighted final score, 0-1.
- `--fps` (default 2) — sampling rate for candidate frames.
- `--no-faces` — force the product-lane weight profile (blur+aesthetic only, no
  face-quality term). Use for product/landscape footage; the pipeline also
  auto-detects a whole-clip no-faces case and falls back automatically.
- `--out` (default `./perfect-moment-out`) — output root; each run writes to
  `<out>/<video-stem>/`.

Output: `rank_01.jpg` .. `rank_0N.jpg` (full resolution, best first) and
`manifest.json` recording every sub-score per exported frame (sharpness,
brightness, face_count, eyes_open, smile, composition, aesthetic_norm,
blur_norm, final, low_quality) so every pick is explainable, not a black box.

### Example

```
python -m perfectmoment extract wedding_ceremony.mp4 --top-n 8
```

On a 30s 1080p clip this typically completes in well under a minute on a
modern CPU (measured: 37-47s on the founder's laptop during A8 testing).
Longer/4K clips take proportionally longer — the pipeline warns but does not
fail on oversized input (see "Graceful degrade" below).

## Graceful degrade behavior

The pipeline never crashes or returns nothing on bad input:

- **No frame meets the quality bar** (e.g. very dark footage): prints a
  warning, still exports `min(top_n, available)` best-available frames, flags
  them `low_quality: true` in the manifest, exits 0.
- **Every frame fails the hard technical filter** (e.g. a fully black clip):
  falls back to ranking the least-bad originally-rejected frames rather than
  exporting nothing — found and fixed during A8 real-video testing.
- **No faces detected anywhere in the clip**: falls back to a sharpness +
  composition-only scoring profile (same as `--no-faces`).
- **Oversized/long input** (long duration or >3840px resolution): warns and
  downscales/samples to stay within time and memory limits rather than
  crashing.

## Per-source calibration notes (step A9 — pending real footage)

The default thresholds in `perfectmoment/config.py`
(`BLUR_VARIANCE_MIN`, `BRIGHTNESS_MIN/MAX`, ranking weights) are **global
placeholders**, not yet calibrated against real phone/DSLR/low-light event
footage. Real-footage calibration is step A9 in the implementation plan and
requires actual clips from a beta photographer — it cannot be meaningfully
done against synthetic test patterns.

Known real findings from implementation so far (see git history for A5, A8):
- pyiqa's NIMA has **no MobileNet-backbone variant** — only InceptionV2
  (default), VGG16, and two dataset variants exist. The plan's original
  "swap to a lighter backbone" mitigation isn't available off-the-shelf.
- Measured NIMA cost is **~640ms/frame** on CPU (about 4x the plan's original
  ~150ms estimate). The 180s (AC-9) budget still holds with a real ~4.7x
  margin at worst case (all 60 sampled frames survive to this stage), and a
  much larger margin in the realistic case (~30 survivors).

When real footage becomes available, calibration should:
1. Collect known-sharp / known-blurry frame pairs per capture source (phone,
   DSLR, low-light).
2. Re-tune `BLUR_VARIANCE_MIN` per source rather than using one global value.
3. Validate the weighted `final` formula against a small human-rated sample
   before the full AC-13 blind panel.

## Delivery runbook (manual beta delivery, Track B)

Until a paying customer justifies a self-serve backend (see the plan's Scope
gates), delivery is manual:

1. Receive the source video via the WhatsApp funnel (`landing/index.html`).
2. Run: `python -m perfectmoment extract <received_video> --top-n 5 --out ./perfect-moment-out`
3. Check `perfect-moment-out/<video-stem>/manifest.json` — if
   `quality_bar_met: false`, review the flagged frames before sending; they
   are still the best available, but call this out to the client honestly.
4. Send back the `rank_*.jpg` files directly.

## Project layout

```
perfectmoment/  __main__.py    CLI entrypoint (argparse)
                pipeline.py    stage orchestration, cascade, AC-14/15/16 degrade logic
                extract.py     stages 1-2: ffprobe + ffmpeg sampling
                quality.py     stage 3: Laplacian blur + brightness filter
                faces.py       stage 4: MediaPipe FaceLandmarker eyes/smile scoring
                aesthetics.py  stage 5: pyiqa NIMA aesthetic scoring (CPU)
                rank.py        stage 6: composition scoring + weighted compose + phash dedupe
                output.py      stage 7: full-res re-extract + manifest writer
                config.py      thresholds, weights, defaults
scripts/fetch_model.py         one-time MediaPipe model download
models/face_landmarker.task    gitignored, fetched by the script above
landing/index.html             Hebrew RTL landing page + WhatsApp funnel
```
