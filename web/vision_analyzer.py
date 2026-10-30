#!/usr/bin/env python3
"""
Multimodal Vision Analyzer for Real Estate Video (web/vision_analyzer.py)
Infers engaging Arabic voiceover script, emotional atmosphere/mood, and background music
from extracted video keyframes using Gemini Multimodal Vision API.

Author: MohammedBoure
Role: Backend Architecture & Processing Bridge (agy11)
Branch: backend/agy11-auto-vision-script-and-app-runner
"""

from __future__ import annotations

import base64
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

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


def _generate_dynamic_darja_script(
    speech_duration: float,
    prop_feats: Dict[str, Any],
    directives: Dict[str, Any],
    preset_hint: Optional[str] = None,
) -> str:
    """
    Generate an engaging, continuous Algerian Darja real estate script
    scaled dynamically to cover the net speaking window without abrupt silence.
    Incorporates property features (F1..F6, sea views, property type) and CTA.
    """
    unit = prop_feats.get("unit")
    has_sea_view = prop_feats.get("sea_view", False)
    prop_type = prop_feats.get("property_type") or ("فيلا" if has_sea_view else "شقة")

    unit_str = f" {unit}" if unit else ""
    if has_sea_view:
        view_str = "مطلة مباشرة على البحر وبإطلالة بانورامية ساحرة" if prop_type in ("فيلا", "شقة", "دار") else "مطل مباشرة على البحر وبإطلالة بانورامية ساحرة"
    else:
        view_str = "في موقع استراتيجي راقي وهادئ وقريب من كامل المرافق الحيوية"

    # Phase 1: Hook / Introduction
    hook = f"شوفو معايا هاد الـ{prop_type}{unit_str}، {view_str}."

    # Phase 2: Walkthrough progression scaled dynamically to available duration
    tour_segments = []
    tour_segments.append("رانا هنا ندخلو للصالون الواسع والمضيء، تشطيبات عصرية وفينيسيون متقونة توفر أقصى درجات الراحة.")

    if speech_duration >= 18.0:
        tour_segments.append("توزيع الغرف مدروس ومريح بزاف مع تهوية طبيعية ممتازة ومساحات واسعة تناسب كامل تطلعات العائلة.")
    if speech_duration >= 28.0:
        tour_segments.append("المطبخ عصري ومجهز بالكامل بأحدث التجهيزات، وكل زاوية في هاد العقار مخدومة بإتقان واهتمام بأدق التفاصيل.")
    if speech_duration >= 40.0:
        tour_segments.append("الموقع هادئ وآمن ومثالي، مع إمكانية الوصول السريع لكافة الخدمات الأساسية والمحاور الرئيسية.")

    # Phase 3: Closing Call to Action (CTA)
    cta = "فرصة استثنائية ونادرة للسكن أو الاستثمار، اتصلو بنا على الرقم الظاهر أسفل الشاشة لحجز موعد الزيارة والاستفسار."

    return f"{hook} {' '.join(tour_segments)} {cta}"


def _get_smart_fallback(
    duration: float = 10.0,
    preset_hint: Optional[str] = None,
    speech_description: Optional[str] = None,
    visual_description: Optional[str] = None,
    visual_lead_in: float = 1.2,
    outro_buffer: float = 1.2,
    keyframe_count: int = 0,
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
    desc_for_mood = f"{visual_description or ''} {speech_description or ''}".lower()
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

    fb_result = {
        "script": script,
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
    keyframe_paths: List[Union[str, Path]],
    video_duration: float = 10.0,
    preset_hint: Optional[str] = None,
    speech_description: Optional[str] = None,
    visual_description: Optional[str] = None,
    visual_lead_in: float = 1.2,
    outro_buffer: float = 1.2,
) -> Dict[str, Any]:
    """
    Analyze extracted video keyframes via Gemini Multimodal Vision API to infer:
      1. An engaging Arabic real estate voiceover script matched to video length.
      2. An emotional atmosphere / mood (الحالة الشعورية - e.g. 'فاخر وهادئ', 'متحمس وحيوي', 'دافئ وأنيق').
      3. The best matching background music from assets/music/ ('luxury_piano', 'acoustic_guitar', 'ambient_meditation').

    Args:
        keyframe_paths: List of file paths to extracted keyframe JPEG images.
        video_duration: Duration of the video in seconds to pace narrative word count.
        preset_hint: Optional preset ID hint to guide architectural context if available.
        speech_description: Optional linguistic speech intent guidance ("وصف لغوي لما تريده أن يقال وليس نصاً حرفياً").
        visual_description: Optional linguistic visual intent description ("وصف ما يظهر في الفيديو وتوجيه التركيز البصري").
        visual_lead_in: Visual establishing lead-in delay in seconds (default 1.2s).
        outro_buffer: Outro ambient swell buffer in seconds (default 1.2s).

    Returns:
        Dict with keys 'script', 'emotional_tone', 'emotional_prompt', 'recommended_music', 'highlights', 'engine',
        'analyzed_frames_count', 'visual_lead_in_seconds', 'speech_duration'.
    """
    _ensure_env_loaded()
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEYS")

    # If no keyframe provided or API key absent, use smart fallback immediately
    valid_keyframe_files = [Path(p).resolve() for p in keyframe_paths if Path(p).is_file() and Path(p).stat().st_size > 0]
    if not valid_keyframe_files or not api_key:
        logger.warning(
            "Vision analysis using fallback (keyframe_count=%d, has_api_key=%s)",
            len(valid_keyframe_files),
            bool(api_key),
        )
        return _get_smart_fallback(
            duration=video_duration,
            preset_hint=preset_hint,
            speech_description=speech_description,
            visual_description=visual_description,
            visual_lead_in=visual_lead_in,
            outro_buffer=outro_buffer,
            keyframe_count=min(16, len(valid_keyframe_files)),
        )

    # Dense keyframe sampling: pass up to 16 representative frames evenly
    selected_frames: List[Path] = []
    if len(valid_keyframe_files) <= 16:
        selected_frames = valid_keyframe_files
    else:
        step = len(valid_keyframe_files) / 16.0
        selected_frames = [valid_keyframe_files[int(i * step)] for i in range(16)]

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
        f"2. 'emotional_tone': An emotional atmosphere / mood in Arabic (الحالة الشعورية), e.g. 'فاخر وهادئ', 'متحمس وحيوي', 'دافئ وأنيق', 'هادئ ومطمئن', 'حيوي وعصري'.\n"
        f"3. 'emotional_prompt': An acoustic style prompt in English for Gemini TTS guidance (e.g. 'Warm, luxurious, calm and prestigious tone with elegant cadence' or 'Bright, enthusiastic, welcoming real estate tour').\n"
        f"4. 'recommended_music': The single best matching music track ID from this exact list:\n"
        f"   - 'luxury_piano' (best for luxury apartments, penthouses, high-end architecture, elegant finishes)\n"
        f"   - 'acoustic_guitar' (best for cozy family homes, bright apartments, cheerful or modern spaces)\n"
        f"   - 'ambient_meditation' (best for villas, sea views, pools, gardens, serene or relaxation spaces)\n"
        f"5. 'highlights': Array of 1 to 3 short Arabic highlight captions for on-screen lower-third badges (e.g. ['صالون ملكي واسع', 'مطبخ عصري مجهز']). "
        f"If visual description guidance is provided, align these highlights directly with the key property areas described.\n"
        f"6. 'recommended_cuts': Optional array of highlight video shots to keep if montage or trimming is desired (e.g. [{{'start_sec': 0.0, 'end_sec': 5.0, 'title': 'المدخل'}}]) or null.\n"
        f"7. 'phone_number': Any Algerian phone number requested by user (e.g. '0558815453') or null.\n"
        f"8. 'bottom_text': Any persistent bottom text requested by user (or null).\n\n"
        f"Return strictly valid JSON with keys: 'script', 'emotional_tone', 'emotional_prompt', 'recommended_music', 'highlights', 'recommended_cuts', 'phone_number', 'bottom_text'."
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

    for model_name in candidate_models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        request_body = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "temperature": 0.35,
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
                            return {
                                "script": inferred_script,
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
    )
