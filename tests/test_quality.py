from perfectmoment import quality


def test_sharp_frame_passes(sharp_frame):
    score = quality.score_frame(sharp_frame)
    assert score.passed is True
    assert score.reject_reason is None


def test_blurry_frame_rejected_as_blurry(blurry_frame):
    score = quality.score_frame(blurry_frame)
    assert score.passed is False
    assert "blurry" in score.reject_reason


def test_black_frame_rejected_as_underexposed(black_frame):
    score = quality.score_frame(black_frame)
    assert score.passed is False
    assert "underexposed" in score.reject_reason


def test_white_frame_rejected_as_blown_out(white_frame):
    score = quality.score_frame(white_frame)
    assert score.passed is False
    assert "blown out" in score.reject_reason


def test_filter_frames_splits_survivors_and_rejected(sharp_frame, blurry_frame, black_frame, white_frame):
    survivors, rejected = quality.filter_frames([sharp_frame, blurry_frame, black_frame, white_frame])
    assert [s.path for s in survivors] == [sharp_frame]
    assert len(rejected) == 3


def test_scale_consistency(sharp_frame, tmp_path):
    """Laplacian variance must be comparable across differently-sized copies
    of the same image (SKILL.md pitfall #2) -- regression test for the fix
    verified by hand during A3."""
    import subprocess

    small = tmp_path / "small.jpg"
    large = tmp_path / "large.jpg"
    subprocess.run(["ffmpeg", "-y", "-i", str(sharp_frame), "-vf", "scale=640:360", str(small)], capture_output=True)
    subprocess.run(["ffmpeg", "-y", "-i", str(sharp_frame), "-vf", "scale=3840:2160", str(large)], capture_output=True)

    s_small = quality.score_frame(small).sharpness
    s_orig = quality.score_frame(sharp_frame).sharpness
    s_large = quality.score_frame(large).sharpness

    # Not identical (interpolation differs) but same order of magnitude --
    # all should comfortably clear the default threshold together.
    values = [s_small, s_orig, s_large]
    assert max(values) / min(values) < 3.0
