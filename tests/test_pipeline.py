"""End-to-end pipeline tests, formalizing the manual A7/A8 verification runs."""

import json

from perfectmoment import config, pipeline


def test_end_to_end_30s_1080p_exports_and_manifest(video_1080p_10s, tmp_path):
    out_dir = tmp_path / "out"
    result = pipeline.run(video_1080p_10s, out_dir, top_n=5)

    assert result.exported_count > 0
    assert result.manifest_path.exists()
    # AC-9 groundwork: even a slower CI box should clear 180s by a wide margin on a 10s clip.
    assert result.elapsed_seconds < 180

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["exported_count"] == result.exported_count
    for frame in manifest["frames"]:
        for field in ("sharpness", "brightness", "face_count", "eyes_open", "smile", "composition", "final"):
            assert field in frame


def test_determinism_across_full_pipeline_runs(video_1080p_10s, tmp_path):
    """AC-10: identical input must produce identical output across two full runs."""
    result1 = pipeline.run(video_1080p_10s, tmp_path / "out1", top_n=5)
    result2 = pipeline.run(video_1080p_10s, tmp_path / "out2", top_n=5)

    m1 = json.loads(result1.manifest_path.read_text(encoding="utf-8"))
    m2 = json.loads(result2.manifest_path.read_text(encoding="utf-8"))

    ts1 = [f["timestamp_seconds"] for f in m1["frames"]]
    ts2 = [f["timestamp_seconds"] for f in m2["frames"]]
    final1 = [round(f["final"], 6) for f in m1["frames"]]
    final2 = [round(f["final"], 6) for f in m2["frames"]]

    assert ts1 == ts2
    assert final1 == final2


def test_ac12_top_n_caps_at_available(video_1080p_10s, tmp_path):
    result = pipeline.run(video_1080p_10s, tmp_path / "out", top_n=1000)
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["exported_count"] < 1000
    assert manifest["exported_count"] == result.exported_count


def test_ac14_all_frames_rejected_never_exports_zero(video_black_10s, tmp_path):
    """Regression test for the bug found in A8: a fully rejected clip must
    still export min(top_n, available), never zero."""
    result = pipeline.run(video_black_10s, tmp_path / "out", top_n=5)
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))

    assert result.exported_count > 0
    assert manifest["quality_bar_met"] is False
    assert all(f["low_quality"] for f in manifest["frames"])
    assert any("stage-3 quality filter" in w for w in result.warnings)


def test_ac15_no_faces_fallback_triggers_on_faceless_clip(video_1080p_10s, tmp_path):
    result = pipeline.run(video_1080p_10s, tmp_path / "out", top_n=5)
    assert result.no_faces_in_clip is True
    assert any("no faces detected" in w for w in result.warnings)


def test_ac16_4k_warns_and_completes(video_4k, tmp_path):
    result = pipeline.run(video_4k, tmp_path / "out", top_n=3)
    assert any("large/long input" in w for w in result.warnings)
    assert result.exported_count > 0  # completed, did not crash
