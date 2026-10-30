#!/usr/bin/env python3
"""
Integration Gatekeeper Test Suite: Prompt Intent Disentanglement, Script Inspection Card, and Persistent Bottom Overlays.
Author: MohammedBoure <datasupabase@gmail.com>
Branch: test/agy100-prompt-intent-and-overlays-gatekeeper

Comprehensive Gatekeeper Verification:
1. Prompt Intent Disentanglement:
   - Disentangling creative user instructions (e.g., "أريد أن يظهر نص أسفل الفيديو به الرقم التالي طول ما الفيديو شغال 0558815453... وأريد تعليق صوتي بالدارجة")
     from spoken narration.
   - Extracting Algerian phone numbers across formats (05/06/07, +213, 00213, spaced/hyphenated).
   - Isolating and stripping meta-prompt directives so Gemini TTS strictly receives authentic marketing Darja voiceover script.
2. Persistent Bottom Text Overlays:
   - FFmpeg drawtext filter generation with style="persistent_bottom".
   - Semi-transparent black background box (boxcolor=black@0.6, boxborderw=8).
   - Centered horizontal alignment ((w-text_w)/2) and bottom pinned (y=h-text_h-40).
   - Spanning full duration of the video.
3. Frontend Contracts:
   - HTML & DOM contracts for #generatedScriptCard, #generatedScriptText, #btnCopyScript, #bottomTextBadge, #resultOverlayPill.
   - Script copy functionality and toast feedback in app.js.
   - User guidance hints and responsive styles.
4. Server API Integration:
   - /api/jobs/create, /api/upload-and-process, and /api/status/{job_id} exposing script, bottom_text, and phone_number.
5. Strict Character Mapping:
   - Zero occurrences of forbidden Arabic character U+0669 across repository.
"""

from __future__ import annotations

import io
import json
import os
import re
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

REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = REPO_ROOT / "web" / "static"

SAMPLE_USER_PROMPT_WITH_DIRECTIVES = (
    "أريد أن يظهر نص أسفل الفيديو به الرقم التالي طول ما الفيديو شغال 0558815453 "
    "يظهر النص التالي و أيضا أريد أن يكون هناك تعليق صوتي يتناسب مع الفيديو و محتواه و بالدارجة"
)


class TestGatekeeperPromptIntentExtractionAndDisentanglement:
    """Verify robust extraction of Algerian phone numbers, directives, and meta-prompt isolation."""

    @pytest.mark.parametrize(
        "phone_input,expected_phone",
        [
            ("0558815453", "0558815453"),
            ("0558 81 54 53", "0558815453"),
            ("0558-81-54-53", "0558815453"),
            ("+213558815453", "0558815453"),
            ("+213 558 81 54 53", "0558815453"),
            ("00213558815453", "0558815453"),
            ("0661223344", "0661223344"),
            ("0770-12-34-56", "0770123456"),
            (SAMPLE_USER_PROMPT_WITH_DIRECTIVES, "0558815453"),
        ],
    )
    def test_extract_algerian_phone_gatekeeper(self, phone_input: str, expected_phone: str):
        """Ensure phone numbers are extracted correctly across international, spaced, and hyphenated variations."""
        extracted = extract_algerian_phone(phone_input)
        assert extracted == expected_phone, f"Failed to extract {expected_phone} from '{phone_input}' (got '{extracted}')"

    def test_is_meta_prompt_distinguishes_instructions_from_literal_script(self):
        """Ensure system distinguishes creative instructions from literal voiceover narrations."""
        meta_prompts = [
            SAMPLE_USER_PROMPT_WITH_DIRECTIVES,
            "أريد تعليق صوتي بالدارجة ورقم الهاتف في الأسفل 0558815453",
            "اجعل التعليق الصوتي دافئ وضيف رقم الهاتف 0661223344 في الأسفل",
            "يرجى وضع شريط سفلي به الرقم 0770123456 طوال الفيديو",
            "اكتب نص تسويقي بالدارجة مع إظهار رقم 0558815453",
        ]
        for prompt in meta_prompts:
            assert is_meta_prompt(prompt) is True, f"Expected meta-prompt detection for: {prompt}"

        literal_scripts = [
            "شوفو معايا هاد الشقة الفاخرة F4 في قلب العاصمة، فينيسيون متقونة وإطلالة شابة بزاف.",
            "فيلا عصرية بواجهة بحرية ساحرة في وهران، حديقة ومسبح خاص وتصميم راقي.",
            "محل تجاري في موقع استراتيجي حيوي في قسنطينة، واجهة واسعة وحركة ممتازة.",
        ]
        for script in literal_scripts:
            assert is_meta_prompt(script) is False, f"Expected literal script detection for: {script}"

    def test_extract_directives_from_sample_user_prompt(self):
        """Ensure directives, phone number, and persistent overlay flags are extracted from the user's prompt."""
        directives = extract_directives(SAMPLE_USER_PROMPT_WITH_DIRECTIVES)
        assert directives["is_meta_prompt"] is True
        assert directives["phone_number"] == "0558815453"
        assert directives["bottom_text"] == "0558815453"
        assert directives["darja_requested"] is True
        assert directives["voiceover_requested"] is True
        assert directives["persistent_overlay"] is True

    def test_parse_prompt_instructions_integrates_directives(self):
        """Ensure parse_prompt_instructions seamlessly merges directives and audio parameters."""
        prompt_with_modifiers = f"{SAMPLE_USER_PROMPT_WITH_DIRECTIVES} speed: 1.15"
        parsed = parse_prompt_instructions(prompt_with_modifiers)
        assert parsed["phone_number"] == "0558815453"
        assert parsed["bottom_text"] == "0558815453"
        assert parsed["is_meta_prompt"] is True
        assert parsed["speed"] == 1.15

    def test_sanitize_script_against_meta_prompts(self):
        """Verify that meta-prompt instructions are stripped and never used as spoken narration."""
        # 1. Strip labeling prefixes
        labeled_script = "السيناريو: شوفو معايا هاد الشقة الفاخرة في قلب المدينة."
        sanitized = sanitize_script_against_meta_prompts(labeled_script)
        assert sanitized == "شوفو معايا هاد الشقة الفاخرة في قلب المدينة."
        assert not sanitized.startswith("السيناريو:")

        # 2. Meta-prompt passed directly as script is replaced with authentic Algerian Darja narration
        meta_as_script = SAMPLE_USER_PROMPT_WITH_DIRECTIVES
        cleaned = sanitize_script_against_meta_prompts(meta_as_script)
        assert "أريد أن يظهر" not in cleaned
        assert "0558815453" not in cleaned
        assert "طول ما الفيديو شغال" not in cleaned
        assert any(phrase in cleaned for phrase in ["عقار استثنائي", "شوفو معايا", "تصميم راقي"])


class TestGatekeeperPersistentBottomOverlayFFmpegFilter:
    """Verify FFmpeg drawtext overlay filter generation for persistent bottom text."""

    def test_drawtext_filter_persistent_bottom_style(self):
        """Verify styling parameters for style='persistent_bottom'."""
        annotation = {
            "text": "0558815453",
            "style": "persistent_bottom",
            "position": "bottom_banner",
            "start_sec": 0.0,
            "end_sec": 14.5,
            "persistent": True,
        }
        filter_str = _build_drawtext_filter(annotation)

        # 1. Centered horizontally and positioned at bottom with safe margin
        assert "x=(w-text_w)/2" in filter_str
        assert "y=h-text_h-" in filter_str

        # 2. Semi-transparent black background box
        assert "box=1" in filter_str
        assert "boxcolor=black@" in filter_str

        # 3. Clean white typography
        assert "fontcolor=white" in filter_str

        # 4. Spans entire duration
        assert "between(t,0.00,14.50)" in filter_str

    def test_drawtext_filter_default_coordinates_for_bottom_styles(self):
        """Verify coordinates default to bottom center for persistent_bottom or phone_overlay styles."""
        for style_name in ["persistent_bottom", "bottom_box", "phone_overlay"]:
            annotation = {"text": "اتصل الآن: 0558815453", "style": style_name}
            filter_str = _build_drawtext_filter(annotation)
            assert "x=(w-text_w)/2" in filter_str
            assert "y=h-text_h-" in filter_str
            assert "boxcolor=black@" in filter_str


class TestGatekeeperTtsScriptIsolationE2E:
    """Verify Gemini TTS voiceover engine never receives user meta-prompt instructions."""

    def test_smart_fallback_never_speaks_user_instructions(self):
        """Ensure _get_smart_fallback formulates natural Darja marketing narration without echoing meta directives."""
        fallback = _get_smart_fallback(
            duration=15.0,
            speech_description=SAMPLE_USER_PROMPT_WITH_DIRECTIVES,
            visual_lead_in=1.0,
            outro_buffer=1.0,
        )
        script = fallback.get("script", "")

        # TTS narration must NOT echo meta instructions or phone numbers
        assert "أريد أن يظهر" not in script
        assert "طول ما الفيديو شغال" not in script
        assert "0558815453" not in script

        # Must generate authentic Algerian Darja marketing copy
        assert any(kw in script for kw in ["شوفو معايا", "عقار استثنائي", "تصميم راقي", "فيلا"])

        # Directives must be exposed in fallback metadata
        assert fallback.get("phone_number") == "0558815453"
        assert fallback.get("bottom_text") == "0558815453"

    @patch("web.pipeline_bridge.annotate_video")
    @patch("web.pipeline_bridge.synthesize_narration")
    @patch("subprocess.run")
    @patch("frame_extractor.extract_keyframes")
    @patch("frame_extractor.get_video_metadata")
    def test_process_mobile_video_isolates_tts_script_and_applies_bottom_overlay(
        self,
        mock_meta,
        mock_kf,
        mock_subproc,
        mock_tts,
        mock_annotate,
        tmp_path,
    ):
        """Verify process_mobile_video strips meta-prompts before TTS and creates bottom overlay annotation."""
        mock_meta.return_value = {"width": 1080, "height": 1920, "total_duration": 12.0}
        mock_kf.return_value = {"frames": []}
        mock_tts.return_value = {
            "wav_path": str(tmp_path / "narration.wav"),
            "duration": 6.0,
            "synthesizer": "mock_gemini_tts",
        }
        mock_annotate.return_value = {"status": "ok"}

        def fake_ffmpeg_runner(cmd, *args, **kwargs):
            if isinstance(cmd, list) and len(cmd) > 0:
                out_path = Path(cmd[-1])
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_bytes(b"dummy_cut_bytes")
            return MagicMock(returncode=0, stdout="", stderr="")

        mock_subproc.side_effect = fake_ffmpeg_runner

        dummy_input = tmp_path / "raw_input.mp4"
        dummy_input.write_bytes(b"dummy_video_content")

        # Caller provides user instructions in the script field
        result_summary = process_mobile_video(
            video_path=dummy_input,
            script=SAMPLE_USER_PROMPT_WITH_DIRECTIVES,
            output_dir=tmp_path / "outputs",
            voice="ar-XA-Standard-A",
        )

        # 1. Assert TTS synthesize_narration was called with stripped / authentic script
        mock_tts.assert_called_once()
        tts_script = mock_tts.call_args.kwargs.get("script", "")
        assert "أريد أن يظهر" not in tts_script
        assert "طول ما الفيديو شغال" not in tts_script
        assert "0558815453" not in tts_script

        # 2. Assert result summary contains extracted phone number and bottom text
        assert result_summary.get("phone_number") == "0558815453"
        assert result_summary.get("bottom_text") == "0558815453"
        assert result_summary.get("auto_mode") is True

        # 3. Assert video annotator was invoked with persistent bottom overlay annotation
        mock_annotate.assert_called_once()
        annotations_arg = mock_annotate.call_args.kwargs.get("annotations", [])
        bottom_annotations = [
            ann for ann in annotations_arg
            if ann.get("style") == "persistent_bottom" or ann.get("position") == "bottom_banner"
        ]
        assert len(bottom_annotations) >= 1
        assert bottom_annotations[0]["text"] == "0558815453"
        assert bottom_annotations[0]["persistent"] is True
        assert bottom_annotations[0]["start_sec"] == 0.0


class TestGatekeeperFrontendContracts:
    """Verify frontend UI DOM contracts for generated script card and persistent overlay badge."""

    def test_frontend_dom_elements_in_html(self):
        """Verify required DOM elements exist in web/static/index.html."""
        html_content = (STATIC_DIR / "index.html").read_text(encoding="utf-8")

        # 1. Result card container
        assert 'id="resultCard"' in html_content
        assert 'id="resultContainer"' in html_content

        # 2. Generated script inspection card
        assert 'id="generatedScriptCard"' in html_content
        assert 'id="generatedScriptText"' in html_content
        assert 'id="btnCopyScript"' in html_content
        assert "السيناريو والتعليق الصوتي المولّد" in html_content
        assert "نسخ السيناريو" in html_content

        # 3. Persistent bottom text overlay feedback (both pill and bottomTextBadge supported)
        assert 'id="resultOverlayPill"' in html_content
        assert 'id="resultOverlayText"' in html_content
        assert 'id="bottomTextBadge"' in html_content
        assert "الشريط السفلي" in html_content

        # 4. Prompt textarea guidance hint for instructions and bottom text
        assert 'id="promptInputHint"' in html_content
        assert "0558815453" in html_content

    def test_frontend_app_js_contracts(self):
        """Verify logic in web/static/app.js for script display, copying, and overlay pills."""
        js_content = (STATIC_DIR / "app.js").read_text(encoding="utf-8")

        # 1. DOM references
        assert "generatedScriptCard" in js_content
        assert "generatedScriptText" in js_content
        assert "btnCopyScript" in js_content
        assert "resultOverlayPill" in js_content
        assert "resultOverlayText" in js_content
        assert "bottomTextBadge" in js_content

        # 2. Copy script event handler
        assert "handleCopyScript" in js_content
        assert "navigator.clipboard.writeText" in js_content
        assert "تم نسخ نص السيناريو بنجاح" in js_content

        # 3. Displaying script on job completion
        assert "data.script" in js_content or "generatedScript" in js_content

        # 4. Displaying bottom overlay on job completion
        assert "data.bottom_text" in js_content or "data.phone_number" in js_content

        # 5. Form submission extracting phone number for bottom overlay
        assert "phoneMatch" in js_content or "bottom_text" in js_content

    def test_frontend_css_contracts(self):
        """Verify styling rules in web/static/style.css."""
        css_content = (STATIC_DIR / "style.css").read_text(encoding="utf-8")
        assert ".generated-script-card" in css_content
        assert ".result-overlay-pill" in css_content
        assert ".prompt-guidance-hint" in css_content


class TestGatekeeperServerEndpointsWithDirectives:
    """Verify server endpoints handle directives and expose bottom text and phone number."""

    @patch("web.server._execute_processing_job")
    def test_create_job_async_extracts_phone_and_bottom_text(self, mock_exec):
        """Test POST /api/jobs/create extracts directives into progress store and response."""
        client = TestClient(app)
        
        # 1. Login to obtain session token
        r_login = client.post("/api/auth/login", json={"username": "oran_seafood_bistro", "password": "merchant123"})
        assert r_login.status_code == 200, f"Login failed: {r_login.text}"
        token = r_login.json()["session_token"]

        # 2. Submit job with user prompt containing instructions
        files = {
            "video": ("test.mp4", io.BytesIO(b"fake_video_stream"), "video/mp4"),
        }
        data = {
            "prompt": SAMPLE_USER_PROMPT_WITH_DIRECTIVES,
            "voice": "ar-XA-Standard-A",
        }

        response = client.post(
            "/api/jobs/create",
            data=data,
            files=files,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 202, f"Expected 202, got: {response.text}"
        res_json = response.json()
        assert res_json.get("status") == "processing"
        job_id = res_json.get("job_id")
        assert job_id is not None
        assert res_json.get("phone_number") == "0558815453"
        assert res_json.get("bottom_text") == "0558815453"
        assert res_json.get("auto_mode") is True

        # Check progress store
        job_store = PROGRESS_STORE.get(job_id, {})
        assert job_store.get("phone_number") == "0558815453"
        assert job_store.get("bottom_text") == "0558815453"

        # Check status endpoint with completed job
        test_job_id = f"gatekeeper_completed_{job_id}"
        cut_file = Path("outputs/mobile_cuts") / f"cut_{test_job_id}.mp4"
        cut_file.parent.mkdir(parents=True, exist_ok=True)
        cut_file.write_bytes(b"dummy mp4 data")
        try:
            PROGRESS_STORE[test_job_id] = {
                "job_id": test_job_id,
                "status": "completed",
                "step": 5,
                "progress": 100,
                "video_url": f"/outputs/mobile_cuts/cut_{test_job_id}.mp4",
                "script": "شوفو معايا هاد العقار الفاخر بتصميم عصري وتشطيبات راقية.",
                "bottom_text": "0558815453",
                "phone_number": "0558815453",
                "result": {
                    "job_id": test_job_id,
                    "status": "completed",
                    "script": "شوفو معايا هاد العقار الفاخر بتصميم عصري وتشطيبات راقية.",
                    "bottom_text": "0558815453",
                    "phone_number": "0558815453",
                    "video_url": f"/outputs/mobile_cuts/cut_{test_job_id}.mp4",
                },
            }

            status_resp = client.get(f"/api/status/{test_job_id}")
            assert status_resp.status_code == 200
            status_json = status_resp.json()
            assert status_json.get("status") == "completed"
            assert status_json.get("phone_number") == "0558815453"
            assert status_json.get("bottom_text") == "0558815453"
            assert status_json.get("script") == "شوفو معايا هاد العقار الفاخر بتصميم عصري وتشطيبات راقية."
        finally:
            if cut_file.exists():
                cut_file.unlink()


class TestGatekeeperCharacterMappingCompliance:
    """Strict verification of zero occurrences of forbidden Arabic character U+0669."""

    def test_zero_forbidden_character_across_repo(self):
        """Assert zero occurrences of forbidden Arabic character U+0669 across all repository text files."""
        violations = []
        skip_dirs = {".git", "__pycache__", "venv", ".pytest_cache", "brain"}
        target_exts = {".py", ".html", ".css", ".js", ".json", ".md", ".sh"}

        for root, dirs, files in os.walk(REPO_ROOT):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for file in files:
                if any(file.endswith(ext) for ext in target_exts):
                    file_path = Path(root) / file
                    try:
                        content = file_path.read_text(encoding="utf-8", errors="ignore")
                        if "\u0669" in content:
                            violations.append(str(file_path.relative_to(REPO_ROOT)))
                    except Exception:
                        pass

        assert violations == [], f"Forbidden Arabic character U+0669 found in: {violations}"
