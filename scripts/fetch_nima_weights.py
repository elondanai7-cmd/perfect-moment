"""Pre-download the pyiqa NIMA aesthetic-scoring model weights.

pyiqa.create_metric() downloads pretrained weights from the network on first
use, exactly like the face landmarker model (see fetch_model.py) -- and just
like that one, the download has no timeout we control. On a slow/stalled
connection this hangs the *first real visitor's request* indefinitely instead
of failing fast (this is what was actually happening in production: the face
model was already fixed via fetch_model.py, but this second, larger download
was still happening lazily on the first request).

Run this once during the build step (see render.yaml) so the weights are
already cached under ~/.cache/torch/hub/ before any request arrives:

    python scripts/fetch_nima_weights.py
"""

import sys

from perfectmoment import config
from perfectmoment.aesthetics import AestheticScorer


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print(f"Downloading/caching NIMA weights ({config.NIMA_BACKBONE})...")
    AestheticScorer(device=config.NIMA_DEVICE, metric_name=config.NIMA_BACKBONE)
    print("Done.")


if __name__ == "__main__":
    main()
