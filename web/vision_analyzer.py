#!/usr/bin/env python3
"""
Multimodal Vision Analyzer for Real Estate Video (web/vision_analyzer.py)
Infers engaging Arabic voiceover script, emotional atmosphere/mood, and background music
from extracted video keyframes using Gemini Multimodal Vision API.

Author: MouhammedBoure
Role: Backend Architecture & Processing Bridge (agy11)
Branch: backend/agy11-auto-vision-script-and-app-runner
"""

from __future__ import annotations

import base64
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import requests

from config.production_principles_manager import (
    build_vision_prompt_principles,
    load_principles,
)
from web.pipeline_bridge import (
    extract_algerian_phone,
    is_meta_prompt,
    extract_directives,
    sanitize_script_against_meta_prompts,
    extract_property_features,
)

logger = logging.getLogger("vision_analyzer")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s")

# Active high-performance Gemini Multimodal Vision models in preference order
ACTIVE_VISION_MODELS = [
    "gemini-3.8-flash",
    "gemini-2.5-flash",
    "gemini-3.1-pro-preview",
]

# Ensure environment configuration (.env)
REPO_ROOT = Path(__file__).resolve().parent.parent

def _ensure_env_loaded() -> None:
    """Load GEMINI_API_KEY from .env if not currently present in os.environ."""
    if os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEYS"):
        return
    candidates = [
        REPO_ROOT / ".env",
        REPO_ROOT / "tts" / ".env",
        Path.cwd() / ".env",
    ]
    for env_path in candidates:
        if env_path.is_file():
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k, v = k.strip(), v.strip().strip("\"'")
                            if k not in os.environ:
                                os.environ[k] = v
            except OSError:
                pass

_ensure_env_loaded()


# ---------------------------------------------------------------------------
# Keyframe Records, Shot Timeline & Subtitles Pipeline
# ---------------------------------------------------------------------------

def extract_keyframe_records(
    keyframe_paths: List[Union[str, Path, Dict[str, Any]]],
    keyframes_metadata: Optional[List[Dict[str, Any]]] = None,
    video_duration: float = 10.0,
) -> List[Dict[str, Any]]:
    """
    Normalize keyframe inputs into structured records with precise timestamp_sec.
    Extracts timestamps from metadata dicts, embedded timestamp fields, or filenames.
    """
    records: List[Dict[str, Any]] = []
    for idx, item in enumerate(keyframe_paths):
        if isinstance(item, dict):
            p_val = item.get("file_path") or item.get("path") or item.get("absolute_file_path", "")
            p = Path(p_val).resolve()
            raw_t = item.get("timestamp_sec") if item.get("timestamp_sec") is not None else item.get("timestamp", 0.0)
            try:
                t = float(raw_t)
            except (ValueError, TypeError):
                t = 0.0
            records.append({
                "path": p,
                "timestamp_sec": round(max(0.0, t), 2),
                "frame_index": item.get("frame_index", idx),
            })
        else:
            p = Path(item).resolve()
            t = 0.0
            if keyframes_metadata and idx < len(keyframes_metadata):
                meta = keyframes_metadata[idx]
                raw_t = meta.get("timestamp_sec") if meta.get("timestamp_sec") is not None else meta.get("timestamp", 0.0)
                try:
                    t = float(raw_t)
                except (ValueError, TypeError):
                    t = 0.0
            else:
                m = re.search(r"_(\d+(?:\.\d+)?)s\.(?:jpg|png|jpeg)", p.name, re.IGNORECASE)
                if m:
                    t = float(m.group(1))
                elif len(keyframe_paths) > 1:
                    t = round((idx / max(1, len(keyframe_paths) - 1)) * video_duration, 2)
            records.append({
                "path": p,
                "timestamp_sec": round(max(0.0, t), 2),
                "frame_index": idx,
            })

    # Sort strictly by timestamp
    valid_records = [r for r in records if r["path"].is_file() and r["path"].stat().st_size > 0]
    valid_records.sort(key=lambda r: r["timestamp_sec"])
    return valid_records


def build_shot_timeline(
    keyframe_records: List[Dict[str, Any]],
    video_duration: float = 10.0,
) -> List[Dict[str, Any]]:
    """
    Construct an explicit shot-by-shot timeline interval for every keyframe.
    E.g. Scene 1 [0.0s - 3.5s], Scene 2 [3.5s - 7.0s], etc.
    Provides chronological visual grounding preventing hallucinated spaces.
    """
    if not keyframe_records:
        return []

    timeline: List[Dict[str, Any]] = []
    n = len(keyframe_records)
    for i in range(n):
        curr_t = keyframe_records[i]["timestamp_sec"]
        start_sec = max(0.0, round(curr_t, 2))
        if i + 1 < n:
            next_t = keyframe_records[i + 1]["timestamp_sec"]
            end_sec = round(max(start_sec + 0.5, next_t), 2)
        else:
            end_sec = round(max(start_sec + 0.5, video_duration), 2)

        timeline.append({
            "scene_index": i + 1,
            "start_sec": start_sec,
            "end_sec": end_sec,
            "duration": round(end_sec - start_sec, 2),
            "keyframe_timestamp": curr_t,
            "keyframe_path": str(keyframe_records[i]["path"]),
            "title": f"Scene {i + 1} [{start_sec:.1f}s - {end_sec:.1f}s]",
        })
    return timeline


def generate_synchronized_subtitles(
    script: str,
    narration_duration: float,
    visual_lead_in: float = 1.2,
    min_segment_duration: float = 1.2,
    max_words_per_segment: int = 7,
) -> List[Dict[str, Any]]:
    """
    Generate timestamp-synchronized subtitle segments (start_sec, end_sec, text)
    matching the natural spoken phrasing of the narration script across the audio duration.
    """
    raw_script = str(script or "").strip()
    if not raw_script:
        return []

    # Split script into natural phrasing clauses by punctuation
    raw_clauses = re.split(r"[.،!؟\n;:]+", raw_script)
    clauses = [c.strip() for c in raw_clauses if c.strip()]
    if not clauses:
        clauses = [raw_script]

    # Break long clauses into manageable reading chunks (4 to 7 words)
    segments_text: List[str] = []
    for clause in clauses:
        words = clause.split()
        if len(words) <= max_words_per_segment:
            segments_text.append(clause)
        else:
            for chunk_idx in range(0, len(words), max_words_per_segment):
                chunk = " ".join(words[chunk_idx : chunk_idx + max_words_per_segment])
                if chunk:
                    segments_text.append(chunk)

    if not segments_text:
        segments_text = [raw_script]

    total_words = sum(max(1, len(seg.split())) for seg in segments_text)
    effective_speech_dur = max(2.0, float(narration_duration))

    subtitles: List[Dict[str, Any]] = []
    curr_t = round(float(visual_lead_in), 2)

    for idx, seg in enumerate(segments_text):
        seg_words = max(1, len(seg.split()))
        seg_ratio = seg_words / float(total_words)
        seg_dur = max(min_segment_duration, round(seg_ratio * effective_speech_dur, 2))

        start_t = curr_t
        end_t = round(start_t + seg_dur, 2)

        subtitles.append({
            "segment_index": idx + 1,
            "start_sec": start_t,
            "end_sec": end_t,
            "text": seg,
        })
        curr_t = round(end_t + 0.05, 2)

    # Normalize final segment end time so it aligns cleanly with audio duration
    max_allowed = round(visual_lead_in + effective_speech_dur, 2)
    if subtitles and subtitles[-1]["end_sec"] > max_allowed:
        scale = effective_speech_dur / max(0.1, (subtitles[-1]["end_sec"] - visual_lead_in))
        for sub in subtitles:
            sub["start_sec"] = round(visual_lead_in + (sub["start_sec"] - visual_lead_in) * scale, 2)
            sub["end_sec"] = round(visual_lead_in + (sub["end_sec"] - visual_lead_in) * scale, 2)

    return subtitles


# ---------------------------------------------------------------------------
# Smart Heuristic Fallback Profiles
# ---------------------------------------------------------------------------

FALLBACK_PROFILES = [
    {
        "script": "شقة فاخرة بتشطيبات عالية الجودة وإطلالة استثنائية في قلب العاصمة، موقع هادئ وقريب من كل المرافق الحيوية.",
        "emotional_tone": "فاخر وهادئ",
        "emotional_prompt": "Warm, luxurious, prestigious, and calm real estate narration",
        "recommended_music": "luxury_piano",
        "highlights": ["شقة فاخرة عالية التشطيب", "موقع استراتيجي هادئ"],
    },
    {
        "script": "فيلا عصرية بواجهة خلابة وتصميم معماري رفيع يلبي أعلى معايير الرفاهية والراحة لجميع أفراد عائلتك.",
        "emotional_tone": "دافئ وأنيق",
        "emotional_prompt": "Warm, elegant, inviting and serene acoustic cadence",
        "recommended_music": "ambient_meditation",
        "highlights": ["فيلا عصرية راقية", "تصميم معماري فاخر"],
    },
    {
        "script": "فرصة استثمارية واعدة في موقع تجاري حيوي واستراتيجي، واجهة ممتازة تضمن لعملك النجاح والازدهار.",
        "emotional_tone": "متحمس وحيوي",
        "emotional_prompt": "Energetic, bright, confident and dynamic commercial presentation",
        "recommended_music": "acoustic_guitar",
        "highlights": ["فرصة استثمارية واعدة", "موقع تجاري حيوي"],
    },
    {
        "script": "عقار متميز ومجهز بالكامل بأحدث التجهيزات العصرية، يجمع بين الأمان والراحة العائلية الفائقة.",
        "emotional_tone": "هادئ ومطمئن",
        "emotional_prompt": "Gentle, reassuring, cozy and friendly familial tone",
        "recommended_music": "acoustic_guitar",
        "highlights": ["تجهيزات عصرية متكاملة", "أمان وراحة عائلية"],
    },
]


MARKETING_ANGLES = [
    "Architectural Elegance & Luxury Finishes (الفخامة والتشطيبات المعمارية الراقية)",
    "Family Sanctuary & Peaceful Living (السكينة والراحة العائلية الفائقة)",
    "Prime Investment & Strategic Opportunity (الاستثمار الاستراتيجي والعائد المتميز)",
    "Modern Mediterranean Flow & Panoramic Horizons (الحياة العصرية المشرقة والإطلالات البانورامية)",
    "Warm Welcoming Living & Contemporary Prestige (الدفء والتميز المعاصر)",
]

HOOK_TEMPLATES = [
    "شوفو معايا هاد الـ{prop_type}{unit_str}، {view_str}.",
    "شوفو معايا هاد الجولة الحصرية لهاد الـ{prop_type}{unit_str}، {view_str}.",
    "شوفو معايا هاد العقار الاستثنائي: {prop_type}{unit_str} {view_str} يلبي كل التطلعات.",
    "شوفو معايا لعشاق التميز والراحة، هاد الـ{prop_type}{unit_str} {view_str} بمواصفات نادرة.",
    "شوفو معايا هاد العرض الاستثنائي: {prop_type}{unit_str} فاخر ومتميز، {view_str}.",
]

SALON_TEMPLATES = [
    "رانا هنا ندخلو للصالون الواسع والمضيء، تشطيبات عصرية وفينيسيون متقونة توفر أقصى درجات الراحة.",
    "أول ما يلفت انتباهنا هو الصالون الفسيح بإنارة طبيعية مبهجة وديكور راقي ومريح للغاية.",
    "شوفو رحابة الصالون والمساحة المفتوحة، هندسة داخلية مدروسة بعناية لتمنح عائلتكم أجواء دافئة.",
    "صالون استقبال ملكي بمساحة ممتازة وتنسيق أنيق، يجمع بين الفخامة والبساطة المعاصرة.",
]

ROOMS_TEMPLATES = [
    "توزيع الغرف مدروس ومريح بزاف مع تهوية طبيعية ممتازة ومساحات واسعة تناسب كامل تطلعات العائلة.",
    "غرف النوم مستقلة وهادئة بتصميم يوفر الخصوصية والسكينة التامة لجميع أفراد الأسرة.",
    "المساحات المخصصة للنوم والاسترخاء رحبة ومخدومة بذكاء، مع إطلالات شرحة ومداخل إنارة طبيعية رائعة.",
]

KITCHEN_TEMPLATES = [
    "المطبخ عصري ومجهز بالكامل بأحدث التجهيزات، وكل زاوية في هاد العقار مخدومة بإتقان واهتمام بأدق التفاصيل.",
    "مطبخ أمريكي راقي مفتوح وعملي للغاية، مجهز بأجود المواد لتجربة طهي واستقبال عائلية ممتعة.",
    "وفينيسيون المطبخ والحمامات على أعلى مستوى من الإتقان، جودة تدوم وتلبي أرقى الأذواق.",
]

LOCATION_TEMPLATES = [
    "الموقع هادئ وآمن ومثالي، مع إمكانية الوصول السريع لكافة الخدمات الأساسية والمحاور الرئيسية.",
    "حي راقي ومجاور لكافة المرافق الضرورية من مدارس ونقل وتجارة، يضمن لكم حياة يومية مريحة.",
    "موقع متميز يجمع بين السكينة وسهولة التنقل، موقع لا يعوض في قلب المنطقة.",
]

CTA_TEMPLATES = [
    "فرصة استثنائية ونادرة للسكن أو الاستثمار، اتصلو بنا على الرقم الظاهر أسفل الشاشة لحجز موعد الزيارة والاستفسار.",
    "ما تفوتوش هاد الفرصة الذهبية، للمزيد من التفاصيل والزيارة تواصلو معنا مباشرة عبر الرقم الظاهر أسفل الشاشة.",
    "للمهتمين بهاد العقار الفاخر، فريقنا في خدمتكم، سارعو بالاتصال على الرقم الظاهر أسفل الشاشة للحجز.",
    "عقار يضمن لكم قيمة عقارية ممتازة وراحة دائمة، لا تترددوا في الاتصال بالرقم الظاهر أسفل الشاشة.",
]


def _generate_dynamic_darja_script(
    speech_duration: float,
    prop_feats: Dict[str, Any],
    directives: Dict[str, Any],
    preset_hint: Optional[str] = None,
) -> str:
    """
    Generate an engaging, continuous Algerian Darja real estate script
    scaled dynamically to cover the net speaking window without abrupt silence.
    Incorporates property features (F1..F6, sea views, property type) and CTA,
    utilizing rich variation pools to ensure narrative diversity across runs.
    """
    import random

    unit = prop_feats.get("unit")
    has_sea_view = prop_feats.get("sea_view", False)
    prop_type = prop_feats.get("property_type") or ("فيلا" if has_sea_view else "شقة")

    unit_str = f" {unit}" if unit else ""
    if has_sea_view:
        view_str = "مطلة مباشرة على البحر وبإطلالة بانورامية ساحرة" if prop_type in ("فيلا", "شقة", "دار") else "مطل مباشرة على البحر وبإطلالة بانورامية ساحرة"
    else:
        view_str = "في موقع استراتيجي راقي وهادئ وقريب من كامل المرافق الحيوية"

    # Phase 1: Dynamic Hook / Introduction
    hook_tpl = random.choice(HOOK_TEMPLATES)
    hook = hook_tpl.format(prop_type=prop_type, unit_str=unit_str, view_str=view_str)

    # Phase 2: Walkthrough progression scaled dynamically to available duration
    tour_segments = [random.choice(SALON_TEMPLATES)]

    if speech_duration >= 18.0:
        tour_segments.append(random.choice(ROOMS_TEMPLATES))
    if speech_duration >= 28.0:
        tour_segments.append(random.choice(KITCHEN_TEMPLATES))
    if speech_duration >= 40.0:
        tour_segments.append(random.choice(LOCATION_TEMPLATES))

    # Phase 3: Closing Call to Action (CTA)
    cta = random.choice(CTA_TEMPLATES)

    return f"{hook} {' '.join(tour_segments)} {cta}"


def _get_smart_fallback(
    duration: float = 10.0,
    preset_hint: Optional[str] = None,
    speech_description: Optional[str] = None,
    visual_description: Optional[str] = None,
    visual_lead_in: float = 1.2,
    outro_buffer: float = 1.2,
    keyframe_count: int = 0,
    shot_timeline: Optional[List[Dict[str, Any]]] = None,
    videographer_speech: Optional[str] = None,
) -> Dict[str, Any]:
    """Provide intelligent fallback when Gemini Vision API is offline or unreachable."""
    principles = load_principles()
    master = principles.get("master_directive", {})
    custom_text = str(master.get("custom_instructions", ""))
    dialect = str(master.get("dialect", "algerian_darja"))
    perspective = str(master.get("perspective", "videographer_walkthrough"))

    is_darja_or_walkthrough = (
        dialect == "algerian_darja"
        or perspective == "videographer_walkthrough"
        or any(k in custom_text for k in ["جزائر", "دارجة", "يصور", "يتكلم", "جولة", "أنا"])
    )

    # Net speaking duration accounting for visual establishing and outro swell
    speech_duration = max(2.0, round(duration - visual_lead_in - outro_buffer, 2))

    # Base profile selection from hint or visual/speech description keywords
    desc_for_mood = f"{visual_description or ''} {speech_description or ''} {videographer_speech or ''}".lower()
    prop_feats = extract_property_features(speech_description or "")
    has_sea_features = prop_feats.get("sea_view", False) or preset_hint == "oran_seaview_villa" or any(w in desc_for_mood for w in ["بحر", "فيلا", "مسبح", "حديقة", "seaview"])

    if has_sea_features:
        profile = FALLBACK_PROFILES[1]
    elif preset_hint == "constantine_commercial" or any(w in desc_for_mood for w in ["محل", "تجاري", "استثمار", "شارع", "commercial"]):
        profile = FALLBACK_PROFILES[2]
    elif preset_hint == "rental_apartment" or any(w in desc_for_mood for w in ["كراء", "إيجار", "مؤثثة", "rental"]):
        profile = FALLBACK_PROFILES[3]
    else:
        profile = FALLBACK_PROFILES[0]

    directives = extract_directives(speech_description or "")

    # Synthesize fallback script dynamically based on duration and directives
    if speech_description and speech_description.strip():
        if directives.get("is_meta_prompt") or is_darja_or_walkthrough:
            script = _generate_dynamic_darja_script(
                speech_duration=speech_duration,
                prop_feats=prop_feats,
                directives=directives,
                preset_hint=preset_hint,
            )
        else:
            intent = speech_description.strip().rstrip(".،")
            script = f"عقار استثنائي بمواصفات راقية، {intent}، فرصة فريدة تلبي أعلى معايير الرفاهية والتميز."
    elif preset_hint or is_darja_or_walkthrough:
        script = _generate_dynamic_darja_script(
            speech_duration=speech_duration,
            prop_feats=prop_feats,
            directives=directives,
            preset_hint=preset_hint,
        )
    else:
        script = profile["script"]

    # Incorporate videographer speech context into narration if available
    if videographer_speech and str(videographer_speech).strip():
        v_clean = str(videographer_speech).strip().rstrip(".،")
        if v_clean and v_clean not in script:
            script = f"{script} وكما يلاحظ المصور: {v_clean}."

    # Synthesize badges / highlights incorporating visual_description if provided
    highlights = list(profile.get("highlights", []))
    if visual_description and visual_description.strip():
        custom_badges = []
        raw_parts = re.split(r"[،,.\n;]+", visual_description.strip())
        for p in raw_parts:
            p_clean = p.strip()
            words = p_clean.split()
            if 1 <= len(words) <= 7:
                custom_badges.append(p_clean)
        if custom_badges:
            highlights = custom_badges[:3]

    # Generate synchronized subtitles
    subtitles = generate_synchronized_subtitles(
        script=script,
        narration_duration=speech_duration,
        visual_lead_in=visual_lead_in,
    )

    if not shot_timeline and keyframe_count > 0:
        synth_timeline = []
        seg_dur = duration / max(1, keyframe_count)
        for i in range(keyframe_count):
            st = round(i * seg_dur, 2)
            et = round(duration if i == keyframe_count - 1 else (i + 1) * seg_dur, 2)
            synth_timeline.append({
                "scene_index": i + 1,
                "start_sec": st,
                "end_sec": et,
                "duration": round(et - st, 2),
                "title": f"Scene {i + 1} [{st:.1f}s - {et:.1f}s]",
            })
        shot_timeline = synth_timeline

    fb_result = {
        "script": script,
        "subtitles": subtitles,
        "shot_timeline": shot_timeline or [],
        "videographer_speech": videographer_speech,
        "emotional_tone": profile["emotional_tone"],
        "emotional_prompt": profile["emotional_prompt"],
        "recommended_music": profile["recommended_music"],
        "highlights": highlights,
        "recommended_cuts": [
            {"start_sec": 0.0, "end_sec": min(5.0, duration), "title": "المدخل والإطلالة"},
            {"start_sec": min(duration * 0.4, max(0.0, duration - 6.0)), "end_sec": min(duration * 0.4 + 5.0, duration), "title": "المساحات الرئيسية"},
        ] if duration > 12.0 else None,
        "engine": "smart_vision_fallback",
        "analyzed_frames_count": keyframe_count,
        "visual_lead_in_seconds": visual_lead_in,
        "speech_duration": speech_duration,
    }
    if directives.get("phone_number"):
        fb_result["phone_number"] = directives["phone_number"]
    if directives.get("bottom_text"):
        fb_result["bottom_text"] = directives["bottom_text"]

    return fb_result


# ---------------------------------------------------------------------------
# Multimodal Vision Analysis Engine
# ---------------------------------------------------------------------------

def infer_video_script_and_mood(
    keyframe_paths: List[Union[str, Path, Dict[str, Any]]],
    video_duration: float = 10.0,
    preset_hint: Optional[str] = None,
    speech_description: Optional[str] = None,
    visual_description: Optional[str] = None,
    visual_lead_in: float = 1.2,
    outro_buffer: float = 1.2,
    keyframes_metadata: Optional[List[Dict[str, Any]]] = None,
    videographer_speech: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Analyze extracted video keyframes via Gemini Multimodal Vision API to infer:
      1. An engaging Arabic real estate voiceover script matched to video length.
      2. Timestamp-anchored shot-by-shot timeline and anti-hallucination grounded narration.
      3. Synchronized subtitle segments aligned with speech timing.
      4. An emotional atmosphere / mood (الحالة الشعورية - e.g. 'فاخر وهادئ', 'متحمس وحيوي', 'دافئ وأنيق').
      5. The best matching background music from assets/music/ ('luxury_piano', 'acoustic_guitar', 'ambient_meditation').

    Args:
        keyframe_paths: List of file paths or keyframe dicts with timestamp metadata.
        video_duration: Duration of the video in seconds to pace narrative word count.
        preset_hint: Optional preset ID hint to guide architectural context if available.
        speech_description: Optional linguistic speech intent guidance ("وصف لغوي لما تريده أن يقال وليس نصاً حرفياً").
        visual_description: Optional linguistic visual intent description ("وصف ما يظهر في الفيديو وتوجيه التركيز البصري").
        visual_lead_in: Visual establishing lead-in delay in seconds (default 1.2s).
        outro_buffer: Outro ambient swell buffer in seconds (default 1.2s).
        keyframes_metadata: Optional list of frame metadata dictionaries with timestamps.
        videographer_speech: Optional transcribed live speech from the videographer.

    Returns:
        Dict with keys 'script', 'subtitles', 'shot_timeline', 'emotional_tone', 'emotional_prompt',
        'recommended_music', 'highlights', 'engine', 'analyzed_frames_count', 'visual_lead_in_seconds', 'speech_duration'.
    """
    _ensure_env_loaded()
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEYS")

    keyframe_records = extract_keyframe_records(
        keyframe_paths=keyframe_paths,
        keyframes_metadata=keyframes_metadata,
        video_duration=video_duration,
    )
    shot_timeline = build_shot_timeline(keyframe_records, video_duration=video_duration)

    # If no keyframe provided or API key absent, use smart fallback immediately
    if not keyframe_records or not api_key:
        logger.warning(
            "Vision analysis using fallback (keyframe_count=%d, has_api_key=%s)",
            len(keyframe_records),
            bool(api_key),
        )
        return _get_smart_fallback(
            duration=video_duration,
            preset_hint=preset_hint,
            speech_description=speech_description,
            visual_description=visual_description,
            visual_lead_in=visual_lead_in,
            outro_buffer=outro_buffer,
            keyframe_count=min(16, len(keyframe_records)),
            shot_timeline=shot_timeline,
            videographer_speech=videographer_speech,
        )

    # Dense keyframe sampling: pass up to 16 representative frames evenly
    selected_records: List[Dict[str, Any]] = []
    if len(keyframe_records) <= 16:
        selected_records = keyframe_records
    else:
        step = len(keyframe_records) / 16.0
        selected_records = [keyframe_records[int(i * step)] for i in range(16)]

    selected_frames = [r["path"] for r in selected_records]

    # Compute target word count strictly from net speaking window (speech_duration)
    # allowing visual_lead_in for establishing visuals and outro_buffer for music swell
    speech_duration = max(2.0, round(video_duration - visual_lead_in - outro_buffer, 2))
    target_words = max(18, min(160, int(speech_duration * 2.1)))

    # Construct multimodal parts
    parts: List[Dict[str, Any]] = []

    principles_section = build_vision_prompt_principles()

    intent_guidance = ""
    directives = extract_directives(speech_description or "")
    prop_feats = extract_property_features(speech_description or "")

    # 1. Shot-by-Shot Timeline & Anti-Hallucination Mandate
    timeline_lines = [
        f"- {item['title']}: Keyframe at timestamp {item['keyframe_timestamp']:.2f}s"
        for item in shot_timeline
    ]
    shot_grounding_section = (
        f"\n--- SHOT-BY-SHOT TIMELINE & VISUAL GROUNDING (جدول زمني صريح للمشاهد ومنع الهلوسة) ---\n"
        f"The video footage unfolds across these exact chronological visual scenes:\n"
        + "\n".join(timeline_lines) + "\n\n"
        f"CRITICAL SHOT-BY-SHOT VISUAL GROUNDING & ANTI-HALLUCINATION MANDATE:\n"
        f"1. Chronological Grounding: Every sentence in the narration script MUST correspond strictly to the physical space and features shown at that scene's timestamp.\n"
        f"2. ABSOLUTE PROHIBITION OF HALLUCINATIONS: You are STRICTLY FORBIDDEN from mentioning, claiming, or praising any room, facility, or amenity (e.g. second salon, extra bathroom, swimming pool, garden, balcony, garage, elevator) UNLESS it is physically, unmistakably visible in the keyframe for that specific scene.\n"
        f"3. Authenticity Mandate: If a space or feature is not visually present in these frames, DO NOT fabricate or assume its existence. Narrate only verified architectural details, natural light, flooring, and room proportions.\n"
    )
    if videographer_speech and str(videographer_speech).strip():
        shot_grounding_section += (
            f"\n--- VIDEOGRAPHER FIELD SPEECH & INTENT (تحليل صوت المصور الميداني) ---\n"
            f"The person recording the video said: \"{str(videographer_speech).strip()}\".\n"
            f"Incorporate these authentic field remarks into your room walkthrough guidance while respecting visual evidence.\n"
        )
    intent_guidance += shot_grounding_section

    if prop_feats.get("keywords"):
        specs_bullets = []
        if prop_feats.get("property_type"):
            specs_bullets.append(f"- Property Type: {prop_feats['property_type']}")
        if prop_feats.get("unit"):
            specs_bullets.append(f"- Unit Layout / Rooms: {prop_feats['unit']}")
        if prop_feats.get("sea_view"):
            specs_bullets.append("- Prime View / Setting: مطل على البحر (Breathtaking Mediterranean panoramic sea view)")
        intent_guidance += (
            f"\n--- MANDATORY ARCHITECTURAL SPECIFICATIONS (مواصفات إلزامية يجب ذكرها بوضوح في النص) ---\n"
            f"The user requires the following features to be explicitly woven into the spoken narration:\n"
            + "\n".join(specs_bullets) + "\n"
            f"CRITICAL: The voiceover must dynamically mention these specifications in natural Algerian Darja.\n"
        )

    p_type_label = prop_feats.get("property_type") or "عقار"
    p_unit_label = f" {prop_feats['unit']}" if prop_feats.get("unit") else ""
    p_view_label = "إطلالة بحرية ساحرة ومطل على البحر" if prop_feats.get("sea_view") else "موقع استراتيجي راقي"
    dynamic_pacing_guidance = (
        f"\n--- CONTINUOUS DYNAMIC AUDIO PACING (تغطية كامل مدة الفيديو بدون انقطاع مبكر) ---\n"
        f"CRITICAL PACING MANDATE: The video duration is {video_duration:.1f}s (net speaking duration: {speech_duration:.1f}s). "
        f"You MUST generate an expansive, engaging narration of approximately {target_words} words (around {speech_duration:.1f}s at ~2.1 words/sec). "
        f"Do NOT stop early or write a short 1-line script! Structure the narration dynamically across 3 continuous phases:\n"
        f"  1. Opening Hook (~20%): Introduce the {p_type_label}{p_unit_label} and highlight its {p_view_label}.\n"
        f"  2. Visual Guided Walkthrough (~60%): Detail the interior spaces shown in keyframes (salon, natural light, high-end finishes, room layout, modern kitchen) in first-person live walkthrough style.\n"
        f"  3. Concluding CTA (~20%): Value proposition recap and call to action prompting viewers to contact via the number displayed on screen.\n"
    )
    intent_guidance += dynamic_pacing_guidance

    if speech_description and speech_description.strip():
        if directives.get("is_meta_prompt"):
            intent_guidance += (
                f"\n--- USER CREATIVE & PRODUCTION DIRECTIVES (توجيهات وتعليمات إنتاجية) ---\n"
                f"The user provided instructions: \"{speech_description.strip()}\".\n"
                f"CRITICAL DISENTANGLEMENT MANDATE:\n"
                f"Do NOT speak these instructions literally or echo phrases like 'أريد أن يظهر نص' or phone numbers in the voiceover!\n"
                f"Instead, compose an authentic, vivid marketing voiceover script in Algerian Darja tailored to the actual visual video frames.\n"
                f"Additionally, extract any visual overlay directives (such as persistent bottom text, phone numbers, contact info, discounts).\n"
            )
        else:
            intent_guidance += (
                f"\n--- LINGUISTIC SPEECH INTENT GUIDANCE (وصف لغوي لما تريده أن يقال وليس نصاً حرفياً) ---\n"
                f"User Linguistic Speech Guidance: \"{speech_description.strip()}\"\n"
                f"CRITICAL INSTRUCTION: Treat this description strictly as linguistic intent and thematic guidance, NOT literal text. "
                f"Orchestrate and expand this intent into a complete, natural spoken marketing script that coordinates with the visual "
                f"camera movement across the net speaking duration ({speech_duration:.1f}s net speaking window out of {video_duration:.1f}s total video), strictly conforming to the Algerian Darja dialect and "
                f"walkthrough perspective rules set in the Production Principles below.\n"
            )

    if visual_description and visual_description.strip():
        intent_guidance += (
            f"\n--- LINGUISTIC VISUAL INTENT GUIDANCE (وصف ما يظهر في الفيديو وتوجيه التركيز البصري) ---\n"
            f"User Visual Description: \"{visual_description.strip()}\"\n"
            f"CRITICAL INSTRUCTION: Use this visual description to steer your visual focus, architectural interpretation, "
            f"and lower-third highlight badges to prioritize and showcase the specific property areas and details described here.\n"
        )

    # Dynamic marketing hook & variety angle
    import random
    chosen_angle = random.choice(MARKETING_ANGLES)
    intent_guidance += (
        f"\n--- CREATIVE MARKETING ANGLE & NARRATIVE LENS (زاوية التناول والتنوع الإبداعي) ---\n"
        f"Creative Narrative Framing Angle: {chosen_angle}\n"
        f"CRITICAL: Infuse the Algerian Darja voiceover with this authentic creative lens so every generated cut has a distinct personality and fresh marketing momentum.\n"
    )

    prompt = (
        f"You are an expert Algerian real estate marketing director and creative videographer.\n"
        f"Analyze these {len(selected_frames)} representative visual keyframes extracted across the entire walkthrough from a real estate smartphone video recording (total duration: {video_duration:.1f}s, net speaking window: {speech_duration:.1f}s).\n\n"
        f"{intent_guidance}\n"
        f"{principles_section}\n\n"
        f"Based on what you visually see across all rooms, architecture, interior, lighting, finishes, and the user's instructions above, return a JSON response with:\n"
        f"1. 'script': The marketing voiceover script describing this specific property in chronological visual order as the camera moves through the space.\n"
        f"   CRITICAL DIALECT & PERSPECTIVE MANDATE: You MUST strictly obey the Production Principles above. "
        f"If the principles instruct using Algerian dialect (الدارجة الجزائرية), write the script completely in authentic natural Algerian Darja. "
        f"If the principles instruct that the videographer is speaking ('كأن الشخص الذي يصور هو من يتكلم'), write in the first-person live walkthrough style ('رانا هنا ندخلو للصالون...', 'شوفو معايا هاد الإطلالة...'). "
        f"CRITICAL: NEVER speak or repeat user meta-instructions, directions, or overlay requests (e.g. 'أريد', 'رقم الهاتف', 'يظهر أسفل الفيديو') in the script. The script is strictly voiceover narration of the visual tour. "
        f"CRITICAL AUDIO-VISUAL PACING: Narration begins after an initial visual establishing period of {visual_lead_in:.1f}s and concludes {outro_buffer:.1f}s before the end. "
        f"The script duration MUST strictly match the net speaking window: approximately {target_words} words (around {speech_duration:.1f} seconds at standard 2.2 words/sec speech rate).\n"
        f"2. 'subtitles': Array of synchronized subtitle segment objects (e.g. [{{'start_sec': {visual_lead_in:.1f}, 'end_sec': {visual_lead_in + 3.0:.1f}, 'text': '...'}}]) matching the spoken phrasing.\n"
        f"3. 'emotional_tone': An emotional atmosphere / mood in Arabic (الحالة الشعورية), e.g. 'فاخر وهادئ', 'متحمس وحيوي', 'دافئ وأنيق', 'هادئ ومطمئن', 'حيوي وعصري'.\n"
        f"4. 'emotional_prompt': An acoustic style prompt in English for Gemini TTS guidance (e.g. 'Warm, luxurious, calm and prestigious tone with elegant cadence' or 'Bright, enthusiastic, welcoming real estate tour').\n"
        f"5. 'recommended_music': The single best matching music track ID from this exact list:\n"
        f"   - 'luxury_piano' (best for luxury apartments, penthouses, high-end architecture, elegant finishes)\n"
        f"   - 'acoustic_guitar' (best for cozy family homes, bright apartments, cheerful or modern spaces)\n"
        f"   - 'ambient_meditation' (best for villas, sea views, pools, gardens, serene or relaxation spaces)\n"
        f"6. 'highlights': Array of 1 to 3 short Arabic highlight captions for on-screen lower-third badges (e.g. ['صالون ملكي واسع', 'مطبخ عصري مجهز']). "
        f"If visual description guidance is provided, align these highlights directly with the key property areas described.\n"
        f"7. 'recommended_cuts': Optional array of highlight video shots to keep if montage or trimming is desired (e.g. [{{'start_sec': 0.0, 'end_sec': 5.0, 'title': 'المدخل'}}]) or null.\n"
        f"8. 'phone_number': Any Algerian phone number requested by user (e.g. '0558815453') or null.\n"
        f"9. 'bottom_text': Any persistent bottom text requested by user (or null).\n\n"
        f"Return strictly valid JSON with keys: 'script', 'subtitles', 'emotional_tone', 'emotional_prompt', 'recommended_music', 'highlights', 'recommended_cuts', 'phone_number', 'bottom_text'."
    )
    parts.append({"text": prompt})

    # Encode images to base64
    for kf_path in selected_frames:
        try:
            with open(kf_path, "rb") as f_img:
                b64_data = base64.b64encode(f_img.read()).decode("utf-8")
            parts.append({
                "inlineData": {
                    "mimeType": "image/jpeg",
                    "data": b64_data,
                }
            })
        except Exception as exc:
            logger.warning("Failed to encode keyframe %s: %s", kf_path, exc)

    # Candidate Gemini multimodal vision models in preference order
    env_models = os.getenv("GEMINI_VISION_MODELS")
    if env_models:
        candidate_models = [m.strip() for m in env_models.split(",") if m.strip()]
    else:
        candidate_models = list(ACTIVE_VISION_MODELS)

    # Configurable timeouts: 45s read timeout to accommodate large multi-keyframe payloads
    read_timeout = float(os.getenv("GEMINI_VISION_READ_TIMEOUT", "45.0"))
    connect_timeout = float(os.getenv("GEMINI_VISION_CONNECT_TIMEOUT", "10.0"))
    max_retries = int(os.getenv("GEMINI_VISION_MAX_RETRIES", "2"))

    import requests
    import time

    vision_temperature = float(os.getenv("GEMINI_VISION_TEMPERATURE", "0.80"))

    for model_name in candidate_models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        request_body = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "temperature": vision_temperature,
                "topP": 0.95,
                "responseMimeType": "application/json",
            },
        }

        for attempt in range(1, max_retries + 1):
            logger.info(
                "Querying Gemini Vision model '%s' (attempt %d/%d) with %d keyframes...",
                model_name,
                attempt,
                max_retries,
                len(selected_frames),
            )
            try:
                resp = requests.post(
                    url,
                    json=request_body,
                    timeout=(connect_timeout, read_timeout),
                )
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        candidate_part = candidates[0].get("content", {}).get("parts", [{}])[0]
                        raw_text = candidate_part.get("text", "").strip()
                        # Clean potential markdown wrapping
                        clean_json_str = re.sub(r"^```(?:json)?\s*", "", raw_text, flags=re.IGNORECASE)
                        clean_json_str = re.sub(r"\s*```$", "", clean_json_str)

                        parsed = json.loads(clean_json_str)
                        inferred_script = sanitize_script_against_meta_prompts(str(parsed.get("script", "")).strip())
                        emotional_tone = str(parsed.get("emotional_tone", "فاخر وهادئ")).strip()
                        emotional_prompt = str(parsed.get("emotional_prompt", "Warm, prestigious, and calm real estate tone")).strip()
                        recommended_music = str(parsed.get("recommended_music", "luxury_piano")).strip().lower()
                        phone_number = parsed.get("phone_number") or directives.get("phone_number")
                        bottom_text = parsed.get("bottom_text") or directives.get("bottom_text")

                        if recommended_music not in ("luxury_piano", "acoustic_guitar", "ambient_meditation"):
                            recommended_music = "luxury_piano"

                        # If user requested sea view, align music recommendation with coastal meditation
                        if prop_feats.get("sea_view") and recommended_music == "luxury_piano":
                            recommended_music = "ambient_meditation"

                        # Ensure the script length covers the video duration without dying out after a few seconds
                        word_count = len(inferred_script.split())
                        if word_count < 16 and speech_duration >= 20.0:
                            logger.info(
                                "Inferred script too brief (%d words) for duration (%.1fs); supplementing with dynamic walkthrough...",
                                word_count,
                                speech_duration,
                            )
                            supplement = _generate_dynamic_darja_script(
                                speech_duration=speech_duration,
                                prop_feats=prop_feats,
                                directives=directives,
                                preset_hint=preset_hint,
                            )
                            inferred_script = f"{inferred_script} {supplement}"

                        if inferred_script:
                            logger.info(
                                "Gemini Vision model '%s' successfully inferred script (%d words, mood: %s, music: %s)",
                                model_name,
                                len(inferred_script.split()),
                                emotional_tone,
                                recommended_music,
                            )
                            # Parse or generate timestamp-synchronized subtitles
                            raw_subs = parsed.get("subtitles")
                            valid_subs = []
                            if isinstance(raw_subs, list) and raw_subs:
                                for idx, s_item in enumerate(raw_subs):
                                    if isinstance(s_item, dict) and s_item.get("text"):
                                        try:
                                            s_start = max(0.0, float(s_item.get("start_sec", 0.0)))
                                            s_end = max(s_start + 0.5, float(s_item.get("end_sec", s_start + 2.0)))
                                            valid_subs.append({
                                                "segment_index": idx + 1,
                                                "start_sec": round(s_start, 2),
                                                "end_sec": round(s_end, 2),
                                                "text": str(s_item["text"]).strip(),
                                            })
                                        except (ValueError, TypeError):
                                            pass
                            if not valid_subs:
                                valid_subs = generate_synchronized_subtitles(
                                    script=inferred_script,
                                    narration_duration=speech_duration,
                                    visual_lead_in=visual_lead_in,
                                )

                            return {
                                "script": inferred_script,
                                "subtitles": valid_subs,
                                "shot_timeline": shot_timeline,
                                "videographer_speech": videographer_speech,
                                "emotional_tone": emotional_tone,
                                "emotional_prompt": emotional_prompt,
                                "recommended_music": recommended_music,
                                "highlights": parsed.get("highlights", []),
                                "recommended_cuts": parsed.get("recommended_cuts"),
                                "phone_number": phone_number,
                                "bottom_text": bottom_text,
                                "engine": "gemini_multimodal_vision",
                                "model_used": model_name,
                                "analyzed_frames_count": len(selected_frames),
                                "visual_lead_in_seconds": visual_lead_in,
                                "speech_duration": speech_duration,
                            }
                elif resp.status_code == 404:
                    logger.warning("Gemini Vision model '%s' returned 404 Not Found. Skipping to next fallback model.", model_name)
                    break
                elif resp.status_code in (429, 500, 502, 503, 504) and attempt < max_retries:
                    logger.warning(
                        "Gemini Vision model '%s' returned transient status %d on attempt %d/%d: %s. Retrying...",
                        model_name,
                        resp.status_code,
                        attempt,
                        max_retries,
                        resp.text[:160],
                    )
                    time.sleep(1.0)
                    continue
                else:
                    logger.warning(
                        "Gemini Vision model '%s' returned status %d on attempt %d: %s",
                        model_name,
                        resp.status_code,
                        attempt,
                        resp.text[:200],
                    )
                    break

            except requests.exceptions.Timeout as t_err:
                logger.warning(
                    "Timeout (read_timeout=%.1fs) querying Gemini Vision model '%s' on attempt %d/%d: %s",
                    read_timeout,
                    model_name,
                    attempt,
                    max_retries,
                    t_err,
                )
                if attempt < max_retries:
                    time.sleep(1.0)
                    continue
                else:
                    break
            except requests.exceptions.RequestException as req_err:
                logger.warning(
                    "Network error querying Gemini Vision model '%s' on attempt %d/%d: %s",
                    model_name,
                    attempt,
                    max_retries,
                    req_err,
                )
                if attempt < max_retries:
                    time.sleep(1.0)
                    continue
                else:
                    break
            except Exception as exc:
                logger.warning("Unexpected error querying Gemini Vision model '%s': %s", model_name, exc)
                break

    # If all models fail, return smart fallback
    logger.warning("All Gemini Vision models failed or timed out. Activating smart fallback.")
    return _get_smart_fallback(
        duration=video_duration,
        preset_hint=preset_hint,
        speech_description=speech_description,
        visual_description=visual_description,
        visual_lead_in=visual_lead_in,
        outro_buffer=outro_buffer,
        keyframe_count=len(selected_frames),
        shot_timeline=shot_timeline,
        videographer_speech=videographer_speech,
    )
