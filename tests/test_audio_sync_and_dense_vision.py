#!/usr/bin/env python3
"""
Test Suite for Audio-Visual Lead-In Synchronization, Dense Vision Sampling,
and Algerian Real Estate Voice Profile Routing (tests/test_audio_sync_and_dense_vision.py).

Author: MohammedBoure
Role: Backend Logic & Systems Engineer (agy11)
Branch: backend/agy11-audio-sync-and-dense-vision-sampling
"""

from __future__ import annotations

import io
import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from starlette.testclient import TestClient

import assemble_video
from web import prompt_db
from web.pipeline_bridge import (
    SUPPORTED_VOICE_PROFILES,
    VOICE_MAPPING,
    compute_dense_keyframe_timestamps,
    get_voice_profiles_list,
    process_mobile_video,
    resolve_voice_profile,
    synthesize_narration,
)
from web.server import PROGRESS_STORE, app
from web.vision_analyzer import _get_smart_fallback, infer_video_script_and_mood

client = TestClient(app)


# ---------------------------------------------------------------------------
# 1. Voice Selection & Profile Routing Tests
# ---------------------------------------------------------------------------

def test_supported_voice_profiles_catalog():
    """Verify that all 4 required real estate voice profiles exist with expected metadata."""
    assert "ar-XA-Standard-A" in SUPPORTED_VOICE_PROFILES
    assert "ar-XA-Standard-B" in SUPPORTED_VOICE_PROFILES
    assert "ar-XA-Standard-C" in SUPPORTED_VOICE_PROFILES
    assert "ar-XA-Standard-D" in SUPPORTED_VOICE_PROFILES

    # Verify Gemini TTS persona mappings
    assert VOICE_MAPPING["ar-XA-Standard-A"] == "Aoede"
    assert VOICE_MAPPING["ar-XA-Standard-B"] == "Charon"
    assert VOICE_MAPPING["ar-XA-Standard-C"] == "Fenrir"
    assert VOICE_MAPPING["ar-XA-Standard-D"] == "Kore"

    profiles = get_voice_profiles_list()
    assert len(profiles) == 4
    for prof in profiles:
        assert "id" in prof
        assert "gender" in prof
        assert "label" in prof
        assert "gemini_voice" in prof
        assert "description" in prof


def test_resolve_voice_profile():
    """Verify profile resolution for standard, case-insensitive, and custom voices."""
    assert resolve_voice_profile("ar-XA-Standard-A") == ("ar-XA-Standard-A", "Aoede")
    assert resolve_voice_profile("ar-xa-standard-b") == ("ar-XA-Standard-B", "Charon")
    assert resolve_voice_profile("  ar-XA-Standard-C  ") == ("ar-XA-Standard-C", "Fenrir")
    assert resolve_voice_profile("ar-XA-Standard-D") == ("ar-XA-Standard-D", "Kore")

    # Custom voice string passthrough
    assert resolve_voice_profile("Zephyr") == ("Zephyr", "Zephyr")
    assert resolve_voice_profile("Puck") == ("Puck", "Puck")

    # Empty fallback
    assert resolve_voice_profile("") == ("ar-XA-Standard-A", "Aoede")
    assert resolve_voice_profile(None) == ("ar-XA-Standard-A", "Aoede")


def test_get_voices_rest_endpoint():
    """Verify GET /api/voices returns the structured catalog of real estate voice profiles."""
    response = client.get("/api/voices")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "voices" in data
    assert len(data["voices"]) == 4

    voice_ids = [v["id"] for v in data["voices"]]
    assert "ar-XA-Standard-A" in voice_ids
    assert "ar-XA-Standard-B" in voice_ids
    assert "ar-XA-Standard-C" in voice_ids
    assert "ar-XA-Standard-D" in voice_ids


def test_synthesize_narration_voice_routing(tmp_path: Path):
    """Verify synthesize_narration resolves voice profile and passes correct persona to TTS client."""
    out_wav = tmp_path / "narration_test.wav"

    def fake_generate_speech(text, voice_name, output_path, **kwargs):
        Path(output_path).write_bytes(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00")

    mock_client = MagicMock()
    mock_client.generate_speech.side_effect = fake_generate_speech

    with patch.dict(os.environ, {"GEMINI_API_KEY": "mock_api_key"}), \
         patch("tts.gemini_speech.client.GeminiSpeechClient", return_value=mock_client), \
         patch("web.pipeline_bridge.get_media_duration", return_value=4.5):
        narration_info = synthesize_narration(
            script_text="شقة فاخرة للبيع في وهران",
            output_path=out_wav,
            voice="ar-XA-Standard-B",
            emotional_tone="فاخر وهادئ",
        )
        assert narration_info["synthesizer"] == "gemini_tts"
        # Must have mapped ar-XA-Standard-B to Charon
        mock_client.generate_speech.assert_called_once()
        call_kwargs = mock_client.generate_speech.call_args[1]
        assert call_kwargs["voice_name"] == "Charon"
        assert call_kwargs["emotional_tone"] == "فاخر وهادئ"


# ---------------------------------------------------------------------------
# 2. Dense Keyframe Extraction (8-16 Keyframes) Tests
# ---------------------------------------------------------------------------

def test_compute_dense_keyframe_timestamps_distribution():
    """Verify dense keyframe timestamp generation across various video durations."""
    # 1. Typical 10-second mobile video: should sample ~10 uniform frames
    ts_10s = compute_dense_keyframe_timestamps(duration=10.0, min_count=8, max_count=16)
    assert 8 <= len(ts_10s) <= 16
    assert all(0.0 < t < 10.0 for t in ts_10s)
    # Check strictly monotonic increasing order
    assert ts_10s == sorted(ts_10s)
    # Check boundary coverage: first is close to start (~5%), last is close to end (~95%)
    assert ts_10s[0] == pytest.approx(0.5, abs=0.2)
    assert ts_10s[-1] == pytest.approx(9.5, abs=0.2)

    # 2. Short 3-second video: should sample min_count (8 frames)
    ts_3s = compute_dense_keyframe_timestamps(duration=3.0, min_count=8, max_count=16)
    assert len(ts_3s) == 8
    assert all(0.0 < t < 3.0 for t in ts_3s)

    # 3. Longer 30-second video: should sample max_count (16 frames)
    ts_30s = compute_dense_keyframe_timestamps(duration=30.0, min_count=8, max_count=16)
    assert len(ts_30s) == 16
    assert all(0.0 < t < 30.0 for t in ts_30s)


def test_vision_dense_sampling_and_speaking_window():
    """Verify that vision analyzer samples up to 16 frames and computes net speaking window."""
    # Test smart fallback with visual_lead_in=1.2s and outro_buffer=1.2s on 12.0s video
    res = _get_smart_fallback(
        duration=12.0,
        preset_hint="oran_seaview_villa",
        visual_lead_in=1.2,
        outro_buffer=1.2,
        keyframe_count=16,
    )

    # Net speaking window: 12.0 - 1.2 - 1.2 = 9.6s
    assert res["speech_duration"] == pytest.approx(9.6, abs=0.01)
    assert res["visual_lead_in_seconds"] == 1.2
    assert res["analyzed_frames_count"] == 16
    assert "script" in res
    assert "emotional_tone" in res

    # Verify target word count pacing (~2.2 words/sec): 9.6 * 2.2 ~= 21 words
    words = res["script"].split()
    assert len(words) <= 35, "Script should stay within target duration pacing"


def test_infer_video_script_dense_subsampling(tmp_path: Path):
    """Verify infer_video_script_and_mood subsamples frames down to maximum 16."""
    mock_frames = []
    for i in range(25):
        f = tmp_path / f"frame_{i:02d}.jpg"
        f.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb")
        mock_frames.append(f)

    # Force fallback branch to test frame count logic without live Gemini API network calls
    with patch.dict(os.environ, {"GEMINI_API_KEY": ""}, clear=False):
        res = infer_video_script_and_mood(
            keyframe_paths=mock_frames,
            video_duration=15.0,
            preset_hint="algiers_f4_luxury",
            visual_lead_in=1.2,
            outro_buffer=1.2,
        )

    # Subsampling must limit analyzed keyframes to at most 16
    assert res["analyzed_frames_count"] <= 16
    assert res["analyzed_frames_count"] >= 8
    assert res["visual_lead_in_seconds"] == 1.2
    assert res["speech_duration"] == pytest.approx(15.0 - 1.2 - 1.2, abs=0.01)


# ---------------------------------------------------------------------------
# 3. Audio-Visual Synchronization (adelay Lead-In) Tests
# ---------------------------------------------------------------------------

def test_assemble_video_adelay_filter(tmp_path: Path):
    """Verify assemble_video applies FFmpeg adelay filter for visual establishing lead-in."""
    test_out = tmp_path / "test_out.mp4"
    test_summary = tmp_path / "test_summary.json"

    recorded_ffmpeg_cmds = []

    def mock_run(cmd, *args, **kwargs):
        recorded_ffmpeg_cmds.append(cmd)
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = ""
        mock_proc.stderr = ""
        # Create output file if ffmpeg assembly command
        if isinstance(cmd, list) and "-filter_complex" in cmd:
            test_out.write_bytes(b"dummy_mp4_bytes")
        return mock_proc

    mock_probe = {
        "format": {"duration": "10.0", "size": "1000000"},
        "streams": [
            {"codec_type": "video", "codec_name": "h264", "width": 1280, "height": 720, "r_frame_rate": "30/1"},
            {"codec_type": "audio", "codec_name": "aac", "channels": 2, "sample_rate": "48000"},
        ],
    }

    mock_narration_meta = {
        "audio_path": "outputs/narration.wav",
        "duration_seconds": 8.0,
        "sample_rate": 24000,
        "channels": 1,
        "codec": "pcm_s16le",
        "voice": "Charon",
        "model": "Gemini 2.5 Flash TTS",
        "script": "Deep in the heart of the autumn forest...",
    }

    with patch("assemble_video.probe_file", return_value=mock_probe), \
         patch("assemble_video.ensure_narration_audio", return_value=mock_narration_meta), \
         patch("subprocess.run", side_effect=mock_run):

        summary = assemble_video.assemble_video(
            fox_video="inputs/source_fox_cub.mp4",
            squirrel_video="inputs/source_squirrel.mp4",
            narration_audio="outputs/narration.wav",
            output_video=str(test_out),
            summary_output=str(test_summary),
            visual_lead_in=1.3,
        )

        assert summary["status"] == "SUCCESS"
        assert summary["narration"]["visual_lead_in_seconds"] == 1.3

        # Locate ffmpeg assembly command
        assembly_cmd = next(c for c in recorded_ffmpeg_cmds if isinstance(c, list) and "-filter_complex" in c)
        filter_str = assembly_cmd[assembly_cmd.index("-filter_complex") + 1]

        # Verify adelay on narration stream [2:a]
        # 1.3s -> 1300ms
        assert "adelay=1300|1300" in filter_str, f"Expected adelay=1300|1300 in filter_complex, got: {filter_str}"


def test_pipeline_bridge_adelay_audio_sync(tmp_path: Path):
    """Verify process_mobile_video applies adelay lead-in filter during final mixing."""
    test_video = tmp_path / "mobile_input.mp4"
    test_video.write_bytes(b"dummy_video_data")

    recorded_ffmpeg_cmds = []

    def mock_run(cmd, *args, **kwargs):
        recorded_ffmpeg_cmds.append(cmd)
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = ""
        mock_proc.stderr = ""
        # If output cut specified, write dummy file
        if isinstance(cmd, list) and any(str(c).endswith(".mp4") for c in cmd):
            for c in cmd:
                if str(c).endswith(".mp4"):
                    Path(c).write_bytes(b"dummy_rendered_video")
        return mock_proc

    mock_meta = {
        "width": 720,
        "height": 1280,
        "total_duration": 10.0,
    }

    for i in range(4):
        (tmp_path / f"k{i}.jpg").write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb")

    mock_keyframes = {
        "frames": [
            {"frame_index": 0, "timestamp": 1.0, "file_path": str(tmp_path / "k0.jpg"), "is_scene_transition": True},
            {"frame_index": 1, "timestamp": 3.0, "file_path": str(tmp_path / "k1.jpg"), "is_scene_transition": False},
            {"frame_index": 2, "timestamp": 5.0, "file_path": str(tmp_path / "k2.jpg"), "is_scene_transition": False},
            {"frame_index": 3, "timestamp": 7.0, "file_path": str(tmp_path / "k3.jpg"), "is_scene_transition": False},
        ],
        "count": 4,
    }

    mock_narration_res = {
        "audio_path": str(tmp_path / "narration.wav"),
        "duration": 5.0,
        "synthesizer": "gemini_tts",
    }

    with patch("web.pipeline_bridge.frame_extractor.get_video_metadata", return_value=mock_meta), \
         patch("web.pipeline_bridge.frame_extractor.extract_keyframes", return_value=mock_keyframes), \
         patch("web.pipeline_bridge.synthesize_narration", return_value=mock_narration_res), \
         patch("subprocess.run", side_effect=mock_run):

        summary = process_mobile_video(
            video_path=test_video,
            script="فيلا فاخرة للإيجار في الجزائر العاصمة",
            preset_id="algiers_f4_luxury",
            voice="ar-XA-Standard-C",
            output_dir=tmp_path / "cuts",
            visual_lead_in=1.2,
            outro_buffer=1.2,
        )

        assert summary["visual_lead_in_seconds"] == 1.2
        assert summary["outro_buffer_seconds"] == 1.2
        assert summary["voice"] == "ar-XA-Standard-C"
        assert summary["gemini_voice"] == "Fenrir"
        assert summary["analyzed_frames_count"] >= 4

        # Locate assembly command and verify adelay=1200|1200
        assembly_cmd = next(c for c in recorded_ffmpeg_cmds if isinstance(c, list) and "-filter_complex" in c)
        filter_str = assembly_cmd[assembly_cmd.index("-filter_complex") + 1]
        assert "adelay=1200|1200" in filter_str, f"Expected adelay=1200|1200 in filter_complex, got: {filter_str}"


# ---------------------------------------------------------------------------
# 4. Asynchronous & Synchronous Server Ingestion with Lead-In & Voice
# ---------------------------------------------------------------------------

def test_api_jobs_create_with_voice_and_lead_in():
    """Verify POST /api/jobs/create validates, persists, and returns voice and visual_lead_in."""
    dummy_file = io.BytesIO(b"fake_video_stream")
    form_data = {
        "script": "شقة أنيقة في حي راقٍ",
        "voice": "ar-XA-Standard-D",
        "visual_lead_in": "1.4",
        "speech_description": "وصف صوتي لفخامة الشقة",
        "visual_description": "صالون كبير وإطلالة على المدينة",
    }

    with patch("web.server._execute_processing_job") as mock_exec:
        response = client.post(
            "/api/jobs/create",
            data=form_data,
            files={"video": ("test_apartment.mp4", dummy_file, "video/mp4")},
        )
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "processing"
        assert data["voice"] == "ar-XA-Standard-D"
        assert data["visual_lead_in_seconds"] == 1.4

        job_id = data["job_id"]
        assert job_id in PROGRESS_STORE
        assert PROGRESS_STORE[job_id]["voice"] == "ar-XA-Standard-D"
        assert PROGRESS_STORE[job_id]["visual_lead_in"] == 1.4

        # Verify background thread was invoked with visual_lead_in=1.4
        mock_exec.assert_called_once()
        args = mock_exec.call_args[0]
        # args: (job_id, saved_path, script, preset, voice, duck_level, music, auto_mode, emotional_tone, visual_desc, speech_desc, prompt_id, visual_lead_in)
        assert args[4] == "ar-XA-Standard-D"
        assert args[12] == 1.4
