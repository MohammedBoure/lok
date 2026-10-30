"""
Integration & Unit Test Suite for assemble_video.py
Part of the Video Post-Production & MCP Orchestration Pipeline.

Author: MouhammedBoure
Collective: Audio & Narration Specialist + Editorial Decision & Assembly Collective (agy51)
Branch: frontend/agy51-video-assembly-pipeline
"""

import json
import os
import subprocess
from pathlib import Path

import pytest

import assemble_video


def test_probe_file_inputs():
    """Verify that source video files and audio are successfully probed."""
    fox_meta = assemble_video.probe_file("inputs/source_fox_cub.mp4")
    assert "format" in fox_meta
    assert "streams" in fox_meta
    assert float(fox_meta["format"]["duration"]) >= 10.0

    squirrel_meta = assemble_video.probe_file("inputs/source_squirrel.mp4")
    assert "format" in squirrel_meta
    assert float(squirrel_meta["format"]["duration"]) >= 10.0


def test_ensure_narration_audio_metadata():
    """Verify narration audio format, duration, and sampling properties."""
    narration_info = assemble_video.ensure_narration_audio("outputs/narration.wav")
    assert os.path.exists(narration_info["audio_path"])
    assert narration_info["duration_seconds"] == pytest.approx(16.80, abs=0.1)
    assert narration_info["sample_rate"] == 24000
    assert narration_info["channels"] == 1
    assert narration_info["voice"] == "Aoede"


def test_find_matching_keyframes():
    """Verify keyframe extraction index matching within segment intervals."""
    matched_fox = assemble_video.find_matching_keyframes(
        "outputs/keyframes/frame_index.json",
        "source_fox_cub",
        0.0,
        8.5,
    )
    assert len(matched_fox) >= 5
    assert any(f["is_scene_transition"] for f in matched_fox)

    matched_squirrel = assemble_video.find_matching_keyframes(
        "outputs/keyframes/frame_index.json",
        "source_squirrel",
        0.5,
        9.5,
    )
    assert len(matched_squirrel) >= 5


def test_assemble_video_execution(tmp_path):
    """Test video assembly pipeline execution and deliverable verification."""
    test_out = tmp_path / "test_final_cut.mp4"
    test_summary = tmp_path / "test_summary.json"

    summary = assemble_video.assemble_video(
        fox_video="inputs/source_fox_cub.mp4",
        squirrel_video="inputs/source_squirrel.mp4",
        narration_audio="outputs/narration.wav",
        output_video=str(test_out),
        summary_output=str(test_summary),
        keyframe_index="outputs/keyframes/frame_index.json",
        fox_start=0.0,
        fox_end=8.5,
        squirrel_start=0.5,
        squirrel_end=9.5,
        transition_type="fade",
        transition_duration=0.5,
    )

    assert test_out.exists()
    assert test_out.stat().st_size > 1_000_000
    assert test_summary.exists()
    assert summary["status"] == "SUCCESS"
    assert summary["output_video"]["duration_seconds"] == pytest.approx(17.0, abs=0.1)
    assert summary["output_video"]["video_codec"] == "h264"
    assert summary["output_video"]["pixel_format"] == "yuv420p"
    assert summary["output_video"]["audio_codec"] == "aac"
    assert summary["output_video"]["audio_sample_rate"] == 48000
    assert summary["output_video"]["audio_channels"] == 2


def test_production_final_cut_deliverables():
    """Verify primary outputs exist, meet production standards, and summary is valid."""
    assert os.path.exists("outputs/final_cut.mp4")
    assert os.path.exists("outputs/narration.wav")
    assert os.path.exists("outputs/execution_summary.json")

    probe = assemble_video.probe_file("outputs/final_cut.mp4")
    v_stream = next(s for s in probe["streams"] if s["codec_type"] == "video")
    a_stream = next(s for s in probe["streams"] if s["codec_type"] == "audio")

    # Check video specs
    assert v_stream["codec_name"] == "h264"
    assert v_stream["pix_fmt"] == "yuv420p"
    assert int(v_stream["width"]) == 1280
    assert int(v_stream["height"]) == 720
    assert float(probe["format"]["duration"]) == pytest.approx(17.0, abs=0.1)

    # Check audio specs
    assert a_stream["codec_name"] == "aac"
    assert int(a_stream["channels"]) == 2
    assert int(a_stream["sample_rate"]) == 48000

    # Check summary json structure
    with open("outputs/execution_summary.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["status"] == "SUCCESS"
    assert "editorial_collective" in data
    assert data["editorial_collective"]["git_author"] == "MouhammedBoure"
    assert "source_clips" in data
    assert len(data["source_clips"]) == 2
    assert "editorial_timeline" in data
    assert "audio_mixing_parameters" in data
    assert "dynamic_ducking" in data["audio_mixing_parameters"]
    assert data["audio_mixing_parameters"]["dynamic_ducking"]["method"] == "Sidechain Compression (sidechaincompress filter)"
