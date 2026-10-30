#!/usr/bin/env python3
"""
Integration Gatekeeper Test Suite: Synchronized Captions, Shot Grounding, and Strict Prompt Adherence
Author: MouhammedBoure <mohamadbormoz2@gmail.com>
Branch: test/agy100-captions-and-shot-grounding-gatekeeper

Comprehensive Gatekeeper Verification:
1. Synchronized Subtitles & Captions Pipeline:
   - generate_synchronized_subtitles generates monotonically increasing intervals matching narration phrasing.
   - FFmpeg drawtext filters with position="subtitle" or style="subtitle" render with enable='between(t, start, end)'.
   - Subtitle safe margin is elevated (>= 185px) to sit strictly above persistent bottom overlay (contact banner / phone).
   - Coexistence verification: Subtitles and bottom overlay never collide.
2. Shot-by-Shot Visual Grounding & Anti-Hallucination:
   - extract_keyframe_records and build_shot_timeline build contiguous non-overlapping scenes covering total video duration.
   - Gemini Vision prompt contains strict anti-hallucination instructions forbidding mention of features not visible in keyframes.
   - Fallback and vision analysis incorporate videographer field speech when available.
3. Strict Customer Prompt Adherence:
   - Exact extraction of property specs (unit: F5, view: sea view, property: منزل, mute music, large font, phone number).
   - customer_specifications dictionary populated in job summary.
   - Phone digits strictly excluded from TTS narration.
4. Frontend UI/UX Contracts:
   - DOM elements in index.html: resultCaptionsPill, shotsTimelineSection, shotsTimelineList, timelineBadge, promptTextarea, promptInputHint.
   - app.js dynamic logic: captions badge, renderShotTimeline, formatTimestampRange.
   - CSS tokens in style.css.
5. Server API Exposure:
   - /api/status/{job_id} exposes subtitles, subtitles_count, shot_timeline, and customer_specifications.
6. Zero U+0669 Character Compliance across repository.
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

from web.pipeline_bridge import (
    analyze_source_audio_for_speech,
    extract_directives,
    extract_property_features,
    parse_music_directives,
    process_mobile_video,
)
from web.server import PROGRESS_STORE, app
from web.video_annotator import _build_drawtext_filter
from web.vision_analyzer import (
    _get_smart_fallback,
    build_shot_timeline,
    extract_keyframe_records,
    generate_synchronized_subtitles,
    infer_video_script_and_mood,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = REPO_ROOT / "web" / "static"

SAMPLE_CLIENT_PROMPT = (
    "أريد فيديو لشقة F5 مطلة على البحر بالدارجة وبدون موسيقى، "
    "مع إظهار رقم الهاتف 0558815453 في الأسفل بخط كبير وواضح وترجمة متزامنة لكلام المعلق"
)


class TestGatekeeperSynchronizedCaptionsFilters:
    """Gatekeeper verification for timestamp-synchronized captions, drawtext filter syntax, and non-collision."""

    def test_gatekeeper_subtitles_timing_and_alignment(self):
        """Verify generated subtitles cover narration duration monotonically without gaps or inversions."""
        script = (
            "شوفو معايا هاد الشقة F5 المطلة على البحر. "
            "رانا ندخلو للصالون الواسع والمضيء بتشطيبات عصرية وفينيسيون متقونة. "
            "المطبخ مجهز بالكامل بأحدث التجهيزات العصرية. "
            "اتصلو بنا على الرقم الظاهر أسفل الشاشة لحجز موعد الزيارة."
        )
        narration_dur = 16.0
        lead_in = 1.2

        subs = generate_synchronized_subtitles(
            script=script,
            narration_duration=narration_dur,
            visual_lead_in=lead_in,
        )

        assert len(subs) >= 4, f"Expected at least 4 subtitle chunks, got {len(subs)}"

        # Check first segment starts at or after lead-in
        assert subs[0]["start_sec"] >= lead_in
        assert subs[0]["end_sec"] > subs[0]["start_sec"]
        assert subs[0]["text"]

        # Check monotonic continuity
        for i in range(len(subs) - 1):
            cur = subs[i]
            nxt = subs[i + 1]
            assert cur["start_sec"] < cur["end_sec"]
            assert cur["end_sec"] <= nxt["start_sec"] + 0.15, (
                f"Overlap or gap between chunk {i} ({cur['end_sec']}) and {i+1} ({nxt['start_sec']})"
            )

        # Last segment should finish within reasonable bounds of total speaking duration
        last = subs[-1]
        assert last["end_sec"] <= lead_in + narration_dur + 0.5

    def test_gatekeeper_drawtext_filter_subtitle_position_and_enable_syntax(self):
        """Verify drawtext filter syntax for position='subtitle' uses enable='between(t, start, end)'."""
        sub_annotation = {
            "text": "صالون فسيح بإطلالة بحرية رائعة",
            "start_sec": 2.4,
            "end_sec": 5.8,
            "position": "subtitle",
            "style": "subtitle",
            "font_size": 34,
        }

        filter_str = _build_drawtext_filter(sub_annotation, video_width=1080, video_height=1920)

        # Must be valid drawtext filter
        assert filter_str.startswith("drawtext=")
        assert "text='صالون فسيح بإطلالة بحرية رائعة'" in filter_str
        assert "enable='between(t,2.40,5.80)'" in filter_str
        assert "fontcolor=white" in filter_str
        assert "x=(w-text_w)/2" in filter_str

        # Safe margin must elevate subtitle above bottom banner
        m = re.search(r"h-text_h-(\d+)", filter_str)
        assert m is not None
        margin = int(m.group(1))
        assert margin >= 185

    def test_gatekeeper_subtitles_and_persistent_bottom_overlay_coexistence(self):
        """Verify that subtitles sit strictly above persistent bottom overlay and do not collide."""
        phone_overlay = {
            "text": "0558815453",
            "start_sec": 0.0,
            "end_sec": 15.0,
            "position": "bottom_banner",
            "style": "persistent_bottom",
            "large_font": True,
        }
        subtitle_overlay = {
            "text": "شوفو معايا هاد الشقة F5",
            "start_sec": 1.2,
            "end_sec": 4.5,
            "position": "subtitle",
            "style": "subtitle",
        }

        filter_phone = _build_drawtext_filter(phone_overlay, video_width=1080, video_height=1920)
        filter_sub = _build_drawtext_filter(subtitle_overlay, video_width=1080, video_height=1920)

        m_phone = re.search(r"h-text_h-(\d+)", filter_phone)
        m_sub = re.search(r"h-text_h-(\d+)", filter_sub)
        assert m_phone is not None
        assert m_sub is not None

        phone_safe_margin = int(m_phone.group(1))
        sub_safe_margin = int(m_sub.group(1))

        # Subtitle safe margin must be strictly greater than bottom banner safe margin
        assert sub_safe_margin > phone_safe_margin
        assert sub_safe_margin - phone_safe_margin >= 50

    @patch("web.pipeline_bridge.annotate_video")
    @patch("web.pipeline_bridge.synthesize_narration")
    @patch("subprocess.run")
    @patch("frame_extractor.extract_keyframes")
    @patch("frame_extractor.get_video_metadata")
    def test_gatekeeper_process_video_includes_subtitles_in_annotations(
        self,
        mock_meta,
        mock_kf,
        mock_subproc,
        mock_tts,
        mock_annotate,
        tmp_path,
    ):
        """Verify process_mobile_video passes generated subtitles into annotate_video."""
        mock_meta.return_value = {"width": 1080, "height": 1920, "total_duration": 15.0}
        mock_kf.return_value = {"frames": []}
        mock_tts.return_value = {
            "wav_path": str(tmp_path / "voice.wav"),
            "duration": 9.0,
            "synthesizer": "gemini_speech_neural",
        }
        mock_annotate.return_value = {"status": "ok"}

        def fake_ffmpeg(cmd, *args, **kwargs):
            if isinstance(cmd, list) and len(cmd) > 0:
                out_path = Path(cmd[-1])
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_bytes(b"mock_mp4_bytes")
            return MagicMock(returncode=0, stdout="", stderr="")

        mock_subproc.side_effect = fake_ffmpeg

        dummy_input = tmp_path / "input.mp4"
        dummy_input.write_bytes(b"dummy_data")

        summary = process_mobile_video(
            video_path=dummy_input,
            script=SAMPLE_CLIENT_PROMPT,
            output_dir=tmp_path / "outputs",
            voice="ar-XA-Standard-A",
        )

        assert "subtitles" in summary
        assert len(summary["subtitles"]) >= 1
        assert summary["subtitles_count"] == len(summary["subtitles"])

        # Check call to annotate_video
        mock_annotate.assert_called_once()
        call_kwargs = mock_annotate.call_args[1]
        annotations = call_kwargs.get("annotations", [])
        subtitle_annots = [a for a in annotations if a.get("position") == "subtitle" or a.get("style") == "subtitle"]
        assert len(subtitle_annots) >= 1
        assert subtitle_annots[0]["start_sec"] >= 0.0
        assert subtitle_annots[0]["end_sec"] > subtitle_annots[0]["start_sec"]


class TestGatekeeperShotGroundingAndAntiHallucination:
    """Gatekeeper verification for shot timeline construction, timestamp association, and anti-hallucination."""

    def test_gatekeeper_extract_keyframe_records_and_shot_timeline(self, tmp_path):
        """Verify normalization of keyframe records and construction of contiguous scenes."""
        k1 = tmp_path / "frame_0000_000.00s.jpg"
        k2 = tmp_path / "frame_0001_003.80s.jpg"
        k3 = tmp_path / "frame_0002_008.20s.jpg"
        for k in (k1, k2, k3):
            k.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 40)

        records = extract_keyframe_records([k1, k2, k3], video_duration=12.0)
        assert len(records) == 3
        assert records[0]["timestamp_sec"] == 0.0
        assert records[1]["timestamp_sec"] == 3.8
        assert records[2]["timestamp_sec"] == 8.2

        timeline = build_shot_timeline(records, video_duration=12.0)
        assert len(timeline) == 3

        assert timeline[0]["scene_index"] == 1
        assert timeline[0]["start_sec"] == 0.0
        assert timeline[0]["end_sec"] == 3.8

        assert timeline[1]["scene_index"] == 2
        assert timeline[1]["start_sec"] == 3.8
        assert timeline[1]["end_sec"] == 8.2

        assert timeline[2]["scene_index"] == 3
        assert timeline[2]["start_sec"] == 8.2
        assert timeline[2]["end_sec"] == 12.0

    @patch("web.vision_analyzer.requests.post")
    def test_gatekeeper_anti_hallucination_mandate_in_vision_prompt(self, mock_post, tmp_path, monkeypatch):
        """Verify Gemini Vision prompt contains strict anti-hallucination constraints and scene timeline."""
        monkeypatch.setenv("GEMINI_API_KEY", "mock_key_for_testing")

        f1 = tmp_path / "frame_0000_000.00s.jpg"
        f2 = tmp_path / "frame_0001_004.00s.jpg"
        for f in (f1, f2):
            f.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 40)

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": json.dumps({
                            "script": "شوفو معايا هاد الشقة F5 المطلة على البحر.",
                            "subtitles": [
                                {"start_sec": 1.2, "end_sec": 4.0, "text": "شوفو معايا هاد الشقة F5"},
                                {"start_sec": 4.0, "end_sec": 8.0, "text": "مطلة على البحر والواجهة ممتازة"},
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
            video_duration=10.0,
            speech_description=SAMPLE_CLIENT_PROMPT,
            videographer_speech="رانا ندخلو للصالون الكبير المطل على البحر",
        )

        assert res["script"]
        assert len(res["subtitles"]) == 2
        assert len(res["shot_timeline"]) == 2

        # Check prompt payload
        call_kwargs = mock_post.call_args[1]
        body = call_kwargs["json"]
        prompt_text = body["contents"][0]["parts"][0]["text"]

        assert "ANTI-HALLUCINATION" in prompt_text
        assert "Scene 1 [0.0s - 4.0s]" in prompt_text
        assert "VIDEOGRAPHER FIELD SPEECH" in prompt_text
        assert "رانا ندخلو للصالون الكبير المطل على البحر" in prompt_text

    def test_gatekeeper_smart_fallback_produces_timeline_and_subtitles(self):
        """Verify _get_smart_fallback returns shot_timeline and subtitles without hallucinations."""
        fb = _get_smart_fallback(
            duration=20.0,
            speech_description=SAMPLE_CLIENT_PROMPT,
            visual_lead_in=1.2,
            outro_buffer=1.2,
            keyframe_count=4,
        )

        assert "script" in fb
        assert "shot_timeline" in fb
        assert len(fb["shot_timeline"]) >= 3
        assert "subtitles" in fb
        assert len(fb["subtitles"]) >= 2
        assert "F5" in fb["script"]
        assert "0558815453" not in fb["script"]  # Phone digits not spoken in fallback


class TestGatekeeperStrictCustomerPromptAdherence:
    """Gatekeeper verification for strict adherence to customer prompt specifications."""

    def test_gatekeeper_customer_specifications_parsed_completely(self):
        """Verify prompt parsing extracts unit, sea view, property type, large font, mute music, and phone."""
        directives = extract_directives(SAMPLE_CLIENT_PROMPT)
        prop_feats = extract_property_features(SAMPLE_CLIENT_PROMPT)
        music_dirs = parse_music_directives(SAMPLE_CLIENT_PROMPT)

        assert prop_feats["unit"] == "F5"
        assert prop_feats["sea_view"] is True
        assert prop_feats["property_type"] == "شقة"

        assert music_dirs["mute_music"] is True
        assert directives["large_font"] is True
        assert directives["phone_number"] == "0558815453"

    @patch("web.pipeline_bridge.annotate_video")
    @patch("web.pipeline_bridge.synthesize_narration")
    @patch("subprocess.run")
    @patch("frame_extractor.extract_keyframes")
    @patch("frame_extractor.get_video_metadata")
    def test_gatekeeper_process_video_stores_customer_specifications(
        self,
        mock_meta,
        mock_kf,
        mock_subproc,
        mock_tts,
        mock_annotate,
        tmp_path,
    ):
        """Verify process_mobile_video summary holds exact customer specifications."""
        mock_meta.return_value = {"width": 1080, "height": 1920, "total_duration": 10.0}
        mock_kf.return_value = {"frames": []}
        mock_tts.return_value = {
            "wav_path": str(tmp_path / "voice.wav"),
            "duration": 5.0,
            "synthesizer": "gemini_speech_neural",
        }
        mock_annotate.return_value = {"status": "ok"}

        def fake_ffmpeg(cmd, *args, **kwargs):
            if isinstance(cmd, list) and len(cmd) > 0:
                out_path = Path(cmd[-1])
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_bytes(b"mock_mp4_bytes")
            return MagicMock(returncode=0, stdout="", stderr="")

        mock_subproc.side_effect = fake_ffmpeg

        dummy_input = tmp_path / "input.mp4"
        dummy_input.write_bytes(b"dummy_bytes")

        summary = process_mobile_video(
            video_path=dummy_input,
            script=SAMPLE_CLIENT_PROMPT,
            output_dir=tmp_path / "outputs",
            voice="ar-XA-Standard-A",
        )

        specs = summary.get("customer_specifications", {})
        assert specs.get("unit") == "F5"
        assert specs.get("sea_view") is True
        assert specs.get("property_type") == "شقة"
        assert specs.get("mute_music") is True
        assert specs.get("large_font") is True
        assert specs.get("phone_number") == "0558815453"


class TestGatekeeperFrontendUIContracts:
    """Gatekeeper verification for frontend captions pill, shot timeline section, and prompt guidance."""

    def test_gatekeeper_html_dom_elements(self):
        """Verify presence of resultCaptionsPill and shotsTimelineSection in index.html."""
        html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")

        # Captions Feedback Pill
        assert 'id="resultCaptionsPill"' in html
        assert 'id="resultCaptionsIcon"' in html
        assert 'id="resultCaptionsText"' in html
        assert 'id="resultCaptionsBadge"' in html
        assert "ترجمة الكلام المتزامنة:" in html

        # Shot-by-Shot Timeline Section
        assert 'id="shotsTimelineSection"' in html
        assert 'id="timelineBadge"' in html
        assert 'id="shotsTimelineList"' in html
        assert "التسلسل الزمني للمشاهد واللقطات" in html
        assert "Shot-by-Shot Timeline" in html

        # Prompt guidance
        assert "ترجمة الكلام المتزامنة" in html
        assert "كلمة بكلمة" in html

    def test_gatekeeper_app_js_contracts(self):
        """Verify app.js handles captions pill and renders shot-by-shot timeline breakdown."""
        js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")

        # Captions handling
        assert "resultCaptionsPill" in js
        assert "resultCaptionsText" in js
        assert "resultCaptionsBadge" in js
        assert "ترجمة الكلام متزامنة" in js

        # Timeline rendering
        assert "renderShotTimeline" in js
        assert "formatTimestampRange" in js
        assert "shotsTimelineSection" in js
        assert "shotsTimelineList" in js
        assert "shot-timeline-item" in js
        assert "shot-timestamp" in js

    def test_gatekeeper_style_css_contracts(self):
        """Verify style.css rules for captions pill and shot timeline section."""
        css = (STATIC_DIR / "style.css").read_text(encoding="utf-8")

        assert ".result-captions-pill" in css
        assert ".captions-badge" in css
        assert ".shots-timeline-section" in css
        assert ".shots-timeline-list" in css
        assert ".shot-timeline-item" in css
        assert ".shot-timestamp" in css


class TestGatekeeperServerApiIntegration:
    """Gatekeeper verification for server API exposure of subtitles, count, and shot timeline."""

    def test_gatekeeper_status_api_exposes_subtitles_and_timeline(self):
        """Verify GET /api/status/{job_id} includes subtitles, subtitles_count, and shot_timeline."""
        client = TestClient(app)
        test_job_id = "test_captions_gatekeeper_job"

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
                "script": "شوفو معايا هاد الشقة F5 المطلة على البحر.",
                "bottom_text": "0558815453",
                "phone_number": "0558815453",
                "result": {
                    "job_id": test_job_id,
                    "status": "completed",
                    "video_url": f"/outputs/mobile_cuts/cut_{test_job_id}.mp4",
                    "script": "شوفو معايا هاد الشقة F5 المطلة على البحر.",
                    "subtitles": [
                        {"start_sec": 1.2, "end_sec": 4.5, "text": "شوفو معايا هاد الشقة F5"},
                        {"start_sec": 4.5, "end_sec": 8.0, "text": "مطلة على البحر بتشطيبات عصرية"},
                    ],
                    "subtitles_count": 2,
                    "shot_timeline": [
                        {"scene_index": 1, "start_sec": 0.0, "end_sec": 4.5, "title": "Scene 1 [0.0s - 4.5s]"},
                        {"scene_index": 2, "start_sec": 4.5, "end_sec": 10.0, "title": "Scene 2 [4.5s - 10.0s]"},
                    ],
                    "customer_specifications": {
                        "unit": "F5",
                        "sea_view": True,
                        "property_type": "شقة",
                        "phone_number": "0558815453",
                    },
                },
            }

            resp = client.get(f"/api/status/{test_job_id}")
            assert resp.status_code == 200
            data = resp.json()

            assert data["status"] == "completed"
            assert "subtitles" in data
            assert len(data["subtitles"]) == 2
            assert data["subtitles_count"] == 2
            assert "shot_timeline" in data
            assert len(data["shot_timeline"]) == 2
            assert data["customer_specifications"]["unit"] == "F5"
            assert data["customer_specifications"]["sea_view"] is True
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
