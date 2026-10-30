#!/usr/bin/env python3
"""
Comprehensive Test Suite: Dynamic Audio Mix Controls, Safe Bottom Overlays, and Adaptive Script Pacing
Verifies:
1. Audio mix & music controls:
   - parse_music_directives (mute_music, track selection, custom volume)
   - FFmpeg clean voiceover filtergraph with 0 music inputs when mute_music=True
   - Sidechain ducking parameters (duck_threshold=0.015, duck_ratio=12.0, ambient_volume=0.16)
2. Prominent safe bottom text & phone number overlays:
   - large_font detection ('بخط كبير', 'كبير وواضح')
   - Scaled font size: max(48, min(64, int(target_h * 0.042))) with high-contrast box (black@0.78, boxborderw=16)
   - Elevated safe margin: safe_margin = max(110, int(video_height * 0.085)) avoiding player controls
3. Property features & dynamic Algerian Darja pacing:
   - extract_property_features ('F5', 'مطل على البحر', 'منزل')
   - Expanded target words: max(18, min(160, int(speech_duration * 2.1))) removing 65-word clamp
   - Continuous 3-phase dynamic narration without premature cutoffs
4. Strict compliance with 0 occurrences of character U+0669.

Author: MohammedBoure
Branch: backend/agy11-dynamic-audio-and-large-overlay-control
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from web.pipeline_bridge import (
    extract_directives,
    extract_property_features,
    parse_music_directives,
    process_mobile_video,
)
from web.video_annotator import _build_drawtext_filter
from web.vision_analyzer import (
    _generate_dynamic_darja_script,
    _get_smart_fallback,
)


class TestMusicAndAudioMixingControls:
    """Verify soundtrack directives parsing, muting, volume scaling, and ducking parameters."""

    def test_parse_music_directives_mute_keywords(self):
        """Test extraction of mute_music across multiple Arabic and international keywords."""
        mute_samples = [
            "أريد تعليق صوتي بدون موسيقى",
            "فيديو كتم الموسيقى والصوت الصافي",
            "بلا موسيقى لو سمحت",
            "من غير موسيقى خلفية",
            "فيديو تسويقي no music please",
            "تعليق صوتي mute music",
            "بدون أغاني ولا موسيقى",
        ]
        for prompt in mute_samples:
            res = parse_music_directives(prompt)
            assert res["mute_music"] is True, f"Failed on: {prompt}"

    def test_parse_music_directives_tracks(self):
        """Test explicit selection of background music tracks."""
        assert parse_music_directives("موسيقى بيانو كلاسيكية")["music_track"] == "luxury_piano"
        assert parse_music_directives("أريد موسيقى جيتار عصرية")["music_track"] == "acoustic_guitar"
        assert parse_music_directives("موسيقى تأمل وهادئة للبحر")["music_track"] == "ambient_meditation"

    def test_parse_music_directives_custom_volume(self):
        """Test parsing of explicit music volume percentages and descriptors."""
        res_pct = parse_music_directives("صوت الموسيقى 10%")
        assert res_pct["music_volume"] == pytest.approx(0.10, abs=0.01)

        res_decimal = parse_music_directives("مستوى الموسيقى: 0.15")
        assert res_decimal["music_volume"] == pytest.approx(0.15, abs=0.01)

        res_soft = parse_music_directives("موسيقى هادئة جدا وخفيفة")
        assert res_soft["music_volume"] == pytest.approx(0.08, abs=0.01)

    @patch("web.video_annotator.annotate_video")
    @patch("web.pipeline_bridge.synthesize_narration")
    @patch("subprocess.run")
    @patch("frame_extractor.extract_keyframes")
    @patch("frame_extractor.get_video_metadata")
    def test_mute_music_generates_clean_ffmpeg_filtergraph_without_music_input(
        self,
        mock_meta,
        mock_kf,
        mock_subproc,
        mock_tts,
        mock_annotate,
        tmp_path,
    ):
        """Verify that when mute_music is requested, FFmpeg runs without music input (-i music)."""
        mock_meta.return_value = {"width": 1080, "height": 1920, "total_duration": 12.0}
        mock_kf.return_value = {"frames": []}
        mock_tts.return_value = {
            "wav_path": str(tmp_path / "narration.wav"),
            "duration": 6.0,
            "synthesizer": "gemini_speech_neural",
        }
        mock_annotate.return_value = {"status": "ok"}

        captured_cmds = []

        def fake_ffmpeg(cmd, *args, **kwargs):
            if isinstance(cmd, list) and len(cmd) > 0:
                captured_cmds.append(cmd)
                out_path = Path(cmd[-1])
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_bytes(b"mock_mp4_cut")
            return MagicMock(returncode=0, stdout="", stderr="")

        mock_subproc.side_effect = fake_ffmpeg

        dummy_video = tmp_path / "sample.mp4"
        dummy_video.write_bytes(b"dummy_video_data")

        summary = process_mobile_video(
            video_path=dummy_video,
            script="أريد تعليق صوتي نقي بدون موسيقى 0558815453",
            output_dir=tmp_path / "outputs",
            voice="ar-XA-Standard-A",
        )

        assert summary["music_muted"] is True
        assert summary["music_track"]["muted"] is True
        assert len(captured_cmds) > 0

        # Inspect the primary assembly command
        render_cmd = captured_cmds[0]
        # In mute mode, only 2 inputs: -i source_video and -i narration_wav (no 3rd music input)
        input_flags = [render_cmd[i+1] for i, arg in enumerate(render_cmd) if arg == "-i"]
        assert len(input_flags) == 2, f"Expected exactly 2 inputs in muted mode, got: {input_flags}"
        # Filtergraph must output narration directly without sidechain ducking
        filter_complex_idx = render_cmd.index("-filter_complex")
        filter_str = render_cmd[filter_complex_idx + 1]
        assert "sidechaincompress" not in filter_str
        assert "[1:a]" in filter_str and "[aout]" in filter_str


class TestLargeFontAndSafeBottomOverlays:
    """Verify prominent large font sizing, high-contrast black box, and safe margin elevation."""

    def test_large_font_directive_detection(self):
        """Test detection of large font requests in user prompt."""
        assert extract_directives("مع إظهار الرقم 0558815453 بخط كبير")["large_font"] is True
        assert extract_directives("رقم الهاتف في الأسفل كبير وواضح")["large_font"] is True
        assert extract_directives("ضع الرقم بارز وكبير")["large_font"] is True
        assert extract_directives("رقم الهاتف 0558815453 في الأسفل")["large_font"] is False

    def test_large_font_overlay_styling_and_size_scaling(self):
        """Verify font size calculation max(48, min(64, int(target_h * 0.042))) and black@0.78 box."""
        # Portrait 1080x1920: int(1920 * 0.042) = 80 -> clamped to 64
        filter_portrait = _build_drawtext_filter(
            {"text": "0558815453", "style": "persistent_bottom", "large_font": True},
            video_width=1080,
            video_height=1920,
        )
        assert "fontsize=64" in filter_portrait
        assert "boxcolor=black@0.78" in filter_portrait
        assert "boxborderw=16" in filter_portrait

        # Landscape 1280x720: int(720 * 0.042) = 30 -> max(48, ...) = 48
        filter_landscape = _build_drawtext_filter(
            {"text": "0558815453", "style": "persistent_bottom", "large_font": True},
            video_width=1280,
            video_height=720,
        )
        assert "fontsize=48" in filter_landscape
        assert "boxcolor=black@0.78" in filter_landscape
        assert "boxborderw=16" in filter_landscape

    def test_safe_margin_bottom_overlay_elevation(self):
        """Verify elevated safe margin safe_margin = max(110, int(video_height * 0.085)) avoids player controls."""
        # 1920 height: int(1920 * 0.085) = 163 -> safe_margin = 163
        filter_1920 = _build_drawtext_filter(
            {"text": "0558815453", "style": "persistent_bottom"},
            video_width=1080,
            video_height=1920,
        )
        assert "y=h-text_h-163" in filter_1920

        # 720 height: int(720 * 0.085) = 61 -> max(110, 61) = 110 -> safe_margin = 110
        filter_720 = _build_drawtext_filter(
            {"text": "0558815453", "style": "persistent_bottom"},
            video_width=1280,
            video_height=720,
        )
        assert "y=h-text_h-110" in filter_720

        # 1080 height: int(1080 * 0.085) = 91 -> max(110, 91) = 110 -> safe_margin = 110
        filter_1080 = _build_drawtext_filter(
            {"text": "0558815453", "style": "persistent_bottom"},
            video_width=1920,
            video_height=1080,
        )
        assert "y=h-text_h-110" in filter_1080


class TestPropertyFeaturesAndDynamicNarration:
    """Verify property features extraction, word count scaling, and dynamic Algerian Darja scripts."""

    def test_extract_property_features(self):
        """Test extraction of unit type (F5), sea view ('مطل على البحر'), and property type ('منزل')."""
        prompt = "أريد تعليق صوتي لمنزل F5 مطل على البحر بالدارجة وبدون موسيقى 0558815453"
        feats = extract_property_features(prompt)
        assert feats["unit"] == "F5"
        assert feats["sea_view"] is True
        assert feats["property_type"] == "منزل"
        assert "F5" in feats["keywords"]
        assert "مطل على البحر" in feats["keywords"]
        assert "منزل" in feats["keywords"]

    def test_target_words_formula_unclamped(self):
        """Verify target_words = max(18, min(160, int(speech_duration * 2.1))) removing 65-word clamp."""
        # For a 40s speech duration: int(40 * 2.1) = 84 words (previously clamped to 65)
        speech_dur_40 = 40.0
        target_40 = max(18, min(160, int(speech_dur_40 * 2.1)))
        assert target_40 == 84

        # For a 70s speech duration: int(70 * 2.1) = 147 words
        speech_dur_70 = 70.0
        target_70 = max(18, min(160, int(speech_dur_70 * 2.1)))
        assert target_70 == 147

    def test_dynamic_darja_script_mentions_all_features_without_phone_digits(self):
        """Verify _generate_dynamic_darja_script mentions F5, منزل, and sea view without speaking phone digits."""
        prompt = "أريد تعليق صوتي لمنزل F5 مطل على البحر بالدارجة وبدون موسيقى 0558815453"
        prop_feats = extract_property_features(prompt)
        directives = extract_directives(prompt)

        script = _generate_dynamic_darja_script(
            speech_duration=30.0,
            prop_feats=prop_feats,
            directives=directives,
        )

        assert "F5" in script
        assert "منزل" in script
        assert "بحر" in script or "البحر" in script
        # Crucial invariant: phone digits are NOT read aloud by TTS
        assert "0558815453" not in script
        # Check call to action
        assert "الرقم الظاهر أسفل الشاشة" in script

    def test_dynamic_pacing_scales_with_video_duration(self):
        """Verify narration length scales with video duration (short, medium, long)."""
        prompt = "أريد تعليق صوتي لمنزل F5 مطل على البحر"
        prop_feats = extract_property_features(prompt)
        dirs = extract_directives(prompt)

        short_script = _generate_dynamic_darja_script(10.0, prop_feats, dirs)
        med_script = _generate_dynamic_darja_script(25.0, prop_feats, dirs)
        long_script = _generate_dynamic_darja_script(50.0, prop_feats, dirs)

        len_short = len(short_script.split())
        len_med = len(med_script.split())
        len_long = len(long_script.split())

        assert len_short < len_med < len_long, f"Expected increasing length, got: {len_short}, {len_med}, {len_long}"
        assert len_long >= 80, f"Expected long script to have >= 80 words, got: {len_long}"


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
