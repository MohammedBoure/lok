#!/usr/bin/env python3
"""
Test Suite for Vision Script Inference, Emotional Tone Passing, and app.py Root Entrypoint.
(tests/test_vision_script_and_app.py)

Author: MouhammedBoure
Role: Backend Architecture & Processing Bridge (agy11)
Branch: backend/agy11-auto-vision-script-and-app-runner
"""

import json
import os
import subprocess
import time
from pathlib import Path
import pytest
from starlette.testclient import TestClient
from PIL import Image

from app import detect_lan_ip, print_banner
from tts.gemini_speech.client import GeminiSpeechClient
from web.pipeline_bridge import process_mobile_video
from web.server import app
from web.vision_analyzer import _get_smart_fallback, infer_video_script_and_mood

client = TestClient(app)


# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def short_test_video(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Generate a lightweight 3.0s MP4 video fixture with color shifts mimicking scenes."""
    tmp_dir = tmp_path_factory.mktemp("vision_fixtures")
    video_path = tmp_dir / "short_property_clip.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=duration=3:size=480x640:rate=20",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
        "-c:v", "libx264", "-preset", "ultrafast",
        "-c:a", "aac",
        "-t", "3.0",
        str(video_path),
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return video_path


@pytest.fixture
def dummy_keyframe_images(tmp_path: Path) -> list[Path]:
    """Generate sample JPEG keyframe images for vision analysis testing."""
    img_paths = []
    colors = [(220, 200, 180), (140, 180, 210), (160, 210, 160)]
    for idx, col in enumerate(colors):
        p = tmp_path / f"frame_{idx:03d}.jpg"
        img = Image.new("RGB", (320, 240), color=col)
        img.save(p, format="JPEG")
        img_paths.append(p)
    return img_paths


# ---------------------------------------------------------------------------
# Vision Analyzer Tests
# ---------------------------------------------------------------------------

def test_smart_vision_fallback_logic():
    """Verify that offline / fallback vision inference returns valid schema and presets."""
    fb1 = _get_smart_fallback(duration=10.0, preset_hint="algiers_f4_luxury")
    assert "script" in fb1 and len(fb1["script"]) > 10
    assert fb1["emotional_tone"] == "فاخر وهادئ"
    assert fb1["recommended_music"] == "luxury_piano"
    assert fb1["engine"] == "smart_vision_fallback"

    fb2 = _get_smart_fallback(duration=12.0, preset_hint="oran_seaview_villa")
    assert fb2["emotional_tone"] == "دافئ وأنيق"
    assert fb2["recommended_music"] == "ambient_meditation"

    fb3 = _get_smart_fallback(duration=8.0, preset_hint="constantine_commercial")
    assert fb3["emotional_tone"] == "متحمس وحيوي"
    assert fb3["recommended_music"] == "acoustic_guitar"


def test_infer_video_script_and_mood_execution(dummy_keyframe_images: list[Path]):
    """Test multimodal vision inference (live Gemini API or smart fallback)."""
    result = infer_video_script_and_mood(
        keyframe_paths=dummy_keyframe_images,
        video_duration=8.0,
    )
    assert isinstance(result, dict)
    assert "script" in result and len(result["script"]) > 10
    assert "emotional_tone" in result and result["emotional_tone"]
    assert "emotional_prompt" in result and result["emotional_prompt"]
    assert result["recommended_music"] in ("luxury_piano", "acoustic_guitar", "ambient_meditation")
    assert result["engine"] in ("gemini_multimodal_vision", "smart_vision_fallback")


# ---------------------------------------------------------------------------
# TTS Emotional Tone Modulation Tests
# ---------------------------------------------------------------------------

def test_gemini_speech_client_emotional_tone_parameters():
    """Verify GeminiSpeechClient.generate_speech accepts emotional_tone and style_prompt."""
    client_tts = GeminiSpeechClient()
    # Test method signature accepts keywords without TypeError
    import inspect
    sig = inspect.signature(client_tts.generate_speech)
    assert "emotional_tone" in sig.parameters
    assert "style_prompt" in sig.parameters
    assert "voice_style_prompt" in sig.parameters


# ---------------------------------------------------------------------------
# Pipeline Bridge Auto-Mode & Telemetry Tests
# ---------------------------------------------------------------------------

def test_process_mobile_video_auto_mode(short_test_video: Path, tmp_path: Path):
    """Test process_mobile_video in autonomous vision mode and verify telemetry events."""
    logs_received = []

    def on_progress(evt):
        if evt.get("log"):
            logs_received.append(evt["log"])

    cuts_dir = tmp_path / "auto_cuts"
    summary = process_mobile_video(
        video_path=short_test_video,
        auto_mode=True,
        output_dir=cuts_dir,
        progress_callback=on_progress,
    )

    assert summary["status"] == "completed"
    assert summary["auto_mode"] is True
    assert summary["emotional_tone"] is not None
    assert summary["inferred_script"] is not None
    assert Path(summary["output_path"]).is_file()

    # Check that required telemetry log events were generated
    logs_str = " ".join(logs_received)
    assert "🖼️ استخراج لقطات المعاينة البصرية من الفيديو..." in logs_str
    assert "🧠 تحليل المشاهد المعمارية عبر Gemini Multimodal Vision..." in logs_str
    assert "✨ تم استنتاج الوصف التسويقي والحالة الشعورية:" in logs_str
    assert "🎙️ توليد التعليق الصوتي العصبي بالحالة الشعورية المحددة..." in logs_str


# ---------------------------------------------------------------------------
# REST API Endpoints Auto-Mode Tests
# ---------------------------------------------------------------------------

def test_api_upload_and_process_auto_mode(short_test_video: Path):
    """Test POST /api/upload-and-process with auto_mode=true."""
    with open(short_test_video, "rb") as f:
        resp = client.post(
            "/api/upload-and-process",
            files={"video": ("auto_sample.mp4", f, "video/mp4")},
            data={"auto_mode": "true"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["auto_mode"] is True
    assert "emotional_tone" in data and data["emotional_tone"]
    assert "inferred_script" in data and data["inferred_script"]
    assert data["video_url"].startswith("/outputs/mobile_cuts/cut_")


def test_api_jobs_create_auto_mode(short_test_video: Path):
    """Test POST /api/jobs/create with auto_mode=true and query /api/status/{job_id}."""
    with open(short_test_video, "rb") as f:
        resp = client.post(
            "/api/jobs/create",
            files={"video": ("auto_async.mp4", f, "video/mp4")},
            data={"auto_mode": "true", "emotional_tone": "فاخر وهادئ"},
        )
    assert resp.status_code == 202
    res_data = resp.json()
    job_id = res_data["job_id"]
    assert res_data["auto_mode"] is True
    assert res_data["emotional_tone"] == "فاخر وهادئ"

    # Query status endpoint
    status_resp = client.get(f"/api/status/{job_id}")
    assert status_resp.status_code == 200
    s_data = status_resp.json()
    assert s_data["job_id"] == job_id
    assert "status" in s_data
    assert "emotional_tone" in s_data


# ---------------------------------------------------------------------------
# Root app.py Tests
# ---------------------------------------------------------------------------

def test_app_py_lan_ip_detection():
    """Verify app.py detect_lan_ip() detects valid IPv4 address."""
    ip = detect_lan_ip()
    assert isinstance(ip, str)
    parts = ip.split(".")
    assert len(parts) == 4
    for p in parts:
        assert p.isdigit() and 0 <= int(p) <= 255


def test_app_py_banner_output(capsys: pytest.CaptureFixture):
    """Verify app.py print_banner() executes cleanly without exception."""
    print_banner(lan_ip="192.168.1.7", port=8000)
    out = capsys.readouterr().out
    assert "ALGERIAN REAL ESTATE AI VIDEO STUDIO" in out
    assert "http://localhost:8000" in out
    assert "http://192.168.1.7:8000" in out
