"""Summarize pilot feedback across BOTH jobs.csv files (webapp + dispatcher).

PILOT.md's gate: avg feedback >=4/5 across 10 real users -> continue. The two
delivery paths (self-serve webapp, manual WhatsApp dispatcher) log to separate
jobs.csv files with slightly different columns -- this script reads both,
combines only the rows with a numeric feedback rating, and reports the
combined average against the gate, plus a per-path breakdown so a lopsided
result (e.g. all feedback from one path) is visible, not hidden in one number.

Usage:
    python scripts/pilot_feedback_summary.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = {
    "webapp": ROOT / "webapp" / "jobs.csv",
    "dispatcher": ROOT / "dispatcher" / "jobs.csv",
}
GATE_THRESHOLD = 4.0
GATE_MIN_RESPONSES = 10


def load_ratings(path: Path) -> list[float]:
    if not path.exists():
        return []
    ratings = []
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            raw = (row.get("feedback") or "").strip()
            if not raw:
                continue
            try:
                ratings.append(float(raw))
            except ValueError:
                continue
    return ratings


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    all_ratings: list[float] = []
    print("Perfect Moment -- pilot feedback summary\n")
    for name, path in SOURCES.items():
        ratings = load_ratings(path)
        all_ratings.extend(ratings)
        if not ratings:
            print(f"  {name:<12} 0 responses ({path} {'missing' if not path.exists() else 'no feedback yet'})")
        else:
            avg = sum(ratings) / len(ratings)
            print(f"  {name:<12} {len(ratings)} response(s), avg {avg:.2f}  [{', '.join(str(r) for r in ratings)}]")

    print()
    total = len(all_ratings)
    if total == 0:
        print("No feedback recorded yet on either path.")
        return 0

    combined_avg = sum(all_ratings) / total
    print(f"Combined: {total} response(s), avg {combined_avg:.2f}")

    if total < GATE_MIN_RESPONSES:
        print(f"Gate: not enough data yet ({total}/{GATE_MIN_RESPONSES} needed).")
    elif combined_avg >= GATE_THRESHOLD:
        print(f"Gate: PASS ({combined_avg:.2f} >= {GATE_THRESHOLD}) -- continue building the consumer direction (see PILOT.md).")
    else:
        print(f"Gate: FAIL ({combined_avg:.2f} < {GATE_THRESHOLD}) -- stop and diagnose per PILOT.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
