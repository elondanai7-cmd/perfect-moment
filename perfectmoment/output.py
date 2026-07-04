"""Stage 7: full-res re-extract of chosen frames + JPEG/manifest writer.

Chosen frames were scored at scoring resolution (config.SCORING_LONG_EDGE, e.g.
1280px) for speed; this stage re-extracts them from the ORIGINAL video at full
resolution using their recorded timestamps, so delivered stills aren't
downscaled (AC-11 groundwork: manifest must be explainable, and deliverables
must be print-worthy, not thumbnail-quality).
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import asdict
from pathlib import Path

from perfectmoment.rank import RankedFrame


def reextract_full_res(video_path: Path, timestamp_seconds: float, out_path: Path) -> None:
    """Pull a single full-resolution frame from the source video at the given timestamp."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-ss", f"{timestamp_seconds:.3f}",
        "-i", str(video_path),
        "-frames:v", "1",
        "-qscale:v", "2",
        str(out_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Full-res re-extract failed at t={timestamp_seconds}: {result.stderr.strip()}")


def write_outputs(
    video_path: Path,
    ranked_frames: list[RankedFrame],
    out_dir: Path,
    top_n: int,
    quality_bar_met: bool,
    min_score: float,
) -> Path:
    """Re-extract top-N frames at full res, write JPEGs + manifest.json. Returns manifest path.

    Exports exactly min(top_n, len(ranked_frames)) stills (AC-12). Never raises
    on an empty ranked_frames list from an upstream degrade -- that case is the
    caller's responsibility to have already handled via the AC-14 warning path;
    this function just writes whatever it's given.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    selected = ranked_frames[: min(top_n, len(ranked_frames))]

    manifest_frames = []
    for i, frame in enumerate(selected, start=1):
        still_path = out_dir / f"rank_{i:02d}.jpg"
        reextract_full_res(video_path, frame.timestamp_seconds, still_path)

        entry = asdict(frame)
        entry["path"] = str(entry["path"])  # Path -> str for JSON
        entry["output_file"] = still_path.name
        entry["rank"] = i
        manifest_frames.append(entry)

    manifest = {
        "video": str(video_path),
        "quality_bar_met": quality_bar_met,
        "min_score": min_score,
        "requested_top_n": top_n,
        "exported_count": len(selected),
        "frames": manifest_frames,
    }

    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path
