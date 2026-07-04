# Architecture — The Perfect Moment (architect pass 3)

Architect: sdd:software-architect. Date: 2026-07-04.

## 0. Framing

This is a startup plan, not a change to an existing repo. "Architecture" here = two coupled
systems that must be designed as one bet:
1. **Technical**: the $0/CPU MVP pipeline (CLI, stages, file layout, data flow, output format).
2. **Business/product**: how beachhead cull-lane + FlowUp SMB cash-lane + Hebrew/WhatsApp GTM
   funnel connect through the *same scoring engine* so neither lane needs paid acquisition.

The coherent bet: one engine, two warm-channel lanes, zero variable cost until a named gate.
Trade-off accepted: classical-CV ceiling (validated at AC-13) is the risk we deliberately run in
exchange for the $0 constraint; if pros don't trust the top-N, the honest fallback is a lifestyle
tool, and the plan says so rather than papering over it with paid models.

## 1. Solution Strategy (reasoning)

- **Engine-first, wrappers-thin.** The atom is "video → ranked best human frames + explainable
  manifest." Photographer cull and FlowUp SMB product-photo are two delivery wrappers on the
  identical CLI; building one builds both. This is why we resist the consumer-app framing — it
  would fork the engine toward a walled-garden convenience we lose head-to-head on distribution.
- **CLI-first, not web app.** No upload backend in MVP. Founder runs the CLI locally and hands
  back stills (manual delivery). This keeps running cost literally $0 (no cloud compute) and lets
  validation happen in a room with a photographer before any infra is built.
- **Cascade cheap→expensive** (per SKILL.md pitfall #1): ffmpeg sample → Laplacian/exposure reject
  → MediaPipe face/eye/smile → pyiqa/NIMA only on survivors → dedupe. This is what makes the
  3-minute CPU budget (AC-9) achievable; NIMA on every frame would blow it.
- **Deterministic scoring** (AC-10): no randomness, fixed sampling grid, so demos and blind tests
  are reproducible and trust is buildable.
- **Gate discipline**: nothing with variable cost (paid vision APIs, self-serve backend, mobile,
  global) ships until a *named* revenue/validated-demand milestone in the Scope table is crossed.

## 2. MVP Pipeline Architecture

### CLI entrypoint
```
python -m perfectmoment extract <video> --top-n 5 --min-score 0.6 [--fps 2] [--no-faces] [--out ./out]
```
- `<video>` positional path.
- `--top-n` (default 5) → exactly `min(N, qualifying frames)` exported (AC-12).
- `--min-score` (default 0.6) quality bar on the normalized final score.
- `--fps` sampling rate, default **2** (see throughput math; promoted into AC-9).
- `--no-faces` / auto-detect fallback for product/landscape clips (AC-15).
- `--out` output dir (default `./perfect-moment-out/<video-stem>/`).

### Pipeline stages (in order)
1. **Probe + plan** — `ffprobe` reads duration/resolution/rotation. If longest edge > ~1920 or
   duration long/4K, set a downscale-for-scoring flag and warn (AC-16). Decide sampling: default
   dense `fps=2`; for long continuous footage fall back to I-frame first pass then windowed dense.
2. **Frame extraction (ffmpeg @ ~2fps)** — `ffmpeg -i in -vf "fps=2,scale='min(1280,iw)':-2"
   -qscale:v 2 frame_%05d.jpg` into a temp dir. Downscale for scoring only; original timestamps
   retained in filename for re-extracting the chosen frame at full res for delivery.
3. **Cheap technical filter (OpenCV)** — per frame: Laplacian variance (sharpness) + mean
   brightness (exposure sanity, ~25–230). Resize to consistent 800px longest edge *before*
   Laplacian (pitfall: scale-dependence). Drop obviously blurry/blown/black frames. Blur threshold
   is calibrated per-source, not a global constant.
4. **Face/eye/smile scoring (MediaPipe Tasks FaceLandmarker)** — on survivors only. Blendshapes:
   `open_eyes = 1 - max(eyeBlinkL, eyeBlinkR)`, `smile = mean(mouthSmileL, mouthSmileR)`,
   aggregate across faces → per-frame face-quality. If a frame has 0 faces and clip is
   face-bearing, low face weight; if whole clip has no faces → `--no-faces` fallback path (AC-15).
5. **Aesthetic scoring (pyiqa NIMA, CPU)** — `device='cpu'`, run **only** on frames passing 3+4.
   Emits 1–10 aesthetic mean.
6. **Compose + dedupe/diversity** — weighted final score
   `final = 0.3*blur_norm + 0.4*face_quality + 0.3*aesthetic_norm` (portrait weights; product
   weights shift to blur+aesthetic). Perceptual-hash (`imagehash.phash`, hamming ≤ ~6) dedupe so
   top-N isn't N near-identical burst frames (AC's spirit — diverse picks).
7. **Ranked output** — re-extract each chosen frame at full resolution from source at its
   timestamp, write JPEGs + manifest.

### Graceful degrade — "no frames meet the quality bar" (AC-14)
If, after stage 6, **no** frame's `final ≥ --min-score`: do NOT exit empty/crash. Instead:
- Rank all candidates anyway, take the top `min(N, available)`.
- Set manifest `quality_bar_met: false` and per-frame `low_quality: true`.
- Print a clear line: `WARNING: no frames met the quality bar (min-score 0.6). Returning
  best-available frames flagged low-quality.`
- Exit code 0 (clean) — the founder still has something to show; the flag drives the
  paid-model-gate conversation, not a silent failure.
This is the same clean-exit contract as the dark-video error scenario.

### Throughput math (proves AC-9's 3-min CPU budget for 30s 1080p)
- Sampling @ **2fps × 30s = 60 candidate frames**.
- Stage 3 (Laplacian+exposure): ~5ms/frame → 60×5ms = **0.3s**.
- Stage 4 (MediaPipe BlazeFace+landmarker): ~10–30ms/frame, say worst 30ms on survivors.
  Even if all 60 survive: 60×30ms = **1.8s**.
- Stage 5 (NIMA via pyiqa, InceptionResNetV2 worst case 150ms/frame): only survivors of 2+3+4
  reach it. Even upper-bound all 60: 60×150ms = **9s** (MobileNet backbone ~40ms → 2.4s).
- Stage 2 ffmpeg extract of 60 frames + stage 6 phash(60): a few seconds combined.
- **Total worst-case ≈ 0.3 + 1.8 + 9 + ffmpeg/dedupe ≈ 15–25s** — comfortably inside the
  **3-minute (180s)** budget, leaving ~7–10× headroom for a slower CPU / higher survivor count.
  This is why fps is pinned at 2: it keeps candidate count ~60 (not 150+ at higher fps) so the
  NIMA stage — the bottleneck — stays bounded.

### Python project layout
```
perfect-moment/
  perfectmoment/
    __init__.py
    __main__.py            # argparse CLI → dispatch to extract()
    pipeline.py            # orchestrates stages 1–7, cascade + timing guards
    extract.py             # stage 1–2: ffprobe plan + ffmpeg sampling/downscale
    quality.py             # stage 3: Laplacian blur + exposure
    faces.py               # stage 4: MediaPipe FaceLandmarker, blendshape scores
    aesthetics.py          # stage 5: pyiqa NIMA (device='cpu')
    rank.py                # stage 6: weighted compose + phash dedupe/diversity
    output.py              # stage 7: full-res re-extract, JPEG + JSON manifest writer
    config.py              # weights, thresholds, defaults (min-score, fps)
  models/
    face_landmarker.task   # downloaded free from Google model zoo (gitignored)
  requirements.txt         # opencv-python, mediapipe, pyiqa, torch (CPU wheel), imagehash, Pillow
  README.md
  landing/                 # static Hebrew LP + WhatsApp funnel (Vercel free tier)
    index.html
```

### Output format
Per run → `./out/<video-stem>/`:
- `rank_01.jpg … rank_0N.jpg` (best first, full-res).
- `manifest.json`:
```json
{
  "video": "ceremony.mp4",
  "config": {"top_n": 5, "min_score": 0.6, "fps": 2},
  "quality_bar_met": true,
  "runtime_seconds": 22.4,
  "frames": [
    {"rank": 1, "file": "rank_01.jpg", "timestamp": 12.5, "final": 0.81,
     "sharpness": 640.2, "brightness": 128, "face_count": 2,
     "eyes_open": 0.97, "smile": 0.62, "composition": 0.7,
     "aesthetic": 6.8, "low_quality": false}
  ]
}
```
Manifest records every sub-score (AC-11) so a pick is explainable, not a black box.

## 3. Business/GTM Architecture

One lead flow, two lanes, same engine:

- **Lane A (beachhead) — photographer/videographer cull.** Direct/beta outreach + the 10
  validation interviews (Key Assumptions). Founder runs CLI on a real shoot clip, hands back
  ranked stills. Value line: "saved ~2h scrubbing + extra deliverables." Blind test = AC-13.
- **Lane C (cash) — FlowUp SMB product-photo.** Reuses the *existing* FlowUp warm SMB list +
  WhatsApp funnel + Hebrew landing page (no new CAC). SMB sends 20s product video → clean catalog
  stills, bundled with a Make.com listing automation. `--no-faces` path; product weights.
- **Shared funnel front-end.** One Hebrew-first static landing page (Vercel free) → WhatsApp CTA
  (972547676000 pattern from FlowUp) → manual intake → founder runs CLI → delivery. Photographers
  hit it via direct outreach; SMBs via FlowUp's existing sequence. Same page, same WhatsApp,
  same engine — cross-lane de-risking with zero paid acquisition.

### Upgrade to paid, at the named Scope gates
- Self-serve web upload backend ← ≥1 paying customer + repeated manual delivery proving demand.
- Paid vision APIs ← paid revenue covers per-call cost at positive unit economics **AND**
  classical-CV ceiling demonstrably hit (AC-13 fails at ≥4/5 across the panel).
- Mobile app ← ≥3 paying users asking for on-the-go.
- Global/multi-language ← Israel beachhead shows retention + WTP.
Pricing when a B2B2C tier lands: flat/unlimited ~$10–30/mo band (research: market converged there;
usage-based Imagen is the disliked exception).

## 4. Data Flow Diagram

```
  <video file>
       │  ffprobe (plan: fps, downscale?, warn if 4K/long)   [stage 1]
       ▼
  ffmpeg  fps=2 + scale→1280 + qscale:v2  ──► temp frames (~60 for 30s)  [stage 2]
       │
       ▼
  OpenCV: Laplacian var + brightness ──► drop blurry/blown/black         [stage 3]
       │  (survivors)
       ▼
  MediaPipe FaceLandmarker blendshapes ──► eyes_open, smile, face_count  [stage 4]
       │  (survivors; if no faces anywhere → --no-faces fallback)
       ▼
  pyiqa NIMA (CPU) ──► aesthetic 1–10   (ONLY on survivors)              [stage 5]
       │
       ▼
  weighted compose + phash dedupe/diversity ──► ranked candidates        [stage 6]
       │  (if none ≥ min-score → flag low_quality, keep best-available, warn)  [AC-14]
       ▼
  full-res re-extract at timestamps ──► rank_01..0N.jpg + manifest.json  [stage 7]
       │
       ▼
  manual delivery: founder → photographer (Lane A) / FlowUp SMB via WhatsApp (Lane C)
```

## 5. Key Architectural Decisions

1. **Classical/open CV over paid vision API for MVP** — satisfies the hard $0/month constraint;
   quality risk is explicitly deferred to AC-13's blind test and gated behind revenue+ceiling.
2. **CLI-first, no web/upload backend** — $0 compute, validation possible in-room; self-serve is
   gated on proven repeated manual demand.
3. **Manual delivery, not self-serve** — removes all infra from the validation loop; the founder
   is the "backend" until a paying customer justifies building one.
4. **Cascade cheap→expensive (Laplacian → MediaPipe → NIMA)** — the only way the 3-min CPU budget
   holds; NIMA is the bottleneck and must run on survivors only.
5. **Deterministic, fixed-grid sampling @ 2fps** — reproducible rankings (AC-10) and bounds
   candidate count so NIMA cost stays inside budget (AC-9 math).
6. **Single engine, two wrapper lanes (photographer + FlowUp SMB)** — build once, sell twice;
   `--no-faces` flag + per-wedge weights are the only lane-specific code.
7. **Explainable manifest (all sub-scores emitted)** — builds pro trust and makes the AC-13 blind
   test diagnosable, not a black box.
8. **Graceful degrade contract (clean exit + low-quality flags)** — dark/no-face/huge-file inputs
   and the "no frame meets bar" case all return best-available + warn, never crash (AC-14/15/16).
9. **Gate-guarded roadmap** — every cost-incurring capability sits behind a named revenue/demand
   trigger, keeping the $0 promise structurally honest.

## 6. Expected Changes / Build Artifacts (input for decomposition)

Modules/files to create:
1. `perfectmoment/__main__.py` — argparse CLI (flags: top-n, min-score, fps, no-faces, out).
2. `perfectmoment/pipeline.py` — stage orchestration, cascade, timing/memory guards.
3. `perfectmoment/extract.py` — ffprobe plan + ffmpeg sampling/downscale (stages 1–2).
4. `perfectmoment/quality.py` — Laplacian blur + exposure filter (stage 3).
5. `perfectmoment/faces.py` — MediaPipe FaceLandmarker blendshape scoring (stage 4).
6. `perfectmoment/aesthetics.py` — pyiqa NIMA CPU scoring (stage 5).
7. `perfectmoment/rank.py` — weighted compose + phash dedupe/diversity (stage 6).
8. `perfectmoment/output.py` — full-res re-extract + JPEG/manifest writer (stage 7).
9. `perfectmoment/config.py` — weights, thresholds, defaults.
10. `requirements.txt` — CPU-pinned deps (torch CPU wheel index note).
11. `models/face_landmarker.task` — fetched from Google model zoo (setup step, gitignored).
12. `README.md` — install + run + calibration notes.
13. `landing/index.html` — Hebrew LP + WhatsApp funnel (Vercel free tier), reuses FlowUp playbook.

Also: AC edits in the task file (ACs 1, 4, 6 tightened; 9 gets fps+timing; 13 gets n-caveat; 14
degrade guidance) — done in place, not new artifacts.
