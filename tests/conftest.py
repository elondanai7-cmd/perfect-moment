"""Shared pytest fixtures: synthetic test videos/images generated via ffmpeg,
plus a session-cached real portrait photo for face-detection tests.

No binary fixtures are committed to git -- everything is generated on demand
into a session-scoped tmp directory, matching how these modules were
originally verified by hand during A1-A8.
"""

from __future__ import annotations

import subprocess
import urllib.request
from pathlib import Path

import pytest

PORTRAIT_URL = "https://storage.googleapis.com/mediapipe-assets/portrait.jpg"


def _run_ffmpeg(args: list[str]) -> None:
    result = subprocess.run(["ffmpeg", "-y", *args], capture_output=True, text=True)
    if result.returncode != 0:
        pytest.fail(f"ffmpeg fixture generation failed: {result.stderr.strip()}")


@pytest.fixture(scope="session")
def fixtures_dir(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("pm_fixtures")


@pytest.fixture(scope="session")
def video_1080p_10s(fixtures_dir: Path) -> Path:
    """10s, 1920x1080, 30fps synthetic test pattern -- no faces, no motion blur."""
    path = fixtures_dir / "sample_1080p_10s.mp4"
    _run_ffmpeg([
        "-f", "lavfi", "-i", "testsrc=duration=10:size=1920x1080:rate=30",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path),
    ])
    return path


@pytest.fixture(scope="session")
def video_4k(fixtures_dir: Path) -> Path:
    """Short 4K clip, used to exercise the AC-16 large/long warning path."""
    path = fixtures_dir / "sample_4k.mp4"
    _run_ffmpeg([
        "-f", "lavfi", "-i", "testsrc=duration=2:size=3840x2160:rate=15",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path),
    ])
    return path


@pytest.fixture(scope="session")
def video_black_10s(fixtures_dir: Path) -> Path:
    """Fully black clip -- every frame should fail the stage-3 hard quality filter,
    exercising the AC-14 all-rejected fallback path (the bug found in A8)."""
    path = fixtures_dir / "sample_black_10s.mp4"
    _run_ffmpeg([
        "-f", "lavfi", "-i", "color=c=black:size=1920x1080:duration=10:rate=30",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path),
    ])
    return path


@pytest.fixture(scope="session")
def sharp_frame(fixtures_dir: Path) -> Path:
    path = fixtures_dir / "sharp.jpg"
    _run_ffmpeg(["-f", "lavfi", "-i", "testsrc=duration=1:size=1280x720:rate=1", "-frames:v", "1", str(path)])
    return path


@pytest.fixture(scope="session")
def blurry_frame(fixtures_dir: Path, sharp_frame: Path) -> Path:
    path = fixtures_dir / "blurry.jpg"
    _run_ffmpeg(["-i", str(sharp_frame), "-vf", "gblur=sigma=25", str(path)])
    return path


@pytest.fixture(scope="session")
def black_frame(fixtures_dir: Path) -> Path:
    path = fixtures_dir / "black.jpg"
    _run_ffmpeg(["-f", "lavfi", "-i", "color=c=black:size=1280x720", "-frames:v", "1", str(path)])
    return path


@pytest.fixture(scope="session")
def white_frame(fixtures_dir: Path) -> Path:
    path = fixtures_dir / "white.jpg"
    _run_ffmpeg(["-f", "lavfi", "-i", "color=c=white:size=1280x720", "-frames:v", "1", str(path)])
    return path


@pytest.fixture(scope="session")
def aesthetic_scorer():
    """Session-scoped: NIMA model load takes ~2.5s, must not repeat per test."""
    from perfectmoment.aesthetics import AestheticScorer

    return AestheticScorer()


@pytest.fixture(scope="session")
def portrait_photo(fixtures_dir: Path) -> Path:
    """MediaPipe's own official test portrait -- the only real face fixture we use,
    downloaded once per test session and skipped gracefully if offline."""
    path = fixtures_dir / "portrait.jpg"
    if not path.exists():
        try:
            urllib.request.urlretrieve(PORTRAIT_URL, path)
        except Exception as exc:  # noqa: BLE001 - network fixture, skip don't fail
            pytest.skip(f"portrait fixture unavailable (no network?): {exc}")
    return path
