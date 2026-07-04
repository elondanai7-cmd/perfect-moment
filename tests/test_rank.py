from perfectmoment import faces, quality, rank


def _score_all(paths, aesthetic_scorer):
    qscores = [quality.score_frame(p) for p in paths]
    fscores_list, _ = faces.score_frames(paths)
    fscores = {f.path: f for f in fscores_list}
    ascores = {p: aesthetic_scorer.score(p).aesthetic for p in paths}
    return qscores, fscores, ascores


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
