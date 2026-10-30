"""
Tests for Strict Opt-In Architecture, Multi-Tenant Job Sandboxing, and Creative Variety Engine.
Author: MouhammedBoure <mohamadbormoz2@gmail.com>
Agent: agy11 (Backend Logic & Systems Engineer)
Branch: backend/agy11-optin-sandboxing-and-creative-variety
"""

from __future__ import annotations

import io
import json
import os
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from web.pipeline_bridge import (
    extract_directives,
    extract_property_features,
    parse_music_directives,
    process_mobile_video,
)
from web.vision_analyzer import (
    MARKETING_ANGLES,
    _generate_dynamic_darja_script,
    _get_smart_fallback,
    infer_video_script_and_mood,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestStrictOptInArchitecture:
    """Verify strict opt-in defaults: subtitles, music, and text overlays are OFF by default."""

    def test_subtitles_default_off_in_directives(self):
        """Prompt without subtitles directives must yield subtitles_requested=False."""
        prompts = [
            "أريد فيديو تسويقي لشقة فاخرة بالدارجة",
            "عقار رائع في قلب وهران",
            "فيديو جميل وبصوت هادئ",
        ]
        for p in prompts:
            dirs = extract_directives(p)
            assert dirs.get("subtitles_requested") is False, f"Expected False for: {p}"

    @pytest.mark.parametrize(
        "optin_prompt",
        [
            "أريد فيديو مع أضف ترجمة للكلام",
            "فيديو مع شريط ترجمة في الأسفل",
            "ترجمة فورية متزامنة مع المعلق",
            "اكتب الكلام في الأسفل مع نطق المعلق",
            "فيديو عقاري مع subtitles",
            "يرجى وضع captions متزامنة",
            "فيديو مع ترجمة متزامنة",
        ],
    )
    def test_subtitles_optin_detected(self, optin_prompt: str):
        """Prompt with explicit subtitle keywords must yield subtitles_requested=True."""
        dirs = extract_directives(optin_prompt)
        assert dirs.get("subtitles_requested") is True, f"Expected True for: {optin_prompt}"

    def test_music_default_off_in_directives(self):
        """Music is strictly muted (OFF) by default unless explicitly opted into."""
        default_prompts = [
            "أريد تعليق بالدارجة لشقة فاخرة",
            "فيديو سريع بدون إضافات",
            "جولة في المنزل مع التركيز على الغرف",
        ]
        for p in default_prompts:
            m_res = parse_music_directives(p)
            assert m_res["mute_music"] is True
            assert m_res["music_requested"] is False

    @pytest.mark.parametrize(
        "music_prompt,expected_track",
        [
            ("أريد موسيقى بيانو فاخرة", "luxury_piano"),
            ("مع موسيقى جيتار عصرية", "acoustic_guitar"),
            ("أضف موسيقى تأمل وبحر", "ambient_meditation"),
            ("خلفية موسيقية هادئة", None),
        ],
    )
    def test_music_optin_detected(self, music_prompt: str, expected_track: str | None):
        """Explicit music opt-in enables background music and extracts track."""
        m_res = parse_music_directives(music_prompt)
        assert m_res["mute_music"] is False
        assert m_res["music_requested"] is True
        if expected_track:
            assert m_res["music_track"] == expected_track

    @patch("web.pipeline_bridge.annotate_video")
    @patch("web.pipeline_bridge.synthesize_narration")
    @patch("web.pipeline_bridge.subprocess.run")
    @patch("frame_extractor.extract_keyframes")
    @patch("frame_extractor.get_video_metadata")
    def test_clean_video_default_produces_zero_annotations_and_muted_audio(
        self,
        mock_meta,
        mock_kf,
        mock_subp,
        mock_synth,
        mock_annot,
        tmp_path,
    ):
        """When user provides clean video without text, phone, subtitles, or music, output is 100% clean."""
        dummy_video = tmp_path / "clean_source.mp4"
        dummy_video.write_bytes(b"\x00" * 3000)

        mock_meta.return_value = {"width": 1080, "height": 1920, "total_duration": 12.0}
        mock_kf.return_value = {"frames": []}
        mock_synth.return_value = {
            "duration": 6.0,
            "synthesizer": "mock_tts",
            "file": str(tmp_path / "voice.wav"),
        }

        captured_cmds = []

        def fake_ffmpeg(cmd, *args, **kwargs):
            if isinstance(cmd, list) and len(cmd) > 0:
                captured_cmds.append(cmd)
                out_path = Path(cmd[-1])
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_bytes(b"mock_mp4_bytes")
            return MagicMock(returncode=0, stdout="", stderr="")

        mock_subp.side_effect = fake_ffmpeg
        mock_annot.return_value = {"status": "ok", "annotations_applied": 0}

        summary = process_mobile_video(
            video_path=dummy_video,
            script="شوفو معايا هاد الشقة الفاخرة بتشطيبات عصرية وموقع هادئ.",
            output_dir=tmp_path / "mobile_cuts",
            voice="ar-XA-Standard-A",
        )

        assert summary["status"] == "completed"
        # Subtitles default to empty
        assert summary["subtitles"] == []
        assert summary["subtitles_count"] == 0
        assert summary["subtitles_enabled"] is False
        # Music defaults to muted
        assert summary["music_muted"] is True
        assert summary["music_track"]["muted"] is True
        # Bottom text and phone are None
        assert summary["bottom_text"] is None
        assert summary["phone_number"] is None
        # No annotations were sent to annotate_video
        mock_annot.assert_not_called()
        assert summary["annotations_applied"] == 0

        # Check FFmpeg command has only 2 inputs: video + narration (no music)
        render_cmds = [c for c in captured_cmds if "-filter_complex" in c]
        assert len(render_cmds) > 0
        render_cmd = render_cmds[0]
        i_flags = [render_cmd[idx + 1] for idx, arg in enumerate(render_cmd) if arg == "-i"]
        assert len(i_flags) == 2, f"Expected 2 inputs (video + narration), got: {i_flags}"

    @patch("web.pipeline_bridge.annotate_video")
    @patch("web.pipeline_bridge.synthesize_narration")
    @patch("web.pipeline_bridge.subprocess.run")
    @patch("frame_extractor.extract_keyframes")
    @patch("frame_extractor.get_video_metadata")
    def test_explicit_optin_enables_subtitles_and_phone_and_music(
        self,
        mock_meta,
        mock_kf,
        mock_subp,
        mock_synth,
        mock_annot,
        tmp_path,
    ):
        """When user explicitly opts into subtitles, phone, and music, all features activate."""
        dummy_video = tmp_path / "optin_source.mp4"
        dummy_video.write_bytes(b"\x00" * 3000)

        mock_meta.return_value = {"width": 1080, "height": 1920, "total_duration": 15.0}
        mock_kf.return_value = {"frames": []}
        mock_synth.return_value = {
            "duration": 8.0,
            "synthesizer": "mock_tts",
            "file": str(tmp_path / "voice.wav"),
        }

        def fake_ffmpeg(cmd, *args, **kwargs):
            if isinstance(cmd, list) and len(cmd) > 0:
                out_path = Path(cmd[-1])
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_bytes(b"mock_mp4_bytes")
            return MagicMock(returncode=0, stdout="", stderr="")

        mock_subp.side_effect = fake_ffmpeg
        mock_annot.return_value = {"status": "ok", "annotations_applied": 6}

        summary = process_mobile_video(
            video_path=dummy_video,
            speech_description="أريد شقة F5 مطلة على البحر بالدارجة مع موسيقى بيانو وإظهار رقم 0558815453 وترجمة متزامنة",
            output_dir=tmp_path / "mobile_cuts",
            voice="ar-XA-Standard-A",
            auto_mode=True,
        )

        assert summary["status"] == "completed"
        # Subtitles active
        assert summary["subtitles_enabled"] is True
        assert summary["subtitles_count"] > 0
        # Music active
        assert summary["music_muted"] is False
        assert summary["music_track"]["id"] == "luxury_piano"
        # Phone active
        assert summary["phone_number"] == "0558815453"
        # Annotations passed to annotate_video
        mock_annot.assert_called_once()
        annots = mock_annot.call_args[1].get("annotations", [])
        has_sub = any(a.get("style") == "subtitle" for a in annots)
        has_phone = any(a.get("style") == "persistent_bottom" for a in annots)
        assert has_sub is True
        assert has_phone is True


class TestMultiTenantJobSandboxing:
    """Verify job isolation: all intermediate artifacts, keyframes, audio slices, and renders inside sandbox."""

    @patch("web.pipeline_bridge.annotate_video")
    @patch("web.pipeline_bridge.synthesize_narration")
    @patch("web.pipeline_bridge.subprocess.run")
    @patch("frame_extractor.extract_keyframes")
    @patch("frame_extractor.get_video_metadata")
    def test_job_sandbox_isolation_and_artifacts(
        self,
        mock_meta,
        mock_kf,
        mock_subp,
        mock_synth,
        mock_annot,
        tmp_path,
    ):
        """Verify per-job sandbox directory holds cut, narration, and summary files."""
        dummy_video = tmp_path / "sandbox_test.mp4"
        dummy_video.write_bytes(b"\x00" * 2000)

        mock_meta.return_value = {"width": 1080, "height": 1920, "total_duration": 10.0}

        kf1 = tmp_path / "frame_00.jpg"
        kf1.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 50)
        mock_kf.return_value = {"frames": [{"file_path": str(kf1), "timestamp": 0.0, "frame_index": 0}]}
        mock_synth.return_value = {
            "duration": 5.0,
            "synthesizer": "mock_tts",
            "file": str(tmp_path / "voice.wav"),
        }

        def fake_ffmpeg(cmd, *args, **kwargs):
            if isinstance(cmd, list) and len(cmd) > 0:
                out_path = Path(cmd[-1])
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_bytes(b"mock_mp4_bytes")
            return MagicMock(returncode=0, stdout="", stderr="")

        mock_subp.side_effect = fake_ffmpeg
        mock_annot.return_value = {"status": "ok"}

        out_cuts = tmp_path / "mobile_cuts"
        summary = process_mobile_video(
            video_path=dummy_video,
            script="شوفو معايا هاد الشقة العصرية الراقية.",
            output_dir=out_cuts,
        )

        job_id = summary["job_id"]
        sandbox_dir = Path(summary["sandbox_dir"])
        assert sandbox_dir.is_dir()
        assert f"outputs/jobs/{job_id}/sandbox" in str(sandbox_dir)

        # Check sandboxed video URL
        assert summary["sandboxed_video_url"] == f"/outputs/jobs/{job_id}/sandbox/cut_{job_id}.mp4"

        # Check sandboxed cut file exists
        sandboxed_cut = sandbox_dir / f"cut_{job_id}.mp4"
        assert sandboxed_cut.is_file()

        # Check sandboxed summary file exists
        sandboxed_summary = sandbox_dir / f"summary_{job_id}.json"
        assert sandboxed_summary.is_file()

        # Check backward compatibility mirror in mobile_cuts
        mirror_cut = out_cuts / f"cut_{job_id}.mp4"
        assert mirror_cut.is_file()


class TestCreativeVarietyEngine:
    """Verify stochastic variation in Darja narration scripts, marketing hooks, and Gemini Vision config."""

    def test_dynamic_darja_script_generates_varied_phrasing(self):
        """Repeated invocations of _generate_dynamic_darja_script must produce different outputs."""
        prop_feats = {"property_type": "شقة", "unit": "F4", "sea_view": True, "keywords": ["F4", "مطل على البحر"]}
        directives = {"is_meta_prompt": True}

        generated_scripts = set()
        for _ in range(12):
            s = _generate_dynamic_darja_script(
                speech_duration=35.0,
                prop_feats=prop_feats,
                directives=directives,
            )
            generated_scripts.add(s)

        # In 12 runs, with multiple hooks, salons, rooms, and CTAs, we should generate at least 3 distinct scripts
        assert len(generated_scripts) >= 3, f"Expected variety, got {len(generated_scripts)} unique scripts: {generated_scripts}"

    def test_marketing_angles_catalog_integrity(self):
        """Verify marketing angles pool has distinct themes."""
        assert len(MARKETING_ANGLES) >= 5
        assert any("Architectural Elegance" in a for a in MARKETING_ANGLES)
        assert any("Family Sanctuary" in a for a in MARKETING_ANGLES)
        assert any("Prime Investment" in a for a in MARKETING_ANGLES)

    def test_gemini_vision_temperature_and_angle_injection(self, tmp_path):
        """Verify infer_video_script_and_mood queries with temperature=0.80 and injects creative angle."""
        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": json.dumps({
                                    "script": "شوفو معايا هاد الشقة F4 الفاخرة بتشطيبات راقية.",
                                    "emotional_tone": "فاخر وهادئ",
                                    "emotional_prompt": "Warm, luxurious and prestigious narration",
                                    "recommended_music": "luxury_piano",
                                    "highlights": ["شقة F4 راقية"],
                                })
                            }
                        ]
                    }
                }
            ]
        }

        with patch("requests.post", return_value=fake_response) as mock_post, \
             patch.dict("os.environ", {"GEMINI_API_KEY": "mock_api_key"}):
            dummy_frame = tmp_path / "kf.jpg"
            dummy_frame.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 50)

            infer_video_script_and_mood(
                keyframe_paths=[dummy_frame],
                video_duration=20.0,
                speech_description="أريد تعليق صوتي لشقة F4",
            )

            assert mock_post.called
            call_kwargs = mock_post.call_args.kwargs
            json_payload = call_kwargs.get("json", {})
            gen_config = json_payload.get("generationConfig", {})

            # Temperature must be 0.80 for creative variety
            assert gen_config.get("temperature") == pytest.approx(0.80, abs=0.01)
            assert gen_config.get("topP") == pytest.approx(0.95, abs=0.01)

            # Prompt parts must include creative angle injection
            parts = json_payload.get("contents", [{}])[0].get("parts", [])
            prompt_text = "".join(p.get("text", "") for p in parts if "text" in p)
            assert "CREATIVE MARKETING ANGLE" in prompt_text
