# A8 — Test on Real Videos

Date: 2026-07-04. Machine: founder's Windows laptop, CPU only (torch 2.12.1+cpu, 8 threads).
All clips generated with ffmpeg (synthetic test patterns / a real portrait photo looped),
run through the full `python -m perfectmoment extract` CLI end to end.

## Test 1 — 30s 1080p clip (AC-9, AC-10, AC-11, AC-12)

Clip: `testsrc` pattern, 1920x1080, 30s, 30fps.

- **AC-9** (<180s budget): two full runs measured **47.1s** and **36.7s**. PASS, well within budget (~4x margin).
- **AC-10** (deterministic): ran the identical clip twice; exported timestamps and `final` scores identical to 6 decimal places across both runs. PASS.
- **AC-11** (explainable manifest): every exported frame's manifest entry carries sharpness, brightness, face_count, eyes_open, smile, composition, aesthetic_norm, blur_norm, final, low_quality, rank, output_file. PASS.
- **AC-12** (`min(N, available)` exports): `--top-n 100` on a clip with only 17 unique (post-dedupe) survivors exported exactly 17, not 100 and not an error. PASS.

## Test 2 — Dark/black clip (AC-14)

Clip: pure black, 1920x1080, 10s, 30fps.

- First run **FAILED silently down to 0 exported frames** — a real bug: every one of the 20 sampled frames failed the stage-3 hard quality filter (all rejected as underexposed), so zero candidates ever reached the ranking stage, and the pipeline exported nothing. This violated the "never return empty" AC-14 contract, which was previously only implemented for the *soft* min-score bar in stage 6, not for the *hard* stage-3 rejection case.
- **Fixed** in `pipeline.py`: when stage-3 filtering rejects every single frame, the pipeline now falls back to treating all originally-rejected frames as forced candidates so scoring/ranking/dedupe still runs and picks a least-bad set, with a new explicit warning line.
- Re-run after fix: exports **1 frame** (all 20 black frames are visually identical, so phash dedupe correctly collapses them to 1 representative), `quality_bar_met: false`, `low_quality: true`, sharpness=0.0, brightness≈1.0 — all honestly reported, no crash, exit code 0. PASS (post-fix).

## Test 3 — 90s 4K clip (AC-16)

Clip: `testsrc` pattern, 3840x2160, 90s, 30fps.

- AC-16 warning triggered correctly: `"large/long input (resolution 3840x2160 exceeds 3840px long edge)"`.
- Completed without crashing or exhausting memory: **242.6s** elapsed, 5 frames exported. AC-16 only requires warn + complete (no time bound specified for oversized/long inputs, unlike AC-9's 180s budget which is scoped to a 30s 1080p clip specifically) — PASS.
- Real scaling data point for A9 calibration: 90s@4K (180 candidate frames at 2fps) took ~5.2x the 30s@1080p case (60 candidate frames) — roughly proportional to the ~3x frame-count increase plus extra ffmpeg 4K-decode overhead. Useful reference if a future real beta clip runs long.

## Test 4 — Clip with a real detectable face (AC-15 non-trigger path)

Clip: MediaPipe's official test portrait image, looped as a 10s 1080x1350 video.

- AC-15 fallback correctly did **NOT** trigger (face was detected) — confirms the no-faces path is conditional or real detections, not a default.
- Manifest confirms real face scores flowed through the full pipeline: `face_count=1, eyes_open=0.734, smile=0.946, composition=0.361, final=0.594` — matches the values measured when testing `faces.py` in isolation (A4), confirming no regression in wiring.
- Only 1 frame exported (all frames identical — a looped still image — correctly deduped to 1).

## Summary

| AC | Status | Notes |
|---|---|---|
| AC-9 (<180s, 30s 1080p) | PASS | 47.1s / 36.7s measured |
| AC-10 (deterministic) | PASS | identical across 2 full runs |
| AC-11 (explainable manifest) | PASS | all sub-scores present |
| AC-12 (min(N,avail) exports) | PASS | 100 requested -> 17 exported |
| AC-14 (quality-bar degrade) | PASS (after fix) | found + fixed a hard-reject edge case that returned 0 frames |
| AC-15 (no-faces fallback) | PASS | both trigger and non-trigger paths verified |
| AC-16 (huge/long file) | PASS | warns + completes, no crash |

One real bug found and fixed during this step (AC-14 hard-rejection edge case, see Test 2). No other failures.
