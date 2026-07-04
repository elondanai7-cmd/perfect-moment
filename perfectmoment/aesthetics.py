"""Stage 5: aesthetic scoring via pyiqa NIMA — the cascade bottleneck.

Runs ONLY on survivors of stages 3+4 (quality.py + faces.py), never on the full
candidate set, because this is by far the most expensive stage per frame
(a CNN forward pass vs. microseconds for Laplacian variance).

IMPORTANT — deviations from the original plan, found during implementation
(2026-07-04, measured on the founder's CPU, 8 torch threads):

1. pyiqa's NIMA does NOT ship a MobileNet-backbone variant (only 'nima'
   [InceptionV2], 'nima-vgg16-ava', 'nima-koniq', 'nima-spaq' exist). The
   plan's "MobileNet backbone for throughput" mitigation does not exist as an
   off-the-shelf option.
2. Real measured cost is ~640ms/frame (InceptionV2, CPU) — about 4x higher
   than the plan's ~150ms/frame estimate. Worst case (all ~60 sampled frames
   survive stages 3+4): 640ms x 60 = ~38s, still comfortably inside the 180s
   AC-9 budget (~4.7x margin, not the originally claimed ~7-10x). Realistic
   case (~30 survivors): ~19s.

If A8/A9 testing on real clips shows the survivor count regularly pushes
close to the budget, the real mitigation is tightening the stage-3 quality
bar (fewer frames reach this stage) or lowering --fps, not a lighter backbone
swap (none exists).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pyiqa
import torch

from perfectmoment import config


@dataclass(frozen=True)
class AestheticScore:
    path: Path
    aesthetic: float  # NIMA raw score, roughly 1-10, higher = better


class AestheticScorer:
    """Wraps a pyiqa NIMA metric instance so the (slow) model load happens once."""

    def __init__(self, device: str = config.NIMA_DEVICE, metric_name: str = config.NIMA_BACKBONE):
        self._metric = pyiqa.create_metric(metric_name, device=device)

    def score(self, image_path: Path) -> AestheticScore:
        with torch.no_grad():
            raw = self._metric(str(image_path))
        value = float(raw.item() if hasattr(raw, "item") else raw)
        return AestheticScore(path=image_path, aesthetic=value)

    def score_many(self, image_paths: list[Path]) -> list[AestheticScore]:
        return [self.score(p) for p in image_paths]


def score_survivors(
    survivor_paths: list[Path],
    device: str = config.NIMA_DEVICE,
) -> list[AestheticScore]:
    """Convenience entrypoint: score a list of stage-3/4 survivors with a fresh scorer.

    For repeated calls within one pipeline run, prefer instantiating
    AestheticScorer once and reusing it (model load is the expensive part).
    """
    scorer = AestheticScorer(device=device)
    return scorer.score_many(survivor_paths)
