"""Perfect Moment — self-serve web app.

This IS the "connected agents" flow the founder asked for, made real instead
of fake theater:

  Agent 1 (this file / Gradio):  receives the uploaded video from the visitor.
  Agent 2 (perfectmoment.pipeline): probes -> samples -> filters blur/exposure
      -> scores faces/eyes/smile -> scores aesthetics -> ranks -> exports.
  Agent 1 (this file, again):    reads Agent 2's output back and shows the
      best frames to the visitor immediately. No WhatsApp, no manual step.

Cost: $0. HF Spaces' free tier no longer supports this (policy change,
2026-07: new accounts need paid PRO for cpu-basic Gradio Spaces) and
Render's free tier can't fit the ~1GB RSS this stack needs (torch + NIMA),
so this currently runs from the founder's own machine via `webapp/start.sh`
(app + a free cloudflared tunnel) -- see PILOT.md. No paid API is called
anywhere in this file — the "AI" is the same local scoring pipeline already
tested in perfectmoment/, not an LLM call.
"""

from __future__ import annotations

import csv
import shutil
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

import gradio as gr

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from perfectmoment import config, extract, pipeline  # noqa: E402
from perfectmoment.aesthetics import AestheticScorer  # noqa: E402

# gradio_client 1.5.2 (pinned by gradio==5.9.1) crashes generating the
# auto "view API" schema whenever a JSON-Schema sub-node is a bare bool
# (e.g. "additionalProperties": true) -- a valid JSON Schema shape that
# this older code assumes is always a dict, raising
# "TypeError: argument of type 'bool' is not iterable" and taking down
# the whole request. It's triggered by the frontend fetching /info on
# every page load, so it crashes real visitors, not just at startup.
# Patch the recursive converter to treat a bool schema as "Any" instead
# of crashing; every other schema shape still goes through the original.
import gradio_client.utils as _gr_client_utils  # noqa: E402

_orig_json_schema_to_python_type = _gr_client_utils._json_schema_to_python_type


def _safe_json_schema_to_python_type(schema, defs):
    if isinstance(schema, bool):
        return "Any"
    return _orig_json_schema_to_python_type(schema, defs)


_gr_client_utils._json_schema_to_python_type = _safe_json_schema_to_python_type

# gradio 5.9.1 builds several locks/events (App.lock, App.stop_event,
# Queue.pending_message_lock, Queue.delete_lock) via utils.safe_get_lock() /
# safe_get_stop_event(), which only construct asyncio.Lock() / asyncio.
# Event() inside a try/except around asyncio.get_event_loop() -- a leftover
# guard from when that call could raise RuntimeError with no running loop
# yet (true at construction time, before uvicorn starts the loop). On
# Python 3.14, asyncio.get_event_loop() with no running/current loop always
# raises, so all of these silently end up None. Queue.pending_message_lock
# = None then crashes every actual queue/predict request ("async with
# self.pending_message_lock" in queueing.py's push(), used to process a
# submitted video) with an unrelated-looking 500 on /gradio_api/queue/join
# -- a real video upload could never complete. App.stop_event = None
# separately crashes the heartbeat/stop_stream endpoint on every client
# connect. Neither asyncio.Lock() nor asyncio.Event() actually need a
# running loop to construct in modern Python (both bind lazily on first
# await), so the try/except here is just stale.
#
# Patching gradio.utils.safe_get_lock alone is not enough: routes.py does
# `from gradio import utils` and calls utils.safe_get_lock() (a live
# lookup, patch works), but queueing.py does
# `from gradio.utils import safe_get_lock` (binds its own local name to the
# original function object at import time, before this patch ever runs) --
# so queueing.py's copy has to be patched directly too.
import gradio.queueing as _gr_queueing  # noqa: E402
import gradio.utils as _gr_utils  # noqa: E402


def _safe_get_stop_event():
    import asyncio
    return asyncio.Event()


def _safe_get_lock():
    import asyncio
    return asyncio.Lock()


_gr_utils.safe_get_stop_event = _safe_get_stop_event
_gr_utils.safe_get_lock = _safe_get_lock
_gr_queueing.safe_get_lock = _safe_get_lock

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
    "face_landmarker/float16/1/face_landmarker.task"
)

# Guardrails for exposing this on a public tunnel (a single home machine runs
# the pipeline, so a flood of large/long uploads is a real self-DoS risk, not
# just a theoretical one).
MAX_UPLOAD_MB = 60
MAX_DURATION_SECONDS = 45
MIN_SECONDS_BETWEEN_REQUESTS = 20  # per client IP
TEMP_DIR_MAX_AGE_SECONDS = 3600  # sweep stale job dirs older than this

_last_request_at: dict[str, float] = {}

JOBS_CSV = Path(__file__).resolve().parent / "jobs.csv"
JOBS_CSV_FIELDS = ["timestamp", "video", "status", "exported_count", "top_score", "notes", "feedback"]

# Every video processed gets one row here, keyed by this id, so a feedback
# rating submitted afterwards can be matched back to the right job — this is
# the same jobs.csv shape the dispatcher agent uses, so the pilot's feedback
# gate (PILOT.md: 10 users, avg >=4/5) can be tracked across both agents.
_last_job_id: dict[str, str] = {}


def _log_job(row: dict) -> str:
    JOBS_CSV.parent.mkdir(parents=True, exist_ok=True)
    is_new = not JOBS_CSV.exists()
    with JOBS_CSV.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=JOBS_CSV_FIELDS)
        if is_new:
            writer.writeheader()
        writer.writerow(row)
    return row["timestamp"]


def _record_feedback(job_id: str, rating: str) -> None:
    if not JOBS_CSV.exists() or not job_id:
        return
    rows = list(csv.DictReader(JOBS_CSV.open(encoding="utf-8")))
    for row in rows:
        if row["timestamp"] == job_id:
            row["feedback"] = rating
            break
    with JOBS_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=JOBS_CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _sweep_stale_temp_dirs() -> None:
    """Each request leaves a pm_web_* temp dir behind for the gallery to read
    from; nothing was ever deleting them, so disk usage grows without bound
    on a long-running Space. Sweep anything older than an hour on each call."""
    tmp_root = Path(tempfile.gettempdir())
    now = time.time()
    for entry in tmp_root.glob("pm_web_*"):
        try:
            if now - entry.stat().st_mtime > TEMP_DIR_MAX_AGE_SECONDS:
                shutil.rmtree(entry, ignore_errors=True)
        except OSError:
            pass


def _real_client_ip(request: gr.Request | None) -> str:
    """request.client.host is the proxy's IP behind HF Spaces' tunnel/proxy,
    not the visitor's — using it directly means the first visitor's request
    would rate-limit every subsequent visitor. Prefer the forwarded header."""
    if request is None:
        return "unknown"
    forwarded = request.headers.get("x-forwarded-for") if request.headers else None
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host or "unknown"
    return "unknown"


def _ensure_face_model() -> None:
    """First-run download of the face landmark model (gitignored, ~a few MB).

    urlretrieve has no default timeout -- on a slow/stalled connection (seen
    on Render's free tier) this hung indefinitely on the very first real
    request, with no progress feedback and no way to recover except
    restarting the instance. A bounded timeout turns that into a normal
    caught exception (process_video already wraps this in try/except),
    so the visitor gets an error message instead of an infinite spinner.
    Writes to a temp file first so a failed/partial download never leaves
    a corrupt model file that `dest.exists()` would treat as done.
    """
    dest = config.FACE_LANDMARKER_MODEL_PATH
    if dest.exists():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp_dest = dest.with_suffix(dest.suffix + ".part")
    try:
        with urllib.request.urlopen(MODEL_URL, timeout=30) as resp, tmp_dest.open("wb") as f:
            shutil.copyfileobj(resp, f)
        tmp_dest.rename(dest)
    finally:
        tmp_dest.unlink(missing_ok=True)


# Lazy singleton, not a per-request load: without this, every single visitor
# paid the NIMA model load (~2.5s) on top of their own video's processing
# time. Lazy (not eager at import) keeps `import app` fast for tooling/tests
# that never actually serve a request.
_scorer_singleton: AestheticScorer | None = None


def _get_scorer() -> AestheticScorer:
    global _scorer_singleton
    if _scorer_singleton is None:
        _ensure_face_model()
        # AestheticScorer() downloads the NIMA weights on first use if they
        # aren't already cached (render.yaml pre-fetches them at build time,
        # but this is the same class of bug as the face model: pyiqa/torch's
        # own download path has no timeout we control). A global socket
        # timeout is a blunt but effective safety net -- bounds *any*
        # network call made during model construction, not just the ones
        # we've found so far, so it fails fast instead of hanging forever.
        import socket
        prev_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(30)
        try:
            _scorer_singleton = AestheticScorer()
        finally:
            socket.setdefaulttimeout(prev_timeout)
    return _scorer_singleton


RESULTS_TOP_N = 3  # 5 felt like too many similar choices to real pilot users -- 3 is enough


def _zip_images(images: list[Path], out_dir: Path) -> Path:
    """Bundle the result JPEGs (full resolution) into one ZIP for a single
    real download -- pilot feedback: users were screenshotting the gallery
    (low quality) instead of finding Gradio's per-image download icon."""
    zip_path = out_dir / "perfect-moment-photos.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_STORED) as zf:
        for p in images:
            zf.write(p, arcname=p.name)
    return zip_path


def process_video(video_path: str, request: gr.Request, progress: gr.Progress = gr.Progress()):
    no_download = gr.update(visible=False)

    if not video_path:
        yield [], "העלה סרטון קודם.", gr.update(visible=False), no_download
        return

    src = Path(video_path)
    client = _real_client_ip(request)
    job_timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    now = time.monotonic()
    last = _last_request_at.get(client)
    if last is not None and (now - last) < MIN_SECONDS_BETWEEN_REQUESTS:
        wait = MIN_SECONDS_BETWEEN_REQUESTS - (now - last)
        yield [], f"רגע, לאט 🙂 אפשר עוד ניסיון בעוד כ-{wait:.0f} שניות.", gr.update(visible=False), no_download
        return
    _last_request_at[client] = now

    # Set only once we're past the rate-limit guard: every path below this
    # point calls _log_job(job_timestamp), so jobs.csv always has a matching
    # row. Setting it earlier (before the rate-limit check) let a rate-
    # limited retry silently overwrite this with a timestamp that was never
    # logged — a later feedback rating would then match no row in jobs.csv
    # and be dropped, while submit_feedback still shows "תודה!" as if it
    # worked (see _record_feedback: no-op when the id isn't found).
    _last_job_id[client] = job_timestamp

    try:
        size_mb = src.stat().st_size / (1024 * 1024)
    except OSError as exc:  # noqa: BLE001 — Gradio's temp upload can vanish/be inaccessible; don't crash the app
        msg = f"לא הצלחתי לקרוא את הקובץ שהועלה: {exc}"
        _log_job({"timestamp": job_timestamp, "video": src.name, "status": "unreadable",
                   "exported_count": 0, "top_score": "", "notes": str(exc), "feedback": ""})
        yield [], msg, gr.update(visible=False), no_download
        return
    if size_mb > MAX_UPLOAD_MB:
        msg = f"הקובץ גדול מדי ({size_mb:.0f}MB). מקסימום {MAX_UPLOAD_MB}MB — נסה סרטון קצר/דחוס יותר."
        _log_job({"timestamp": job_timestamp, "video": src.name, "status": "rejected_size",
                   "exported_count": 0, "top_score": "", "notes": msg, "feedback": ""})
        yield [], msg, gr.update(visible=False), no_download
        return

    try:
        duration = extract.probe_video(src).duration_seconds
    except Exception as exc:  # noqa: BLE001 — bad/corrupt upload, don't crash the app
        msg = f"לא הצלחתי לקרוא את הסרטון: {exc}"
        _log_job({"timestamp": job_timestamp, "video": src.name, "status": "unreadable",
                   "exported_count": 0, "top_score": "", "notes": str(exc), "feedback": ""})
        yield [], msg, gr.update(visible=False), no_download
        return
    if duration > MAX_DURATION_SECONDS:
        msg = f"הסרטון ארוך מדי ({duration:.0f} שניות). מקסימום {MAX_DURATION_SECONDS} שניות בבטא."
        _log_job({"timestamp": job_timestamp, "video": src.name, "status": "rejected_duration",
                   "exported_count": 0, "top_score": "", "notes": msg, "feedback": ""})
        yield [], msg, gr.update(visible=False), no_download
        return

    # Real-user feedback: without this, the wait between clicking submit and
    # the progress bar's first update looked identical to "frozen/broken" --
    # people didn't trust it was working. Yield an immediate, unmissable
    # status before any of the slow work (model load, ffmpeg, NIMA) starts.
    yield [], "🔄 המערכת פועלת על הסרטון שלך... זה יכול לקחת בין 30 שניות לדקה. נא לא לרענן את הדף.", gr.update(visible=False), no_download

    progress(0, desc="מכין...")
    _sweep_stale_temp_dirs()

    work_root = Path(tempfile.mkdtemp(prefix="pm_web_"))
    out_dir = work_root / src.stem

    def on_progress(msg: str) -> None:
        # pipeline prefixes each stage message "[n/7] ..." -- parse it so the
        # bar actually advances instead of sitting fixed at 50%.
        frac = 0.5
        if msg.startswith("[") and "/" in msg.split("]", 1)[0]:
            try:
                n, total = msg[1:msg.index("]")].split("/")
                frac = int(n) / int(total)
            except (ValueError, ZeroDivisionError):
                pass
        progress(frac, desc=msg)

    try:
        result = pipeline.run(
            video_path=src,
            out_dir=out_dir,
            top_n=RESULTS_TOP_N,
            min_score=config.DEFAULT_MIN_SCORE,
            fps=config.DEFAULT_FPS,
            on_progress=on_progress,
            make_report=False,
            scorer=_get_scorer(),
        )
    except Exception as exc:  # noqa: BLE001 — surface any pipeline error to the visitor, don't crash the app
        msg = f"משהו השתבש: {exc}"
        _log_job({"timestamp": job_timestamp, "video": src.name, "status": "error",
                   "exported_count": 0, "top_score": "", "notes": str(exc), "feedback": ""})
        yield [], msg, gr.update(visible=False), no_download
        return

    images = sorted(out_dir.glob("rank_*.jpg"))
    if not images:
        msg = "לא נמצאו פריימים מספיק טובים בסרטון הזה. נסה סרטון עם יותר אור או יציבות."
        _log_job({"timestamp": job_timestamp, "video": src.name, "status": "no_frames",
                   "exported_count": 0, "top_score": "", "notes": "", "feedback": ""})
        yield [], msg, gr.update(visible=False), no_download
        return

    note = f"נבחרו {len(images)} התמונות הטובות ביותר מתוך הסרטון, תוך {result.elapsed_seconds:.0f} שניות."
    if not result.quality_bar_met:
        note += " (איכות הסרטון בגבול הנמוך — אלו עדיין הפריימים הכי טובים שנמצאו.)"

    top_score = ""
    try:
        import json
        manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
        frames = manifest.get("frames") or []
        if frames:
            top_score = frames[0].get("final", "")
    except Exception:  # noqa: BLE001 — top_score is a nice-to-have for jobs.csv, never fatal
        pass
    _log_job({"timestamp": job_timestamp, "video": src.name, "status": "done",
               "exported_count": len(images), "top_score": top_score, "notes": "", "feedback": ""})

    # Real file download in original quality (not the gallery's screenshot-
    # sized preview) -- one click, no separate "prepare" step, since we
    # already have the images on disk right here.
    try:
        zip_path = _zip_images(images, out_dir)
        download_update = gr.update(value=str(zip_path), visible=True)
    except OSError:  # noqa: BLE001 — download convenience only, never block showing the gallery
        download_update = no_download

    yield [str(p) for p in images], note, gr.update(visible=True), download_update


def submit_feedback(rating: str, request: gr.Request) -> str:
    client = _real_client_ip(request)
    job_id = _last_job_id.get(client)
    if not job_id or not rating:
        return ""
    _record_feedback(job_id, rating)
    return "תודה! 🙏"


# Hebrew UI is right-to-left; Gradio doesn't set this itself, so without it
# the layout renders LTR while the text is Hebrew -- readable but visually
# backwards on the mobile-first audience this is built for.
RTL_CSS = """
.gradio-container { direction: rtl; text-align: right; }
"""

with gr.Blocks(title="הרגע המושלם", css=RTL_CSS) as demo:
    gr.Markdown(
        """
        # 📸 הרגע המושלם
        העלה סרטון קצר (עד 45 שניות, עד 60MB) — הסוכן יבחר עבורך את התמונות הכי טובות ממנו:
        עיניים פקוחות, בלי טשטוש, החיוך הכי טוב. חינם, בטא.
        """
    )
    with gr.Row():
        video_in = gr.Video(label="הסרטון שלך", sources=["upload"])
    submit = gr.Button("מצא לי את הרגע המושלם", variant="primary")
    status = gr.Markdown()
    # Fixed columns=5 crams onto a phone screen; Gradio's responsive column
    # spec lets it collapse to 2 on narrow viewports and grow on desktop.
    gallery = gr.Gallery(
        label="התמונות שנבחרו", columns=[2, 3, RESULTS_TOP_N], height="auto", object_fit="cover"
    )
    # Real pilot users were screenshotting the gallery (low quality) instead
    # of finding Gradio's small per-image download icon -- one big button
    # that downloads the full-resolution ZIP in a single click.
    download_btn = gr.DownloadButton("💾 הורדת כל התמונות (איכות מלאה)", visible=False)

    with gr.Row(visible=False) as feedback_row:
        rating = gr.Radio(
            ["1", "2", "3", "4", "5"], label="איך היה? (1=לא טוב, 5=מעולה)"
        )
        feedback_note = gr.Markdown()

    submit.click(
        fn=process_video, inputs=video_in, outputs=[gallery, status, feedback_row, download_btn]
    )
    rating.change(fn=submit_feedback, inputs=rating, outputs=feedback_note)


if __name__ == "__main__":
    import os

    # concurrency_limit=1: one video processed at a time — this runs on a
    # single free-tier instance, not a scalable server.
    # PM_SHARE=1 opts into Gradio's own free public tunnel (a temporary
    # *.gradio.live link) for running the pilot from this machine instead of
    # a hosted deploy — off by default so local dev doesn't open a public link.
    share = os.environ.get("PM_SHARE") == "1"
    # Render (and most PaaS free tiers) assign the port via $PORT and expect
    # the process to bind 0.0.0.0; local dev keeps Gradio's own default.
    port = int(os.environ.get("PORT", 0)) or None
    host = "0.0.0.0" if port else None

    if host:
        # Gradio's launch() self-verifies reachability by making an HTTP
        # request to http://{server_name}:{server_port}/ before printing the
        # URL. On Render (and most container platforms) 0.0.0.0 is a valid
        # bind address but not a valid address to *connect to* -- the check
        # fails even though the server is actually up and reachable
        # externally, and gradio treats that as fatal (raises ValueError,
        # crashing the process) unless share=True. Skip the check: we've
        # already confirmed the server binds and serves correctly, this
        # self-ping is the only thing that's broken.
        import gradio.networking as _gr_networking
        _gr_networking.url_ok = lambda url: True

    # Reuse the landing page's favicon so the browser tab matches the brand
    # instead of Gradio's default logo -- cosmetic, but it's the first thing
    # a pilot user sees if they keep the tab open.
    favicon = Path(__file__).resolve().parent.parent / "landing" / "favicon.svg"

    demo.queue(default_concurrency_limit=1, max_size=10).launch(
        share=share, server_name=host, server_port=port,
        favicon_path=str(favicon) if favicon.exists() else None,
    )
