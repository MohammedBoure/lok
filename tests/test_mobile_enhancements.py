#!/usr/bin/env python3
"""
Test Suite for Mobile Enhancements: Real Gemini TTS, Open-Source Music, and Live Agent Telemetry.
"""

import os
import pytest
from pathlib import Path
from starlette.testclient import TestClient

from web.pipeline_bridge import (
    MUSIC_LIBRARY,
    VOICE_MAPPING,
    get_music_tracks_list,
    process_mobile_video,
    synthesize_narration,
)
from web.server import app

client = TestClient(app)


def test_music_library_catalog():
    """Verify open-source music library catalog and file existence."""
    tracks = get_music_tracks_list()
    assert len(tracks) >= 3
    track_ids = [t["id"] for t in tracks]
    assert "luxury_piano" in track_ids
    assert "acoustic_guitar" in track_ids
    assert "ambient_meditation" in track_ids

    for mid, info in MUSIC_LIBRARY.items():
        assert Path(info["file"]).is_file(), f"Music file for {mid} must exist on disk"
        assert info["license"], f"License must be provided for {mid}"


def test_voice_mapping_to_gemini():
    """Verify voice mapping resolves to valid Gemini personas."""
    assert VOICE_MAPPING["ar-xa-standard-a"] == "Aoede"
    assert VOICE_MAPPING["ar-xa-standard-b"] == "Charon"
    assert VOICE_MAPPING["female"] == "Aoede"
    assert VOICE_MAPPING["male"] == "Charon"


def test_api_music_tracks_endpoint():
    """Test GET /api/music-tracks endpoint returns JSON list."""
    response = client.get("/api/music-tracks")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 3
    assert any(t["id"] == "luxury_piano" for t in data)


def test_api_async_job_creation_and_telemetry(tmp_path):
    """Test POST /api/jobs/create and subsequent status polling."""
    # Create minimal test video
    import subprocess
    test_video = tmp_path / "test_mini.mp4"
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", "testsrc=duration=2:size=320x240:rate=15",
        "-f", "lavfi", "-i", "sine=frequency=1000:duration=2",
        "-c:v", "libx264", "-preset", "ultrafast",
        "-c:a", "aac", str(test_video)
    ]
    subprocess.run(cmd, capture_output=True, check=True)

    with open(test_video, "rb") as f:
        response = client.post(
            "/api/jobs/create",
            files={"video": ("test_mini.mp4", f, "video/mp4")},
            data={"preset": "algiers_f4_luxury", "music": "luxury_piano"},
        )

    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "processing"

    job_id = data["job_id"]
    status_resp = client.get(f"/api/status/{job_id}")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["job_id"] == job_id
    assert "status" in status_data
    assert "message" in status_data


def test_process_mobile_video_with_real_music(tmp_path):
    """Test video assembly using real open-source acoustic piano music."""
    import subprocess
    test_video = tmp_path / "test_real_music.mp4"
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", "testsrc=duration=3:size=640x360:rate=24",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
        "-c:v", "libx264", "-preset", "ultrafast",
        "-c:a", "aac", str(test_video)
    ]
    subprocess.run(cmd, capture_output=True, check=True)

    telemetry_events = []

    def on_progress(evt):
        telemetry_events.append(evt)

    summary = process_mobile_video(
        video_path=test_video,
        script="شقة عصرية راقية للبيع",
        music_track="luxury_piano",
        output_dir=tmp_path / "cuts",
        progress_callback=on_progress,
    )

    assert summary["status"] == "completed"
    assert Path(summary["output_path"]).is_file()
    assert summary["music_track"]["id"] == "luxury_piano"
    assert len(telemetry_events) >= 4, "Progress callback should capture pipeline milestones"
