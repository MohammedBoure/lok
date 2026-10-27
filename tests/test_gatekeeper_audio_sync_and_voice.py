#!/usr/bin/env python3
"""
Gatekeeper Integration Test Suite for Audio-Visual Sync, Dense Vision Sampling,
Voice Profile Selection, and UI Declutter (tests/test_gatekeeper_audio_sync_and_voice.py).

Quality Gatekeeper: agy100
Author: MohammedBoure <datasupabase@gmail.com>
Branch: test/agy100-audio-sync-and-voice-gatekeeper
Scope:
  1. Audio-Visual Lead-In Sync (adelay filtergraph insertion, visual_lead_in parameter).
  2. Dense Vision Sampling (8-16 keyframe uniform extraction, prompt injection across full timeline).
  3. Voice Selector & API Contract (ar-XA-Standard-A/B/C/D catalog, REST endpoints, persona mapping).
  4. UI Declutter Verification (prominent voice cards, collapsible advanced options, single CTA button).
  5. Character Mapping & Typography Compliance (no forbidden Arabic numeral U+0669).
"""

from __future__ import annotations

import io
import json
import os
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from starlette.testclient import TestClient

import assemble_video
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

REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = REPO_ROOT / "web" / "static"

client = TestClient(app)


# ---------------------------------------------------------------------------
# 1. Audio-Visual Lead-In Sync (adelay Filtergraph Verification)
# ---------------------------------------------------------------------------

class TestAudioVisualLeadInSync:
    """Verifies that speech narration is delayed so visual scenes and intro music establish first."""

    def test_assemble_video_adelay_filter_insertion(self, tmp_path: Path):
        """Verify assemble_video inserts adelay filter into FFmpeg filter_complex."""
        out_video = tmp_path / "final_cut.mp4"
        out_summary = tmp_path / "summary.json"

        captured_commands = []

        def mock_subprocess_run(cmd, *args, **kwargs):
            captured_commands.append(cmd)
            proc = MagicMock()
            proc.returncode = 0
            proc.stdout = ""
            proc.stderr = ""
            if isinstance(cmd, list) and "-filter_complex" in cmd:
                out_video.write_bytes(b"mock_mp4_content")
            return proc

        mock_probe_data = {
            "format": {"duration": "12.0", "size": "2048000"},
            "streams": [
                {"codec_type": "video", "codec_name": "h264", "width": 1280, "height": 720, "r_frame_rate": "30/1"},
                {"codec_type": "audio", "codec_name": "aac", "channels": 2, "sample_rate": "48000"},
            ],
        }

        mock_narration_data = {
            "audio_path": "outputs/narration.wav",
            "duration_seconds": 9.0,
            "sample_rate": 24000,
            "channels": 1,
            "codec": "pcm_s16le",
            "voice": "Charon",
            "model": "Gemini 2.5 Flash TTS",
            "script": "مرحبا بكم في جولة عقارية استثنائية",
        }

        with patch("assemble_video.probe_file", return_value=mock_probe_data), \
             patch("assemble_video.ensure_narration_audio", return_value=mock_narration_data), \
             patch("subprocess.run", side_effect=mock_subprocess_run):

            summary = assemble_video.assemble_video(
                fox_video="inputs/source_fox_cub.mp4",
                squirrel_video="inputs/source_squirrel.mp4",
                narration_audio="outputs/narration.wav",
                output_video=str(out_video),
                summary_output=str(out_summary),
                visual_lead_in=1.5,
            )

            assert summary["status"] == "SUCCESS"
            assert summary["narration"]["visual_lead_in_seconds"] == 1.5

            ffmpeg_cmd = next(c for c in captured_commands if isinstance(c, list) and "-filter_complex" in c)
            filter_arg = ffmpeg_cmd[ffmpeg_cmd.index("-filter_complex") + 1]

            # 1.5 seconds -> 1500 milliseconds for stereo channels
            assert "adelay=1500|1500" in filter_arg, f"Missing adelay=1500|1500 in filter_complex: {filter_arg}"

    def test_pipeline_bridge_adelay_and_default_lead_in(self, tmp_path: Path):
        """Verify process_mobile_video defaults to 1.2s lead-in and formats adelay properly."""
        dummy_input = tmp_path / "input_clip.mp4"
        dummy_input.write_bytes(b"dummy_video_bytes")

        captured_commands = []

        def mock_subprocess_run(cmd, *args, **kwargs):
            captured_commands.append(cmd)
            proc = MagicMock()
            proc.returncode = 0
            proc.stdout = ""
            proc.stderr = ""
            if isinstance(cmd, list) and any(str(c).endswith(".mp4") for c in cmd):
                for c in cmd:
                    if str(c).endswith(".mp4"):
                        Path(c).write_bytes(b"dummy_mp4_output")
            return proc

        mock_meta = {"width": 1080, "height": 1920, "total_duration": 14.0}
        mock_keyframes = {
            "frames": [
                {"frame_index": i, "timestamp": float(i + 1), "file_path": str(tmp_path / f"kf_{i}.jpg")}
                for i in range(8)
            ],
            "count": 8,
        }
        for i in range(8):
            (tmp_path / f"kf_{i}.jpg").write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01")

        mock_narration = {
            "audio_path": str(tmp_path / "voice.wav"),
            "duration": 8.0,
            "synthesizer": "gemini_tts",
        }

        with patch("web.pipeline_bridge.frame_extractor.get_video_metadata", return_value=mock_meta), \
             patch("web.pipeline_bridge.frame_extractor.extract_keyframes", return_value=mock_keyframes), \
             patch("web.pipeline_bridge.synthesize_narration", return_value=mock_narration), \
             patch("subprocess.run", side_effect=mock_subprocess_run):

            # Test default lead-in (1.2s)
            summary = process_mobile_video(
                video_path=dummy_input,
                script="شقة عصرية راقية للبيع في سيدي يحيى",
                preset_id="algiers_f4_luxury",
                voice="ar-XA-Standard-A",
                output_dir=tmp_path / "mobile_cuts",
            )

            assert summary["visual_lead_in_seconds"] == 1.2
            assert summary["outro_buffer_seconds"] == 1.2

            ffmpeg_cmd = next(c for c in captured_commands if isinstance(c, list) and "-filter_complex" in c)
            filter_arg = ffmpeg_cmd[ffmpeg_cmd.index("-filter_complex") + 1]
            # 1.2s -> 1200ms
            assert "adelay=1200|1200" in filter_arg


# ---------------------------------------------------------------------------
# 2. Dense Keyframe Sampling (8-16 Frames Across Duration)
# ---------------------------------------------------------------------------

class TestDenseVisionSampling:
    """Verifies that 8-16 representative keyframes are sampled across the full video timeline."""

    @pytest.mark.parametrize(
        "duration, expected_min, expected_max",
        [
            (3.0, 8, 8),    # Short duration hits lower floor (8)
            (8.0, 8, 12),   # Medium duration
            (16.0, 10, 16), # Standard mobile duration
            (45.0, 16, 16), # Long duration hits upper ceiling (16)
        ],
    )
    def test_compute_dense_keyframe_timestamps_bounds(self, duration: float, expected_min: int, expected_max: int):
        """Verify computed timestamps stay strictly within the 8 to 16 frame range."""
        ts = compute_dense_keyframe_timestamps(duration=duration, min_count=8, max_count=16)
        assert expected_min <= len(ts) <= expected_max
        assert ts == sorted(ts), "Timestamps must be strictly ascending"
        assert all(0.0 < t < duration for t in ts), "Timestamps must be inside (0, duration)"

        # Coverage verification: first timestamp near beginning, last near ending
        assert ts[0] < duration * 0.2, "First keyframe should cover the beginning scene"
        assert ts[-1] > duration * 0.8, "Last keyframe should cover the closing scene"

    def test_dense_sampling_speaking_window_and_prompt_injection(self, tmp_path: Path):
        """Verify infer_video_script_and_mood limits frames to 16 and computes correct speaking window."""
        dummy_frames = []
        for i in range(24):
            kf = tmp_path / f"frame_{i:02d}.jpg"
            kf.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb")
            dummy_frames.append(kf)

        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}, clear=False):
            result = infer_video_script_and_mood(
                keyframe_paths=dummy_frames,
                video_duration=20.0,
                preset_hint="oran_seaview_villa",
                visual_lead_in=1.5,
                outro_buffer=1.5,
            )

        # Analyzed frame count must be capped at 16
        assert 8 <= result["analyzed_frames_count"] <= 16
        assert result["visual_lead_in_seconds"] == 1.5
        # Net speaking window: 20.0 - 1.5 - 1.5 = 17.0s
        assert result["speech_duration"] == pytest.approx(17.0, abs=0.01)
        assert "script" in result
        assert len(result["script"]) > 15


# ---------------------------------------------------------------------------
# 3. Voice Selector & API Contract
# ---------------------------------------------------------------------------

class TestVoiceSelectorAndApiContract:
    """Verifies real estate voice profiles catalog and API parameter propagation."""

    def test_supported_voice_catalog_and_personas(self):
        """Verify all 4 Algerian real estate voice profiles map to designated Gemini personas."""
        expected_profiles = {
            "ar-XA-Standard-A": ("female", "Aoede"),
            "ar-XA-Standard-B": ("male", "Charon"),
            "ar-XA-Standard-C": ("male", "Fenrir"),
            "ar-XA-Standard-D": ("female", "Kore"),
        }

        catalog = get_voice_profiles_list()
        assert len(catalog) == 4

        for item in catalog:
            vid = item["id"]
            assert vid in expected_profiles
            gender, persona = expected_profiles[vid]
            assert item["gender"] == gender
            assert item["gemini_voice"] == persona
            assert VOICE_MAPPING[vid] == persona
            assert len(item["label"]) > 0
            assert len(item["description"]) > 0

    def test_resolve_voice_profile_normalizations(self):
        """Verify resolve_voice_profile handles whitespace, case variations, and fallbacks."""
        assert resolve_voice_profile("ar-XA-Standard-A") == ("ar-XA-Standard-A", "Aoede")
        assert resolve_voice_profile("  ar-xa-standard-b  ") == ("ar-XA-Standard-B", "Charon")
        assert resolve_voice_profile("AR-XA-STANDARD-C") == ("ar-XA-Standard-C", "Fenrir")
        assert resolve_voice_profile("ar-xa-standard-d") == ("ar-XA-Standard-D", "Kore")

        # Custom pass-through
        assert resolve_voice_profile("Puck") == ("Puck", "Puck")

        # Empty / None fallback to standard A
        assert resolve_voice_profile("") == ("ar-XA-Standard-A", "Aoede")
        assert resolve_voice_profile(None) == ("ar-XA-Standard-A", "Aoede")

    def test_get_voices_endpoint(self):
        """Verify GET /api/voices returns HTTP 200 with complete catalog."""
        resp = client.get("/api/voices")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("status") == "ok"
        assert "voices" in data
        assert len(data["voices"]) == 4
        ids = [v["id"] for v in data["voices"]]
        assert "ar-XA-Standard-A" in ids
        assert "ar-XA-Standard-B" in ids
        assert "ar-XA-Standard-C" in ids
        assert "ar-XA-Standard-D" in ids

    def test_post_jobs_create_receives_voice_and_lead_in(self):
        """Verify POST /api/jobs/create persists voice selection and visual lead-in."""
        fake_video = io.BytesIO(b"binary_fake_video_payload")
        payload = {
            "script": "فيلا فاخرة بتشطيبات ممتازة في وهران",
            "voice": "ar-XA-Standard-C",
            "visual_lead_in": "1.6",
            "duck_level": "0.18",
        }

        with patch("web.server._execute_processing_job") as mock_exec:
            res = client.post(
                "/api/jobs/create",
                data=payload,
                files={"video": ("sample_villa.mp4", fake_video, "video/mp4")},
            )
            assert res.status_code == 202
            body = res.json()
            assert body.get("status") == "processing"
            assert body.get("voice") == "ar-XA-Standard-C"
            assert body.get("visual_lead_in_seconds") == 1.6

            job_id = body.get("job_id")
            assert job_id in PROGRESS_STORE
            assert PROGRESS_STORE[job_id]["voice"] == "ar-XA-Standard-C"
            assert PROGRESS_STORE[job_id]["visual_lead_in"] == 1.6

            mock_exec.assert_called_once()
            call_args = mock_exec.call_args[0]
            assert call_args[4] == "ar-XA-Standard-C"  # voice parameter
            assert call_args[12] == 1.6                 # visual_lead_in parameter


# ---------------------------------------------------------------------------
# 4. Mobile UI Declutter & Clean Layout Verification
# ---------------------------------------------------------------------------

class TestMobileUiDeclutter:
    """Verifies decluttered UI: prominent voice cards, single produce CTA, clean collapsible options."""

    def test_index_html_voice_cards_and_single_produce_cta(self):
        """Verify index.html contains prominent voice cards and no duplicate visible produce buttons."""
        html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")

        # 1. Voice selector card on main screen
        assert 'id="voiceSelectionCard"' in html
        assert 'id="mainVoiceCardsGrid"' in html
        assert 'id="voiceCardStandardA"' in html
        assert 'id="voiceCardStandardB"' in html
        assert 'id="voiceCardStandardC"' in html
        assert 'id="voiceCardStandardD"' in html

        # Radio buttons for all 4 profiles
        for vid in ["ar-XA-Standard-A", "ar-XA-Standard-B", "ar-XA-Standard-C", "ar-XA-Standard-D"]:
            assert f'value="{vid}"' in html

        # 2. Collapsible advanced options
        assert '<details class="advanced-accordion" id="advancedAccordion">' in html
        assert '<summary class="accordion-summary" id="accordionSummary">' in html

        # 3. Single prominent production CTA container
        assert '<div class="production-cta-container">' in html
        assert 'id="btnProduce"' in html

        # 4. Ensure #submitBtn is demoted to screen-reader alias and not a duplicate button
        assert 'id="submitBtn" class="sr-only"' in html

    def test_style_css_voice_and_declutter_classes(self):
        """Verify style.css provides styling for voice selection and clean card layouts."""
        css = (STATIC_DIR / "style.css").read_text(encoding="utf-8")

        # Voice selection styles
        assert ".voice-selector-card" in css
        assert ".voice-cards-grid" in css
        assert ".voice-card" in css
        assert ".voice-card.active" in css
        assert ".voice-radio-marker" in css

        # Decluttered CTA and collapsible styles
        assert ".production-cta-container" in css
        assert ".terminal-collapsible" in css

    def test_app_js_voice_binding_and_localstorage_persistence(self):
        """Verify app.js manages voice card selection, localStorage persistence, and FormData binding."""
        js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")

        # Storage keys & setup functions
        assert "preferred_voice" in js
        assert "PREF_VOICE_KEY" in js
        assert "setupVoiceSelector" in js
        assert "applyVoiceSelectionToUI" in js

        # FormData binding
        assert 'formData.append("voice"' in js


# ---------------------------------------------------------------------------
# 5. Typography & Character Mapping Compliance (User Rule 5)
# ---------------------------------------------------------------------------

class TestTypographyCharacterMapping:
    """Verifies that the forbidden Arabic numeral ٩ (U+0669) is not present in code or deliverables."""

    @pytest.mark.parametrize(
        "relative_path",
        [
            "web/static/index.html",
            "web/static/style.css",
            "web/static/app.js",
            "web/pipeline_bridge.py",
            "web/server.py",
            "web/vision_analyzer.py",
            "assemble_video.py",
        ],
    )
    def test_no_forbidden_arabic_character(self, relative_path: str):
        """Ensure U+0669 is strictly absent from deliverables (must use Arabic letter 'ج')."""
        file_path = REPO_ROOT / relative_path
        content = file_path.read_text(encoding="utf-8")
        assert "\u0669" not in content, f"Forbidden Arabic numeral U+0669 detected in {relative_path}"
