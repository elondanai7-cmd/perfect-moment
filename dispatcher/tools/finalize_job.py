"""Finalize a dispatcher job: package approved frames for delivery.

Usage:
  python tools/finalize_job.py <output_dir> --approve rank_01.jpg rank_02.jpg ...
  python tools/finalize_job.py <output_dir> --review "reason"   # send to failed/ for human review

<output_dir> is the pipeline output folder (contains manifest.json + rank_*.jpg),
as printed by run_pipeline.py.

Approve path:
  - copies approved rank_*.jpg + manifest.json to done/<job>/
  - writes done/<job>/reply.txt — ready-to-paste Hebrew WhatsApp message
  - appends a row to jobs.csv, including the pipeline's unassisted top pick
    (pipeline_top_frame) alongside what the human actually sent
    (human_top_frame) -- comparing these two is the real calibration signal
    for config.py's scoring weights, since a pilot rating alone can't tell
    you whether the algorithm or the human QA step produced the good result.
  - cleans up processing/ leftovers (video + out dir)

Review path:
  - moves everything to failed/<job>/ with a review-reason file
  - appends a "needs_review" row to jobs.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
import time
from pathlib import Path

DISPATCHER = Path(__file__).resolve().parent.parent
DONE = DISPATCHER / "done"
FAILED = DISPATCHER / "failed"
PROCESSING = DISPATCHER / "processing"
JOBS_CSV = DISPATCHER / "jobs.csv"

REPLY_TEMPLATE = """היי! 👋
סיימנו לעבור על הסרטון שלך ב-Perfect Moment 📸

מתוך כל הפריימים בסרטון, אלה {count} הרגעים המושלמים שמצאנו עבורך:
{file_lines}

התמונות מצורפות כאן בהודעה — באיכות מלאה, מוכנות לשיתוף ולהדפסה.

איך היה? נשמח לציון קטן מ-1 עד 5 (5 = מושלם) — עוזר לנו לשפר את המנוע 🙏

מוזמנים לשלוח לנו עוד סרטונים מתי שרוצים 🎬
צוות Perfect Moment
"""


def log_row(
    video: str,
    status: str,
    exported: int,
    top_score,
    notes: str,
    feedback: str = "",
    pipeline_top_frame: str = "",
    human_top_frame: str = "",
) -> None:
    # pipeline_top_frame/human_top_frame let us compare what the algorithm
    # picked unassisted vs what the human actually sent, without touching the
    # pilot's rating -- that comparison is the real calibration signal for
    # config.py's scoring weights (a >=4/5 rating alone can't tell you if the
    # algorithm or the human QA step produced the good result).
    with JOBS_CSV.open("a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(
            [time.strftime("%Y-%m-%d %H:%M:%S"), video, status, exported, top_score, notes, feedback,
             pipeline_top_frame, human_top_frame]
        )


def cleanup_processing(job: str) -> None:
    for item in PROCESSING.iterdir() if PROCESSING.exists() else []:
        if item.stem == job or item.name == f"{job}-out":
            shutil.rmtree(item, ignore_errors=True) if item.is_dir() else item.unlink(missing_ok=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("output_dir", help="pipeline output dir containing manifest.json")
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--approve", nargs="+", metavar="FILE", help="approved frame filenames")
    group.add_argument("--review", metavar="REASON", help="send job to failed/ for human review")
    args = ap.parse_args()

    out_dir = Path(args.output_dir)
    manifest_path = out_dir / "manifest.json"
    if not manifest_path.exists():
        print(json.dumps({"ok": False, "error": f"manifest.json not found in {out_dir}"}))
        return 1

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    job = out_dir.name
    video_name = Path(manifest.get("video", job)).name
    frames = {f["output_file"]: f for f in manifest.get("frames", [])}
    top_score = manifest["frames"][0]["final"] if manifest.get("frames") else ""
    # The manifest's frames are pre-sorted best-first by the pipeline, before
    # any human QA touches them -- this is the algorithm's unassisted pick.
    pipeline_top_frame = manifest["frames"][0]["output_file"] if manifest.get("frames") else ""

    if args.review:
        dest = FAILED / job
        dest.mkdir(parents=True, exist_ok=True)
        for f in out_dir.iterdir():
            shutil.copy2(f, dest / f.name)
        (dest / "review-reason.txt").write_text(args.review, encoding="utf-8")
        log_row(video_name, "needs_review", len(frames), top_score, args.review,
                pipeline_top_frame=pipeline_top_frame)
        cleanup_processing(job)
        print(json.dumps({"ok": True, "status": "needs_review", "dir": str(dest)}, ensure_ascii=False))
        return 0

    missing = [f for f in args.approve if not (out_dir / f).exists()]
    if missing:
        print(json.dumps({"ok": False, "error": f"approved files not found: {missing}"}))
        return 1

    dest = DONE / job
    dest.mkdir(parents=True, exist_ok=True)
    for i, fname in enumerate(args.approve, start=1):
        shutil.copy2(out_dir / fname, dest / fname)
    shutil.copy2(manifest_path, dest / "manifest.json")

    file_lines = "\n".join(f"  {i}. {name}" for i, name in enumerate(args.approve, start=1))
    reply = REPLY_TEMPLATE.format(count=len(args.approve), file_lines=file_lines)
    (dest / "reply.txt").write_text(reply, encoding="utf-8")

    log_row(video_name, "done", len(args.approve), top_score, "",
            pipeline_top_frame=pipeline_top_frame, human_top_frame=args.approve[0])
    cleanup_processing(job)

    print(json.dumps({
        "ok": True,
        "status": "done",
        "dir": str(dest),
        "images": args.approve,
        "reply_file": str(dest / "reply.txt"),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
