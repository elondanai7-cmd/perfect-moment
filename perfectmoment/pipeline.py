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
from typing import Callable

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
    stage_timings: dict[str, float] | None = None  # seconds per stage, for A8/A9 profiling
    report_path: Path | None = None  # HTML contact sheet, if generated


def run(
    video_path: Path,
    out_dir: Path,
    top_n: int = config.DEFAULT_TOP_N,
    min_score: float = config.DEFAULT_MIN_SCORE,
    fps: float = config.DEFAULT_FPS,
    force_no_faces: bool = False,
    scorer: AestheticScorer | None = None,
    on_progress: Callable[[str], None] | None = None,
    make_report: bool = True,
) -> PipelineResult:
    """Run the full pipeline on one video. Never raises on degraded-quality input
    (AC-14/15/16) -- only raises on genuinely unrecoverable errors (missing file,
    ffmpeg/model not found), matching the plan's graceful-degrade contract.

    `scorer`: pass a pre-loaded AestheticScorer to skip the ~2.5s NIMA model
    load -- essential for batch mode, where reloading per clip wastes seconds
    times the number of clips in a shoot folder.
    `on_progress`: optional callback receiving one short line per stage (the
    CLI passes print) so a 30-240s run isn't silent.
    """
    start = time.time()
    warnings: list[str] = []
    stage_timings: dict[str, float] = {}

    def _progress(message: str) -> None:
        if on_progress is not None:
            on_progress(message)

    def _mark(stage: str, stage_start: float) -> None:
        stage_timings[stage] = round(time.time() - stage_start, 2)

    # Stage 1: probe (also serves as the ffmpeg-availability + file-exists guard)
    stage_start = time.time()
    _progress(f"[1/7] Probing {video_path.name}...")
    probe = extract.probe_video(video_path)
    if probe.warn_large_or_long:
        warnings.append(f"WARNING: large/long input ({probe.warn_reason}); sampling and downscaling to stay within budget.")
    _mark("probe", stage_start)

    # Stages 2-7 use a scratch dir for scoring-resolution frames; cleaned up after.
    with tempfile.TemporaryDirectory(prefix="perfectmoment_") as scratch:
        scratch_dir = Path(scratch)

        # Stage 2: fixed-grid sampling
        stage_start = time.time()
        _progress(f"[2/7] Sampling frames at {fps} fps...")
        extracted_frames = extract.sample_frames(video_path, scratch_dir, fps=fps)
        frame_paths = [f.path for f in extracted_frames]
        timestamp_by_path = {f.path: f.timestamp_seconds for f in extracted_frames}
        _mark("sample", stage_start)

        # Stage 3: cheap quality filter
        stage_start = time.time()
        _progress(f"[3/7] Quality-filtering {len(frame_paths)} candidate frames...")
        survivors_q, rejected_q = quality.filter_frames(frame_paths)

        # AC-14 hard edge case: if EVERY frame fails the stage-3 hard filter
        # (e.g. a fully dark/black clip), there would be zero candidates left
        # for every later stage, and the pipeline would export nothing --
        # violating the "never return empty" contract. Fall back to treating
        # all originally-rejected frames as forced candidates so downstream
        # stages (and the min_score bar in rank.py) can still pick a
        # least-bad set and flag it low_quality, rather than exporting zero.
        if not survivors_q:
            warnings.append("WARNING: every frame failed the stage-3 quality filter (fully rejected clip); falling back to least-bad available frames (AC-14).")
            survivors_q = [replace(s, passed=True) for s in rejected_q]

        survivor_paths = [s.path for s in survivors_q]
        _mark("quality_filter", stage_start)

        # Stage 4: face/eye/smile (only on stage-3 survivors)
        stage_start = time.time()
        _progress(f"[4/7] Face/expression scoring {len(survivor_paths)} survivors...")
        face_scores_list, no_faces_in_clip = faces.score_frames(survivor_paths)
        face_scores = {f.path: f for f in face_scores_list}

        use_no_faces_profile = force_no_faces or no_faces_in_clip
        if no_faces_in_clip and not force_no_faces:
            warnings.append("WARNING: no faces detected anywhere in this clip; falling back to sharpness+composition-only scoring (AC-15).")
        _mark("faces", stage_start)

        # Stage 5: aesthetic scoring (only on stage-3 survivors, the bottleneck stage)
        stage_start = time.time()
        _progress(f"[5/7] Aesthetic scoring (NIMA, the slow stage) -- {len(survivor_paths)} frames...")
        if scorer is None:
            scorer = AestheticScorer()
        aesthetic_scores = {p: scorer.score(p).aesthetic for p in survivor_paths}
        _mark("aesthetics", stage_start)

        # Stage 6: compose + dedupe/rank
        stage_start = time.time()
        _progress("[6/7] Ranking and deduplicating...")
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
        _mark("rank", stage_start)

        # Stage 7: full-res re-extract + manifest (reads scratch frames' timestamps,
        # but pulls pixels from the ORIGINAL video_path, not the scratch dir).
        stage_start = time.time()
        _progress("[7/7] Re-extracting winners at full resolution...")
        manifest_path = output.write_outputs(
            video_path=video_path,
            ranked_frames=ranked,
            out_dir=out_dir,
            top_n=top_n,
            quality_bar_met=quality_bar_met,
            min_score=min_score,
            stage_timings=stage_timings,
        )
        _mark("output", stage_start)

        report_path = None
        if make_report:
            report_path = output.write_report(manifest_path)

    elapsed = time.time() - start
    return PipelineResult(
        manifest_path=manifest_path,
        quality_bar_met=quality_bar_met,
        no_faces_in_clip=no_faces_in_clip,
        exported_count=min(top_n, len(ranked)),
        elapsed_seconds=elapsed,
        warnings=warnings,
        stage_timings=stage_timings,
        report_path=report_path,
    )
