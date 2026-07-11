"""Scan the dispatcher inbox for new video jobs.

Usage: python tools/scan_inbox.py
Prints one JSON object per line for each file found in inbox/:
  {"file": "...", "ok": true/false, "reason": "..."}

Files that are not valid videos are reported with ok=false (the agent
moves them to failed/ — this script never deletes anything).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

DISPATCHER = Path(__file__).resolve().parent.parent
INBOX = DISPATCHER / "inbox"

VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}
MIN_SIZE_BYTES = 50_000  # anything smaller is almost certainly not a real video
MAX_SIZE_BYTES = 2_000_000_000  # 2 GB sanity cap


def scan() -> list[dict]:
    results = []
    if not INBOX.exists():
        return results
    for f in sorted(INBOX.iterdir()):
        if f.is_dir() or f.name.startswith("."):
            continue
        entry = {"file": str(f), "name": f.name, "size_bytes": f.stat().st_size}
        ext = f.suffix.lower()
        if ext not in VIDEO_EXTS:
            entry.update(ok=False, reason=f"unsupported extension '{ext}'")
        elif f.stat().st_size < MIN_SIZE_BYTES:
            entry.update(ok=False, reason=f"file too small ({f.stat().st_size} bytes) — likely corrupt or not a video")
        elif f.stat().st_size > MAX_SIZE_BYTES:
            entry.update(ok=False, reason="file over 2GB — ask client for a shorter clip")
        else:
            entry.update(ok=True, reason="ready")
        results.append(entry)
    return results


def main() -> int:
    results = scan()
    if not results:
        print(json.dumps({"inbox": "empty"}))
        return 0
    for r in results:
        print(json.dumps(r, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
