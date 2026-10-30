#!/usr/bin/env python3
"""
Tests for Synchronized Captions, Shot-by-Shot Visual Grounding & Strict Prompt Adherence.
Location: tests/test_synchronized_captions_and_shot_grounding.py

Author: MohammedBoure
Branch: backend/agy11-synchronized-captions-and-shot-grounding
"""

import json
import os
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from starlette.requests import Request
from starlette.responses import JSONResponse

from web.pipeline_bridge import (
    analyze_source_audio_for_speech,
    extract_directives,
    extract_property_features,
    process_mobile_video,
)
from web.video_annotator import _build_drawtext_filter, annotate_video
from web.vision_analyzer import (
    build_shot_timeline,
    extract_keyframe_records,
    generate_synchronized_subtitles,
    infer_video_script_and_mood,
    _get_smart_fallback,
)
from web.server import get_job_status, PROGRESS_STORE, JOBS_STORE


REPO_ROOT = Path(__file__).resolve().parent.parent


class TestShotGroundingAndAntiHallucination:
    """Verifies shot-by-shot keyframe timestamp association and strict anti-hallucination prompt constraints."""

    def test_extract_keyframe_records_with_timestamps(self, tmp_path):
        """Verify keyframe files or dictionaries are normalized with accurate timestamp_sec."""
        f1 = tmp_path / "frame_0000_000.00s.jpg"
        f2 = tmp_path / "frame_0001_003.50s.jpg"
        f3 = tmp_path / "frame_0002_007.25s.jpg"
        for f in (f1, f2, f3):
            f.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

        # 1. From filenames
        records = extract_keyframe_records([f1, f2, f3], video_duration=10.0)
        assert len(records) == 3
        assert records[0]["timestamp_sec"] == 0.0
        assert records[1]["timestamp_sec"] == 3.5
        assert records[2]["timestamp_sec"] == 7.25

        # 2. From metadata dicts
        dict_keyframes = [
            {"file_path": str(f1), "timestamp": 0.0, "frame_index": 0},
            {"file_path": str(f2), "timestamp_sec": 4.1, "frame_index": 1},
        ]
        records_from_dict = extract_keyframe_records(dict_keyframes, video_duration=10.0)
        assert len(records_from_dict) == 2
        assert records_from_dict[0]["timestamp_sec"] == 0.0
        assert records_from_dict[1]["timestamp_sec"] == 4.1

    def test_build_shot_timeline_coverage_and_continuity(self, tmp_path):
        """Verify shot timeline builds contiguous non-overlapping scenes covering total duration."""
        f1 = tmp_path / "frame_1.jpg"
        f2 = tmp_path / "frame_2.jpg"
        f3 = tmp_path / "frame_3.jpg"
        for f in (f1, f2, f3):
            f.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 50)

        records = [
            {"path": f1, "timestamp_sec": 0.0, "frame_index": 0},
            {"path": f2, "timestamp_sec": 4.0, "frame_index": 1},
            {"path": f3, "timestamp_sec": 8.5, "frame_index": 2},
        ]

        timeline = build_shot_timeline(records, video_duration=15.0)
        assert len(timeline) == 3

        # Scene 1: 0.0s -> 4.0s
        assert timeline[0]["scene_index"] == 1
        assert timeline[0]["start_sec"] == 0.0
        assert timeline[0]["end_sec"] == 4.0
        assert "Scene 1 [0.0s - 4.0s]" in timeline[0]["title"]

        # Scene 2: 4.0s -> 8.5s
        assert timeline[1]["scene_index"] == 2
        assert timeline[1]["start_sec"] == 4.0
        assert timeline[1]["end_sec"] == 8.5

        # Scene 3: 8.5s -> 15.0s (covers until video_duration)
        assert timeline[2]["scene_index"] == 3
        assert timeline[2]["start_sec"] == 8.5
        assert timeline[2]["end_sec"] == 15.0

    @patch("web.vision_analyzer.requests.post")
    def test_anti_hallucination_mandate_in_vision_prompt(self, mock_post, tmp_path, monkeypatch):
        """Verify Gemini Vision prompt contains shot timeline and strict anti-hallucination constraint."""
        monkeypatch.setenv("GEMINI_API_KEY", "test_mock_gemini_key")

        f1 = tmp_path / "frame_0000_000.00s.jpg"
        f2 = tmp_path / "frame_0001_004.50s.jpg"
        for f in (f1, f2):
            f.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": json.dumps({
                            "script": "شوفو معايا هاد الشقة F4 المطلة على البحر. الصالون واسع والمطبخ مجهز بأحدث التجهيزات. اتصلو بنا على الرقم الظاهر أسفل الشاشة.",
                            "subtitles": [
                                {"start_sec": 1.2, "end_sec": 4.5, "text": "شوفو معايا هاد الشقة F4 المطلة على البحر"},
                                {"start_sec": 4.6, "end_sec": 8.5, "text": "الصالون واسع ومطبخ مجهز بأحدث التجهيزات"},
                            ],
                            "emotional_tone": "فاخر وهادئ",
                            "emotional_prompt": "Warm luxury tone",
                            "recommended_music": "luxury_piano",
                            "highlights": ["صالون واسع", "إطلالة بحرية"],
                        })
                    }]
                }
            }]
        }
        mock_post.return_value = mock_resp

        res = infer_video_script_and_mood(
            keyframe_paths=[f1, f2],
            video_duration=12.0,
            speech_description="أريد تعليق صوتي لشقة F4 مطلة على البحر 0558815453",
            videographer_speech="هنا الصالون كبير ومطل على الواجهة البحرية",
        )

        assert res["script"]
        assert len(res["subtitles"]) >= 1
        assert len(res["shot_timeline"]) == 2

        # Inspect the prompt payload sent to Gemini
        call_args = mock_post.call_args
        body = call_args[1]["json"]
        prompt_text = body["contents"][0]["parts"][0]["text"]

        # Anti-hallucination checks
        assert "ANTI-HALLUCINATION" in prompt_text
        assert "FORBIDDEN" in prompt_text or "STRICT" in prompt_text
        assert "Scene 1 [0.0s - 4.5s]" in prompt_text
        assert "VIDEOGRAPHER FIELD SPEECH" in prompt_text
        assert "هنا الصالون كبير ومطل على الواجهة البحرية" in prompt_text


class TestSynchronizedSubtitlesAndCaptions:
    """Verifies timestamp-synchronized subtitle generation and FFmpeg drawtext integration."""

    def test_generate_synchronized_subtitles_timing_and_alignment(self):
        """Verify subtitles are segmented and aligned monotonically across speaking window."""
        script = "شوفو معايا هاد الشقة F4 المطلة على البحر. رانا ندخلو هنا للصالون الفسيح والمضيء. تشطيبات عصرية وفينيسيون متقونة. اتصلو بنا على الرقم الظاهر أسفل الشاشة."
        narration_duration = 14.0
        visual_lead_in = 1.2

        subs = generate_synchronized_subtitles(
            script=script,
            narration_duration=narration_duration,
            visual_lead_in=visual_lead_in,
        )

        assert len(subs) >= 3
        # Check monotonic progression and bounds
        first_seg = subs[0]
        assert first_seg["start_sec"] >= visual_lead_in
        assert first_seg["end_sec"] > first_seg["start_sec"]
        assert first_seg["text"]

        for i in range(len(subs) - 1):
            assert subs[i]["start_sec"] < subs[i]["end_sec"]
            assert subs[i]["end_sec"] <= subs[i + 1]["start_sec"] + 0.1

        last_seg = subs[-1]
        assert last_seg["end_sec"] <= visual_lead_in + narration_duration + 0.5

    def test_drawtext_subtitles_filter_styling_and_timing(self):
        """Verify FFmpeg drawtext filter for subtitles has proper style, timing, and elevated margin."""
        sub_annotation = {
            "text": "صالون فسيح وتشطيبات متقونة",
            "start_sec": 3.5,
            "end_sec": 6.8,
            "position": "subtitle",
            "style": "subtitle",
            "font_size": 36,
        }

        filter_str = _build_drawtext_filter(sub_annotation, video_width=1080, video_height=1920)

        assert "drawtext=" in filter_str
        assert "text='صالون فسيح وتشطيبات متقونة'" in filter_str
        assert "enable='between(t,3.50,6.80)'" in filter_str
        assert "fontcolor=white" in filter_str
        assert "x=(w-text_w)/2" in filter_str
        # Subtitle safe margin elevated above 185 to clear persistent bottom badge
        m = re.search(r"h-text_h-(\d+)", filter_str)
        assert m is not None
        safe_margin = int(m.group(1))
        assert safe_margin >= 185

    def test_subtitles_and_persistent_bottom_overlay_coexistence(self):
        """Verify that persistent bottom badge (phone) and subtitle can coexist without overlapping coordinates."""
        phone_overlay = {
            "text": "0558815453",
            "start_sec": 0.0,
            "end_sec": 15.0,
            "position": "bottom_banner",
            "style": "persistent_bottom",
            "large_font": True,
        }
        subtitle_overlay = {
            "text": "شوفو معايا هاد الشقة F4",
            "start_sec": 1.2,
            "end_sec": 4.5,
            "position": "subtitle",
            "style": "subtitle",
        }

        filter_phone = _build_drawtext_filter(phone_overlay, video_width=1080, video_height=1920)
        filter_subtitle = _build_drawtext_filter(subtitle_overlay, video_width=1080, video_height=1920)

        m_phone = re.search(r"h-text_h-(\d+)", filter_phone)
        m_sub = re.search(r"h-text_h-(\d+)", filter_subtitle)

        assert m_phone is not None
        assert m_sub is not None
        phone_margin = int(m_phone.group(1))
        sub_margin = int(m_sub.group(1))

        # Subtitle must sit strictly higher than the bottom contact badge
        assert sub_margin > phone_margin
        assert sub_margin - phone_margin >= 50


class TestStrictCustomerPromptAdherence:
    """Verifies that all user instructions and directives are faithfully extracted and represented."""

    def test_strict_customer_specifications_parsed_and_executed(self):
        """Verify comprehensive customer prompt parameters are accurately parsed."""
        user_prompt = "أريد فيديو لشقة F5 مطلة على البحر وبخط كبير وواضح وبدون موسيقى والهاتف 0558815453 أسفل الفيديو"
        dirs = extract_directives(user_prompt)

        assert dirs["is_meta_prompt"] is True
        assert dirs["phone_number"] == "0558815453"
        assert dirs["large_font"] is True
        assert dirs["music"]["mute_music"] is True
        assert dirs["property_features"]["unit"] == "F5"
        assert dirs["property_features"]["sea_view"] is True
        assert dirs["property_features"]["property_type"] == "شقة"

    def test_smart_fallback_produces_grounded_subtitles_and_timeline(self):
        """Verify fallback mode generates compliant shot_timeline and subtitles without hallucination."""
        fb = _get_smart_fallback(
            duration=16.0,
            speech_description="أريد شقة F3 في موقع هادئ مع رقم الهاتف 0661122334",
            visual_lead_in=1.2,
            outro_buffer=1.2,
        )

        assert "F3" in fb["script"]
        assert fb["phone_number"] == "0661122334"
        assert len(fb["subtitles"]) >= 2
        # Check that phone digits are not spoken aloud in narration
        assert "0661122334" not in fb["script"]
        # Subtitles must match script
        sub_text_combined = " ".join(s["text"] for s in fb["subtitles"])
        assert "0661122334" not in sub_text_combined


class TestPipelineBridgeAndApiEndToEnd:
    """Verifies full processing and status API responses exposing subtitles and shot grounding."""

    @patch("web.pipeline_bridge.annotate_video")
    @patch("web.pipeline_bridge.synthesize_narration")
    @patch("web.pipeline_bridge.subprocess.run")
    @patch("web.pipeline_bridge.frame_extractor.extract_keyframes")
    @patch("web.pipeline_bridge.frame_extractor.get_video_metadata")
    def test_process_mobile_video_includes_subtitles_and_shot_grounding(
        self, mock_meta, mock_extract, mock_subp, mock_synth, mock_annot, tmp_path
    ):
        """Verify process_mobile_video outputs subtitles and shot_timeline in summary."""
        test_video = tmp_path / "source.mp4"
        test_video.write_bytes(b"\x00" * 2000)

        mock_meta.return_value = {"width": 1080, "height": 1920, "total_duration": 10.0}

        kf1 = tmp_path / "frame_0000_000.00s.jpg"
        kf2 = tmp_path / "frame_0001_004.00s.jpg"
        for kf in (kf1, kf2):
            kf.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

        mock_extract.return_value = {
            "frames": [
                {"file_path": str(kf1), "timestamp": 0.0, "frame_index": 0},
                {"file_path": str(kf2), "timestamp": 4.0, "frame_index": 1},
            ]
        }
        mock_synth.return_value = {
            "duration": 6.5,
            "synthesizer": "mock_tts",
            "file": str(tmp_path / "narration.wav"),
        }

        def fake_ffmpeg_run(cmd, *args, **kwargs):
            if isinstance(cmd, list) and len(cmd) > 0:
                out_path = Path(cmd[-1])
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_bytes(b"fake_mp4_cut_data")
            return MagicMock(returncode=0, stdout="", stderr="")

        mock_subp.side_effect = fake_ffmpeg_run
        mock_annot.return_value = {"status": "ok", "annotations_applied": 4}

        summary = process_mobile_video(
            video_path=test_video,
            speech_description="أريد تعليق بالدارجة لشقة F4 مع إظهار رقم 0770123456 أسفل الفيديو",
            auto_mode=True,
        )

        assert summary["status"] == "completed"
        assert "subtitles" in summary
        assert len(summary["subtitles"]) >= 1
        assert "shot_timeline" in summary
        assert len(summary["shot_timeline"]) >= 1
        assert summary["customer_specifications"]["phone_number"] == "0770123456"
        assert summary["customer_specifications"]["unit"] == "F4"

        # Check call to annotate_video contains both subtitle and persistent bottom overlays
        annot_call_kwargs = mock_annot.call_args[1]
        annots = annot_call_kwargs.get("annotations", [])
        has_sub = any(a.get("style") == "subtitle" for a in annots)
        has_bottom = any(a.get("style") == "persistent_bottom" for a in annots)
        assert has_sub is True
        assert has_bottom is True

    @pytest.mark.asyncio
    async def test_api_status_exposes_subtitles_and_timeline(self):
        """Verify GET /api/status/{job_id} exposes subtitles, shot_timeline, and customer specs."""
        job_id = "test_status_captions_job"
        sample_subs = [
            {"start_sec": 1.2, "end_sec": 4.0, "text": "مرحباً بكم في هاد الشقة"},
            {"start_sec": 4.05, "end_sec": 7.5, "text": "صالون فسيح وتشطيبات عصرية"},
        ]
        sample_timeline = [
            {"scene_index": 1, "start_sec": 0.0, "end_sec": 4.0, "title": "Scene 1"},
            {"scene_index": 2, "start_sec": 4.0, "end_sec": 8.0, "title": "Scene 2"},
        ]

        # Populate PROGRESS_STORE
        PROGRESS_STORE[job_id] = {
            "status": "completed",
            "progress": 100,
            "progress_percent": 100,
            "subtitles": sample_subs,
            "shot_timeline": sample_timeline,
            "phone_number": "0558815453",
            "result": {
                "job_id": job_id,
                "subtitles": sample_subs,
                "shot_timeline": sample_timeline,
                "phone_number": "0558815453",
                "customer_specifications": {"unit": "F4", "phone_number": "0558815453"},
            }
        }

        # Mock cut file existing
        out_file = REPO_ROOT / "outputs" / "mobile_cuts" / f"cut_{job_id}.mp4"
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_bytes(b"\x00" * 1024)

        try:
            scope = {
                "type": "http",
                "method": "GET",
                "path": f"/api/status/{job_id}",
                "path_params": {"job_id": job_id},
                "headers": [],
            }
            req = Request(scope)
            resp = await get_job_status(req)
            assert resp.status_code == 200

            data = json.loads(resp.body.decode("utf-8"))
            assert data["status"] == "completed"
            assert data["subtitles"] == sample_subs
            assert data["shot_timeline"] == sample_timeline
            assert data["customer_specifications"]["unit"] == "F4"
        finally:
            if out_file.is_file():
                out_file.unlink()
            PROGRESS_STORE.pop(job_id, None)


def test_no_forbidden_arabic_character_in_repository():
    """Verify strictly ZERO occurrences of Arabic character U+0669 across the repository."""
    forbidden = "\u0669"
    violations = []
    for root, dirs, files in os.walk(REPO_ROOT):
        if ".git" in dirs:
            dirs.remove(".git")
        if "__pycache__" in dirs:
            dirs.remove("__pycache__")
        if ".pytest_cache" in dirs:
            dirs.remove(".pytest_cache")
        for f in files:
            if f.endswith((".py", ".html", ".js", ".css", ".md", ".json", ".sh")):
                filepath = os.path.join(root, f)
                try:
                    with open(filepath, "r", encoding="utf-8") as fp:
                        content = fp.read()
                        if forbidden in content:
                            violations.append(filepath)
                except Exception:
                    pass

    assert not violations, f"Forbidden Arabic character U+0669 found in: {violations}"
