from pathlib import Path

from perfectmoment import extract


def test_probe_1080p_no_warning(video_1080p_10s):
    probe = extract.probe_video(video_1080p_10s)
    assert probe.width == 1920
    assert probe.height == 1080
    assert probe.duration_seconds == 10.0
    assert probe.warn_large_or_long is False


def test_probe_4k_triggers_warning(video_4k):
    probe = extract.probe_video(video_4k)
    assert probe.warn_large_or_long is True
    assert "3840" in probe.warn_reason


def test_probe_missing_file_raises(tmp_path):
    missing = tmp_path / "does_not_exist.mp4"
    try:
        extract.probe_video(missing)
        assert False, "expected ProbeError"
    except extract.ProbeError:
        pass


def test_sample_frames_count_and_timestamps(video_1080p_10s, tmp_path):
    out_dir = tmp_path / "frames"
    frames = extract.sample_frames(video_1080p_10s, out_dir, fps=2)
    assert len(frames) == 20  # 10s @ 2fps
    assert frames[0].timestamp_seconds == 0.0
    assert frames[-1].timestamp_seconds == 9.5


def test_sample_frames_downscales(video_1080p_10s, tmp_path):
    from PIL import Image

    out_dir = tmp_path / "frames"
    frames = extract.sample_frames(video_1080p_10s, out_dir, fps=2, long_edge=1280)
    with Image.open(frames[0].path) as img:
        assert img.size == (1280, 720)


def test_sample_frames_deterministic(video_1080p_10s, tmp_path):
    import hashlib

    def hashes(out_dir):
        frames = extract.sample_frames(video_1080p_10s, out_dir, fps=2)
        return [hashlib.md5(f.path.read_bytes()).hexdigest() for f in frames]

    run1 = hashes(tmp_path / "run1")
    run2 = hashes(tmp_path / "run2")
    assert run1 == run2
