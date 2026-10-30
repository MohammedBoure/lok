#!/usr/bin/env python3
"""
Comprehensive Test Suite: Prompt Intent Disentanglement & Persistent Video Overlays
Verifies:
1. Extraction of Algerian phone numbers (05/06/07 and international prefixes).
2. Distinguishing meta-prompt instructions from literal voiceover narration.
3. Ensuring Gemini TTS NEVER speaks user meta-prompt instructions word-for-word.
4. FFmpeg drawtext filter generation for persistent bottom text / phone overlays
   (black@0.6 semi-transparent box, white text, fontsize 28, centered at y=h-text_h-40).
5. Job status API and upload endpoints exposing script, bottom_text, and phone_number.
6. Zero occurrences of forbidden character U+0669.

Author: MohammedBoure
Branch: backend/agy11-prompt-intent-parser-and-persistent-overlays
"""

from __future__ import annotations

import io
import json
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from starlette.testclient import TestClient

from web.pipeline_bridge import (
    extract_algerian_phone,
    extract_directives,
    is_meta_prompt,
    parse_prompt_instructions,
    process_mobile_video,
    sanitize_script_against_meta_prompts,
)
from web.server import PROGRESS_STORE, app
from web.video_annotator import _build_drawtext_filter
from web.vision_analyzer import _get_smart_fallback


USER_SAMPLE_PROMPT = (
    "أريد أن يظهر نص أسفل الفيديو به الرقم التالي طول ما الفيديو شغال 0558815453 "
    "يظهر النص التالي و أيضا أريد أن يكون هناك تعليق صوتي يتناسب مع الفيديو و محتواه و بالدارجة"
)


class TestPromptIntentAndDirectives:
    """Verify phone extraction and directive disentanglement logic."""

    def test_extract_algerian_phone_various_formats(self):
        """Test extraction and normalization of Algerian phone numbers across formats."""
        cases = [
            ("0558815453", "0558815453"),
            ("0558 81 54 53", "0558815453"),
            ("0558-81-54-53", "0558815453"),
            ("+213558815453", "0558815453"),
            ("+213 558 81 54 53", "0558815453"),
            ("00213558815453", "0558815453"),
            ("0661223344", "0661223344"),
            ("0770-12-34-56", "0770123456"),
            (USER_SAMPLE_PROMPT, "0558815453"),
        ]
        for input_text, expected_phone in cases:
            extracted = extract_algerian_phone(input_text)
            assert extracted == expected_phone, f"Failed on: {input_text} -> {extracted}"

    def test_is_meta_prompt_detection(self):
        """Test differentiation between meta instructions and literal narration."""
        meta_prompts = [
            USER_SAMPLE_PROMPT,
            "أريد فيديو تسويقي لفيلا فخمة في وهران",
            "اجعل التعليق الصوتي دافئ وضيف رقم الهاتف 0661223344 في الأسفل",
            "اكتب نص تسويقي بالدارجة مع إظهار رقم 0558815453",
            "يرجى وضع شريط سفلي به الرقم 0770123456 طوال الفيديو",
        ]
        for mp in meta_prompts:
            assert is_meta_prompt(mp) is True, f"Should be identified as meta-prompt: {mp}"

        literal_scripts = [
            "شوفو معايا هاد الشقة الفاخرة F4 في قلب العاصمة، فينيسيون متقونة وإطلالة شابة بزاف.",
            "فيلا عصرية بواجهة بحرية ساحرة في وهران، حديقة ومسبح خاص وتصميم راقي.",
            "محل تجاري في موقع استراتيجي حيوي في قسنطينة، واجهة واسعة وحركة ممتازة.",
        ]
        for ls in literal_scripts:
            assert is_meta_prompt(ls) is False, f"Should be identified as literal narration: {ls}"

    def test_extract_directives_user_sample_prompt(self):
        """Test complete extraction of directives from user's actual prompt."""
        dirs = extract_directives(USER_SAMPLE_PROMPT)
        assert dirs["is_meta_prompt"] is True
        assert dirs["phone_number"] == "0558815453"
        assert dirs["bottom_text"] == "0558815453"
        assert dirs["darja_requested"] is True
        assert dirs["voiceover_requested"] is True
        assert dirs["persistent_overlay"] is True

    def test_parse_prompt_instructions_includes_directives(self):
        """Test parse_prompt_instructions incorporates directive analysis."""
        parsed = parse_prompt_instructions(f"{USER_SAMPLE_PROMPT} speed: 1.1")
        assert parsed["phone_number"] == "0558815453"
        assert parsed["is_meta_prompt"] is True
        assert parsed["speed"] == 1.1

    def test_sanitize_script_against_meta_prompts(self):
        """Test sanitization removes labeling and prevents echoing user meta-instructions."""
        raw_llm_output = "السيناريو: شوفو معايا هاد الشقة الفاخرة في قلب المدينة."
        cleaned = sanitize_script_against_meta_prompts(raw_llm_output)
        assert cleaned == "شوفو معايا هاد الشقة الفاخرة في قلب المدينة."
        assert not cleaned.startswith("السيناريو:")

        # If pure meta-prompt is passed as script, it must be replaced with Darja narration
        meta_as_script = USER_SAMPLE_PROMPT
        sanitized = sanitize_script_against_meta_prompts(meta_as_script)
        assert "أريد أن يظهر" not in sanitized
        assert "0558815453" not in sanitized
        assert "عقار استثنائي" in sanitized or "شوفو معايا" in sanitized


class TestPersistentBottomOverlayFFmpeg:
    """Verify FFmpeg drawtext filter generation for persistent bottom text & phone overlays."""

    def test_persistent_bottom_overlay_drawtext_filter_syntax(self):
        """Verify exact styling properties for persistent bottom text overlays."""
        annotation = {
            "text": "0558815453",
            "style": "persistent_bottom",
            "position": "bottom_banner",
            "start_sec": 0.0,
            "end_sec": 12.0,
            "persistent": True,
        }
        filter_str = _build_drawtext_filter(annotation)

        # Centered at bottom with safe margin
        assert "x=(w-text_w)/2" in filter_str
        assert "y=h-text_h-" in filter_str

        # Semi-transparent high-contrast black background box
        assert "box=1" in filter_str
        assert "boxcolor=black@" in filter_str

        # Clear white text
        assert "fontcolor=white" in filter_str

        # Persistent across video duration (from 0.00 to 12.00)
        assert "between(t,0.00,12.00)" in filter_str

    def test_persistent_bottom_default_positioning_when_style_specified(self):
        """Verify position defaults to bottom center when style is persistent_bottom."""
        annotation = {
            "text": "اتصلوا بنا: 0558815453",
            "style": "persistent_bottom",
        }
        filter_str = _build_drawtext_filter(annotation)
        assert "y=h-text_h-" in filter_str
        assert "x=(w-text_w)/2" in filter_str
        assert "boxcolor=black@" in filter_str


class TestTTSNeverSpeaksMetaPrompts:
    """Verify Gemini TTS voiceover engine never receives user meta-prompt instructions."""

    def test_smart_fallback_never_interpolates_meta_prompts(self):
        """Test _get_smart_fallback does NOT interpolate meta-prompts into spoken script."""
        fb = _get_smart_fallback(
            duration=12.0,
            speech_description=USER_SAMPLE_PROMPT,
            visual_lead_in=1.2,
            outro_buffer=1.2,
        )
        script = fb.get("script", "")
        # Meta-prompt words MUST NOT appear in the spoken narration
        assert "أريد أن يظهر" not in script
        assert "طول ما الفيديو شغال" not in script
        assert "0558815453" not in script
        # Valid Algerian Darja narration must be generated
        assert "عقار استثنائي" in script or "شوفو معايا" in script or "فيلا" in script
        # Directives should be exposed in fallback result
        assert fb.get("phone_number") == "0558815453"
        assert fb.get("bottom_text") == "0558815453"

    @patch("web.video_annotator.annotate_video")
    @patch("web.pipeline_bridge.synthesize_narration")
    @patch("subprocess.run")
    @patch("frame_extractor.extract_keyframes")
    @patch("frame_extractor.get_video_metadata")
    def test_process_mobile_video_disentangles_meta_prompt_from_tts(
        self,
        mock_meta,
        mock_kf,
        mock_subproc,
        mock_tts,
        mock_annotate,
        tmp_path,
    ):
        """Verify process_mobile_video does not pass user instructions to TTS when passed as script."""
        mock_meta.return_value = {"width": 1080, "height": 1920, "total_duration": 10.0}
        mock_kf.return_value = {"frames": []}
        mock_tts.return_value = {
            "wav_path": str(tmp_path / "mock.wav"),
            "duration": 5.0,
            "synthesizer": "mock_gemini_tts",
        }
        mock_annotate.return_value = {"status": "ok"}

        def fake_ffmpeg_run(cmd, *args, **kwargs):
            if isinstance(cmd, list) and len(cmd) > 0:
                out_path = Path(cmd[-1])
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_bytes(b"fake_mp4_cut_data")
            return MagicMock(returncode=0, stdout="", stderr="")

        mock_subproc.side_effect = fake_ffmpeg_run

        # Create dummy source video file
        dummy_video = tmp_path / "input.mp4"
        dummy_video.write_bytes(b"dummy video data")

        # User passes the meta-prompt in the script parameter!
        summary = process_mobile_video(
            video_path=dummy_video,
            script=USER_SAMPLE_PROMPT,
            output_dir=tmp_path / "outputs",
            voice="ar-XA-Standard-A",
        )

        # Inspect what was passed to synthesize_narration
        mock_tts.assert_called_once()
        tts_script_arg = mock_tts.call_args.kwargs.get("script", "")

        # CRITICAL ASSERTIONS:
        # TTS engine was NOT given the meta-prompt instructions
        assert "أريد أن يظهر" not in tts_script_arg
        assert "طول ما الفيديو شغال" not in tts_script_arg
        assert "0558815453" not in tts_script_arg

        # The summary correctly holds the extracted phone and persistent bottom text
        assert summary.get("phone_number") == "0558815453"
        assert summary.get("bottom_text") == "0558815453"
        assert summary.get("auto_mode") is True


class TestStatusApiExposesScriptAndOverlays:
    """Verify /api/jobs/create and /api/status/{job_id} expose script and overlays."""

    @patch("web.server._execute_processing_job")
    def test_create_job_async_disentangles_meta_prompt_and_exposes_directives(
        self,
        mock_exec,
    ):
        """Test that POST /api/jobs/create extracts phone & bottom_text and marks auto_mode."""
        client = TestClient(app)
        # Login to obtain active session
        r_login = client.post("/api/auth/login", json={"username": "oran_seafood_bistro", "password": "merchant123"})
        assert r_login.status_code == 200
        sess_token = r_login.json()["session_token"]

        video_bytes = b"fake MP4 video binary header content"
        files = {
            "video": ("recording.mp4", io.BytesIO(video_bytes), "video/mp4"),
        }
        data = {
            "prompt": USER_SAMPLE_PROMPT,
        }

        resp = client.post("/api/jobs/create", data=data, files=files, headers={"Authorization": f"Bearer {sess_token}"})
        assert resp.status_code == 202

        body = resp.json()
        assert body["status"] == "processing"
        assert body.get("phone_number") == "0558815453"
        assert body.get("bottom_text") == "0558815453"
        assert body.get("auto_mode") is True

        job_id = body["job_id"]
        # In PROGRESS_STORE, phone_number and bottom_text should be stored
        assert PROGRESS_STORE[job_id]["phone_number"] == "0558815453"
        assert PROGRESS_STORE[job_id]["bottom_text"] == "0558815453"

    def test_status_endpoint_returns_script_and_overlay_fields(self, tmp_path):
        """Test GET /api/status/{job_id} includes script, bottom_text, and phone_number."""
        client = TestClient(app)

        test_job_id = "job_test_overlays_456"
        cut_file = Path("outputs/mobile_cuts") / f"cut_{test_job_id}.mp4"
        cut_file.parent.mkdir(parents=True, exist_ok=True)
        cut_file.write_bytes(b"dummy mp4 cut")

        try:
            PROGRESS_STORE[test_job_id] = {
                "job_id": test_job_id,
                "status": "completed",
                "step": 5,
                "progress": 100,
                "progress_percent": 100,
                "video_url": f"/outputs/mobile_cuts/cut_{test_job_id}.mp4",
                "script": "شوفو معايا هاد الشقة الفاخرة بتشطيبات عصرية وإطلالة ممتازة.",
                "bottom_text": "0558815453",
                "phone_number": "0558815453",
                "result": {
                    "job_id": test_job_id,
                    "status": "completed",
                    "script": "شوفو معايا هاد الشقة الفاخرة بتشطيبات عصرية وإطلالة ممتازة.",
                    "bottom_text": "0558815453",
                    "phone_number": "0558815453",
                    "video_url": f"/outputs/mobile_cuts/cut_{test_job_id}.mp4",
                },
            }

            resp = client.get(f"/api/status/{test_job_id}")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "completed"
            assert data["script"] == "شوفو معايا هاد الشقة الفاخرة بتشطيبات عصرية وإطلالة ممتازة."
            assert data["bottom_text"] == "0558815453"
            assert data["phone_number"] == "0558815453"
        finally:
            if cut_file.is_file():
                cut_file.unlink()
            PROGRESS_STORE.pop(test_job_id, None)


def test_no_forbidden_arabic_character_in_repository():
    """Verify zero occurrences of forbidden Arabic character U+0669 across repository."""
    repo_root = Path(__file__).resolve().parent.parent
    tracked_extensions = {".py", ".html", ".js", ".css", ".md", ".json"}
    excluded_dirs = {".git", ".pytest_cache", "venv", ".venv", "__pycache__"}

    violations = []
    for root, dirs, files in os.walk(repo_root):
        dirs[:] = [d for d in dirs if d not in excluded_dirs]
        for f in files:
            p = Path(root) / f
            if p.suffix in tracked_extensions:
                try:
                    content = p.read_text(encoding="utf-8")
                    if "\u0669" in content:
                        violations.append(str(p.relative_to(repo_root)))
                except (UnicodeDecodeError, OSError):
                    pass

    assert not violations, f"Forbidden Arabic character U+0669 found in: {violations}"
