# Decomposition — The Perfect Moment (tech-lead pass 4)

Tech lead: sdd:tech-lead. Date: 2026-07-04.
Companion to: architecture-3.md, SKILL.md best-frame-extraction, task file ACs 1–16.

## 0. Judge-3 fixes applied (task file, in place)
1. Folded §4 Data Flow Diagram into §2 (single diagram now under the stage list; §4/§5/§6 renumbered to §4/§5).
2. Added rejected-alternative + rationale to load-bearing decisions §4.4 (NIMA vs BRISQUE vs vendored weights) and §4.5 (fixed-grid 2fps vs scene-change vs I-frame).
3. Inlined the SKILL.md link into the §2 header sentence.
4. Reconciled `--out`: default `./perfect-moment-out/`, run dir `./perfect-moment-out/<video-stem>/`; CLI line, output section, and a new AC-14 output note all agree.
5. Named the composition sub-score module: computed in `rank.py` (stage 6) from stage-4 MediaPipe face boxes — stated in stage 6 text.

## 1. Decomposition philosophy
Two tracks run partly in parallel. Track A (build) is the risk that kills the venture on *tech* (AC-13 trust); Track B (business) is the risk that kills it on *demand/WTP*. They converge at the AC-13 blind panel — the single most load-bearing gate. Order by dependency, not by track: Setup → Foundational → Core value → Validation → Polish/GTM. B-track discovery (interviews, landing) can start Day 1 in parallel with A-track scaffold because neither blocks the other; they only join at beta delivery + AC-13.

Critical path = the chain that must complete for AC-13 to be evaluable: scaffold → extract → quality → faces → aesthetics → rank → CLI/manifest → calibration → beta delivery → AC-13 panel. Everything else (landing page, interviews, pricing test) is parallelizable around it.

## 2. Step-by-step reasoning

### Phase: Setup
- **A1 Project scaffold** (S). Python package skeleton, requirements.txt with CPU-pinned torch, config.py defaults, model fetch script for face_landmarker.task, .gitignore. No dependency. Blocker: torch CUDA-wheel creep (pitfall #6) → resolution: pin `--index-url .../whl/cpu`, assert CPU at import. This unblocks all A-track code.
- **B1 Interview panel recruitment** (M). Recruit the 10 photographers (AC-13/Assumption-1 uses the *same* panel — key constraint, they must be real event photographers, not one reviewer). No code dependency; start Day 1. Blocker: can't reach 10 → resolution: FlowUp warm network + Israeli wedding-photographer FB groups; min viable 6, note variance. HIGH-RISK: entire validation depends on this panel existing.

### Phase: Foundational
- **A2 ffmpeg extraction (extract.py, stages 1–2)** (M). ffprobe plan + downscale-for-scoring + fixed-grid 2fps sampling + timestamp-in-filename for full-res re-extract. Depends A1. Covers AC-16 sampling/downscale groundwork. Blocker: ffmpeg not on PATH on Windows → resolution: document winget/curl install in README (reuse analyze-youtube-video skill pattern).
- **A3 Quality filter (quality.py, stage 3)** (S). Laplacian variance (resize 800px first — pitfall #2) + brightness bounds. Depends A2. Per-source calibration is deferred to A9 (calibration is its own step). 
- **B2 Hebrew landing page + WhatsApp funnel (landing/index.html)** (M). Reuse FlowUp playbook + WhatsApp 972547676000, Vercel free. Depends only on positioning copy (from task doc), not on code. Parallel with A2/A3. AC-5 (reuse named FlowUp assets), AC-1 GTM same-day action.

### Phase: Core value
- **A4 Face/eye/smile scoring (faces.py, stage 4)** (M). MediaPipe Tasks FaceLandmarker blendshapes; open_eyes/smile aggregate; no-faces detection feeding --no-faces. Depends A3. Emits face boxes consumed by A6 composition. Blocker: MediaPipe API churn (pitfall #3, 2026 note) → resolution: re-verify Tasks package/task names before coding; target FaceLandmarker not legacy Solutions.
- **A5 Aesthetic scoring (aesthetics.py, stage 5)** (M). pyiqa NIMA device='cpu', survivors only. Depends A4 (survivor set). HIGH-RISK: this is the throughput bottleneck (AC-9) and the quality lever (AC-13). Mitigation: MobileNet backbone option; enforce survivors-only; measure wall-clock in A7.
- **A6 Dedupe/rank + composition sub-score (rank.py, stage 6)** (M). Composition (face size/centering, rule-of-thirds) from A4 boxes; weighted final; phash dedupe hamming≤6 (pitfall #7). Depends A4+A5. Covers AC-11 sub-scores present.
- **A7 CLI + manifest output (\_\_main\_\_.py, pipeline.py, output.py, stage 7)** (M). argparse (top-n, min-score, fps, no-faces, out); cascade orchestration + timing/memory guards; full-res re-extract; JSON manifest with every sub-score; graceful-degrade contract (AC-14) + no-faces (AC-15) + huge-file guard (AC-16); deterministic (AC-10). Depends A2–A6. This is where ACs 9–16 become testable end-to-end. Blocker: nondeterminism sneaking in → resolution: no randomness, fixed sort tiebreak on timestamp.

### Phase: Validation
- **A8 Test on real videos** (M). Run pipeline on real 30s 1080p + 4K/long + dark + no-face clips; assert AC-9 (<180s), AC-10 (identical twice), AC-12 (min(N,avail)), AC-14/15/16 behaviors. Depends A7. Produces a test-log. Blocker: >180s on founder CPU → resolution: MobileNet NIMA, raise min-score pre-filter aggressiveness, cap survivors.
- **A9 Per-source calibration** (M). Calibrate Laplacian + score weights on real phone-vs-DSLR-vs-lowlight footage (pitfall #2); portrait vs product (--no-faces) weight profiles in config.py. Depends A8 (needs real clips + working pipeline). Gate into B4.
- **B3 10-photographer interview panel** (M). Run the interviews: hours/event culling, WTP per event (Assumption 1/2). Depends B1. Feeds pricing (B6) and confirms pain. Parallel with A-track core.
- **B4 Private beta (1–3 photographers + 1–2 FlowUp SMBs)** (L). Founder runs calibrated CLI on real beta clips, manual delivery (Lane A stills, Lane C product stills bundled w/ Make.com listing automation). Depends A9 + B2 + B3. HIGH-RISK: first real external exposure; both lanes exercised. Blocker: beta clips break pipeline → A8/A9 must have covered edge cases; hotfix loop budgeted.
- **B5 AC-13 blind panel validation** (M). Same 10-panel blind-reviews top-5 vs their manual pick; bar = ≥4/5 mean across panel. Depends B4 + B3. HIGH-RISK + THE decision gate: fail → triggers paid-vision-API gate discussion / honest "lifestyle tool" fallback, NOT silent shipping. Mitigation: explainable manifest (AC-11) makes failures diagnosable (which sub-score misranks).

### Phase: Polish / GTM
- **B6 Pricing test** (S). Test WTP band (~$10–30/mo flat) against B3/B5 signal; component-vs-package price reconciliation from Research. Depends B3+B5. Gate to paid tier.
- **A10/B7 Gate reviews + roadmap decision** (S). Formal review against Scope gates: self-serve backend (≥1 paying + repeated manual), paid vision APIs (revenue + AC-13 ceiling), mobile (≥3 asking), global (retention+WTP). Depends B5+B6. Produces go/no-go on each gate. Ties DoD together.
- **B8 README + calibration/runbook docs (README.md)** (S). Install, run, per-source calibration notes, beta-delivery runbook. Depends A9. AC-2 concreteness support. Can overlap late.

## 3. Critical path (must be serial)
A1 → A2 → A3 → A4 → A5 → A6 → A7 → A8 → A9 → B4 → B5.
(B1→B3 feeds B4/B5 and must finish before B5 but runs in parallel with A2–A9; B2 parallel; B6→B7 tail after B5.)

## 4. High-priority (high-risk) steps — count = 5
- B1 (panel recruitment — validation depends on it existing)
- A5 (NIMA bottleneck: owns both AC-9 timing and AC-13 quality)
- B4 (private beta — first external exposure, both lanes)
- B5 (AC-13 blind panel — THE gate; failure forks the whole venture)
- A7 is elevated but not top-tier; the 5 flagged are B1, A5, B4, B5 + one more:
- A8/A9 timing+calibration risk folded — the 5th high-risk is **A9 calibration** (if free-tech scores can't be calibrated to trust, AC-13 fails regardless of B-track).

Final high-risk set (5): B1, A5, A9, B4, B5.

## 5. Counts
- Steps: **17 total** = A-track 9 (A1–A9) + B-track 8 (B1–B8). The earlier A10/B7 "gate-review" split is collapsed into a single step, **B7**; the vision-narrative doc is not a discrete build step (it lives in the plan body), so it is not counted. Reconciled 1:1 with the task-file Implementation-summary table: A1,A2,A3,A4,A5,A6,A7,A8,A9 + B1,B2,B3,B4,B5,B6,B7,B8 = 9 + 8 = **17**.
- Subtasks: counted in task-file table = 68.
