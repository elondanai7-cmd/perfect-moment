"""Unit tests for webapp/app.py's non-pipeline logic: job logging, feedback
matching, and the reverse-proxy IP fix. These run without ffmpeg/video fixtures
-- gradio itself is exercised only enough to build a fake Request.
"""

from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

WEBAPP_APP = Path(__file__).resolve().parent.parent / "webapp" / "app.py"


@pytest.fixture()
def app_module(tmp_path, monkeypatch):
    """Import webapp/app.py fresh per test, with JOBS_CSV redirected into tmp_path
    so tests never touch (or race on) the real webapp/jobs.csv."""
    spec = importlib.util.spec_from_file_location("pm_webapp_under_test", WEBAPP_APP)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "JOBS_CSV", tmp_path / "jobs.csv")
    yield mod
    del sys.modules[spec.name]


def _fake_request(forwarded_for: str | None = None, client_host: str | None = "10.0.0.1"):
    headers = {"x-forwarded-for": forwarded_for} if forwarded_for else {}
    client = SimpleNamespace(host=client_host) if client_host else None
    return SimpleNamespace(headers=headers, client=client)


class TestRealClientIp:
    def test_prefers_forwarded_header_over_proxy_ip(self, app_module):
        # Regression: HF Spaces sits behind a proxy, so request.client.host is
        # the proxy's own address for every visitor -- using it directly would
        # rate-limit every user as if they were one person.
        req = _fake_request(forwarded_for="203.0.113.5, 10.0.0.1", client_host="10.0.0.1")
        assert app_module._real_client_ip(req) == "203.0.113.5"

    def test_falls_back_to_client_host_when_no_header(self, app_module):
        req = _fake_request(forwarded_for=None, client_host="198.51.100.9")
        assert app_module._real_client_ip(req) == "198.51.100.9"

    def test_handles_missing_request(self, app_module):
        assert app_module._real_client_ip(None) == "unknown"

    def test_handles_request_with_no_client(self, app_module):
        req = SimpleNamespace(headers={}, client=None)
        assert app_module._real_client_ip(req) == "unknown"


class TestJobLogging:
    def test_log_job_creates_csv_with_header(self, app_module):
        row = {
            "timestamp": "2026-07-10 10:00:00", "video": "a.mp4", "status": "done",
            "exported_count": 5, "top_score": 0.9, "notes": "", "feedback": "",
        }
        app_module._log_job(row)

        assert app_module.JOBS_CSV.exists()
        rows = list(csv.DictReader(app_module.JOBS_CSV.open(encoding="utf-8")))
        assert len(rows) == 1
        assert rows[0]["video"] == "a.mp4"
        assert rows[0]["status"] == "done"

    def test_log_job_appends_without_duplicating_header(self, app_module):
        for i in range(3):
            app_module._log_job({
                "timestamp": f"t{i}", "video": f"v{i}.mp4", "status": "done",
                "exported_count": 1, "top_score": "", "notes": "", "feedback": "",
            })
        lines = app_module.JOBS_CSV.read_text(encoding="utf-8").splitlines()
        assert lines[0] == ",".join(app_module.JOBS_CSV_FIELDS)
        assert len(lines) == 4  # header + 3 rows

    def test_record_feedback_updates_matching_row_by_timestamp(self, app_module):
        app_module._log_job({
            "timestamp": "job-1", "video": "a.mp4", "status": "done",
            "exported_count": 3, "top_score": 0.8, "notes": "", "feedback": "",
        })
        app_module._log_job({
            "timestamp": "job-2", "video": "b.mp4", "status": "done",
            "exported_count": 2, "top_score": 0.7, "notes": "", "feedback": "",
        })

        app_module._record_feedback("job-2", "5")

        rows = {r["timestamp"]: r for r in csv.DictReader(app_module.JOBS_CSV.open(encoding="utf-8"))}
        assert rows["job-2"]["feedback"] == "5"
        assert rows["job-1"]["feedback"] == ""  # untouched

    def test_record_feedback_noop_when_csv_missing(self, app_module):
        # Should not raise even if no job was ever logged yet.
        app_module._record_feedback("nonexistent", "5")
        assert not app_module.JOBS_CSV.exists()

    def test_record_feedback_noop_for_unknown_job_id(self, app_module):
        app_module._log_job({
            "timestamp": "job-1", "video": "a.mp4", "status": "done",
            "exported_count": 1, "top_score": "", "notes": "", "feedback": "",
        })
        app_module._record_feedback("job-does-not-exist", "5")
        rows = list(csv.DictReader(app_module.JOBS_CSV.open(encoding="utf-8")))
        assert rows[0]["feedback"] == ""


class TestSubmitFeedback:
    def test_submit_feedback_records_rating_for_last_job_from_that_client(self, app_module):
        app_module._log_job({
            "timestamp": "job-1", "video": "a.mp4", "status": "done",
            "exported_count": 1, "top_score": "", "notes": "", "feedback": "",
        })
        app_module._last_job_id["203.0.113.5"] = "job-1"
        req = _fake_request(forwarded_for="203.0.113.5")

        result = app_module.submit_feedback("4", req)

        assert result  # a thank-you message
        rows = list(csv.DictReader(app_module.JOBS_CSV.open(encoding="utf-8")))
        assert rows[0]["feedback"] == "4"

    def test_submit_feedback_empty_rating_is_noop(self, app_module):
        req = _fake_request(forwarded_for="203.0.113.5")
        assert app_module.submit_feedback("", req) == ""


class TestSweepStaleTempDirs(object):
    def test_sweeps_old_dirs_but_keeps_recent(self, app_module, tmp_path, monkeypatch):
        import tempfile
        import time

        monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))

        old_dir = tmp_path / "pm_web_old"
        old_dir.mkdir()
        (old_dir / "rank_1.jpg").write_bytes(b"x")
        old_time = time.time() - app_module.TEMP_DIR_MAX_AGE_SECONDS - 60
        import os
        os.utime(old_dir, (old_time, old_time))

        fresh_dir = tmp_path / "pm_web_fresh"
        fresh_dir.mkdir()

        app_module._sweep_stale_temp_dirs()

        assert not old_dir.exists()
        assert fresh_dir.exists()
