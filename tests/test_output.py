import json

from perfectmoment import output


def _write_fake_manifest(tmp_path, video_name='clip "special" & <chars>.mp4'):
    """Manifest with hostile characters in the video name and reason -- the
    report generator must escape them, not inject them raw into HTML."""
    manifest = {
        "video": str(tmp_path / video_name),
        "quality_bar_met": False,
        "min_score": 0.6,
        "requested_top_n": 2,
        "exported_count": 1,
        "stage_timings_seconds": {"probe": 0.1},
        "frames": [
            {
                "rank": 1,
                "output_file": "rank_01.jpg",
                "final": 0.512,
                "reason": 'weak expression, <script>alert(1)</script>',
                "gated": True,
                "gate_reason": "eyes closed & blurry <b>",
                "low_quality": True,
                "scene": "portrait",
                "timestamp_seconds": 1.5,
                "eyes_open": 0.4,
                "smile": 0.3,
                "gaze_deviation": 0.2,
                "composition": 0.5,
                "sharpness": 42.0,
            }
        ],
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path


def test_write_report_generates_html(tmp_path):
    manifest_path = _write_fake_manifest(tmp_path)
    report_path = output.write_report(manifest_path)

    assert report_path.exists()
    html_text = report_path.read_text(encoding="utf-8")
    assert "rank_01.jpg" in html_text
    assert "GATED" in html_text
    assert "low quality" in html_text


def test_write_report_escapes_hostile_content(tmp_path):
    """A filename or reason containing <script> must be escaped, never
    injected raw (code-checker category: XSS via unescaped values)."""
    manifest_path = _write_fake_manifest(tmp_path)
    html_text = output.write_report(manifest_path).read_text(encoding="utf-8")

    assert "<script>" not in html_text
    assert "&lt;script&gt;" in html_text
    # video title with quotes/& also escaped
    assert "&amp;" in html_text
