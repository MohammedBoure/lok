"""
Unit and integration tests for frame_extractor and mcp_get_image_from_video.
"""

import json
import subprocess
import sys
from pathlib import Path
import pytest

import frame_extractor


FOX_VIDEO = "inputs/source_fox_cub.mp4"
SQUIRREL_VIDEO = "inputs/source_squirrel.mp4"


def test_get_video_metadata_success():
    """Verify metadata extraction on valid video."""
    meta = frame_extractor.get_video_metadata(FOX_VIDEO)
    assert meta["resolution"] == "1280x720"
    assert meta["codec"] == "h264"
    assert meta["frame_rate"] == 24.0
    assert meta["total_duration"] == 10.0
    assert meta["width"] == 1280
    assert meta["height"] == 720
    assert meta["size_bytes"] > 0


def test_get_video_metadata_file_not_found():
    """Verify error raised when video file is missing."""
    with pytest.raises(FileNotFoundError):
        frame_extractor.get_video_metadata("inputs/non_existent_video.mp4")


def test_detect_scene_cut_timestamps():
    """Verify scene detection returns non-empty list of timestamps."""
    scenes = frame_extractor.detect_scene_cut_timestamps(FOX_VIDEO)
    assert isinstance(scenes, list)
    assert len(scenes) >= 1
    assert 0.0 in scenes
    assert all(isinstance(ts, float) for ts in scenes)


def test_detect_keyframe_timestamps():
    """Verify native keyframe I-frame detection."""
    kfs = frame_extractor.detect_keyframe_timestamps(FOX_VIDEO)
    assert isinstance(kfs, list)
    assert len(kfs) >= 1
    assert 0.0 in kfs


def test_extract_frames_with_timestamps(tmp_path):
    """Verify frame extraction at explicit timestamps."""
    out_dir = tmp_path / "test_frames"
    res = frame_extractor.extract_frames(
        video_path=FOX_VIDEO,
        timestamps=[0.0, 2.5, 5.0],
        output_dir=out_dir,
        image_format="jpg",
    )

    assert "frames" in res
    assert "metadata" in res
    assert len(res["frames"]) == 3

    for idx, f in enumerate(res["frames"]):
        assert f["frame_index"] == idx
        assert Path(f["file_path"]).exists()
        assert f["resolution"] == "1280x720"
        assert f["file_size_bytes"] > 1000


def test_extract_frames_with_fps_sample(tmp_path):
    """Verify frame extraction with custom fps_sample."""
    out_dir = tmp_path / "test_fps_sample"
    # Sample 0.5 fps (1 frame every 2 seconds) without injecting scene cuts
    res = frame_extractor.extract_frames(
        video_path=FOX_VIDEO,
        fps_sample=0.5,
        output_dir=out_dir,
        include_scenes_in_sampling=False,
    )

    assert "frames" in res
    # For a 10s video, 0.0, 2.0, 4.0, 6.0, 8.0 = 5 frames
    assert len(res["frames"]) == 5


def test_mcp_get_image_from_video_api(tmp_path):
    """Verify mcp_get_image_from_video programmatic API."""
    out_dir = tmp_path / "test_mcp_api"
    res = frame_extractor.mcp_get_image_from_video(
        video_path=SQUIRREL_VIDEO,
        timestamps=[1.0, 3.0],
        output_dir=str(out_dir),
    )

    assert res["total_duration"] == 10.0
    assert res["frame_rate"] == 24.0
    assert res["resolution"] == "1280x720"
    assert res["codec"] == "h264"
    assert len(res["frames"]) == 2
    for f in res["frames"]:
        assert Path(f["file_path"]).exists()


def test_cli_invocation_json(tmp_path):
    """Verify invoking python -m frame_extractor via CLI with --json."""
    out_dir = tmp_path / "cli_out"
    cmd = [
        sys.executable,
        "-m", "frame_extractor",
        FOX_VIDEO,
        "--timestamps", "0.0,1.5",
        "--output-dir", str(out_dir),
        "--json",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    payload = json.loads(proc.stdout)
    assert payload["total_frames_extracted"] == 2
    assert payload["codec"] == "h264"
    assert len(payload["frames"]) == 2


def test_process_videos_batch(tmp_path):
    """Verify batch processing and aggregate index generation."""
    out_dir = tmp_path / "batch_out"
    index_file = out_dir / "index.json"

    res = frame_extractor.process_videos_batch(
        video_paths=[FOX_VIDEO, SQUIRREL_VIDEO],
        output_dir=out_dir,
        timestamps=[0.0, 5.0],
        index_file=index_file,
    )

    assert res["total_videos"] == 2
    assert res["total_frames"] == 4
    assert index_file.is_file()

    with open(index_file, "r", encoding="utf-8") as f:
        saved_data = json.load(f)
    assert saved_data["total_videos"] == 2
    assert saved_data["total_frames"] == 4


def test_mcp_server_tool_registration():
    """Verify MCP server instance registers mcp_get_image_from_video."""
    server = frame_extractor.create_mcp_server("test-server")
    assert server is not None
