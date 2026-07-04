# Business Analysis Scratchpad — The Perfect Moment (business-2c)

Analyst: sdd:business-analyst. Date: 2026-07-03. Task: refine business requirements for the startup plan feature.

## 1. What is the product, honestly

Core capability: given a video, automatically surface the few frames a human would have picked — sharp, eyes open, good expression, decent composition — and rank them. That's the atom. Everything else (consumer app, B2B tool, SMB add-on) is a delivery wrapper around that atom.

The naive framing ("turn phone footage into a killer photo") is a **consumer feature**, not a **business**. It's exactly what Google Photos Top Shot and Apple's Live Photo key-frame already do, for free, on-device, at the moment of capture. If the wedge is "consumer picks best selfie frame," we lose — distribution and default-position beat us before we start.

## 2. The "Google Photos already does this" problem — where the wedge actually survives

Google/Apple win at: single short Live Photo / burst, one subject, casual, at capture time, one platform's walled garden. They are WEAK at:
- **Volume culling of professional footage.** A wedding photographer/videographer shoots hundreds of GB. Google Photos won't rank the best 5 frames out of a 4K ceremony clip and hand them back as deliverable stills. Nobody ranks *across a whole shoot* against *client-defined* criteria (this couple, these key people).
- **Extracting stills from video-first workflows.** More events are shot video-first (gimbals, mirrorless hybrid). "I have 40 min of 4K, give me 30 print-worthy stills of the key moments" is an unserved job.
- **B2B / batch / API.** Google's is a consumer convenience, not a tool you can drop into a studio pipeline or a Make.com automation.
- **Hebrew-first + Israeli SMB relationship channel** — irrelevant to Google, but exactly where the founder already has distribution (FlowUp).

### Wedge candidates evaluated
- **(A) Photographer/videographer culling B2B** — strongest defensible wedge. Real pain (culling is hours of unpaid labor), real budget (₪5–15k/event), founder has a channel to reach them in Israel. Video→stills is genuinely unserved. **Chosen beachhead.**
- **(B) Event "AI second shooter"** — aspirational, same buyer as (A) but bigger promise; treat as the *narrative expansion* of (A), not the MVP.
- **(C) SMB product-photo from video, tied to FlowUp** — excellent *distribution* wedge (founder's warm list of Israeli small businesses), lower technical bar (product shots = no eyes/expression, just sharpness/composition/framing), natural cross-sell. **Chosen as second lane / fastest cash.**
- **(D) Hebrew-first consumer app** — worst wedge (competes head-on with free defaults, needs paid CAC the founder can't fund). Explicitly deprioritized; only revisit as a top-of-funnel freemium lead magnet, never as the business.

**Decision:** Beachhead = (A) photographer video-cull, with (C) SMB-via-FlowUp as the parallel cash-generating lane that reuses the same engine. (B) is the vision. (D) is at most a free viral wrapper.

### "Why now"
- Video-first capture is now the default even at events (mirrorless hybrids, gimbals, phones shoot 4K/60).
- Free/open CV + face/landmark models (OpenCV, MediaPipe) are good enough for a scoring pipeline at $0.
- Founder already has the exact adjacent skills (FFmpeg frame extraction, Python, Hebrew GTM, a warm SMB channel via FlowUp). The build cost is near-zero and the channel already exists — the window is "cheap to test before someone bundles it."

## 3. Scope reasoning

Hard constraints: $0/month, solo founder, Python + FFmpeg + OpenCV/MediaPipe, Windows dev machine, no paid vision APIs, no cloud compute bills.

**In-scope MVP** must be provable on the founder's own machine and demo-able to a photographer in a room:
- CLI pipeline: input video → FFmpeg frame sampling → per-frame classical CV scoring → ranked top-N stills exported as JPEGs + a scores manifest (JSON/CSV).
- Scoring signals achievable free: Laplacian-variance blur/sharpness, exposure/brightness sanity, face detection (OpenCV Haar / MediaPipe), eyes-open heuristic (eye-aspect-ratio from landmarks), simple composition proxy (face size/centering, rule-of-thirds distance).
- Config for N and for "who matters" is out of MVP-core except as a stretch; MVP ranks generic "best human frames."
- One Hebrew-first landing page + WhatsApp funnel reusing FlowUp playbook (static, Vercel free tier).
- Manual/private beta delivery (founder runs the CLI for a beta photographer, hands back stills) — no self-serve upload infra needed to validate.

**Out-of-scope for MVP (with unlock gates):**
- Mobile apps → gate: ≥3 paying users asking for on-the-go use.
- Realtime / at-capture → gate: not until there's a hardware/SDK partner; never a $0 concern.
- Paid vision APIs (aesthetic scoring, face-recognition of specific people, emotion) → gate: only after paid revenue covers per-call cost with positive unit economics AND a classical-CV ceiling is demonstrably hit.
- Self-serve web upload + processing backend → gate: ≥1 paying customer + repeated manual delivery proving demand; even then start on free tier limits.
- Global/multi-language GTM → gate: after Israel beachhead shows retention/willingness-to-pay.
- Video highlight reels / editing → out; different product.

The gate mechanism keeps the $0 promise honest: nothing that costs money ships until a named revenue or validated-demand milestone is crossed.

## 4. Acceptance criteria design

Two targets, per the task:
- **The plan document** (deliverable = the .feature.md / eventual plan doc): self-contained, same-day-actionable, concrete MVP, respects $0, honest competitive wedge, reuses FlowUp.
- **The MVP prototype** (what the plan tells the founder to build): testable pipeline behavior with numeric thresholds so "done" is unambiguous.

Chose measurable numbers the founder can actually hit on a Windows CPU:
- Runtime target: 30s 1080p clip → top-5 in under ~3 min on CPU (sampling ~2 fps, not every frame; classical CV is cheap). Gives headroom; can tighten later.
- Determinism: same input + same config → same ranking (no randomness in scoring) — important for trust/demo.
- Graceful degradation on the three known error inputs (dark, no faces, huge file) rather than crashing.

Given/When/Then used where the condition is non-trivial (error inputs, cross-sell), plain assertions for document properties.

## 5. Scenarios

- Primary A: founder demos photographer cull (video → ranked stills, "this saved you 2 hours").
- Primary C: SMB product-photo cross-sell via FlowUp (existing lead sends a 20s phone video of a product → clean catalog stills → tie to a Make.com listing automation).
- Error: dark/underexposed video (no usable frames) → tool reports "no frames met quality bar," returns best-available flagged, doesn't crash.
- Error: no faces (landscape/product) → falls back to sharpness+composition-only scoring instead of failing.
- Error: huge/long 4K file → sampling + resolution downscale for scoring keeps it within memory/time, warns and proceeds.
- FlowUp cross-sell scenario documented explicitly (shared engine, warm channel, bundled offer).

## 6. Billion-dollar vs lifestyle — honest read

Lifestyle outcome (likely default): a $0-cost tool that earns the founder consulting-style income culling for a handful of Israeli photographers + an SMB add-on to FlowUp. Real money, not venture-scale.

For it to be huge, ALL of these must become true (each is an assumption to validate, not a given):
1. **Culling is a top-3 pain with cash attached** — validate: 10 photographer interviews, measure hours/event spent culling and willingness to pay per event.
2. **Video-first stills is a growing, not niche, workflow** — validate: survey capture mix; look for the trend line, not a one-off.
3. **Classical-CV quality is "good enough" that pros trust the top-N** — validate: blind test — does the photographer agree with 4/5 of the tool's picks? If not, the whole thesis wobbles (and the fix costs money = paid models = kills $0 edge).
4. **A wedge exists that Google/Apple structurally won't enter** (B2B batch/API, pro deliverable, relationship channel) — validate: confirm no incumbent ships video→ranked-deliverable-stills for pros.
5. **It generalizes beyond events** (stock/e-com/media asset libraries all have the same "find the best frame at scale" problem) — the TAM that makes it a company, not a freelance tool. Validate later, only after beachhead.

If (3) fails on free tech, the honest conclusion is: lifestyle tool, or needs funding for paid models — state that plainly in the plan rather than hand-waving.

## 7. Structure to write into task file
- Rewrite ## Description (product, who, why now, surviving wedge).
- Add ## Scope (In / Out + Unlock Gates table).
- Replace ## Acceptance Criteria (draft) with numbered testable AC — plan doc AC + MVP prototype AC (G/W/T where complex).
- Add ## User Scenarios (primary x2, errors x3, cross-sell).
- Add ## Key Assumptions & Validation (the 5 above + method).
