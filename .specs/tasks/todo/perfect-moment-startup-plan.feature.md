---
title: "The Perfect Moment — AI best-frame extraction startup: complete plan"
depends_on: []
---

# The Perfect Moment — Startup Plan

## Description

**Product.** "The Perfect Moment" is an AI pipeline that takes a video and automatically surfaces the few frames a human would have chosen — sharp (not motion-blurred), eyes open, good expression, decent composition — and ranks them, so a video-first shoot becomes a set of print-worthy stills without manual scrubbing. The engine is the product; the consumer "one killer photo from your phone clip" framing is just one thin wrapper around it.

**Who it's for (beachhead first).** Not the casual consumer. The wedge that survives is **B2B: event photographers/videographers in Israel** (weddings, bar/bat mitzvahs, birthdays; shoots priced ₪5,000–15,000) who now capture video-first (mirrorless hybrids, gimbals, 4K/60) and spend unpaid hours culling to deliver stills. A parallel, faster-cash lane is **Israeli small businesses via the founder's existing FlowUp channel**: turn a short phone video of a product into clean catalog stills, bundled with a Make.com listing automation.

**Why now.** (1) Video-first capture is now the default even at events; "I have 40 min of 4K, give me 30 print-worthy stills of the key moments" is a real, unserved job. (2) Free/open CV and face-landmark models (OpenCV, MediaPipe) are good enough to build a scoring pipeline at **$0/month**. (3) The founder already holds the exact adjacent assets — FFmpeg frame extraction, Python tooling, Hebrew GTM, and a **warm SMB channel (FlowUp)** — so the build and first-customer cost is near zero. The window is: cheap to validate before an incumbent bundles it.

**The surviving wedge (the honest answer to "Google Photos already does this").** Google Photos Top Shot and Apple Live Photo key-frame already pick the best frame of a short burst, on-device, free, at capture time — and they win that consumer job on distribution before we start. They are structurally weak exactly where our beachhead lives, and we compete only there:
- **Volume culling of professional footage** — ranking the best N frames *across a whole shoot* against *client-relevant* criteria, delivered as usable stills. No consumer default does this.
- **Video-first → deliverable stills** — extracting print-worthy frames from long 4K clips, not one short Live Photo.
- **B2B / batch / API / pipeline** — a tool a studio (or a Make.com automation) can drop in, not a walled-garden convenience.
- **Hebrew-first + relationship distribution** — irrelevant to Google, but the founder's home turf via FlowUp.

Wedge decision: beachhead = photographer/videographer video-cull (B2B); FlowUp SMB product-photo = parallel cash lane on the same engine; "AI second shooter" = the vision/expansion narrative; a Hebrew consumer app = at most a free viral top-of-funnel lead magnet, **never the business** (it loses head-to-head with free defaults and would demand CAC the founder can't fund).

Founder context (must be honored throughout):
- Solo founder in Israel (Elon), non-funded, hard constraint: **$0/month running cost for MVP** (no paid APIs until revenue).
- Existing assets/skills: FFmpeg experience (YouTube frame-extraction skill), Python tooling, FlowUp lead-gen/proposal agents for Israeli small businesses, Hebrew marketing content generation, Vercel free tier, Make.com knowledge.
- Beachhead market idea: event photography in Israel (weddings, bar mitzvahs, birthdays — photographers cost ₪5,000–15,000), plus adjacent wedge options (small-business product shots from video, pet/kids photos, profile photos).

The plan must include:
1. Market research & competitive landscape (Google Photos Top Shot, Apple Live Photos key frame, existing best-shot apps) and the differentiated wedge.
2. MVP build plan at $0 cost: FFmpeg frame extraction + classical CV scoring (Laplacian blur, face/eye detection with OpenCV/MediaPipe free models) — concrete architecture, pipeline stages, file layout, and a runnable prototype spec.
3. Business model & pricing (freemium? B2B2C via photographers? SMB angle tying into FlowUp?), unit economics once paid vision APIs enter.
4. Go-to-market for Israel first (Hebrew-first landing page, WhatsApp funnel — reuse FlowUp playbook), then global.
5. Roadmap: prototype → private beta → paid tier → scale, with decision gates and risks.

## Scope

### In scope (MVP — must be provable on the founder's Windows machine at $0/month)
- **CLI pipeline**: `input video → FFmpeg frame sampling → per-frame classical-CV scoring → ranked top-N stills (JPEG) + a scores manifest (JSON/CSV)`.
- **Scoring signals, all free**: Laplacian-variance sharpness/blur; exposure/brightness sanity; face detection (OpenCV Haar or MediaPipe); eyes-open heuristic (eye-aspect-ratio from landmarks); simple composition proxy (face size/centering, rule-of-thirds distance).
- **Configurable N** (default top-5) and quality threshold via CLI flags.
- **One Hebrew-first landing page + WhatsApp funnel**, static, reusing the FlowUp playbook, on Vercel free tier.
- **Manual private-beta delivery**: founder runs the CLI for a beta photographer / FlowUp SMB and hands back stills — no self-serve upload backend required to validate.

### Out of scope for MVP — and the gate that unlocks each
| Out-of-scope item | Unlock gate |
|---|---|
| Native mobile app | ≥3 paying users explicitly asking for on-the-go use |
| Realtime / at-capture selection | A hardware/SDK partner; never a $0 concern |
| Paid vision APIs (aesthetic/emotion/named-face scoring) | Paid revenue covers per-call cost at positive unit economics **AND** classical-CV quality ceiling is demonstrably hit (AC-13) |
| Self-serve web upload + processing backend | ≥1 paying customer + repeated manual delivery proving demand; still start within free-tier limits |
| Global / multi-language GTM | Israel beachhead shows retention + willingness-to-pay |
| Highlight reels / video editing | Never — different product |
| "Who matters" (client-specific person ranking) | After beachhead; likely needs paid face-recognition → same gate as paid vision APIs |

Gate rule (keeps the $0 promise honest): nothing that costs money ships until a **named** revenue or validated-demand milestone above is crossed.

## Acceptance Criteria

### A. The plan document
1. The plan is a single self-contained document (no external doc required to act) whose MVP section, GTM section, and roadmap each contain at least one concrete next action the founder can start the same day without further research.
2. The MVP section is concrete enough to start coding immediately: it names exact libraries (FFmpeg, OpenCV/MediaPipe, Python), lists each pipeline stage, and specifies the CLI interface (inputs, flags, outputs).
3. Every recommendation respects the $0/month constraint, or is explicitly placed behind a named unlock gate in the Scope table.
4. The competitive section explicitly names Google Photos Top Shot / Best Take and Apple Live Photos key-frame, states the specific structural gap (they only operate within a ~1.5–3s native-camera capture window, not on arbitrary pre-existing video files), and states the surviving wedge (B2B batch/API + video-first deliverable stills + Hebrew/WhatsApp channel) in one paragraph.
5. GTM reuses named existing FlowUp assets (Hebrew landing page, WhatsApp funnel, warm SMB list) rather than starting from zero.
6. The plan names all four positioning roles — beachhead (photographer video-cull B2B), parallel cash lane (FlowUp SMB product-photo), vision ("AI second shooter"), deprioritized (consumer app) — and for each gives at least one sentence of rationale tied to a named factor (pain, channel, defensibility, or CAC).
7. The roadmap has explicit decision gates (prototype → private beta → paid tier → scale) each tied to a measurable trigger, not a date.
8. The plan lists the key assumptions from the "Key Assumptions & Validation" section and, for each, how it will be tested.

### B. The MVP prototype (behavioral, testable)
9. **Given** a 30-second 1080p phone video containing people, **when** it is run through the pipeline on the founder's CPU (no GPU) sampling at **~2 fps** (≈60 candidate frames), **then** it outputs the top-5 frames ranked (best first) plus a scores manifest, in **under 3 minutes** (180s). Reproducibility basis: at 2 fps the cascade cost is bounded — Laplacian+exposure ~5ms×60 ≈ 0.3s, MediaPipe ~30ms×60 ≈ 1.8s, NIMA (bottleneck) ~150ms×survivors ≤ ~9s, plus ffmpeg extract/dedupe — worst case ≈ 15–25s, ~7–10× inside the 180s budget. The 2 fps rate is fixed precisely to keep candidate count (and thus the NIMA stage) bounded.
10. **Given** the same input video and the same config, **when** the pipeline is run twice, **then** the ranking is identical (scoring is deterministic — no randomness).
11. **Given** a video where humans are present, **when** ranked, **then** each output frame's manifest entry records its sharpness, brightness, face-count, eyes-open, and composition sub-scores (so a picks can be explained, not a black box).
12. **Given** the `--top N` flag, **when** set to any N ≥ 1, **then** exactly min(N, available-qualifying-frames) stills are exported.
13. **Given** real shoot clips from the beta panel (the same **10 photographers** interviewed in Key Assumption 1, not a single reviewer), **when** each blind-reviews the tool's top-5 against their own manual pick, **then** agreement is **≥4 of 5 on average across the panel** (per-reviewer variance expected; the panel mean is the bar). Failing this across the panel triggers the paid-model gate discussion (AC-13 → paid vision APIs gate), not silent shipping.

### C. Error handling (prototype)
14. **Given** a dark/underexposed video with no frames above the quality bar (no frame's normalized final score ≥ `--min-score`), **when** run, **then** the tool: (a) prints `WARNING: no frames met the quality bar` naming the `--min-score` value used; (b) still returns the top `min(N, available)` best-available frames rather than an empty result; (c) sets `quality_bar_met: false` in the manifest and `low_quality: true` on each returned frame; and (d) exits cleanly with code 0 (no crash, no empty crash-dump). The low-quality flag — not a silent empty exit — is what feeds the paid-model-gate discussion.

Output location for all behavioral ACs above: ranked stills + `manifest.json` are written to `<out>/<video-stem>/`, where `<out>` defaults to `./perfect-moment-out/` (so the default run directory is `./perfect-moment-out/<video-stem>/`) and is overridable via `--out`.
15. **Given** a video with no detectable faces (e.g. a product or landscape clip), **when** run, **then** the pipeline falls back to sharpness + composition-only scoring and still returns ranked stills (does not fail).
16. **Given** a long/large 4K file, **when** run, **then** the pipeline samples frames and downscales for scoring to stay within memory/time, warns the user, and completes rather than exhausting memory.

## User Scenarios

**Primary 1 — Photographer cull demo (beachhead).** A wedding photographer hands the founder a 4-minute 4K ceremony clip. The founder runs the CLI; minutes later returns a folder of ranked, print-worthy stills of the key moments. Value line: "this just saved you ~2 hours of scrubbing and gave you extra deliverables you'd have missed."

**Primary 2 — FlowUp SMB product-photo cross-sell (cash lane).** An existing FlowUp small-business lead sends a 20-second phone video panning around a product. The same engine returns clean, sharp, well-framed catalog stills, bundled with a Make.com automation that lists them — one warm-channel offer, two products, zero new CAC.

**Error 1 — Dark video.** Poorly lit reception footage yields no frames above the quality bar → tool reports the situation, returns best-available frames flagged low-quality, exits cleanly (AC-14).

**Error 2 — No faces.** A landscape or product clip has no detectable faces → pipeline falls back to sharpness+composition scoring and still delivers ranked stills (AC-15).

**Error 3 — Huge file.** A 40-minute 4K file would blow memory if loaded whole → sampling + downscale keep it within limits; the tool warns and completes (AC-16).

**Cross-sell scenario (explicit).** Because the photographer lane and the FlowUp SMB lane run on the *same scoring engine*, the founder markets both from one codebase: photographers via direct/beta outreach, SMBs via the existing FlowUp WhatsApp funnel and warm list. Each validated lane de-risks the other and neither needs paid acquisition.

## Key Assumptions & Validation

For the outcome to be venture-scale rather than a lifestyle tool, **all** of the following must hold. Each is an assumption to test, not a given.

1. **Culling is a top-3 pain with cash attached.** Validate: interview 10 photographers; measure hours/event spent culling and willingness to pay per event.
2. **Video-first stills is a growing, not niche, workflow.** Validate: survey the capture mix; look for a trend line, not a one-off.
3. **Classical-CV quality is "good enough" that pros trust the top-N.** Validate: AC-13 blind test — does the photographer agree with ≥4/5 of the tool's picks? If this fails on free tech, the honest conclusion is *lifestyle tool, or needs funding for paid models* — the plan must say so plainly.
4. **A wedge exists that Google/Apple structurally won't enter** (B2B batch/API, pro deliverable, relationship channel). Validate: confirm no incumbent ships video→ranked-deliverable-stills for pros.
5. **It generalizes beyond events** (stock, e-commerce, media asset libraries share the "find the best frame at scale" problem) — the TAM that makes it a company. Validate later, only after the beachhead proves out.

Honest default expectation: absent proof of the above, this is a **$0-cost lifestyle/consulting tool** (a handful of Israeli photographers + a FlowUp SMB add-on). The plan should treat the billion-dollar path as a hypothesis gated on assumptions 1–5, not the base case.

## Research

- Reusable technical skill: `.claude/skills/best-frame-extraction/SKILL.md` — concrete $0/CPU pipeline (ffmpeg extraction → OpenCV Laplacian blur filter → MediaPipe FaceLandmarker eye/smile scoring → pyiqa/NIMA aesthetic scoring → perceptual-hash dedupe/rank), with library names, thresholds, and 7 documented pitfalls.
- Full findings + sources: `.specs/scratchpad/research-2a.md` (47 sourced URLs, competitive/market/technical/prior-art).
- **This exact idea already exists as free/cheap tools** (BestFrame, Imagen AI's free frame extractor, AI Frame Grabber, open-source PerfectFrameAI) — the technology is not a moat; the wedge must be workflow/distribution (Hebrew/Israel, WhatsApp funnel, B2B2C via photographers), not "we invented best-frame extraction."
- Google Photos Top Shot / Best Take and Apple Live Photos key-frame only work within a ~1.5-3s native-camera capture window — neither ingests arbitrary pre-existing video files, which is the clearest surviving gap vs. the platform incumbents.
- Photographer culling pain is real and sourced: culling+editing runs 3-5 hours per 1 hour shot, ~80-90% of captured frames get discarded, and photographers already pay $10-48/mo flat-rate for AI culling tools (Aftershoot, Narrative, FilterPixel) — this is stronger proven willingness-to-pay than the general consumer photo-app market, where WTP is weak due to free native alternatives.
- Full $0/month technical stack is CPU-feasible on a Windows laptop and confirmed by a working open-source reference (PerfectFrameAI): ffmpeg + opencv-python + mediapipe + pyiqa (CPU-only torch wheel) + imagehash — no paid APIs needed for MVP.
- Israel-specific wedding photography pricing found (₪1,700-2,400 for photographer time blocks, ₪1,000-1,500 magnet-photographer add-on) is lower than the founder's bundled-package estimate of ₪5-15K — reconcile as component-price vs. full-package price, not a contradiction, when sizing the beachhead.

## Architecture Overview

Full reasoning: `.specs/scratchpad/architecture-3.md`.

### 1. Solution Strategy

One engine, two warm-channel lanes, zero variable cost until a named gate. The atom is "video → ranked best human frames + explainable manifest." Photographer cull (beachhead) and FlowUp SMB product-photo (cash lane) are thin delivery wrappers on the *same* CLI — build once, sell twice — which is exactly why the consumer-app framing is deprioritized (it would fork the engine toward a walled-garden convenience we lose head-to-head on distribution). The MVP is CLI-first with manual delivery (no upload backend, $0 compute) so validation happens in a room with a real photographer before any infra is built. The deliberate trade-off: we run the classical-CV quality risk (validated at AC-13's panel blind test) in exchange for the $0 constraint; if pros don't trust the top-N on free tech, the honest fallback is a lifestyle tool, and the plan says so rather than papering over it with paid models. GTM reuses FlowUp's existing Hebrew landing page + WhatsApp funnel + warm SMB list, so neither lane needs paid acquisition.

### 2. MVP Pipeline Architecture

The concrete $0/CPU technical playbook this pipeline implements — library names, thresholds, and 7 documented pitfalls — lives in the reusable skill `.claude/skills/best-frame-extraction/SKILL.md`.

**CLI entrypoint:**
```
python -m perfectmoment extract <video> --top-n 5 --min-score 0.6 [--fps 2] [--no-faces] [--out ./perfect-moment-out]
```
`--out` defaults to `./perfect-moment-out`; each run writes to `<out>/<video-stem>/` (default `./perfect-moment-out/<video-stem>/`).

**Stages (cascade cheap→expensive so the 3-min CPU budget holds):**
1. **Probe + plan** — `ffprobe` reads duration/resolution/rotation; flags downscale + warns for 4K/long files (AC-16).
2. **Frame extraction (ffmpeg @ ~2 fps)** — `ffmpeg -i in -vf "fps=2,scale='min(1280,iw)':-2" -qscale:v 2 frame_%05d.jpg`; downscale for scoring only, timestamps kept in filenames for full-res re-extract.
3. **Cheap technical filter (OpenCV)** — Laplacian variance (sharpness, resize to 800px first) + mean brightness; drop blurry/blown/black. Threshold calibrated per-source, not a global constant.
4. **Face/eye/smile scoring (MediaPipe Tasks FaceLandmarker)** — blendshapes: `open_eyes = 1 - max(eyeBlinkL, eyeBlinkR)`, `smile = mean(mouthSmileL, mouthSmileR)`, aggregated across faces. Whole-clip no-faces → `--no-faces` fallback (AC-15).
5. **Aesthetic scoring (pyiqa NIMA, `device='cpu'`)** — run **only** on survivors of 2+3+4 (this is the bottleneck).
6. **Compose + dedupe/diversity (`rank.py`)** — the composition sub-score (face size/centering + rule-of-thirds distance, computed in `rank.py` from the MediaPipe face boxes emitted by stage 4) feeds the weighted `final = 0.3*blur_norm + 0.4*face_quality + 0.3*aesthetic_norm` (product lanes shift to blur+aesthetic); `imagehash.phash` hamming ≤ ~6 dedupe so top-N isn't N burst-neighbor frames.
7. **Ranked output** — re-extract chosen frames at full res from source, write JPEGs + manifest.

**Data flow (stages 1→7, end to end):**
```
  <video file>
       │  ffprobe (plan: fps, downscale?, warn 4K/long)          [stage 1]
       ▼
  ffmpeg fps=2 + scale→1280 + qscale:v2 → ~60 temp frames        [stage 2]
       ▼
  OpenCV Laplacian var + brightness → drop blurry/blown/black    [stage 3]
       ▼  (survivors)
  MediaPipe FaceLandmarker → eyes_open, smile, face_count        [stage 4]
       ▼  (no faces anywhere → --no-faces fallback)              [AC-15]
  pyiqa NIMA (CPU) → aesthetic 1–10  (survivors ONLY)            [stage 5]
       ▼
  rank.py: composition sub-score + weighted compose
           + phash dedupe/diversity → ranked candidates          [stage 6]
       ▼  (none ≥ min-score → flag low_quality, keep best, warn) [AC-14]
  full-res re-extract → rank_01..0N.jpg + manifest.json          [stage 7]
       ▼
  manual delivery → photographer (Lane A) / FlowUp SMB WhatsApp (Lane C)
```

**Throughput math (proves AC-9 for 30s 1080p on CPU):** 2 fps × 30s = ~60 candidates. Stage 3 ~5ms×60 ≈ 0.3s; stage 4 ~30ms×60 ≈ 1.8s; stage 5 NIMA ~150ms×survivors ≤ ~9s (MobileNet backbone ~40ms → ~2.4s); + ffmpeg extract/dedupe. Worst case ≈ **15–25s**, ~7–10× inside the 180s budget. fps is pinned at 2 to bound candidate count and thus the NIMA stage.

**Graceful degrade — no frames meet the quality bar (AC-14):** if no `final ≥ --min-score`, still return top `min(N, available)`, set `quality_bar_met: false` + per-frame `low_quality: true`, print a `WARNING: no frames met the quality bar` line, exit code 0. Never empty/crash; the flag feeds the paid-model-gate discussion.

**Project layout:**
```
perfectmoment/  __main__.py  pipeline.py  extract.py  quality.py  faces.py
                aesthetics.py  rank.py  output.py  config.py
scripts/fetch_model.py   models/face_landmarker.task (gitignored)
requirements.txt   .gitignore   README.md   landing/index.html
```

**Output:** `./perfect-moment-out/<video-stem>/rank_01..0N.jpg` (full-res, best first) + `manifest.json` recording every sub-score per frame (sharpness, brightness, face_count, eyes_open, smile, composition, aesthetic, final, low_quality) so picks are explainable (AC-11).

### 3. Business/GTM Architecture

One shared funnel front-end, two lanes on the same engine:
- **Lane A (beachhead, photographer cull):** direct/beta outreach + the 10 validation interviews; founder runs CLI on a real clip, hands back ranked stills ("saved ~2h scrubbing"); blind test = AC-13.
- **Lane C (cash, FlowUp SMB product-photo):** reuses the existing FlowUp warm SMB list + WhatsApp funnel + Hebrew landing page (no new CAC); 20s product video → catalog stills bundled with a Make.com listing automation; `--no-faces` path.
- **Shared front-end:** one Hebrew-first static landing page (Vercel free) → WhatsApp CTA → manual intake → CLI → delivery. Photographers arrive via outreach, SMBs via FlowUp's sequence — same page, same WhatsApp, same engine, cross-lane de-risking, zero paid acquisition.

**Upgrade to paid at Scope gates:** self-serve backend ← ≥1 paying customer + repeated manual delivery; paid vision APIs ← revenue covers per-call cost at positive unit economics **AND** classical-CV ceiling hit (AC-13 fails across panel); mobile ← ≥3 paying users asking on-the-go; global ← Israel retention + WTP proven. B2B2C pricing when it lands: flat/unlimited ~$10–30/mo (research: market converged there).

### 4. Key Architectural Decisions

1. **Classical/open CV over paid vision API for MVP** — meets $0/month; quality risk deferred to AC-13 and gated behind revenue + demonstrated ceiling.
2. **CLI-first, no web/upload backend** — $0 compute, in-room validation; self-serve gated on proven repeated demand.
3. **Manual delivery, not self-serve** — founder is the "backend" until a paying customer justifies infra.
4. **pyiqa NIMA (CPU) for aesthetic scoring, run on survivors only** — cascade cheap→expensive (Laplacian → MediaPipe → NIMA) is the only way the 3-min CPU budget holds. *Rejected alternatives:* (a) **BRISQUE** (classical, ~5ms/frame, cheaper) — judges technical distortion, not composition/"is this a good photo," so it fails the core job of ranking client-worthy stills; kept only as an optional pre-filter. (b) **Hand-vendored NIMA checkpoint weights** — removes the pyiqa/torch dependency but forces the solo founder to hunt, host, and version-manage model weights (a documented pitfall); pyiqa gives NIMA in one pip dep with `device='cpu'`, which wins on solo-maintainability. Chose pyiqa NIMA as the best free composition-aware scorer per unit of setup cost.
5. **Deterministic fixed-grid sampling @ 2 fps** — reproducible rankings (AC-10) and bounds candidate count so NIMA cost stays inside the AC-9 budget. *Rejected alternatives:* (a) **Scene-change (`select='gt(scene,x)')` sampling** — emits a variable, content-dependent frame count, so the NIMA-stage cost (and thus the AC-9 timing guarantee) can't be bounded a priori, and it skips continuous phone/handheld "moments" (a laugh, blown candles) that aren't scene cuts — exactly our beachhead footage. (b) **I-frame/keyframe-only extraction** — cheapest and lowest count, but keyframe placement is codec-driven and non-deterministic across re-encodes, breaking AC-10 reproducibility, and it can miss the actual best instant entirely. Fixed-grid 2 fps is the only option that is simultaneously deterministic (AC-10) and count-bounded (AC-9); the skill notes scene-change/I-frame as fallbacks for long continuous footage only.
6. **Single engine, two wrapper lanes** — `--no-faces` flag + per-wedge weights are the only lane-specific code.
7. **Explainable manifest (all sub-scores emitted)** — pro trust + diagnosable AC-13 blind test, not a black box.
8. **Graceful degrade contract (clean exit + low-quality flags)** — dark / no-face / huge-file / no-frame-meets-bar all return best-available + warn, never crash (AC-14/15/16).
9. **Gate-guarded roadmap** — every cost-incurring capability sits behind a named revenue/demand trigger.

### 5. Expected Changes / Build Artifacts

1. `perfectmoment/__main__.py` — argparse CLI (top-n, min-score, fps, no-faces, out).
2. `perfectmoment/pipeline.py` — stage orchestration, cascade, timing/memory guards.
3. `perfectmoment/extract.py` — ffprobe plan + ffmpeg sampling/downscale (stages 1–2).
4. `perfectmoment/quality.py` — Laplacian blur + exposure filter (stage 3).
5. `perfectmoment/faces.py` — MediaPipe FaceLandmarker blendshape scoring (stage 4).
6. `perfectmoment/aesthetics.py` — pyiqa NIMA CPU scoring (stage 5).
7. `perfectmoment/rank.py` — weighted compose + phash dedupe/diversity (stage 6).
8. `perfectmoment/output.py` — full-res re-extract + JPEG/manifest writer (stage 7).
9. `perfectmoment/config.py` — weights, thresholds, defaults.
10. `requirements.txt` — CPU-pinned deps (torch CPU-wheel index note).
11. `models/face_landmarker.task` — fetched from Google model zoo (setup step, gitignored).
12. `README.md` — install, run, per-source calibration notes.
13. `landing/index.html` — Hebrew landing page + WhatsApp funnel (Vercel free tier), reuses FlowUp playbook.

## Implementation Process

Two tracks. **Track A (build)** = the $0/CPU pipeline; **Track B (business)** = validation + GTM. They run partly in parallel and converge at the AC-13 blind panel — the single load-bearing gate. Order is by dependency, grouped Setup → Foundational → Core value → Validation → Polish/GTM. Estimates: S ≈ ≤½ day, M ≈ 1–2 days, L ≈ 3–5 days (solo).

### Phase 1 — Setup

**A1. Project scaffold** (S). *Track A.* Depends: none.
- Goal: a runnable, CPU-only Python package skeleton every later step builds on.
- Outputs: `perfectmoment/__init__.py`, `config.py` (weights/thresholds/defaults: `min_score=0.6`, `fps=2`, `out='./perfect-moment-out'`), `requirements.txt` (opencv-python, mediapipe, pyiqa, torch CPU-wheel, imagehash, Pillow), a `scripts/fetch_model.py` for `models/face_landmarker.task`, `.gitignore` (models, out dir).
- Success: `pip install -r requirements.txt` succeeds and `python -c "import torch; assert not torch.cuda.is_available()"` passes on the founder's machine; `python -m perfectmoment --help` runs (stub).
- Subtasks: create package dirs; pin torch CPU index-url; write config defaults; write model-fetch script; assert-CPU guard.
- **Blocker:** torch pulls multi-GB CUDA build (SKILL pitfall #6). **Resolution:** `pip install torch --index-url https://download.pytorch.org/whl/cpu`; assert CPU at import.
- **Verify (LOW → None):** no LLM judge. Boilerplate scaffold; the step's own success test (`pip install` succeeds, CPU-assert passes, `--help` stub runs) is a sufficient mechanical gate.

**B1. Interview/beta panel recruitment** (M). *Track B.* Depends: none. **HIGH-RISK.**
- Goal: line up the **10 event photographers** who serve as BOTH the Assumption-1 interview panel AND the AC-13 blind-review panel (same panel — hard constraint).
- Outputs: a contact list (name, segment, WTP-relevant notes) in `.specs/scratchpad/panel.md`; scheduled interview slots.
- Success: ≥10 real Israeli event photographers committed (min viable 6, variance noted).
- Subtasks: draft Hebrew outreach; pull FlowUp warm network; post in Israeli wedding-photographer groups; confirm slots.
- **Blocker:** can't reach 10. **Resolution:** FlowUp channel + FB groups; fall back to 6 and flag panel-mean variance. **Risk:** all validation depends on this panel existing — start Day 1.
- **Verify (HIGH → Panel, 3 judges, threshold 3.7):** judge the roster artifact (`panel.md`). Threshold deliberately lower — recruitment is best-effort with a min-6 fallback. Rubric: realness/verifiability of each contact 0.30 (real Israeli event photographers, not proxies); segment representativeness 0.25 (weddings/mitzvahs/birthdays spread, not one niche); panel size vs target 0.25 (≥10 = 5, 6–9 = 3–4 with variance noted, <6 = fail); scheduling commitment 0.20 (confirmed slots, not soft "maybe"). Fail → re-run outreach before any B-track validation.

### Phase 2 — Foundational

**A2. ffmpeg extraction — stages 1–2 (`extract.py`)** (M). *Track A.* Depends: A1.
- Goal: probe a video and emit ~60 downscaled candidate frames deterministically, with timestamps preserved for full-res re-extract.
- Outputs: `perfectmoment/extract.py` (ffprobe plan: duration/res/rotation, downscale flag + 4K/long warn per AC-16; `ffmpeg -vf "fps=2,scale='min(1280,iw)':-2" -qscale:v 2 frame_%05d.jpg`).
- Success: on a 30s 1080p clip yields ~60 frames named with recoverable timestamps; on a 4K/long clip prints the downscale/size warning.
- Subtasks: ffprobe wrapper; sampling command; timestamp-in-filename scheme; 4K warn path.
- **Blocker:** ffmpeg not on PATH (Windows). **Resolution:** README winget/curl install (reuse analyze-youtube-video skill pattern); check on startup.
- **Verify (MED → Single judge, threshold 4.0):** rubric on `extract.py`. Determinism of sampling (fixed-grid 2 fps, no content-dependent selection — AC-10 groundwork) 0.30; timestamp recoverability for full-res re-extract (filename scheme round-trips) 0.30; 4K/long downscale + warn path present (AC-16 groundwork) 0.25; Windows-PATH ffmpeg guard on startup 0.15.

**A3. Quality filter — stage 3 (`quality.py`)** (S). *Track A.* Depends: A2.
- Goal: cheaply reject blurry/blown/black frames before any model runs.
- Outputs: `perfectmoment/quality.py` (Laplacian variance after resize-to-800px-longest-edge per pitfall #2; mean-brightness bounds ~25–230).
- Success: known-sharp frames pass, known-blurry/black frames drop, on a fixed test set; scale-consistent (resize before Laplacian).
- Subtasks: resize helper; Laplacian var; brightness bounds; survivor list output. (Threshold *calibration* deferred to A9.)
- **Verify (LOW → None):** no LLM judge. Small deterministic filter; the in-step fixed sharp/blur/black test set (known-sharp pass, known-blurry/black drop, scale-consistent) is the sufficient gate.

**B2. Hebrew landing page + WhatsApp funnel (`landing/index.html`)** (M). *Track B.* Depends: positioning copy (task doc) only — parallel with A2/A3.
- Goal: one shared Hebrew-first front-end → WhatsApp intake, reusing FlowUp assets (AC-5), for both lanes.
- Outputs: `landing/index.html` (Vercel free tier), WhatsApp CTA to 972547676000, dual value copy (photographer cull + SMB product-photo).
- Success: deploys on Vercel free; WhatsApp CTA opens a pre-filled Hebrew intake message on mobile.
- Subtasks: adapt FlowUp template; Hebrew copy for both lanes; wa.me link; deploy.
- **Verify (MED → Single judge, threshold 4.0):** rubric on `landing/index.html`. Named-FlowUp-asset reuse, not from-scratch (AC-5) 0.30; dual-lane value copy legible to both photographer-cull and SMB-product audiences 0.30; WhatsApp funnel correctness (wa.me → 972547676000, pre-filled Hebrew intake, opens on mobile) 0.25; Hebrew-first RTL quality + $0 Vercel-free deploy 0.15.

### Phase 3 — Core value

**A4. Face/eye/smile scoring — stage 4 (`faces.py`)** (M). *Track A.* Depends: A3.
- Goal: per-frame face-quality (eyes-open, smile, face-count) + emit face boxes for composition; detect whole-clip no-faces.
- Outputs: `perfectmoment/faces.py` (MediaPipe Tasks FaceLandmarker, `output_face_blendshapes=True`; `open_eyes=1-max(eyeBlinkL,eyeBlinkR)`, `smile=mean(mouthSmileL,mouthSmileR)`, aggregate across faces; no-faces flag → `--no-faces` path, AC-15).
- Success: closed-eyes frames score low, open-eyes+smile high; a face-free clip triggers the no-faces fallback.
- Subtasks: model load; blendshape extraction; per-face→per-frame aggregate; face-box emit; no-faces detection.
- **Blocker:** MediaPipe API churn (pitfall #3 + 2026 note). **Resolution:** re-verify Tasks package/task names before coding; target FaceLandmarker, not legacy Solutions.
- **Verify (MED → Single judge, threshold 4.0):** rubric on `faces.py`. Correct current Tasks FaceLandmarker API (not legacy Solutions) + blendshape math (`open_eyes=1-max(blinkL,blinkR)`, `smile=mean(smileL,smileR)`) 0.35; whole-clip no-faces detection correctly triggers `--no-faces` fallback (AC-15) 0.30; per-face→per-frame aggregation + face-box emit for A6 composition 0.20; determinism (no RNG) 0.15.

**A5. Aesthetic scoring — stage 5 (`aesthetics.py`)** (M). *Track A.* Depends: A4. **HIGH-RISK.**
- Goal: composition-aware aesthetic score on survivors ONLY (the cascade bottleneck).
- Outputs: `perfectmoment/aesthetics.py` (pyiqa NIMA, `device='cpu'`, run only on stage 3+4 survivors).
- Success: returns a 1–10 aesthetic per survivor; runs only on survivors (verified by count); measured cost feeds A7/A8 timing.
- Subtasks: pyiqa init CPU; NIMA metric; survivors-only guard; MobileNet-backbone option for throughput.
- **Risk:** owns BOTH AC-9 timing and AC-13 quality. **Mitigation:** MobileNet backbone; hard survivors-only; wall-clock measured in A8.
- **Verify (HIGH → Panel, 3 judges, threshold 4.0):** rubric on `aesthetics.py` — this owns both the timing budget and the quality lever. Hard survivors-only guard (NIMA never runs on dropped frames — bounds AC-9 cost) 0.30; CPU-only correctness (`device='cpu'`, no CUDA path) 0.20; timing-vs-quality tension handled (MobileNet-backbone option wired so throughput can trade against aesthetic fidelity) 0.25; NIMA score validity + range (1–10 composition-aware, feeds A6 compose) 0.15; determinism 0.10.

**A6. Dedupe/rank + composition sub-score — stage 6 (`rank.py`)** (M). *Track A.* Depends: A4, A5.
- Goal: turn sub-scores into a diverse ranked list; compute the composition sub-score here.
- Outputs: `perfectmoment/rank.py` (composition = face size/centering + rule-of-thirds distance, from A4 boxes; `final = 0.3*blur_norm + 0.4*face_quality + 0.3*aesthetic_norm`, product-lane weight profile; `imagehash.phash` hamming ≤6 dedupe, pitfall #7).
- Success: top-N are not near-duplicate burst neighbors; every candidate carries all sub-scores incl. composition (AC-11 groundwork).
- Subtasks: composition metric; normalization; weighted compose (both weight profiles); phash dedupe.
- **Verify (MED → Single judge, threshold 4.0):** rubric on `rank.py`. Weighted-compose math correct for both profiles (`0.3*blur+0.4*face+0.3*aesthetic` portrait; product-lane shift to blur+aesthetic) 0.30; every candidate carries ALL sub-scores incl. composition (AC-11 groundwork) 0.30; phash dedupe (hamming ≤6) removes burst-neighbor near-duplicates from top-N (pitfall #7) 0.25; composition metric from A4 boxes (face size/centering + rule-of-thirds) sound 0.15.

**A7. CLI + manifest output — stage 7 (`__main__.py`, `pipeline.py`, `output.py`)** (M). *Track A.* Depends: A2–A6.
- Goal: wire the cascade into a deterministic CLI that writes ranked full-res stills + explainable manifest, honoring the graceful-degrade contract.
- Outputs: `__main__.py` (argparse: `--top-n`, `--min-score`, `--fps`, `--no-faces`, `--out` default `./perfect-moment-out`); `pipeline.py` (cascade + timing/memory guards, AC-16); `output.py` (full-res re-extract at timestamps → `<out>/<video-stem>/rank_01..0N.jpg` + `manifest.json` with every sub-score, `quality_bar_met`, per-frame `low_quality`).
- Success: ACs 9–16 become end-to-end testable — deterministic (AC-10), `min(N,avail)` exports (AC-12), AC-14 warn+flag+exit-0, AC-15 no-faces path, AC-16 huge-file guard, AC-11 full sub-scores.
- Subtasks: argparse; stage orchestration; timing/memory guards; full-res re-extract; manifest writer; AC-14 degrade branch; deterministic tiebreak (sort on timestamp, no randomness).
- **Blocker:** nondeterminism creeping in. **Resolution:** no RNG; fixed tiebreak.
- **Verify (MED → Single judge, threshold 4.0):** rubric on the CLI/manifest contract (`__main__.py`, `pipeline.py`, `output.py`). Graceful-degrade contract complete (AC-14 warn+`quality_bar_met:false`+per-frame `low_quality`+exit 0; AC-15 no-faces; AC-16 huge-file guard) 0.35; determinism (no RNG, fixed timestamp tiebreak — AC-10) 0.25; manifest completeness (every sub-score + flags, output to `<out>/<video-stem>/` — AC-11) 0.25; flag/output contract (`--top-n`/`--min-score`/`--fps`/`--no-faces`/`--out`, `min(N,avail)` exports — AC-12) 0.15.

### Phase 4 — Validation

**A8. Test on real videos** (M). *Track A.* Depends: A7.
- Goal: prove the behavioral ACs on real footage on the founder's CPU.
- Outputs: a test-log in `.specs/scratchpad/test-log-a8.md` covering 30s 1080p, 4K/long, dark, and no-face clips.
- Success: AC-9 (<180s), AC-10 (identical twice), AC-12, AC-14, AC-15, AC-16 all pass on real clips.
- Subtasks: gather clip set; run each AC scenario; record timings; log failures.
- **Blocker:** >180s on founder CPU. **Resolution:** MobileNet NIMA, stronger stage-3 pre-filter, cap survivor count.
- **Verify (MED → Single judge, threshold 4.0):** judges the *evidence quality* of `test-log-a8.md`, not code. AC coverage completeness (AC-9 <180s, AC-10 identical-twice, AC-12, AC-14, AC-15, AC-16 each exercised on a real clip) 0.35; measurement rigor (actual wall-clock timings on founder CPU, not asserted) 0.30; realism of clip set (real 30s 1080p + 4K/long + dark + no-face, not synthetic) 0.20; failures logged honestly rather than omitted 0.15.

**A9. Per-source calibration** (M). *Track A.* Depends: A8. **HIGH-RISK.**
- Goal: calibrate thresholds/weights so free-tech scores actually track human "good photo" judgment — the precondition for passing AC-13.
- Outputs: calibrated constants + portrait/product weight profiles in `config.py`; calibration notes.
- Success: on real phone-vs-DSLR-vs-lowlight footage the ranking visibly tracks a human eye; blur threshold set per-source (pitfall #2).
- Subtasks: sample known-sharp/blurry per source; set split points; tune weights; product (`--no-faces`) profile.
- **Risk:** if free scores can't be calibrated to trust, AC-13 fails regardless of B-track. **Mitigation:** explainable manifest pinpoints which sub-score misranks; document ceiling honestly if hit.
- **Verify (HIGH → Panel, 3 judges, threshold 3.7):** rubric on calibrated `config.py` + calibration notes. Threshold deliberately lower — a documented free-tech ceiling is a valid, honest outcome, NOT a failure to hide. Ranking visibly tracks a human eye across phone/DSLR/low-light 0.35; per-source blur thresholds set (not one global constant — pitfall #2) 0.25; both weight profiles (portrait vs product `--no-faces`) calibrated 0.20; honest ceiling documentation where free tech underperforms, with the misranking sub-score named 0.20.

**B3. 10-photographer interviews** (M). *Track B.* Depends: B1. Parallel with A-track core.
- Goal: test Assumptions 1–2 — culling is a top-3 pain with cash attached; video-first is a trend.
- Outputs: interview findings in `.specs/scratchpad/interviews-b3.md` (hours/event culling, WTP per event, capture-mix trend).
- Success: quantified culling-hours + WTP range from ≥6 (target 10) photographers.
- Subtasks: interview script; run interviews; tabulate hours/WTP; note capture-mix trend.
- **Verify (MED → Per-Item, rubric applied per interview, threshold 4.0):** each interview record in `interviews-b3.md` scored. Culling-pain quantified in hours/event (a number, not "a lot") 0.35; WTP captured as a per-event range with currency 0.30 (Assumption 1); capture-mix / video-first trend evidence, not a one-off anecdote 0.20 (Assumption 2); source attributable to a named panel photographer 0.15. Panel-level pass = mean across ≥6 interviews ≥4.0.

**B4. Private beta (1–3 photographers + 1–2 FlowUp SMBs)** (L). *Track B.* Depends: A9, B2, B3. **HIGH-RISK.**
- Goal: exercise both lanes on real client work via manual delivery — no self-serve backend.
- Outputs: delivered stills per beta (Lane A ranked ceremony stills; Lane C product stills bundled with a Make.com listing automation); beta feedback log.
- Success: ≥1 photographer + ≥1 SMB receive real deliverables and give structured feedback; pipeline handles their real clips without crashing.
- Subtasks: recruit 1–3 from panel + 1–2 FlowUp SMBs; intake via landing/WhatsApp; run CLI; hand back; capture feedback.
- **Blocker:** beta clips break the pipeline. **Resolution:** A8/A9 edge coverage + a budgeted hotfix loop. **Risk:** first external exposure of both lanes.
- **Verify (HIGH → Panel, 3 judges, threshold 4.0):** rubric on the beta deliverables + feedback log — first external exposure of both lanes. Both lanes exercised on REAL client work (Lane A ranked ceremony stills; Lane C product stills + Make.com listing automation) 0.30; pipeline handled real beta clips without crashing (graceful-degrade held under the wild) 0.25; deliverable quality good enough to hand a paying-adjacent client 0.25; structured feedback actually captured from ≥1 photographer + ≥1 SMB 0.20.

**B5. AC-13 blind panel validation** (M). *Track B.* Depends: B4, B3. **HIGH-RISK — THE gate.**
- Goal: the panel-mean trust test that decides whether free tech is "good enough."
- Outputs: per-reviewer + panel-mean agreement scores in `.specs/scratchpad/ac13-results.md`.
- Success: **≥4 of 5 agreement on average across the panel** (per-reviewer variance expected).
- Subtasks: prep blind top-5-vs-manual comparisons; run each reviewer; compute panel mean; diagnose misranks via manifest.
- **Risk + gate:** failure → triggers the paid-vision-API gate discussion / honest "lifestyle tool or needs funding" fallback, **never silent shipping** (AC-13). **Mitigation:** AC-11 manifest makes failures diagnosable.
- **Verify (HIGH → Panel, 3 judges, threshold 4.5 — the load-bearing gate):** the 10-reviewer blind panel IS the human bar (≥4/5 mean); this LLM panel judges the *result artifact* `ac13-results.md`. Highest threshold in the plan. Blind-test methodology integrity (top-5-vs-manual genuinely blind, no leakage) 0.30; correct panel-mean computation with per-reviewer variance reported (not cherry-picked) 0.25; every misrank diagnosed to a named sub-score via the AC-11 manifest 0.20; honest routing of any fail to the paid-model gate / lifestyle-tool fallback — NEVER silent shipping 0.25.

### Phase 5 — Polish / GTM

**B6. Pricing test** (S). *Track B.* Depends: B3, B5.
- Goal: validate a WTP band before any paid tier.
- Outputs: pricing memo (test of ~$10–30/mo flat band; component-price vs full-package reconciliation from Research).
- Success: a defensible price point with signal from ≥3 photographers/SMBs.
- Subtasks: present price options; capture reactions; reconcile Israeli component vs package pricing.
- **Verify (MED → Single judge, threshold 4.0):** rubric on the pricing memo. Defensible price point backed by signal from ≥3 photographers/SMBs 0.35; WTP band tested against real B3/B5 reactions, not assumed 0.30; component-price vs full-package reconciliation from Research addressed (not treated as a contradiction) 0.20; stays inside the $0-until-gate model (no paid tier assumed pre-trigger) 0.15.

**B7. Gate review + roadmap decision** (S). *Track B (build+business).* Depends: B5, B6.
- Goal: formal go/no-go against each named Scope gate.
- Outputs: gate-decision record (self-serve backend ← ≥1 paying + repeated manual; paid vision APIs ← revenue + AC-13 ceiling; mobile ← ≥3 asking; global ← retention+WTP).
- Success: each gate marked crossed / not-crossed with the triggering evidence; $0 promise still intact.
- Subtasks: assemble evidence per gate; decide each; record next-phase plan.
- **Verify (MED → Single judge, threshold 4.0):** rubric on the gate-decision record. Every named Scope gate marked crossed/not-crossed with the specific triggering evidence 0.35; $0-promise audit — nothing cost-incurring shipped ahead of its trigger 0.30 (DoD gate-integrity); triggers are measurable/evidence-based, not date- or vibe-based (AC-7) 0.20; next-phase plan follows from the decisions 0.15.

**B8. README + calibration/runbook docs (`README.md`)** (S). *Track A/B.* Depends: A9. Overlaps late.
- Goal: make the tool reproducible by the founder and any beta helper (AC-2 concreteness).
- Outputs: `README.md` (install incl. ffmpeg + CPU torch, run, per-source calibration notes, beta-delivery runbook).
- Success: a clean-machine follow-through installs and runs the pipeline from the README alone.
- Subtasks: install steps; run examples; calibration notes; delivery runbook.
- **Verify (LOW → None):** no LLM judge. The step's own success test — a clean-machine follow-through installs and runs the pipeline from the README alone — is a stronger, mechanical gate than a rubric.

### Critical path
A1 → A2 → A3 → A4 → A5 → A6 → A7 → A8 → A9 → B4 → B5. (B1→B3 runs in parallel and must complete before B5; B2 parallel; B6→B7 tail after B5; B8 overlaps after A9.)

### Risks & mitigations (high-priority flagged)
| Risk | Step | Severity | Mitigation |
|---|---|---|---|
| Panel never reaches 10 → validation impossible | B1 | **HIGH** | FlowUp warm net + FB groups; min viable 6, note variance |
| NIMA blows the 180s budget | A5 | **HIGH** | MobileNet backbone; survivors-only; measure in A8 |
| Free-tech scores can't be calibrated to human taste | A9 | **HIGH** | Explainable manifest diagnoses misranks; document ceiling honestly |
| Beta clip breaks pipeline in front of a real client | B4 | **HIGH** | Edge coverage in A8/A9 + budgeted hotfix loop |
| Panel disagrees with top-N (<4/5) | B5 | **HIGH** | Triggers paid-model gate / lifestyle-tool fallback, not silent ship |
| torch pulls CUDA build | A1 | Med | CPU index-url + assert-CPU guard |
| ffmpeg not on PATH (Windows) | A2 | Med | README install + startup check |
| MediaPipe Tasks API renamed | A4 | Med | Re-verify package/task names pre-coding |
| Nondeterministic ranking | A7 | Med | No RNG; fixed timestamp tiebreak |

### Implementation summary table
| Step | Phase | Track | Estimate | Depends-on |
|---|---|---|---|---|
| A1 Project scaffold | Setup | A | S | — |
| B1 Panel recruitment ⚑ | Setup | B | M | — |
| A2 ffmpeg extraction | Foundational | A | M | A1 |
| A3 Quality filter | Foundational | A | S | A2 |
| B2 Landing + WhatsApp | Foundational | B | M | (copy) |
| A4 Face/eye/smile | Core value | A | M | A3 |
| A5 Aesthetic (NIMA) ⚑ | Core value | A | M | A4 |
| A6 Dedupe/rank + composition | Core value | A | M | A4, A5 |
| A7 CLI + manifest | Core value | A | M | A2–A6 |
| A8 Test on real videos | Validation | A | M | A7 |
| A9 Calibration ⚑ | Validation | A | M | A8 |
| B3 Photographer interviews | Validation | B | M | B1 |
| B4 Private beta ⚑ | Validation | B | L | A9, B2, B3 |
| B5 AC-13 blind panel ⚑ | Validation | B | M | B4, B3 |
| B6 Pricing test | Polish/GTM | B | S | B3, B5 |
| B7 Gate review + roadmap | Polish/GTM | B | S | B5, B6 |
| B8 README + runbook | Polish/GTM | A/B | S | A9 |

⚑ = high-risk step (5 total: B1, A5, A9, B4, B5).

## Verification Summary

Level assigned by criticality: HIGH → Panel (3 judges); MEDIUM → Single judge or Per-Item; LOW → None (mechanical/success-test gate suffices). Thresholds are LLM-judge means on 5.0. High-risk steps (B1, A5, A9, B4, B5) and the AC-13 gate carry the strongest verification. 14 of 17 steps carry an LLM judge; 24 evaluations defined (5 Panel × 3 + 8 Single + 1 Per-Item rubric).

| Step | Level | Threshold | Rationale (one line) |
|---|---|---|---|
| A1 Project scaffold | None | — | Boilerplate; `pip install`/CPU-assert/`--help` is a sufficient mechanical gate. |
| A2 ffmpeg extraction | Single | 4.0 | Determinism + timestamp recoverability + 4K-warn need one judged code pass. |
| A3 Quality filter | None | — | Small deterministic filter; fixed sharp/blur/black test set is the gate. |
| A4 Face/eye/smile | Single | 4.0 | MediaPipe API-churn + no-faces fallback (AC-15) correctness need a judged pass. |
| A5 Aesthetic (NIMA) ⚑ | Panel | 4.0 | Owns BOTH AC-9 timing and AC-13 quality — the cascade bottleneck. |
| A6 Dedupe/rank + composition | Single | 4.0 | Weight math + phash dedupe + AC-11 sub-score completeness. |
| A7 CLI + manifest | Single | 4.0 | Wires ACs 9–16 + graceful-degrade contract + determinism (AC-10). |
| A8 Test on real videos | Single | 4.0 | Judges evidence quality — did the log actually prove each AC on real clips. |
| A9 Calibration ⚑ | Panel | 3.7 | Free-tech-to-human-taste tracking; lower bar — a documented ceiling is a valid honest outcome. |
| B1 Panel recruitment ⚑ | Panel | 3.7 | All validation depends on a real, representative panel; lower bar — recruitment is best-effort (min-6). |
| B2 Landing + WhatsApp | Single | 4.0 | AC-5 FlowUp reuse + dual-lane copy + WhatsApp funnel correctness. |
| B3 Photographer interviews | Per-Item | 4.0 | Assumption 1–2 evidence; each interview judged for quantified hours/WTP. |
| B4 Private beta ⚑ | Panel | 4.0 | First external exposure of both lanes on real client work. |
| B5 AC-13 blind panel ⚑ | Panel | 4.5 | THE gate; highest bar; also audits honest fail-routing (never silent ship). |
| B6 Pricing test | Single | 4.0 | WTP-band defensibility + component-vs-package reconciliation. |
| B7 Gate review + roadmap | Single | 4.0 | Gate integrity / $0-promise audit; triggers measurable not date-based (AC-7). |
| B8 README + runbook | None | — | Clean-machine follow-through is a stronger gate than a rubric. |

⚑ = high-risk step.

### Definition of Done (whole plan)
The plan is done when:
- **Plan-doc ACs (1–8):** the document is self-contained with same-day actions in MVP/GTM/roadmap (AC-1, AC-2); every recommendation is $0 or gated (AC-3); the competitive gap + surviving wedge are stated (AC-4); GTM reuses named FlowUp assets (AC-5); all four positioning roles are named with rationale (AC-6); the roadmap gates are trigger-based not date-based (AC-7); assumptions + tests are listed (AC-8). — satisfied by the existing plan body + this process section.
- **Prototype behavioral ACs (9–16):** verified in A8 on real clips — AC-9 (<180s, 30s 1080p, CPU), AC-10 (deterministic), AC-11 (all sub-scores in manifest), AC-12 (`min(N,avail)` exports), AC-13 (panel mean ≥4/5 in B5, or its failure formally routed to the paid-model gate), AC-14 (dark → warn+flag+exit 0), AC-15 (no-faces fallback), AC-16 (huge-file sampling/downscale).
- **Gate integrity:** B7 records each Scope gate as crossed/not-crossed with evidence, and nothing cost-incurring has shipped ahead of its trigger — the $0/month constraint held end to end.
