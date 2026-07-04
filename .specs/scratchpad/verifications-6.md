# Verifications — The Perfect Moment (QA pass 6)

QA engineer: sdd:qa-engineer. Date: 2026-07-04.
Companion to: task file `perfect-moment-startup-plan.feature.md`, decomposition-4.md.

## 0. Approach

LLM-as-Judge verification added to each Implementation-Process step (A1–A9, B1–B8).
Verification level chosen by criticality:
- HIGH → **Panel** (multi-judge, independent scores averaged) — the load-bearing / high-risk artifacts.
- MEDIUM → **Single judge** (one rubric pass) or **Per-Item** (rubric applied to each artifact in a set).
- LOW → **None** (stated explicitly — mechanical/boilerplate, cheaply human-checkable, no judgment).

Rubrics are artifact-specific (code module ≠ interview findings ≠ landing page ≠ blind-panel results),
3–5 weighted criteria summing to 1.0, threshold typically 4.0/5.0. AC-13 gate (B5) is the
load-bearing gate → highest threshold 4.5. Experimental/calibration steps (A9) → lower 3.7 (we expect
a ceiling and want the judge to flag it, not hard-fail the plan). B1 calibration-of-recruitment → 3.7.

## 1. Per-step criticality + level rationale

| Step | Crit | Artifact | Level | Why |
|---|---|---|---|---|
| A1 | LOW | package scaffold | None | Boilerplate; `pip install` + `--help` + CPU-assert are the real check, not judgment. |
| A2 | MED | extract.py code | Single | Determinism + timestamp recoverability matter but single-pass code review suffices. |
| A3 | LOW | quality.py filter | None | Small, deterministic; verified by fixed sharp/blur test set in-step. |
| A4 | MED | faces.py code | Single | MediaPipe API-churn risk + no-faces fallback correctness need a judged pass. |
| A5 | HIGH | aesthetics.py | Panel | Owns BOTH AC-9 timing and AC-13 quality; the cascade bottleneck — flagged high-risk. |
| A6 | MED | rank.py compose | Single | Weight math + phash dedupe + AC-11 sub-score completeness; single judge. |
| A7 | MED | CLI/manifest | Single | Wires ACs 9–16; graceful-degrade contract. Behavioral proof is A8, so judge = code-contract. |
| A8 | MED | test-log | Single | Evidence-quality judge: did the log actually prove each AC on real clips. |
| A9 | HIGH | calibration | Panel | Flagged high-risk; free-tech-to-human-taste tracking is the precondition for AC-13. Low threshold — expect a possible ceiling. |
| B1 | HIGH | panel roster | Panel | Flagged high-risk; all validation depends on this panel being real + representative. Lower threshold (recruitment is best-effort). |
| B2 | MED | landing page | Single | AC-5 reuse + dual-lane copy + WhatsApp funnel correctness; single design/CX judge. |
| B3 | MED | interview findings | Per-Item | Assumption 1–2 evidence; each interview judged for quantified hours/WTP quality. |
| B4 | HIGH | beta deliverables | Panel | Flagged high-risk; first external exposure of both lanes on real client work. |
| B5 | HIGH | AC-13 blind results | Panel | THE gate; highest threshold. The panel IS the verification mechanism (10 reviewers). |
| B6 | MED | pricing memo | Single | WTP band defensibility; single judge on evidence + reconciliation. |
| B7 | MED | gate-decision record | Single | Gate integrity / $0-promise audit; single judge on evidence-per-gate. |
| B8 | LOW | README/runbook | None | Verified by clean-machine follow-through (the step's own success test), not judgment. |

Steps with verification: 12 (A2, A4, A5, A6, A7, A8, A9, B1, B2, B3, B4, B5, B6, B7) — recount below.
None: A1, A3, B8 (3 steps).

Recount of verified steps: A2, A4, A5, A6, A7, A8, A9, B1, B2, B3, B4, B5, B6, B7 = **14 steps with verification**; 3 with None (A1, A3, B8). 14+3 = 17. ✓

## 2. Evaluation count

Panel steps run multiple independent judges. Assumptions:
- A5 Panel = 3 judges. A9 Panel = 3 judges. B1 Panel = 3 judges. B4 Panel = 3 judges. B5 Panel = 3 judges (the reviewer panel-mean is separately the AC-13 human bar; the LLM panel judges the *result artifact*).
- Single = 1 evaluation each: A2, A4, A6, A7, A8, B2, B6, B7 = 8.
- Per-Item: B3 = 1 rubric applied per interview; count the rubric definition as 1 defined evaluation (applied N times at runtime).

Defined evaluations = 5 Panel steps × 3 judges (15) + 8 Single (8) + 1 Per-Item rubric (1) = **24 evaluations defined**.

## 3. Breakdown
- Panel: 5 (A5, A9, B1, B4, B5)
- Single: 8 (A2, A4, A6, A7, A8, B2, B6, B7)
- Per-Item: 1 (B3)
- None: 3 (A1, A3, B8)
Total steps: 17 ✓ (14 verified + 3 None).

## 4. Rubric design notes
- Code modules (A2/A4/A5/A6/A7): criteria weight correctness/contract-adherence highest, then determinism, then maintainability. AC references embedded.
- A5 panel adds an explicit timing-vs-quality tension criterion (it owns both).
- A8 judges evidence quality, not code.
- B1 judges roster realness/representativeness/size; low threshold 3.7 (recruitment is best-effort, min-6 fallback).
- B3 per-interview judges quantification of hours + WTP.
- B4 panel judges deliverable quality across both lanes + no-crash on real clips.
- B5 highest threshold 4.5 — the load-bearing gate; also judges honest routing of a fail to the paid-model gate (never silent ship).
- A9 threshold 3.7 — deliberately lower; a documented ceiling is a valid outcome, not a failure to hide.
