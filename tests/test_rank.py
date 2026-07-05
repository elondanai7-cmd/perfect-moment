from pathlib import Path

from perfectmoment import faces, quality, rank
from perfectmoment.faces import FaceScore
from perfectmoment.quality import QualityScore


def _score_all(paths, aesthetic_scorer):
    qscores = [quality.score_frame(p) for p in paths]
    fscores_list, _ = faces.score_frames(paths)
    fscores = {f.path: f for f in fscores_list}
    ascores = {p: aesthetic_scorer.score(p).aesthetic for p in paths}
    return qscores, fscores, ascores


def _qs(path, sharpness=500.0, brightness=140.0, passed=True):
    return QualityScore(path=path, sharpness=sharpness, brightness=brightness, passed=passed, reject_reason=None)


def _make_dummy_image(path, variant=0):
    """phash_of() needs a real, readable, and VISUALLY DISTINCT image file --
    flat solid colors all phash-identical (zero-frequency content), which
    would make dedupe collapse every test frame into one. Draw a simple
    pattern that differs per variant so frames aren't spuriously deduped."""
    from PIL import Image as PILImage, ImageDraw

    img = PILImage.new("RGB", (64, 64), (30, 30, 30))
    draw = ImageDraw.Draw(img)
    offset = variant * 15
    draw.rectangle([offset, offset, offset + 20, offset + 20], fill=(200, 200, 200))
    img.save(path)
    return path


def test_ac14_degrade_never_empty_impossible_bar(sharp_frame, aesthetic_scorer):
    qscores, fscores, ascores = _score_all([sharp_frame], aesthetic_scorer)
    ranked, quality_bar_met = rank.compose_and_rank(qscores, fscores, ascores, min_score=0.999)
    assert quality_bar_met is False
    assert len(ranked) > 0
    assert all(r.low_quality for r in ranked)


def test_product_profile_ranks_without_face_quality(sharp_frame, aesthetic_scorer):
    qscores, fscores, ascores = _score_all([sharp_frame], aesthetic_scorer)
    ranked, _ = rank.compose_and_rank(qscores, fscores, ascores, no_faces_profile=True, min_score=0.1)
    assert len(ranked) == 1


def test_composition_score_no_faces_is_neutral():
    assert rank.composition_score([]) == 0.5


def test_sharpness_diminishing_returns():
    """Research finding: 'sharp vs sharper barely matters, soft vs sharp matters
    a lot' -- the sqrt curve should compress differences at the high end and
    expand them at the low end."""
    low = rank.sharpness_score(50)
    mid = rank.sharpness_score(500)
    high = rank.sharpness_score(950)

    gap_low_to_mid = mid - low
    gap_mid_to_high = high - mid
    assert gap_low_to_mid > gap_mid_to_high  # low-end gap must be bigger than high-end gap


def test_classify_scene():
    assert rank.classify_scene(0) == "landscape"
    assert rank.classify_scene(1) == "portrait"
    assert rank.classify_scene(2) == "group"
    assert rank.classify_scene(5) == "group"


def test_portrait_closed_eyes_gated_and_ranked_below_open_eyes(tmp_path):
    """Regression test for the two-pass model: a closed-eyes portrait frame
    must be gated and rank below an otherwise-similar open-eyes frame."""
    open_path = _make_dummy_image(tmp_path / "open.jpg", variant=0)
    closed_path = _make_dummy_image(tmp_path / "closed.jpg", variant=1)

    open_face = FaceScore(path=open_path, face_count=1, eyes_open=0.9, smile=0.5,
                           eyes_open_per_face=[0.9], gaze_deviation=0.1, face_lighting=0.9)
    closed_face = FaceScore(path=closed_path, face_count=1, eyes_open=0.1, smile=0.5,
                             eyes_open_per_face=[0.1], gaze_deviation=0.1, face_lighting=0.9)

    qscores = [_qs(open_path, sharpness=400), _qs(closed_path, sharpness=400)]
    fscores = {open_path: open_face, closed_path: closed_face}
    ascores = {open_path: 6.0, closed_path: 6.0}

    ranked, _ = rank.compose_and_rank(qscores, fscores, ascores, min_score=0.0)

    by_path = {r.path: r for r in ranked}
    assert by_path[closed_path].gated is True
    assert "eyes closed" in by_path[closed_path].gate_reason
    assert by_path[open_path].gated is False
    # open-eyes frame must rank strictly above the gated closed-eyes frame
    open_index = [r.path for r in ranked].index(open_path)
    closed_index = [r.path for r in ranked].index(closed_path)
    assert open_index < closed_index


def test_group_worst_face_gates_on_one_closed_eye(tmp_path):
    """Group scene: even if the group MEAN eyes_open looks fine, one closed
    eye should still gate the frame (worst-face rule, not an average)."""
    path = _make_dummy_image(tmp_path / "group.jpg")
    # 3 faces: two wide open, one closed -- mean is high but eyes_open_pct is 2/3 = 0.67 < 0.8 gate
    group_face = FaceScore(
        path=path, face_count=3, eyes_open=0.6, smile=0.4,
        eyes_open_per_face=[0.9, 0.9, 0.05],
        gaze_deviation_per_face=[0.1, 0.1, 0.1],
        gaze_deviation=0.1, face_lighting=0.9,
    )
    qscores = [_qs(path, sharpness=400)]
    fscores = {path: group_face}
    ascores = {path: 6.0}

    ranked, _ = rank.compose_and_rank(qscores, fscores, ascores, min_score=0.0)
    assert ranked[0].scene == "group"
    assert ranked[0].gated is True
    assert "closed eyes" in ranked[0].gate_reason


def test_reason_string_present_for_every_frame(sharp_frame, aesthetic_scorer):
    qscores, fscores, ascores = _score_all([sharp_frame], aesthetic_scorer)
    ranked, _ = rank.compose_and_rank(qscores, fscores, ascores, min_score=0.0)
    assert all(r.reason for r in ranked)


def test_ac14_never_empty_when_every_frame_gated(tmp_path):
    """Even if every candidate is gated (e.g. everyone blinked), the pipeline
    must still return the least-bad frame, not nothing -- gates rank frames
    down, they never get dropped."""
    path = _make_dummy_image(tmp_path / "blink.jpg")
    face = FaceScore(path=path, face_count=1, eyes_open=0.05, smile=0.1,
                      eyes_open_per_face=[0.05], gaze_deviation=0.5, face_lighting=0.5)
    qscores = [_qs(path, sharpness=400)]
    fscores = {path: face}
    ascores = {path: 5.0}

    ranked, _ = rank.compose_and_rank(qscores, fscores, ascores, min_score=0.0)
    assert len(ranked) == 1
    assert ranked[0].gated is True
