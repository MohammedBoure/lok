"""
Quality Gatekeeper Integration & Mobile Pipeline Verification Suite
File: tests/test_mobile_verification.py
Author: MohammedBoure
Role: Quality Gatekeeper & Integration Testing (agy100)
Branch: develop
"""

import json
import os
import re
import socket
import subprocess
import wave
from pathlib import Path
from unittest.mock import patch

import pytest
from starlette.routing import Route, Mount

from web.pipeline_bridge import (
    ALGERIAN_REAL_ESTATE_PRESETS,
    DEFAULT_PROMO_SCRIPT,
    get_presets_list,
    generate_synthetic_voice,
    process_mobile_video,
)
from web.run_server import detect_lan_ip
from web.server import app


# ---------------------------------------------------------------------------
# 1. Preset Catalog & Audio Synthesis Verification
# ---------------------------------------------------------------------------

def test_algerian_presets_metadata_completeness():
    """Verify all real estate presets define complete bilingual metadata and descriptions."""
    required_keys = {"id", "title_ar", "title_fr", "description"}
    assert len(ALGERIAN_REAL_ESTATE_PRESETS) >= 4

    for preset_id, data in ALGERIAN_REAL_ESTATE_PRESETS.items():
        assert preset_id == data["id"]
        missing = required_keys - set(data.keys())
        assert not missing, f"Preset {preset_id} is missing keys: {missing}"
        assert len(data["title_ar"]) > 0
        assert len(data["title_fr"]) > 0
        assert len(data["description"]) > 0


def test_algerian_presets_descriptions_arabic():
    """Verify real estate preset descriptions contain proper Algerian real estate terminology."""
    keywords = ["شقة", "فيلا", "محل", "كراء"]
    all_descriptions = " ".join(p["description"] for p in ALGERIAN_REAL_ESTATE_PRESETS.values())
    for kw in keywords:
        assert kw in all_descriptions, f"Keyword '{kw}' missing from presets descriptions"


def test_synthetic_voice_wav_header_and_duration(tmp_path: Path):
    """Verify synthetic speech generation produces valid 24kHz 16-bit PCM WAV."""
    out_wav = tmp_path / "test_synth.wav"
    script = "شقة رائعة في الجزائر العاصمة تطل على البحر"
    duration = generate_synthetic_voice(script, out_wav)

    assert out_wav.exists()
    assert out_wav.stat().st_size > 1000
    assert duration >= 3.0

    with wave.open(str(out_wav), "rb") as wf:
        assert wf.getframerate() == 24000
        assert wf.getsampwidth() == 2  # 16-bit PCM
        assert wf.getnchannels() in (1, 2)
        calc_duration = wf.getnframes() / wf.getframerate()
        assert abs(calc_duration - duration) < 0.1


def test_synthetic_voice_empty_text_fallback(tmp_path: Path):
    """Verify empty or blank text falls back to default promotional narration."""
    out_wav = tmp_path / "fallback_synth.wav"
    duration = generate_synthetic_voice("   ", out_wav)

    assert out_wav.exists()
    assert out_wav.stat().st_size > 1000
    assert duration >= 3.0


def test_pipeline_bridge_get_presets_list_structure():
    """Verify get_presets_list serializes all presets correctly for client consumption."""
    presets = get_presets_list()
    assert isinstance(presets, list)
    assert len(presets) == len(ALGERIAN_REAL_ESTATE_PRESETS)
    for p in presets:
        assert "id" in p
        assert "title_ar" in p
        assert "title_fr" in p
        assert "description" in p


# ---------------------------------------------------------------------------
# 2. Pipeline Execution & Error Boundaries
# ---------------------------------------------------------------------------

def test_process_mobile_video_missing_file_raises_error():
    """Verify process_mobile_video raises FileNotFoundError when source file does not exist."""
    missing_path = Path("/tmp/definitely_non_existent_video_12345.mp4")
    with pytest.raises(FileNotFoundError):
        process_mobile_video(missing_path, preset_id="algiers_f4_luxury")


def test_process_mobile_video_unsupported_preset_fallback(tmp_path: Path):
    """Verify unknown preset ID gracefully falls back to default promo narration."""
    video_path = tmp_path / "fallback_sample.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=navy:s=360x640:d=1.0",
        "-f", "lavfi", "-i", "sine=f=440:d=1.0",
        "-c:v", "libx264", "-preset", "ultrafast",
        "-c:a", "aac",
        "-t", "1.0",
        str(video_path),
    ]
    subprocess.run(cmd, capture_output=True, check=True)

    result = process_mobile_video(
        video_path=video_path,
        preset_id="unknown_preset_xyz",
        output_dir=tmp_path / "out",
    )

    assert result["status"] == "completed"
    assert result["script"] == DEFAULT_PROMO_SCRIPT
    assert Path(result["output_path"]).exists()


def test_mobile_video_summary_metadata_schema(tmp_path: Path):
    """Verify execution summary JSON contains all required audit and metrics fields."""
    video_path = tmp_path / "summary_sample.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=black:s=360x640:d=1.0",
        "-f", "lavfi", "-i", "sine=f=500:d=1.0",
        "-c:v", "libx264", "-preset", "ultrafast",
        "-c:a", "aac",
        "-t", "1.0",
        str(video_path),
    ]
    subprocess.run(cmd, capture_output=True, check=True)

    result = process_mobile_video(
        video_path=video_path,
        preset_id="oran_seaview_villa",
        output_dir=tmp_path / "out",
    )

    job_id = result["job_id"]
    summary_file = tmp_path / "out" / f"summary_{job_id}.json"
    assert summary_file.exists()
    with open(summary_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["job_id"] == job_id
    assert data["status"] == "completed"
    assert "metadata" in data
    assert "source_duration" in data["metadata"]
    assert "narration_duration" in data["metadata"]
    assert "keyframes" in data
    assert isinstance(data["keyframes"], list)


def test_mobile_video_custom_ducking_volume(tmp_path: Path):
    """Verify custom ducking level override is respected during video post-production."""
    video_path = tmp_path / "duck_sample.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=darkblue:s=360x640:d=1.0",
        "-f", "lavfi", "-i", "sine=f=440:d=1.0",
        "-c:v", "libx264", "-preset", "ultrafast",
        "-c:a", "aac",
        "-t", "1.0",
        str(video_path),
    ]
    subprocess.run(cmd, capture_output=True, check=True)

    custom_duck = 0.12
    result = process_mobile_video(
        video_path=video_path,
        preset_id="algiers_f4_luxury",
        duck_level=custom_duck,
        output_dir=tmp_path / "out",
    )

    assert result["duck_level"] == custom_duck


# ---------------------------------------------------------------------------
# 3. Network, Routing & Server Verification
# ---------------------------------------------------------------------------

def test_lan_ip_detection_format():
    """Verify LAN IP detection produces a valid IPv4 address."""
    ip = detect_lan_ip()
    assert re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", ip)
    octets = [int(o) for o in ip.split(".")]
    assert all(0 <= o <= 255 for o in octets)


def test_lan_ip_fallback_handling():
    """Verify detect_lan_ip falls back to preferred IP when sockets fail."""
    with patch("socket.socket") as mock_sock, patch("socket.gethostname") as mock_host:
        mock_instance = mock_sock.return_value.__enter__.return_value
        mock_instance.connect.side_effect = OSError("Network unreachable")
        mock_host.side_effect = OSError("DNS lookup failed")
        ip = detect_lan_ip(preferred_fallback="10.0.0.99")
        assert ip == "10.0.0.99"


def test_server_app_routes_registered():
    """Verify Starlette application registers all expected API endpoints and static mounts."""
    route_paths = []
    for route in app.routes:
        if isinstance(route, Route):
            route_paths.append(route.path)
        elif isinstance(route, Mount):
            route_paths.append(route.path)

    expected = [
        "/api/upload-and-process",
        "/api/presets",
        "/api/health",
        "/api/status/{job_id}",
        "/",
        "/static",
        "/outputs",
    ]
    for exp in expected:
        assert exp in route_paths, f"Expected route '{exp}' not found in registered routes: {route_paths}"


# ---------------------------------------------------------------------------
# 4. Mobile Front-End & Typography Compliance
# ---------------------------------------------------------------------------

def test_mobile_html_responsive_viewport_and_pwa_tags():
    """Verify mobile HTML defines required responsive viewport and PWA meta tags."""
    index_file = Path("web/static/index.html")
    assert index_file.exists()
    content = index_file.read_text(encoding="utf-8")

    assert '<meta name="viewport"' in content
    assert 'width=device-width' in content
    assert 'initial-scale=1.0' in content
    assert 'mobile-web-app-capable' in content or 'apple-mobile-web-app-capable' in content


def test_mobile_html_arabic_rtl_and_character_mapping():
    """Verify RTL layout and User Rule 5 character mapping compliance (no raw '٩')."""
    index_file = Path("web/static/index.html")
    content = index_file.read_text(encoding="utf-8")

    assert 'dir="rtl"' in content
    assert 'lang="ar"' in content

    # User Rule 5: character '٩' must never be used as text where 'ج' is intended
    app_js_file = Path("web/static/app.js")
    app_js = app_js_file.read_text(encoding="utf-8")
    assert "٩" not in app_js, "Found forbidden character '٩' in app.js"


def test_mobile_css_responsive_media_queries():
    """Verify responsive CSS breakpoints for mobile smartphones."""
    css_file = Path("web/static/style.css")
    assert css_file.exists()
    content = css_file.read_text(encoding="utf-8")

    assert "@media" in content
    assert "max-width" in content
    assert "--gold-400" in content or "gold" in content
    assert "--emerald-500" in content or "emerald" in content


def test_concurrent_synthetic_voice_generation(tmp_path: Path):
    """Verify thread-safe generation of synthetic audio across parallel workers."""
    import concurrent.futures

    scripts = [
        ("فيديو رقم 1 لفيلا وهران", tmp_path / "voice_1.wav"),
        ("فيديو رقم 2 لشقة العاصمة", tmp_path / "voice_2.wav"),
        ("فيديو رقم 3 لمكتب قسنطينة", tmp_path / "voice_3.wav"),
    ]

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [
            executor.submit(generate_synthetic_voice, text, out_file)
            for text, out_file in scripts
        ]
        results = [f.result() for f in futures]

    assert len(results) == 3
    for dur, (_, out_file) in zip(results, scripts):
        assert dur >= 3.0
        assert out_file.exists()
        assert out_file.stat().st_size > 1000
