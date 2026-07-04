"""Orchestrates stages 1-7 end to end: probe -> sample -> filter -> faces ->
aesthetics -> rank -> output. Owns the AC-14/15/16 graceful-degrade contract
and the AC-9 timing guard.
"""

from __future__ import annotations

import shutil
import tempfile
import time
from dataclasses import dataclass, replace
from pathlib import Path

from perfectmoment import config, extract, faces, output, quality
from perfectmoment.aesthetics import AestheticScorer
from perfectmoment.rank import compose_and_rank


@dataclass(frozen=True)
class PipelineResult:
    manifest_path: Path
    quality_bar_met: bool
    no_faces_in_clip: bool
    exported_count: int
    elapsed_seconds: float
    warnings: list[str]


def run(
    video_path: Path,
    out_dir: Path,
    top_n: int = config.DEFAULT_TOP_N,
    min_score: float = config.DEFAULT_MIN_SCORE,
    fps: float = config.DEFAULT_FPS,
    force_no_faces: bool = False,
) -> PipelineResult:
    """Run the full pipeline on one video. Never raises on degraded-quality input
    (AC-14/15/16) -- only raises on genuinely unrecoverable errors (missing file,
    ffmpeg/model not found), matching the plan's graceful-degrade contract.
    """
    start = time.time()
    warnings: list[str] = []

    # Stage 1: probe (also serves as the ffmpeg-availability + file-exists guard)
    probe = extract.probe_video(video_path)
    if probe.warn_large_or_long:
        warnings.append(f"WARNING: large/long input ({probe.warn_reason}); sampling and downscaling to stay within budget.")

    # Stages 2-7 use a scratch dir for scoring-resolution frames; cleaned up after.
    with tempfile.TemporaryDirectory(prefix="perfectmoment_") as scratch:
        scratch_dir = Path(scratch)

        # Stage 2: fixed-grid sampling
        extracted_frames = extract.sample_frames(video_path, scratch_dir, fps=fps)
        frame_paths = [f.path for f in extracted_frames]
        timestamp_by_path = {f.path: f.timestamp_seconds for f in extracted_frames}

        # Stage 3: cheap quality filter
        survivors_q, rejected_q = quality.filter_frames(frame_paths)
        survivor_paths = [s.path for s in survivors_q]

        # Stage 4: face/eye/smile (only on stage-3 survivors)
        face_scores_list, no_faces_in_clip = faces.score_frames(survivor_paths)
        face_scores = {f.path: f for f in face_scores_list}

        use_no_faces_profile = force_no_faces or no_faces_in_clip
        if no_faces_in_clip and not force_no_faces:
            warnings.append("WARNING: no faces detected anywhere in this clip; falling back to sharpness+composition-only scoring (AC-15).")

        # Stage 5: aesthetic scoring (only on stage-3 survivors, the bottleneck stage)
        scorer = AestheticScorer()
        aesthetic_scores = {p: scorer.score(p).aesthetic for p in survivor_paths}

        # Stage 6: compose + dedupe/rank
        ranked, quality_bar_met = compose_and_rank(
            survivors_q,
            face_scores,
            aesthetic_scores,
            no_faces_profile=use_no_faces_profile,
            min_score=min_score,
        )
        # Fill in the real timestamp for each ranked frame (rank.py leaves this as 0.0
        # since it doesn't have access to extract.py's ExtractedFrame objects).
        ranked = [replace(r, timestamp_seconds=timestamp_by_path[r.path]) for r in ranked]

        if not quality_bar_met:
            warnings.append(f"WARNING: no frames met the quality bar (min_score={min_score}); returning best-available frames flagged low_quality (AC-14).")

        # Stage 7: full-res re-extract + manifest (reads scratch frames' timestamps,
        # but pulls pixels from the ORIGINAL video_path, not the scratch dir).
        manifest_path = output.write_outputs(
            video_path=video_path,
            ranked_frames=ranked,
            out_dir=out_dir,
            top_n=top_n,
            quality_bar_met=quality_bar_met,
            min_score=min_score,
        )

    elapsed = time.time() - start
    return PipelineResult(
        manifest_path=manifest_path,
        quality_bar_met=quality_bar_met,
        no_faces_in_clip=no_faces_in_clip,
        exported_count=min(top_n, len(ranked)),
        elapsed_seconds=elapsed,
        warnings=warnings,
    )
