#!/usr/bin/env python3
"""Tests for fast 1080p seeking/cutting, xfade transitions, and AI-guided montage selection."""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web.video_editor import (
    _compute_output_segments,
    _select_preferred_segments,
    assemble_shot_segments,
    auto_smart_montage,
    calculate_smart_montage_segments,
    probe_video_stream,
    trim_video_clip,
)


def _ffmpeg_available() -> bool:
    return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def test_select_preferred_segments_respects_budget_and_chronology():
    preferred = [
        {"start_sec": 2.0, "end_sec": 8.0, "score": 0.9},
        {"start_sec": 20.0, "end_sec": 28.0, "score": 0.7},
        {"start_sec": 45.0, "end_sec": 55.0, "score": 0.95},
        {"start_sec": 90.0, "end_sec": 100.0, "score": 0.6},
    ]
    segs = _select_preferred_segments(preferred, src_dur=120.0, target_duration=15.0)
    assert len(segs) >= 2
    assert segs == sorted(segs, key=lambda s: s[0])
    total = sum(en - st for st, en in segs)
    assert total <= 17.5
    # High score segments (45-55 and 2-8) should beat 90-100
    assert any(st >= 45.0 and en <= 55.0 for st, en in segs)


def test_calculate_smart_montage_uses_quality_segments_without_scene_cuts():
    q_segs = [
        {"start_sec": 0.0, "end_sec": 4.0, "quality_score": 0.15},
        {"start_sec": 10.0, "end_sec": 14.5, "quality_score": 0.94},
        {"start_sec": 25.0, "end_sec": 29.5, "quality_score": 0.89},
        {"start_sec": 40.0, "end_sec": 44.5, "quality_score": 0.86},
    ]
    segs = calculate_smart_montage_segments(
        total_duration=60.0,
        target_duration=12.0,
        scene_cuts=None,
        quality_segments=q_segs,
    )
    assert len(segs) >= 2
    assert all(st >= 9.0 for st, _ in segs)


@pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg/ffprobe not on PATH")
def test_1080p_trim_and_smooth_xfade_montage(tmp_path: Path):
    src = tmp_path / "src_1080p.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc2=s=1080x1920:r=30:d=8",
        "-f", "lavfi", "-i", "sine=frequency=520:duration=8",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "26",
        "-c:a", "aac", "-shortest",
        str(src),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr

    trimmed = tmp_path / "trimmed_1080p.mp4"
    t_res = trim_video_clip(src, trimmed, start_sec=2.0, end_sec=5.0, target_w=1080, target_h=1920)
    assert t_res["status"] == "success"
    t_meta = probe_video_stream(trimmed)
    assert t_meta["width"] == 1080 and t_meta["height"] == 1920
    assert 2.6 <= t_meta["duration"] <= 3.4

    dissolved = tmp_path / "dissolved_1080p.mp4"
    d_res = auto_smart_montage(
        src,
        dissolved,
        target_duration=6.0,
        preferred_scenes=[
            {"start_sec": 0.5, "end_sec": 3.5, "score": 0.9, "title": "مدخل", "narration_line": "رانا فالدخلة"},
            {"start_sec": 4.5, "end_sec": 7.5, "score": 0.95, "title": "حمام", "narration_line": "وهادا الحمام"},
        ],
        target_w=1080,
        target_h=1920,
        transition="fade",
        transition_dur=0.3,
    )
    assert d_res["status"] == "success"
    out_segs = d_res.get("output_segments", [])
    assert len(out_segs) == 2
    assert out_segs[0]["start_sec"] == 0.0
    assert out_segs[0]["narration_line"] == "رانا فالدخلة"
    assert out_segs[1]["narration_line"] == "وهادا الحمام"
    assert out_segs[0]["end_sec"] == out_segs[1]["start_sec"]
    d_meta = probe_video_stream(dissolved)
    assert d_meta["width"] == 1080 and d_meta["height"] == 1920
    assert d_meta["has_audio"] is True
    assert 5.0 <= d_meta["duration"] <= 6.2


def test_compute_output_segments_accounts_for_xfade_overlap():
    raw_segs = [(2.0, 6.0), (10.0, 15.0)]
    concat_map = _compute_output_segments(raw_segs, used_xfade=False, transition_dur=0.4)
    assert concat_map[0]["start_sec"] == 0.0 and concat_map[0]["end_sec"] == 4.0
    assert concat_map[1]["start_sec"] == 4.0 and concat_map[1]["end_sec"] == 9.0

    xfade_map = _compute_output_segments(raw_segs, used_xfade=True, transition_dur=0.4)
    assert xfade_map[0]["start_sec"] == 0.0 and xfade_map[0]["end_sec"] == 3.8
    assert xfade_map[1]["start_sec"] == 3.8 and xfade_map[1]["end_sec"] == 8.6

