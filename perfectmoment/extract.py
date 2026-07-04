"""Stages 1-2: probe the source video and sample downscaled candidate frames.

Stage 1 (probe): ffprobe reads duration/resolution/rotation, decides whether to
warn about large/long inputs (AC-16 groundwork).

Stage 2 (sample): ffmpeg extracts frames at a fixed grid rate (config.DEFAULT_FPS,
default 2 fps) and downscales them for the scoring cascade. Filenames encode the
timestamp so later stages can re-extract the chosen frames at full resolution.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from perfectmoment import config

# AC-16 thresholds: warn (not fail) above these, so huge/long clips still complete.
WARN_DURATION_SECONDS = 20 * 60  # 20 minutes
WARN_LONG_EDGE_PX = 3840  # 4K


class FFmpegNotFoundError(RuntimeError):
    """Raised when ffmpeg/ffprobe are not on PATH."""


class ProbeError(RuntimeError):
    """Raised when ffprobe fails to read the input video."""


@dataclass(frozen=True)
class VideoProbe:
    duration_seconds: float
    width: int
    height: int
    rotation: int  # degrees, from side_data or tags, 0 if unrotated
    warn_large_or_long: bool
    warn_reason: str | None


@dataclass(frozen=True)
class ExtractedFrame:
    """One sampled candidate frame."""

    path: Path
    timestamp_seconds: float
    index: int


def check_ffmpeg_available() -> None:
    """Startup guard: fail fast with an actionable message if ffmpeg/ffprobe are missing.

    Windows install: `winget install ffmpeg` (or download a full build and add
    the bin/ folder to PATH), matching the pattern used in the
    analyze-youtube-video skill. Restart the terminal after installing.
    """
    missing = [tool for tool in ("ffmpeg", "ffprobe") if shutil.which(tool) is None]
    if missing:
        raise FFmpegNotFoundError(
            f"Required tool(s) not found on PATH: {', '.join(missing)}. "
            "Install with `winget install ffmpeg` (Windows) and restart your terminal, "
            "or download a full ffmpeg build and add its bin/ folder to PATH."
        )


def _rotation_from_streams(streams: list[dict]) -> int:
    """Extract rotation in degrees from stream side_data or tags, else 0."""
    for stream in streams:
        if stream.get("codec_type") != "video":
            continue
        for side_data in stream.get("side_data_list", []):
            if "rotation" in side_data:
                return int(side_data["rotation"]) % 360
        tag_rotate = stream.get("tags", {}).get("rotate")
        if tag_rotate is not None:
            return int(tag_rotate) % 360
    return 0


def probe_video(video_path: Path) -> VideoProbe:
    """Stage 1: read duration/resolution/rotation via ffprobe; flag AC-16 warnings."""
    check_ffmpeg_available()
    if not video_path.exists():
        raise ProbeError(f"Video file not found: {video_path}")

    cmd = [
        "ffprobe",
        "-v", "error",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(video_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise ProbeError(f"ffprobe failed on {video_path}: {result.stderr.strip()}")

    data = json.loads(result.stdout)
    video_streams = [s for s in data.get("streams", []) if s.get("codec_type") == "video"]
    if not video_streams:
        raise ProbeError(f"No video stream found in {video_path}")

    stream = video_streams[0]
    width = int(stream["width"])
    height = int(stream["height"])
    duration = float(data.get("format", {}).get("duration") or stream.get("duration") or 0.0)
    rotation = _rotation_from_streams(data.get("streams", []))

    long_edge = max(width, height)
    warn_reasons = []
    if duration >= WARN_DURATION_SECONDS:
        warn_reasons.append(f"duration {duration:.0f}s exceeds {WARN_DURATION_SECONDS}s")
    if long_edge >= WARN_LONG_EDGE_PX:
        warn_reasons.append(f"resolution {width}x{height} exceeds {WARN_LONG_EDGE_PX}px long edge")

    return VideoProbe(
        duration_seconds=duration,
        width=width,
        height=height,
        rotation=rotation,
        warn_large_or_long=bool(warn_reasons),
        warn_reason="; ".join(warn_reasons) if warn_reasons else None,
    )


def sample_frames(
    video_path: Path,
    out_dir: Path,
    fps: float = config.DEFAULT_FPS,
    long_edge: int = config.SCORING_LONG_EDGE,
) -> list[ExtractedFrame]:
    """Stage 2: deterministic fixed-grid ffmpeg sampling for the scoring cascade.

    Uses `fps=<fps>` (not scene-change/keyframe selection) so the candidate count,
    and therefore the downstream NIMA cost, is bounded and reproducible (AC-9, AC-10).
    Frames are downscaled to `long_edge` for scoring only; step A7/output.py
    re-extracts chosen frames at full resolution using the recorded timestamps.
    """
    check_ffmpeg_available()
    out_dir.mkdir(parents=True, exist_ok=True)

    pattern = str(out_dir / "frame_%05d.jpg")
    vf = f"fps={fps},scale='min({long_edge},iw)':-2"
    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(video_path),
        "-vf", vf,
        "-qscale:v", "2",
        pattern,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise ProbeError(f"ffmpeg sampling failed on {video_path}: {result.stderr.strip()}")

    frames: list[ExtractedFrame] = []
    for frame_path in sorted(out_dir.glob("frame_*.jpg")):
        index = int(frame_path.stem.split("_")[1])
        # Fixed-grid sampling: frame N corresponds to timestamp (N-1)/fps seconds.
        timestamp = (index - 1) / fps
        frames.append(ExtractedFrame(path=frame_path, timestamp_seconds=timestamp, index=index))

    return frames
