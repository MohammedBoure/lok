#!/usr/bin/env python3
"""
Verification tests for the 5 core user-reported issues:
1. Audio-Subtitle-Scene synchronization when user requests text with voiceover.
2. User directives & montage desires translated accurately to the montage executor.
3. Voice & script variety when re-submitting the same video for a new voice/script.
4. Improved text overlay templates, cross-platform Arabic font support, and line wrapping.
5. General-purpose customer-driven defaults across all domains (not hardcoded to real estate).
"""

import tempfile
from pathlib import Path

from config.production_principles_manager import build_vision_prompt_principles, load_principles
from web.pipeline_bridge import (
    extract_directives,
    generate_synthetic_voice,
    parse_montage_directives,
    sanitize_script_against_meta_prompts,
)
from web.video_annotator import (
    _build_drawtext_filter,
    _escape_ffmpeg_fontfile_path,
    find_system_font,
    wrap_annotation_text,
)
from web.vision_analyzer import (
    _generate_dynamic_darja_script,
    _get_smart_fallback,
    build_shot_timeline,
    generate_synchronized_subtitles,
)


def test_issue_1_subtitle_audio_scene_synchronization():
    """Verify subtitles align with exact spoken narration duration and shot timeline scenes."""
    script = (
        "مرحبا بيكم في مطعمنا الجديد للبيتزا الإيطالية الأصيلة، "
        "تحضير يومي طازج بأجود المكونات، "
        "اطلبوا الآن واستمتعوا بأفضل مذاق."
    )
    shot_timeline = [
        {"scene_index": 1, "start_sec": 0.0, "end_sec": 3.5},
        {"scene_index": 2, "start_sec": 3.5, "end_sec": 7.0},
        {"scene_index": 3, "start_sec": 7.0, "end_sec": 10.5},
    ]
    narration_dur = 8.4
    lead_in = 1.2

    subs = generate_synchronized_subtitles(
        script=script,
        narration_duration=narration_dur,
        visual_lead_in=lead_in,
        shot_timeline=shot_timeline,
    )
    assert len(subs) >= 2
    assert subs[0]["start_sec"] == lead_in
    assert abs(subs[-1]["end_sec"] - (lead_in + narration_dur)) <= 0.05

    # Ensure monotonic non-overlapping timestamps and scene_index binding
    for i in range(len(subs)):
        assert subs[i]["end_sec"] > subs[i]["start_sec"]
        assert "scene_index" in subs[i]
        assert subs[i]["scene_index"] in (1, 2, 3)
        if i > 0:
            assert subs[i]["start_sec"] >= subs[i - 1]["end_sec"]


def test_issue_2_user_directives_and_montage_translation():
    """Verify broader Arabic/Darja montage commands, voice selection, highlights, and orientation directives."""
    # Trim start in Darja/Arabic
    m1 = parse_montage_directives("نحي أول 4 ثواني من الفيديو")
    assert m1["requested"] is True
    assert m1["mode"] == "trim_start"
    assert m1["trim_start"] == 4.0

    # Target duration with 'لا يتجاوز'
    m2 = parse_montage_directives("اختصر الفيديو بحيث لا يتجاوز 12 ثانية")
    assert m2["requested"] is True
    assert m2["target_duration"] == 12.0

    # Interval with 'لـ'
    m3 = parse_montage_directives("احتفظ بالمقطع من الثانية 2 لـ 9")
    assert m3["requested"] is True
    assert m3["mode"] == "interval"
    assert m3["trim_start"] == 2.0
    assert m3["trim_end"] == 9.0

    # Comprehensive directive extraction (voice, orientation, subtitles, highlights)
    dirs = extract_directives("أريد تعليق صوتي بصوت رجل مع نص مع الصوت وإظهار المميزات لفيديو ريلز عمودي")
    assert dirs["requested_voice"] == "ar-XA-Standard-B"
    assert dirs["subtitles_requested"] is True
    assert dirs["highlights_requested"] is True
    assert dirs["orientation_requested"] == "portrait"


def test_issue_3_voice_and_script_variety_across_reruns():
    """Verify re-running on the same video produces distinct scripts and distinct voice acoustics."""
    shot_timeline = build_shot_timeline([], video_duration=12.0)

    scripts = set()
    for _ in range(5):
        fb = _get_smart_fallback(
            duration=12.0,
            speech_description="إعلان لمطعم برجر مشوي على الفحم",
            shot_timeline=shot_timeline,
        )
        scripts.add(fb["script"])
    # Multiple runs on the same input should yield varied scripts
    assert len(scripts) >= 2

    # Different voices or scripts produce different acoustic waveforms and durations
    with tempfile.TemporaryDirectory() as tmpdir:
        wav_female = Path(tmpdir) / "female.wav"
        wav_male = Path(tmpdir) / "male.wav"
        text = "مرحبا بكم في عرضنا الجديد بجودة عالية وتصميم عصري مميز"

        dur_f = generate_synthetic_voice(text, wav_female, voice="ar-XA-Standard-A", emotional_tone="هادئ")
        dur_m = generate_synthetic_voice(text, wav_male, voice="ar-XA-Standard-C", emotional_tone="متحمس وحيوي")

        assert wav_female.read_bytes() != wav_male.read_bytes()
        assert dur_f != dur_m


def test_issue_4_text_overlay_templates_wrapping_and_windows_font_escaping():
    """Verify Windows font path colon escaping, Arabic text wrapping, and non-colliding badge styles."""
    escaped = _escape_ffmpeg_fontfile_path("C:/Windows/Fonts/arialbd.ttf")
    assert "C\\:/Windows/Fonts/arialbd.ttf" == escaped

    long_text = "هذا النص الطويل جدا يحتاج إلى تقسيم تلقائي على عدة أسطر حتى لا يخرج خارج حدود شاشة الفيديو"
    wrapped = wrap_annotation_text(long_text, max_chars_per_line=34)
    lines = wrapped.split("\n")
    assert 2 <= len(lines) <= 3

    font_path = find_system_font()
    f_badge = _build_drawtext_filter(
        {
            "text": "جودة استثنائية",
            "start_sec": 1.0,
            "end_sec": 4.0,
            "position": "top_right",
            "style": "highlight_badge",
        },
        font_file=font_path,
        video_width=1080,
        video_height=1920,
    )
    assert "fontcolor=0xF8FAFC" in f_badge
    assert "enable='between(t,1.00,4.00)'" in f_badge
    assert "y=max(68,h*0.07)" in f_badge


def test_issue_5_general_purpose_customer_driven_not_real_estate_biased():
    """Verify non-real-estate customer requests generate domain-accurate scripts without forced apartment/salon terms."""
    restaurant_script = _generate_dynamic_darja_script(
        speech_duration=12.0,
        prop_feats={},
        directives={},
        user_topic="مطعم بيتزا إيطالية على الحطب مع توصيل سريع",
    )
    assert "بيتزا" in restaurant_script
    for forbidden_re_word in ["شقة", "عقار", "صالون", "غرف", "سكن"]:
        assert forbidden_re_word not in restaurant_script

    car_fallback = _get_smart_fallback(
        duration=12.0,
        speech_description="معرض سيارات رياضية حديثة بضمان شامل",
    )
    assert "سيارات" in car_fallback["script"]
    for forbidden_re_word in ["شقة", "عقار", "صالون"]:
        assert forbidden_re_word not in car_fallback["script"]

    principles_prompt = build_vision_prompt_principles()
    assert "التكيف التام مع موضوع الفيديو وطلب الزبون" in principles_prompt
    loaded = load_principles()
    assert "التكيف التام مع موضوع الفيديو وطلب الزبون" in loaded["narrative_principles"]["guidelines"]

