from perfectmoment import faces


def test_portrait_detects_one_face(portrait_photo):
    scores, no_faces_in_clip = faces.score_frames([portrait_photo])
    assert scores[0].face_count == 1
    assert 0.0 <= scores[0].eyes_open <= 1.0
    assert 0.0 <= scores[0].smile <= 1.0
    assert len(scores[0].face_boxes) == 1
    assert no_faces_in_clip is False


def test_blank_frame_no_faces(black_frame):
    scores, no_faces_in_clip = faces.score_frames([black_frame])
    assert scores[0].face_count == 0
    assert no_faces_in_clip is True


def test_mixed_clip_no_faces_flag_is_false(portrait_photo, black_frame):
    """Whole-clip no-faces should only trigger when NOT ONE frame has a face."""
    _, no_faces_in_clip = faces.score_frames([portrait_photo, black_frame])
    assert no_faces_in_clip is False
