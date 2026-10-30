"""
Tests for Mobile API Server & Video Post-Production Bridge (tests/test_mobile_api.py)

Author: MouhammedBoure
Role: Backend Architecture & Processing Bridge (agy11)
Branch: backend/agy11-mobile-api-server
"""

import json
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Generator

import pytest
import requests
import uvicorn

from web.pipeline_bridge import (
    ALGERIAN_REAL_ESTATE_PRESETS,
    get_presets_list,
    generate_synthetic_voice,
    process_mobile_video,
)
from web.run_server import detect_lan_ip, print_server_banner
from web.server import app


# ---------------------------------------------------------------------------
# Test Fixtures & Utilities
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def sample_portrait_video(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Generate a lightweight 2.5s vertical (720x1280) MP4 video fixture."""
    tmp_dir = tmp_path_factory.mktemp("video_fixtures")
    video_path = tmp_dir / "sample_portrait.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=navy:s=720x1280:d=2.5",
        "-f", "lavfi", "-i", "sine=f=440:d=2.5",
        "-c:v", "libx264", "-preset", "ultrafast",
        "-c:a", "aac",
        "-t", "2.5",
        str(video_path),
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return video_path


@pytest.fixture(scope="session")
def sample_landscape_video(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Generate a lightweight 2.0s horizontal (1280x720) MP4 video fixture."""
    tmp_dir = tmp_path_factory.mktemp("video_fixtures")
    video_path = tmp_dir / "sample_landscape.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=darkgreen:s=1280x720:d=2.0",
        "-f", "lavfi", "-i", "sine=f=330:d=2.0",
        "-c:v", "libx264", "-preset", "ultrafast",
        "-c:a", "aac",
        "-t", "2.0",
        str(video_path),
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return video_path


@pytest.fixture(scope="session")
def test_server_port() -> int:
    """Designate an isolated local port for test uvicorn instance."""
    return 8988


@pytest.fixture(scope="session")
def live_server(test_server_port: int) -> Generator[str, None, None]:
    """Launch background Uvicorn server for end-to-end HTTP integration testing."""
    server_url = f"http://127.0.0.1:{test_server_port}"

    def run_app():
        uvicorn.run(app, host="127.0.0.1", port=test_server_port, log_level="error")

    thread = threading.Thread(target=run_app, daemon=True)
    thread.start()

    # Poll until responsive
    for _ in range(30):
        try:
            r = requests.get(f"{server_url}/api/health", timeout=1.0)
            if r.status_code == 200:
                break
        except Exception:
            time.sleep(0.1)
    else:
        raise RuntimeError("Test server failed to start.")

    yield server_url


# ---------------------------------------------------------------------------
# Unit Tests: Presets & Audio Synthesis
# ---------------------------------------------------------------------------

def test_algerian_presets_catalog():
    """Verify all required Algerian real estate presets are present and valid."""
    required_keys = [
        "algiers_f4_luxury",
        "oran_seaview_villa",
        "constantine_commercial",
        "rental_apartment",
    ]
    for key in required_keys:
        assert key in ALGERIAN_REAL_ESTATE_PRESETS, f"Missing preset: {key}"
        preset = ALGERIAN_REAL_ESTATE_PRESETS[key]
        assert "title_ar" in preset and preset["title_ar"]
        assert "title_fr" in preset and preset["title_fr"]
        assert "description" in preset and len(preset["description"]) > 20

    presets_list = get_presets_list()
    assert len(presets_list) == 4
    preset_ids = [p["id"] for p in presets_list]
    for rk in required_keys:
        assert rk in preset_ids


def test_synthetic_voice_generation(tmp_path: Path):
    """Verify synthetic speech generation produces valid playable WAV audio."""
    wav_path = tmp_path / "test_synth_audio.wav"
    dur = generate_synthetic_voice(
        text="فيلا عصرية بواجهة بحرية خلابة في وهران",
        output_path=wav_path,
        sample_rate=24000,
    )
    assert dur > 2.0
    assert wav_path.is_file()
    assert wav_path.stat().st_size > 1000

    # Probe WAV with ffprobe
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "stream=codec_name,sample_rate,channels",
        "-of", "json",
        str(wav_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    probe = json.loads(res.stdout)
    stream = probe["streams"][0]
    assert stream["codec_name"] == "pcm_s16le"
    assert stream["sample_rate"] == "24000"
    assert stream["channels"] == 1


# ---------------------------------------------------------------------------
# Pipeline Engine Tests: Portrait & Landscape Video Processing
# ---------------------------------------------------------------------------

def test_process_mobile_video_portrait(sample_portrait_video: Path, tmp_path: Path):
    """Test full processing pipeline on portrait (9:16) mobile recording."""
    cuts_dir = tmp_path / "mobile_cuts"
    summary = process_mobile_video(
        video_path=sample_portrait_video,
        preset_id="algiers_f4_luxury",
        duck_level=0.25,
        output_dir=cuts_dir,
    )

    assert summary["status"] == "completed"
    assert summary["orientation"] == "portrait"
    assert summary["aspect_ratio"] == "9:16"
    assert summary["preset_id"] == "algiers_f4_luxury"
    assert "cut_" in summary["output_path"]
    assert Path(summary["output_path"]).is_file()
    assert Path(summary["output_path"]).stat().st_size > 50000

    # Verify keyframes
    keyframes = summary["keyframes"]
    assert len(keyframes) >= 1
    for kf in keyframes:
        assert "url" in kf
        assert "timestamp" in kf
        assert Path(kf["file_path"]).is_file()


def test_process_mobile_video_landscape_custom_script(sample_landscape_video: Path, tmp_path: Path):
    """Test full processing pipeline on landscape (16:9) video with custom script."""
    cuts_dir = tmp_path / "mobile_cuts"
    custom_script = "فرصة ذهبية لامتلاك شقة فاخرة ومطلة في موقع استراتيجي لا يعوض."
    summary = process_mobile_video(
        video_path=sample_landscape_video,
        script=custom_script,
        duck_level=0.15,
        output_dir=cuts_dir,
    )

    assert summary["status"] == "completed"
    assert summary["orientation"] == "landscape"
    assert summary["aspect_ratio"] == "16:9"
    assert summary["script"] == custom_script
    assert summary["preset_id"] is None
    assert summary["duck_level"] == 0.15
    assert Path(summary["output_path"]).is_file()


# ---------------------------------------------------------------------------
# API Server & HTTP Integration Tests
# ---------------------------------------------------------------------------

def test_api_health_endpoint(live_server: str):
    """Test GET /api/health."""
    r = requests.get(f"{live_server}/api/health", timeout=5.0)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["agent"] == "agy11"


def test_api_presets_endpoint(live_server: str):
    """Test GET /api/presets."""
    r = requests.get(f"{live_server}/api/presets", timeout=5.0)
    assert r.status_code == 200
    presets = r.json()
    assert isinstance(presets, list)
    assert len(presets) == 4
    ids = {p["id"] for p in presets}
    assert "algiers_f4_luxury" in ids
    assert "oran_seaview_villa" in ids


def test_api_index_endpoint(live_server: str):
    """Test GET / returns HTML mobile studio frontend."""
    r = requests.get(f"{live_server}/", timeout=5.0)
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "استوديو عقارات الجزائر" in r.text


def test_api_upload_and_process_endpoint(live_server: str, sample_portrait_video: Path):
    """Test POST /api/upload-and-process with multipart form data."""
    with open(sample_portrait_video, "rb") as f:
        files = {"video": ("my_phone_recording.mp4", f, "video/mp4")}
        data = {
            "preset": "constantine_commercial",
            "voice": "ar-XA-Standard-A",
            "duck_level": "0.30",
        }
        r = requests.post(
            f"{live_server}/api/upload-and-process",
            files=files,
            data=data,
            timeout=30.0,
        )

    assert r.status_code == 200
    res = r.json()
    job_id = res["job_id"]
    assert res["status"] == "completed"
    assert res["preset_id"] == "constantine_commercial"
    assert res["video_url"].startswith("/outputs/mobile_cuts/cut_")
    assert len(res["keyframes"]) >= 1

    # Test GET /api/status/{job_id}
    r_status = requests.get(f"{live_server}/api/status/{job_id}", timeout=5.0)
    assert r_status.status_code == 200
    status_data = r_status.json()
    assert status_data["job_id"] == job_id
    assert status_data["status"] == "completed"

    # Test static serving of rendered cut
    r_media = requests.head(f"{live_server}{res['video_url']}", timeout=5.0)
    assert r_media.status_code == 200
    assert "video/mp4" in r_media.headers.get("content-type", "")


def test_api_status_not_found(live_server: str):
    """Test GET /api/status/{job_id} for a non-existent job."""
    r = requests.get(f"{live_server}/api/status/non_existent_job_12345", timeout=5.0)
    assert r.status_code == 404
    assert r.json()["status"] == "not_found"


def test_api_upload_missing_video(live_server: str):
    """Test POST /api/upload-and-process with missing video file."""
    r = requests.post(f"{live_server}/api/upload-and-process", data={"preset": "algiers_f4_luxury"}, timeout=5.0)
    assert r.status_code == 400
    assert "error" in r.json()


# ---------------------------------------------------------------------------
# LAN IP & QR Code Launcher Tests
# ---------------------------------------------------------------------------

def test_detect_lan_ip():
    """Verify LAN IP detection returns a valid IPv4 string."""
    ip = detect_lan_ip()
    assert isinstance(ip, str)
    parts = ip.split(".")
    assert len(parts) == 4
    for p in parts:
        assert p.isdigit() and 0 <= int(p) <= 255


def test_server_banner_execution(capsys: pytest.CaptureFixture):
    """Verify banner printer prints without errors and contains expected URLs."""
    print_server_banner(lan_ip="192.168.1.7", port=8000)
    captured = capsys.readouterr()
    assert "http://192.168.1.7:8000" in captured.out
    assert "ALGERIAN REAL ESTATE MOBILE VIDEO STUDIO" in captured.out
