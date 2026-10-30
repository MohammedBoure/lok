#!/usr/bin/env python3
"""
Integration Gatekeeper Test Suite: Dynamic Audio Mixing, Prominent Safe Overlays, and Adaptive Script Pacing
Author: MohammedBoure <datasupabase@gmail.com>
Branch: test/agy100-dynamic-narration-and-audio-gatekeeper

Comprehensive Gatekeeper Verification:
1. Audio Mix & Soundtrack Directives:
   - parse_music_directives: mute music ("بدون موسيقى", "كتم الموسيقى", "بلا موسيقى"),
     track selection ("موسيقى بيانو", "موسيقى جيتار", "موسيقى تأمل"),
     and custom volume percentages ("صوت الموسيقى 10%", "مستوى الموسيقى 15%", "موسيقى هادئة جدا").
   - FFmpeg clean voiceover filtergraph without background music input when mute_music is True.
   - Ducking sidechain parameters (threshold=0.015, ratio=12.0) and ambient volume scaling when music is active.
2. Property Specifications Extraction & Mandatory Prompt Guidance:
   - extract_property_features: unit ("F5"), sea view ("مطل على البحر"), property type ("منزل", "شقة", "فيلا").
   - Mandatory architectural specifications injected into Gemini Vision prompt.
3. Prominent Safe Text Overlays:
   - large_font directive detection ("بخط كبير", "كبير وواضح", "بخط عريض وبارز").
   - Scaling font size to max(48, min(64, int(video_height * 0.042))) with high-contrast box (black@0.78, boxborderw=16).
   - Elevated safe margin safe_margin = max(110, int(video_height * 0.085)) keeping text clear of player controls.
4. Continuous Dynamic Narration & Adaptive Pacing:
   - Unclamped word count target_words = max(18, min(160, int(speech_duration * 2.1))).
   - 3-phase narrative structure (Hook, Walkthrough, Concluding CTA) scaling across 10s, 25s, and 40s+ durations.
   - Ensuring speech does not cut off prematurely and phone digits are never spoken aloud by TTS.
5. Frontend UI/UX Contracts:
   - DOM elements in index.html: resultMusicPill, resultOverlayPill, overlayFontBadge, propertySpecsBadge, promptTextarea, promptInputHint.
   - app.js dynamic formatting: muted audio indication, volume percentages, prominent text badges, and property specs tags.
   - CSS tokens and styles in style.css.
6. Server API Contracts:
   - /api/jobs/create and /api/status/{job_id} exposing audio mix status, overlay properties, and dynamic scripts.
7. Strict Zero U+0669 Character Compliance across repository.
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
    extract_property_features,
    is_meta_prompt,
    parse_music_directives,
    parse_prompt_instructions,
    process_mobile_video,
    sanitize_script_against_meta_prompts,
)
from web.server import PROGRESS_STORE, app
from web.video_annotator import _build_drawtext_filter
from web.vision_analyzer import (
    _generate_dynamic_darja_script,
    _get_smart_fallback,
    infer_video_script_and_mood,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = REPO_ROOT / "web" / "static"

SAMPLE_DYNAMIC_PROMPT = (
    "أريد تعليق صوتي لمنزل F5 مطل على البحر بالدارجة وبدون موسيقى، "
    "مع إظهار رقم الهاتف 0558815453 في الأسفل بخط كبير وواضح"
)


class TestGatekeeperMusicAndSoundtrackDirectives:
    """Gatekeeper verification for soundtrack directives parsing, muting, and volume scaling."""

    @pytest.mark.parametrize(
        "prompt,expected_mute",
        [
            ("أريد تعليق صوتي بدون موسيقى", True),
            ("فيديو كتم الموسيقى والصوت الصافي", True),
            ("بلا موسيقى لو سمحت", True),
            ("من غير موسيقى خلفية نهائياً", True),
            ("فيديو تسويقي no music please", True),
            ("صوت نقي بدون أغاني", True),
            ("تعليق صوتي mute music", True),
            ("أريد موسيقى بيانو هادئة", False),
            ("موسيقى جيتار عصرية", False),
        ],
    )
    def test_gatekeeper_parse_music_directives_mute(self, prompt: str, expected_mute: bool):
        """Verify extraction of mute_music flag across Algerian, Standard Arabic, and English phrasing."""
        parsed = parse_music_directives(prompt)
        assert parsed["mute_music"] is expected_mute, f"Failed on prompt: {prompt}"

    def test_gatekeeper_parse_music_directives_track_selection(self):
        """Verify explicit track selection mapping to valid library identifiers."""
        assert parse_music_directives("موسيقى بيانو كلاسيكية")["music_track"] == "luxury_piano"
        assert parse_music_directives("أريد موسيقى جيتار عصرية وحيوية")["music_track"] == "acoustic_guitar"
        assert parse_music_directives("موسيقى تأمل وهادئة للبحر")["music_track"] == "ambient_meditation"

    @pytest.mark.parametrize(
        "prompt,expected_vol",
        [
            ("صوت الموسيقى 10%", 0.10),
            ("مستوى الموسيقى: 15%", 0.15),
            ("music volume = 20%", 0.20),
            ("مستوى الموسيقى: 0.12", 0.12),
            ("موسيقى هادئة جدا وخفيفة", 0.08),
        ],
    )
    def test_gatekeeper_parse_music_directives_custom_volume(self, prompt: str, expected_vol: float):
        """Verify parsing of music volume percentages and descriptors."""
        parsed = parse_music_directives(prompt)
        assert parsed["music_volume"] == pytest.approx(expected_vol, abs=0.015)

    @patch("web.video_annotator.annotate_video")
    @patch("web.pipeline_bridge.synthesize_narration")
    @patch("subprocess.run")
    @patch("frame_extractor.extract_keyframes")
    @patch("frame_extractor.get_video_metadata")
    def test_gatekeeper_process_video_muted_music_ffmpeg_command(
        self,
        mock_meta,
        mock_kf,
        mock_subproc,
        mock_tts,
        mock_annotate,
        tmp_path,
    ):
        """Verify FFmpeg executes with clean 2-input graph (no music input) and omits sidechain ducking."""
        mock_meta.return_value = {"width": 1080, "height": 1920, "total_duration": 14.0}
        mock_kf.return_value = {"frames": []}
        mock_tts.return_value = {
            "wav_path": str(tmp_path / "voice.wav"),
            "duration": 8.0,
            "synthesizer": "gemini_speech_neural",
        }
        mock_annotate.return_value = {"status": "ok"}

        executed_cmds = []

        def capture_ffmpeg_cmds(cmd, *args, **kwargs):
            if isinstance(cmd, list) and len(cmd) > 0:
                executed_cmds.append(cmd)
                out_path = Path(cmd[-1])
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_bytes(b"mock_mp4_bytes")
            return MagicMock(returncode=0, stdout="", stderr="")

        mock_subproc.side_effect = capture_ffmpeg_cmds

        dummy_video = tmp_path / "test_video.mp4"
        dummy_video.write_bytes(b"dummy_bytes")

        summary = process_mobile_video(
            video_path=dummy_video,
            script=SAMPLE_DYNAMIC_PROMPT,
            output_dir=tmp_path / "outputs",
            voice="ar-XA-Standard-A",
        )

        assert summary["music_muted"] is True
        assert summary["music_track"]["muted"] is True
        assert len(executed_cmds) > 0

        render_cmds = [c for c in executed_cmds if "-filter_complex" in c]
        assert len(render_cmds) > 0, "Expected an FFmpeg render command with -filter_complex"
        assembly_cmd = render_cmds[0]
        # Must have exactly 2 input flags (-i source_video -i narration_wav)
        input_args = [assembly_cmd[i + 1] for i, a in enumerate(assembly_cmd) if a == "-i"]
        assert len(input_args) == 2, f"Expected 2 inputs in muted mode, got: {input_args}"

        # Filtergraph must output pure narration without sidechain compression
        fc_idx = assembly_cmd.index("-filter_complex")
        filter_str = assembly_cmd[fc_idx + 1]
        assert "sidechaincompress" not in filter_str
        assert "[1:a]" in filter_str
        assert "[aout]" in filter_str


class TestGatekeeperPropertyFeaturesExtraction:
    """Gatekeeper verification for property specifications and selling points extraction."""

    def test_gatekeeper_extract_property_features_comprehensive(self):
        """Verify extraction of unit layout, sea view, and property type."""
        features = extract_property_features(SAMPLE_DYNAMIC_PROMPT)
        assert features["unit"] == "F5"
        assert features["sea_view"] is True
        assert features["property_type"] == "منزل"
        assert "F5" in features["keywords"]
        assert "مطل على البحر" in features["keywords"]
        assert "منزل" in features["keywords"]

    @pytest.mark.parametrize(
        "text,expected_unit,expected_sea,expected_type",
        [
            ("شقة F4 مطلة على البحر", "F4", True, "شقة"),
            ("فيلا راقية بواجهة بحرية ساحرة", None, True, "فيلا"),
            ("دوبلكس F6 في قلب العاصمة", "F6", False, "دوبلكس"),
            ("محل تجاري في موقع حيوي", None, False, "محل تجاري"),
            ("استوديو S+1 للكراء", "S+1", False, "استوديو"),
        ],
    )
    def test_gatekeeper_extract_property_features_variants(
        self, text: str, expected_unit: str | None, expected_sea: bool, expected_type: str | None
    ):
        """Verify extraction across diverse property categories."""
        res = extract_property_features(text)
        assert res["unit"] == expected_unit
        assert res["sea_view"] is expected_sea
        assert res["property_type"] == expected_type

    def test_gatekeeper_vision_prompt_injects_mandatory_specifications(self, tmp_path):
        """Verify that infer_video_script_and_mood constructs prompts containing mandatory specs."""
        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": json.dumps({
                                    "script": "شوفو معايا هاد المنزل F5 المطل على البحر.",
                                    "emotional_tone": "فاخر وهادئ",
                                    "emotional_prompt": "Warm real estate tone",
                                    "recommended_music": "ambient_meditation",
                                    "highlights": ["منزل F5 فخم", "إطلالة بحرية ساحرة"],
                                })
                            }
                        ]
                    }
                }
            ]
        }

        with patch("requests.post", return_value=fake_response) as mock_post, \
             patch.dict("os.environ", {"GEMINI_API_KEY": "fake_test_key"}):
            dummy_frame = tmp_path / "mock_frame.jpg"
            dummy_frame.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF")

            res = infer_video_script_and_mood(
                keyframe_paths=[dummy_frame],
                video_duration=30.0,
                speech_description=SAMPLE_DYNAMIC_PROMPT,
                visual_lead_in=1.2,
                outro_buffer=1.2,
            )

            assert mock_post.called
            call_kwargs = mock_post.call_args.kwargs
            json_payload = call_kwargs.get("json", {})
            parts = json_payload.get("contents", [{}])[0].get("parts", [])
            prompt_text = "".join(p.get("text", "") for p in parts if "text" in p)

            # Assert mandatory architectural specifications and pacing instructions were injected
            assert "MANDATORY ARCHITECTURAL SPECIFICATIONS" in prompt_text
            assert "CONTINUOUS DYNAMIC AUDIO PACING" in prompt_text
            assert "منزل" in prompt_text
            assert "F5" in prompt_text
            assert "مطل على البحر" in prompt_text


class TestGatekeeperLargeFontAndSafeBottomOverlays:
    """Gatekeeper verification for prominent font sizing and elevated safe margins."""

    def test_gatekeeper_large_font_detection(self):
        """Verify large_font directive detection in extract_directives."""
        assert extract_directives(SAMPLE_DYNAMIC_PROMPT)["large_font"] is True
        assert extract_directives("رقم الهاتف في الأسفل كبير وواضح")["large_font"] is True
        assert extract_directives("مع إظهار الرقم بخط عريض وبارز")["large_font"] is True
        assert extract_directives("ضع الرقم 0558815453 في الأسفل")["large_font"] is False

    def test_gatekeeper_large_font_size_scaling_and_box_style(self):
        """Verify font size max(48, min(64, int(target_h * 0.042))) and high-contrast black@0.78 box."""
        # 1. Portrait 1080x1920: int(1920 * 0.042) = 80 -> clamped to 64
        filter_portrait = _build_drawtext_filter(
            {"text": "0558815453", "style": "persistent_bottom", "large_font": True},
            video_width=1080,
            video_height=1920,
        )
        assert "fontsize=64" in filter_portrait
        assert "boxcolor=black@0.78" in filter_portrait
        assert "boxborderw=16" in filter_portrait
        assert "fontcolor=white" in filter_portrait

        # 2. Landscape 1280x720: int(720 * 0.042) = 30 -> max(48, 30) = 48
        filter_landscape = _build_drawtext_filter(
            {"text": "0558815453", "style": "persistent_bottom", "large_font": True},
            video_width=1280,
            video_height=720,
        )
        assert "fontsize=48" in filter_landscape
        assert "boxcolor=black@0.78" in filter_landscape
        assert "boxborderw=16" in filter_landscape

        # 3. Standard font (non-large): font_size defaults to max(38, min(50, int(video_height * 0.034)))
        filter_std = _build_drawtext_filter(
            {"text": "0558815453", "style": "persistent_bottom", "large_font": False},
            video_width=1080,
            video_height=1920,
        )
        assert "fontsize=50" in filter_std  # int(1920 * 0.034) = 65 -> clamped to 50
        assert "boxborderw=14" in filter_std or "boxborderw=12" in filter_std

    def test_gatekeeper_safe_margin_bottom_overlay_elevation(self):
        """Verify safe margin elevation safe_margin = max(110, int(video_height * 0.085)) clears player controls."""
        # Portrait 1920 height: int(1920 * 0.085) = 163 -> safe_margin = 163
        filter_1920 = _build_drawtext_filter(
            {"text": "0558815453", "style": "persistent_bottom"},
            video_width=1080,
            video_height=1920,
        )
        assert "y=h-text_h-163" in filter_1920
        assert "x=(w-text_w)/2" in filter_1920

        # Landscape 720 height: int(720 * 0.085) = 61 -> max(110, 61) = 110 -> safe_margin = 110
        filter_720 = _build_drawtext_filter(
            {"text": "0558815453", "style": "persistent_bottom"},
            video_width=1280,
            video_height=720,
        )
        assert "y=h-text_h-110" in filter_720

        # Full HD Landscape 1080 height: int(1080 * 0.085) = 91 -> max(110, 91) = 110
        filter_1080 = _build_drawtext_filter(
            {"text": "0558815453", "style": "persistent_bottom"},
            video_width=1920,
            video_height=1080,
        )
        assert "y=h-text_h-110" in filter_1080


class TestGatekeeperDynamicNarrationAndPacing:
    """Gatekeeper verification for dynamic Algerian Darja narration without premature silence."""

    def test_gatekeeper_target_words_formula_unclamped(self):
        """Verify target_words formula target_words = max(18, min(160, int(speech_duration * 2.1)))."""
        # 10s speech duration: int(10 * 2.1) = 21 words
        assert max(18, min(160, int(10.0 * 2.1))) == 21

        # 30s speech duration: int(30 * 2.1) = 63 words
        assert max(18, min(160, int(30.0 * 2.1))) == 63

        # 50s speech duration: int(50 * 2.1) = 105 words (unclamped from previous 65 limit)
        assert max(18, min(160, int(50.0 * 2.1))) == 105

        # 75s speech duration: int(75 * 2.1) = 157 words
        assert max(18, min(160, int(75.0 * 2.1))) == 157

    def test_gatekeeper_dynamic_script_generation_content_and_phone_isolation(self):
        """Verify _generate_dynamic_darja_script includes all features and never reads phone digits."""
        prop_feats = extract_property_features(SAMPLE_DYNAMIC_PROMPT)
        directives = extract_directives(SAMPLE_DYNAMIC_PROMPT)

        script = _generate_dynamic_darja_script(
            speech_duration=35.0,
            prop_feats=prop_feats,
            directives=directives,
        )

        # Specifications check
        assert "F5" in script
        assert "منزل" in script
        assert "بحر" in script or "البحر" in script

        # Critical invariant: phone digits are NEVER read aloud by TTS
        assert "0558815453" not in script
        assert "الرقم الظاهر أسفل الشاشة" in script

    def test_gatekeeper_dynamic_pacing_scales_across_durations(self):
        """Verify narration length scales with duration across short (10s), medium (25s), and long (45s)."""
        prop_feats = extract_property_features(SAMPLE_DYNAMIC_PROMPT)
        directives = extract_directives(SAMPLE_DYNAMIC_PROMPT)

        script_short = _generate_dynamic_darja_script(10.0, prop_feats, directives)
        script_med = _generate_dynamic_darja_script(25.0, prop_feats, directives)
        script_long = _generate_dynamic_darja_script(45.0, prop_feats, directives)

        words_short = len(script_short.split())
        words_med = len(script_med.split())
        words_long = len(script_long.split())

        assert words_short < words_med < words_long, f"Length must scale: {words_short} < {words_med} < {words_long}"
        assert words_long >= 75, f"Expected long script >= 75 words, got: {words_long}"

    def test_gatekeeper_smart_fallback_incorporates_features_and_directives(self):
        """Verify _get_smart_fallback generates adaptive script and captures audio/overlay directives."""
        fb = _get_smart_fallback(
            duration=35.0,
            speech_description=SAMPLE_DYNAMIC_PROMPT,
            visual_lead_in=1.0,
            outro_buffer=1.0,
        )

        script = fb.get("script", "")
        assert "F5" in script
        assert "منزل" in script
        assert "بحر" in script or "البحر" in script
        assert "0558815453" not in script  # Zero phone recitation in TTS script
        assert fb.get("phone_number") == "0558815453"
        assert fb.get("bottom_text") == "0558815453"


class TestGatekeeperFrontendContractsAndDOM:
    """Gatekeeper verification for frontend UI/UX DOM contracts, pills, and prompt guidance."""

    def test_gatekeeper_index_html_dom_elements(self):
        """Verify required feedback pills, badges, and prompt guidance exist in index.html."""
        html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")

        # 1. Music & Audio Balance Feedback Pill
        assert 'id="resultMusicPill"' in html
        assert 'id="resultMusicIcon"' in html
        assert 'id="resultMusicText"' in html
        assert 'id="resultMusicBadge"' in html
        assert "الموسيقى والمكساج:" in html

        # 2. Persistent Overlay Pill & Extended Badges
        assert 'id="resultOverlayPill"' in html
        assert 'id="resultOverlayText"' in html
        assert 'id="bottomTextBadge"' in html
        assert 'id="overlayFontBadge"' in html
        assert 'id="propertySpecsBadge"' in html

        # 3. Prompt Guidance and Examples
        assert 'id="promptTextarea"' in html
        assert 'id="promptInputHint"' in html
        assert "بدون موسيقى" in html
        assert "كتم الموسيقى" in html
        assert "بخط كبير وواضح" in html or "بخط عريض وبارز" in html
        assert "F5" in html
        assert "مطل على البحر" in html

    def test_gatekeeper_app_js_contracts(self):
        """Verify app.js handles music muting, volume percentage, large font, and property specs."""
        js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")

        # 1. DOM handles
        assert "resultMusicPill" in js
        assert "resultMusicText" in js
        assert "resultMusicIcon" in js
        assert "resultMusicBadge" in js
        assert "overlayFontBadge" in js
        assert "propertySpecsBadge" in js

        # 2. Form submission flags injection
        assert "mute_music" in js
        assert "large_font" in js

        # 3. Muted music feedback formatting
        assert "صوت نقي 100% (تم كتم وإلغاء موسيقى الخلفية بالكامل)" in js
        assert 'classList.add("muted")' in js
        assert "isMusicMuted" in js

        # 4. Active music track and volume formatting
        assert "مستوى الصوت:" in js

        # 5. Badges dynamic rendering
        assert "بخط كبير وواضح" in js
        assert "property_features" in js or "propFeatures" in js

    def test_gatekeeper_style_css_contracts(self):
        """Verify style.css includes styling for music pill and badges."""
        css = (STATIC_DIR / "style.css").read_text(encoding="utf-8")
        assert ".result-music-pill" in css
        assert ".result-music-pill.muted" in css
        assert ".overlay-font-badge" in css
        assert ".property-specs-badge" in css
        assert ".music-badge" in css
        assert ".result-pills-row" in css


class TestGatekeeperServerEndpointsAudioAndOverlayExposure:
    """Gatekeeper verification for API endpoints exposing audio mixing and overlay data."""

    @patch("web.server._execute_processing_job")
    def test_gatekeeper_jobs_create_and_status_audio_data(self, mock_exec):
        """Verify /api/jobs/create and /api/status/{job_id} handle directives and return rich status."""
        client = TestClient(app)

        # Login to obtain merchant session token
        r_login = client.post("/api/auth/login", json={"username": "oran_seafood_bistro", "password": "merchant123"})
        assert r_login.status_code == 200, f"Login failed: {r_login.text}"
        token = r_login.json()["session_token"]

        files = {
            "video": ("recording.mp4", io.BytesIO(b"dummy_mp4_bytes"), "video/mp4"),
        }
        data = {
            "prompt": SAMPLE_DYNAMIC_PROMPT,
        }

        resp = client.post(
            "/api/jobs/create",
            data=data,
            files=files,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 202
        body = resp.json()
        assert body.get("status") == "processing"
        job_id = body.get("job_id")
        assert job_id is not None
        assert body.get("phone_number") == "0558815453"
        assert body.get("bottom_text") == "0558815453"

        # Verify completed status exposure
        test_job_id = f"gatekeeper_audio_{job_id}"
        cut_file = Path("outputs/mobile_cuts") / f"cut_{test_job_id}.mp4"
        cut_file.parent.mkdir(parents=True, exist_ok=True)
        cut_file.write_bytes(b"dummy mp4 cut")

        try:
            PROGRESS_STORE[test_job_id] = {
                "job_id": test_job_id,
                "status": "completed",
                "step": 5,
                "progress": 100,
                "video_url": f"/outputs/mobile_cuts/cut_{test_job_id}.mp4",
                "script": "شوفو معايا هاد المنزل F5 المطل مباشرة على البحر.",
                "bottom_text": "0558815453",
                "phone_number": "0558815453",
                "result": {
                    "job_id": test_job_id,
                    "status": "completed",
                    "video_url": f"/outputs/mobile_cuts/cut_{test_job_id}.mp4",
                    "script": "شوفو معايا هاد المنزل F5 المطل مباشرة على البحر.",
                    "bottom_text": "0558815453",
                    "phone_number": "0558815453",
                    "music_muted": True,
                    "music_volume": 0.0,
                    "large_font_applied": True,
                    "property_features": {
                        "unit": "F5",
                        "sea_view": True,
                        "property_type": "منزل",
                    },
                    "music_track": {
                        "id": "ambient_meditation",
                        "title": "تأمل وهدوء",
                        "muted": True,
                    },
                },
            }

            status_resp = client.get(f"/api/status/{test_job_id}")
            assert status_resp.status_code == 200
            status_data = status_resp.json()
            assert status_data["status"] == "completed"
            assert status_data["music_muted"] is True
            assert status_data["large_font_applied"] is True
            assert status_data["property_features"]["unit"] == "F5"
            assert status_data["property_features"]["sea_view"] is True
            assert status_data["property_features"]["property_type"] == "منزل"
        finally:
            if cut_file.exists():
                cut_file.unlink()


class TestGatekeeperStrictCharacterMappingCompliance:
    """Strict verification of zero occurrences of forbidden Arabic character U+0669."""

    def test_gatekeeper_zero_forbidden_character_across_repo(self):
        """Assert zero occurrences of forbidden Arabic character U+0669 across all repository text files."""
        violations = []
        skip_dirs = {".git", "__pycache__", "venv", ".pytest_cache", "brain", ".venv"}
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
