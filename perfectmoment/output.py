"""Stage 7: full-res re-extract of chosen frames + JPEG/manifest writer.

Chosen frames were scored at scoring resolution (config.SCORING_LONG_EDGE, e.g.
1280px) for speed; this stage re-extracts them from the ORIGINAL video at full
resolution using their recorded timestamps, so delivered stills aren't
downscaled (AC-11 groundwork: manifest must be explainable, and deliverables
must be print-worthy, not thumbnail-quality).
"""

from __future__ import annotations

import html
import json
import subprocess
from dataclasses import asdict
from pathlib import Path

from perfectmoment.rank import RankedFrame


def _esc(value) -> str:
    """HTML-escape any value injected into the report -- video filenames and
    reason strings are not attacker-controlled today, but a beta photographer's
    filename can legitimately contain &, <, quotes, or Hebrew punctuation."""
    return html.escape(str(value)) if value is not None else ""


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
    stage_timings: dict[str, float] | None = None,
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
        "stage_timings_seconds": stage_timings or {},
        "frames": manifest_frames,
    }

    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path


def write_report(manifest_path: Path) -> Path:
    """Generate report.html -- a self-contained visual contact sheet next to the
    manifest, so a photographer (or the founder during a beta demo) reviews the
    picks visually with their scores and reasons, without opening JSON.

    Reads back the manifest it just wrote (single source of truth -- the report
    can never drift from the manifest). Image tags use relative filenames, so
    the whole output folder can be zipped/sent and the report still works.
    """
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    out_dir = manifest_path.parent

    video_name = _esc(Path(manifest["video"]).name)
    bar_met = manifest["quality_bar_met"]
    bar_note = (
        ""
        if bar_met
        else '<p class="warn">⚠ No frame met the quality bar — these are the best available, flagged low-quality.</p>'
    )

    cards = []
    for f in manifest["frames"]:
        badge = f'<span class="badge gated">GATED: {_esc(f["gate_reason"])}</span>' if f.get("gated") else ""
        low_q = '<span class="badge lowq">low quality</span>' if f.get("low_quality") else ""
        cards.append(f"""
    <div class="card">
      <img src="{_esc(f['output_file'])}" alt="rank {f['rank']}" loading="lazy">
      <div class="meta">
        <div class="rank">#{f['rank']} <span class="score">{f['final']:.3f}</span> {badge}{low_q}</div>
        <div class="reason">{_esc(f['reason'])}</div>
        <div class="subs">scene {_esc(f['scene'])} · t={f['timestamp_seconds']:.1f}s · eyes {f['eyes_open']:.2f} · smile {f['smile']:.2f} · gaze-dev {f['gaze_deviation']:.2f} · comp {f['composition']:.2f} · sharp {f['sharpness']:.0f}</div>
      </div>
    </div>""")

    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>The Perfect Moment — {video_name}</title>
<style>
  body {{ background:#0b0b11; color:#eee; font-family: system-ui, sans-serif; margin:0; padding:24px; }}
  h1 {{ font-size:1.1rem; font-weight:600; margin:0 0 4px; }}
  .sub {{ color:#888; font-size:0.85rem; margin-bottom:20px; }}
  .warn {{ color:#f0c040; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill, minmax(280px, 1fr)); gap:18px; }}
  .card {{ background:#15151d; border:1px solid #2a2a35; border-radius:10px; overflow:hidden; }}
  .card img {{ width:100%; display:block; }}
  .meta {{ padding:12px 14px; }}
  .rank {{ font-weight:700; margin-bottom:6px; }}
  .score {{ color:#29f0e0; }}
  .reason {{ font-size:0.9rem; color:#ccc; margin-bottom:6px; }}
  .subs {{ font-size:0.75rem; color:#777; }}
  .badge {{ font-size:0.7rem; padding:2px 8px; border-radius:999px; margin-inline-start:6px; }}
  .gated {{ background:#5a1f1f; color:#ff9d9d; }}
  .lowq {{ background:#4a3a12; color:#f0c040; }}
</style>
</head>
<body>
<h1>The Perfect Moment — best frames from {video_name}</h1>
<p class="sub">{manifest['exported_count']} frame(s) exported · min_score {manifest['min_score']}</p>
{bar_note}
<div class="grid">{''.join(cards)}
</div>
</body>
</html>
"""
    report_path = out_dir / "report.html"
    report_path.write_text(html_doc, encoding="utf-8")
    return report_path
