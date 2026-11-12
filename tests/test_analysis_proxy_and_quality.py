#!/usr/bin/env python3
"""Tests for internal 480p analysis proxy generation and fast local segment scoring."""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from frame_extractor import (
    _compute_even_proxy_dimensions,
    create_analysis_proxy,
    detect_scene_cut_timestamps,
    get_video_metadata,
    score_video_segments,
)


def _ffmpeg_available() -> bool:
    return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def test_compute_even_proxy_dimensions_portrait_and_landscape():
    assert _compute_even_proxy_dimensions(1080, 1920, max_short_side=480) == (480, 854)
    assert _compute_even_proxy_dimensions(1920, 1080, max_short_side=480) == (854, 480)
    assert _compute_even_proxy_dimensions(480, 854, max_short_side=480) == (480, 854)
    assert _compute_even_proxy_dimensions(360, 640, max_short_side=480) == (360, 640)


@pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg/ffprobe not on PATH")
def test_create_proxy_and_score_segments_on_1080p_source(tmp_path: Path):
    src = tmp_path / "sample_1080p.mp4"
    # Build a 6s 1080x1920 clip: first 2s dark, next 4s bright textured testsrc2 + sine audio
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=black:s=1080x1920:r=24:d=2",
        "-f", "lavfi", "-i", "testsrc2=s=1080x1920:r=24:d=4",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=6",
        "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]",
        "-map", "[v]", "-map", "2:a",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "26",
        "-c:a", "aac", "-shortest",
        str(src),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr

    proxy_path = tmp_path / "proxy.mp4"
    info = create_analysis_proxy(src, output_path=proxy_path, max_short_side=480, fps=2.0)

    assert proxy_path.exists()
    assert info["width"] == 480
    assert info["height"] == 854
    assert info["source_width"] == 1080
    assert info["source_height"] == 1920
    assert info["size_bytes"] < src.stat().st_size

    proxy_meta = get_video_metadata(proxy_path)
    assert proxy_meta["width"] == 480
    assert proxy_meta["height"] == 854

    cuts = detect_scene_cut_timestamps(proxy_path, threshold=0.25)
    assert any(1.5 <= c <= 2.6 for c in cuts)

    scored = score_video_segments(proxy_path, segment_duration=2.0, sample_fps=2.0, scene_cuts=cuts)
    assert len(scored) >= 2
    dark_segs = [s for s in scored if s["end_sec"] <= 2.4]
    bright_segs = [s for s in scored if s["start_sec"] >= 1.8]
    assert dark_segs and bright_segs
    assert max(s["quality_score"] for s in bright_segs) > min(s["quality_score"] for s in dark_segs)
