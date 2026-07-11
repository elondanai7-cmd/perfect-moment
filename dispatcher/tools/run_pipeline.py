"""Run the Perfect Moment worker pipeline on one inbox video.

Usage: python tools/run_pipeline.py <video_path_in_inbox> [--top-n 5]

Steps:
  1. Move the video from inbox/ to processing/ (timestamp suffix on collision).
  2. Run: python -m perfectmoment extract <video> --top-n N --out processing/<job>-out
  3. Print a JSON result line: job name, manifest path, exit code, stderr tail.

On pipeline failure the video + stderr log are moved to failed/<job>/.
This script never talks to any API — pure local subprocess.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

DISPATCHER = Path(__file__).resolve().parent.parent
REPO_ROOT = DISPATCHER.parent  # ~/perfect-moment, where `python -m perfectmoment` works
PROCESSING = DISPATCHER / "processing"
FAILED = DISPATCHER / "failed"


def unique_dest(dest: Path) -> Path:
    if not dest.exists():
        return dest
    stamp = time.strftime("%Y%m%d-%H%M%S")
    return dest.with_name(f"{dest.stem}-{stamp}{dest.suffix}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("video", help="path to video file (usually in inbox/)")
    ap.add_argument("--top-n", type=int, default=5)
    args = ap.parse_args()

    src = Path(args.video)
    if not src.exists():
        print(json.dumps({"ok": False, "error": f"file not found: {src}"}))
        return 1

    PROCESSING.mkdir(exist_ok=True)
    video = unique_dest(PROCESSING / src.name)
    shutil.move(str(src), str(video))
    job = video.stem
    out_dir = PROCESSING / f"{job}-out"

    cmd = [
        sys.executable, "-m", "perfectmoment", "extract", str(video),
        "--top-n", str(args.top_n), "--out", str(out_dir),
    ]
    proc = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)

    manifest = out_dir / video.stem / "manifest.json"
    result = {
        "job": job,
        "video": str(video),
        "exit_code": proc.returncode,
        "manifest": str(manifest) if manifest.exists() else None,
        "output_dir": str(manifest.parent) if manifest.exists() else None,
    }

    if proc.returncode != 0 or not manifest.exists():
        fail_dir = FAILED / job
        fail_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(video), str(unique_dest(fail_dir / video.name)))
        (fail_dir / "error.log").write_text(
            f"exit code: {proc.returncode}\n\nSTDOUT:\n{proc.stdout}\n\nSTDERR:\n{proc.stderr}",
            encoding="utf-8",
        )
        result.update(ok=False, failed_dir=str(fail_dir), stderr_tail=proc.stderr[-500:])
    else:
        result.update(ok=True)

    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
