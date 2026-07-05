# Scoring Model v2 — Research Report

Research date: 2026-07-05. 33 sources via Explore agent (photographer culling guides,
AI culling tool docs, Google Top Shot patent, academic burst-selection work,
Duchenne-smile/gaze studies).

## Key findings

1. **Pros use a two-pass system, not one weighted sum.** Pass 1: hard-gate
   reject obvious technical failures (closed eyes, motion blur, severe
   exposure). Pass 2: weighted rank the survivors, where expression/moment
   dominates. Aftershoot/Narrative/FilterPixel all structure their tools this way.
2. **"A slightly soft great moment beats a tack-sharp boring one."** Sharpness
   must clear a floor, then gets diminishing returns — expression/moment
   should dominate above that floor. Directly supported by wedding-photographer
   quotes and Google Top Shot's tiered model (functional > objective > subjective,
   subjective wins ties).
3. **Group photos: worst face rules.** One blink ruins the shot. Tools bucket
   closed-eyes separately rather than averaging them away.
4. **Genre-specific weights are the industry standard.** FilterPixel's DeepCull
   explicitly reweights per genre (wedding vs. sports vs. conference); Google
   Top Shot reprioritizes when no faces are present.
5. **Genuine (Duchenne) smiles rate higher than posed ones** — the eye-crinkle
   (orbicularis oculi, i.e. cheek squint blendshapes) alongside a smile is the
   marker, not the smile alone.
6. **Gaze at camera matters strongly for portraits/formal group shots**;
   averted gaze changes the mood but isn't inherently worse for candids.

## Recommended weight structure (adopted into config.py SCORING dict)

| Factor | Portrait | Group | Landscape |
|---|---|---|---|
| Expression quality | 30% | 25% | — |
| Eye gaze at camera | 25% | (inside eyes term) | — |
| Eyes open (worst-face for group) | (inside expression) | 35% | — |
| Sharpness (floor + diminishing returns) | 20% | 12% | 35% |
| Composition | 15% | 8% | 30% |
| Lighting on face/overall | 10% | — | 20% |
| Group cohesion (gaze alignment) | — | 20% | — |
| Exposure correctness | — | — | 15% |

Hard gates (pass 1, all scenes): eyes closed (portrait <0.35 eyes_open; group
<80% of faces open), severe blur (relative to the clip's own sharpness
distribution, not a fixed constant), severe exposure (existing stage-3 logic,
surfaced as a named reason).

## Key sources
- Narrative Select culling guide: https://narrative.so/blog/what-is-culling-in-photography-a-complete-guide
- Aftershoot culling docs: https://aftershoot.com/blog/understanding-culling-in-photography/
- FilterPixel / DeepCull genre-specific scoring: https://filterpixel.com/what-is-photo-culling , https://www.slrlounge.com/filterpixel-ai-photo-culling-deep-cull/
- Google Top Shot patent (US10671895): https://image-ppubs.uspto.com/dirsearch-public/print/downloadPdf/10671895
- Google Top Shot tiered-priority writeup: https://medium.com/decodein/google-is-using-computational-photography-to-revolutionize-smartphone-cameras-56ba331b3c3d
- NIMA paper/blog: https://research.google/blog/introducing-nima-neural-image-assessment/
- Duchenne smile research: https://www.scienceofpeople.com/genuine-smile/
- Gaze-in-portraiture research: https://www.sciencedirect.com/science/article/abs/pii/S027826261730221X
- Group photo aesthetic assessment (academic): https://arxiv.org/pdf/2002.01096
- Burst image quality assessment (academic): https://arxiv.org/pdf/2511.07958

## Implementation note (deviation from literal plan wording)
The plan said "new signal in quality.py" for face-region lighting. In the
actual pipeline, quality.py (stage 3) runs BEFORE face detection (stage 4),
so it has no face boxes to measure a face region against. Face-region
lighting is implemented in faces.py instead (stage 4), where face boxes are
already available — same deliverable, correct pipeline order.
