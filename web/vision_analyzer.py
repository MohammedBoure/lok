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

logger = logging.getLogger("vision_analyzer")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s")

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


def _get_smart_fallback(
    duration: float = 10.0,
    preset_hint: Optional[str] = None,
    speech_description: Optional[str] = None,
    visual_description: Optional[str] = None,
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

    # Base profile selection from hint or visual/speech description keywords
    desc_for_mood = f"{visual_description or ''} {speech_description or ''}".lower()
    if preset_hint == "oran_seaview_villa" or any(w in desc_for_mood for w in ["بحر", "فيلا", "مسبح", "حديقة", "seaview"]):
        profile = FALLBACK_PROFILES[1]
    elif preset_hint == "constantine_commercial" or any(w in desc_for_mood for w in ["محل", "تجاري", "استثمار", "شارع", "commercial"]):
        profile = FALLBACK_PROFILES[2]
    elif preset_hint == "rental_apartment" or any(w in desc_for_mood for w in ["كراء", "إيجار", "مؤثثة", "rental"]):
        profile = FALLBACK_PROFILES[3]
    else:
        profile = FALLBACK_PROFILES[0]

    # Synthesize fallback script incorporating speech_description intent if provided
    if speech_description and speech_description.strip():
        intent = speech_description.strip().rstrip(".،")
        if is_darja_or_walkthrough:
            script = f"شوفو معايا هاد العقار الاستثنائي، {intent}. موقع استراتيجي وتصميم راقي يلبي كل تطلعاتكم للراحة والفخامة."
        else:
            script = f"عقار استثنائي بمواصفات راقية، {intent}، فرصة فريدة تلبي أعلى معايير الرفاهية والتميز."
    elif preset_hint == "oran_seaview_villa":
        script = "رانا هنا في فيلا عصرية بواجهة بحرية ساحرة في وهران، حديقة ومسبح خاص وتصميم راقي يوفر كل معايير الراحة والفخامة." if is_darja_or_walkthrough else profile["script"]
    elif preset_hint == "constantine_commercial":
        script = "محل تجاري في موقع استراتيجي حيوي في قسنطينة، واجهة واسعة وحركة ممتازة توالم كامل المشاريع الناجحة." if is_darja_or_walkthrough else profile["script"]
    elif preset_hint == "rental_apartment":
        script = "شقة مجهزة ومفرشة بالكامل للكراء في موقع ممتاز، راحة وأمان لعائلتك." if is_darja_or_walkthrough else profile["script"]
    else:
        script = "شوفو معايا هاد الشقة الفاخرة F4 في قلب العاصمة، فينيسيون متقونة وإطلالة شابة بزاف، موقع هادئ وقريب من كل المرافق الحيوية." if is_darja_or_walkthrough else profile["script"]

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

    return {
        "script": script,
        "emotional_tone": profile["emotional_tone"],
        "emotional_prompt": profile["emotional_prompt"],
        "recommended_music": profile["recommended_music"],
        "highlights": highlights,
        "engine": "smart_vision_fallback",
    }


# ---------------------------------------------------------------------------
# Multimodal Vision Analysis Engine
# ---------------------------------------------------------------------------

def infer_video_script_and_mood(
    keyframe_paths: List[Union[str, Path]],
    video_duration: float = 10.0,
    preset_hint: Optional[str] = None,
    speech_description: Optional[str] = None,
    visual_description: Optional[str] = None,
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

    Returns:
        Dict with keys 'script', 'emotional_tone', 'emotional_prompt', 'recommended_music', 'highlights', 'engine'.
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
        )

    # Subsample up to 4 representative keyframes evenly
    selected_frames: List[Path] = []
    if len(valid_keyframe_files) <= 4:
        selected_frames = valid_keyframe_files
    else:
        step = max(1, len(valid_keyframe_files) // 4)
        selected_frames = [valid_keyframe_files[i] for i in range(0, len(valid_keyframe_files), step)][:4]

    # Target words count (~2.2 words per second in Arabic)
    target_words = max(10, min(65, int(video_duration * 2.2)))

    # Construct multimodal parts
    parts: List[Dict[str, Any]] = []

    principles_section = build_vision_prompt_principles()

    intent_guidance = ""
    if speech_description and speech_description.strip():
        intent_guidance += (
            f"\n--- LINGUISTIC SPEECH INTENT GUIDANCE (وصف لغوي لما تريده أن يقال وليس نصاً حرفياً) ---\n"
            f"User Linguistic Speech Guidance: \"{speech_description.strip()}\"\n"
            f"CRITICAL INSTRUCTION: Treat this description strictly as linguistic intent and thematic guidance, NOT literal text. "
            f"Orchestrate and expand this intent into a complete, natural spoken marketing script that coordinates with the visual "
            f"camera movement across the {video_duration:.1f}s timeline, strictly conforming to the Algerian Darja dialect and "
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
        f"Analyze these {len(selected_frames)} representative visual keyframes extracted from a real estate smartphone video recording (duration: {video_duration:.1f}s).\n\n"
        f"{intent_guidance}\n"
        f"{principles_section}\n\n"
        f"Based on what you visually see in the architecture, interior, lighting, finishes, and the user's linguistic guidance above, return a JSON response with:\n"
        f"1. 'script': The marketing voiceover script describing this specific property in chronological visual order as the camera moves through the space.\n"
        f"   CRITICAL DIALECT & PERSPECTIVE MANDATE: You MUST strictly obey the Production Principles above. "
        f"If the principles instruct using Algerian dialect (الدارجة الجزائرية), write the script completely in authentic natural Algerian Darja. "
        f"If the principles instruct that the videographer is speaking ('كأن الشخص الذي يصور هو من يتكلم'), write in the first-person live walkthrough style ('رانا هنا ندخلو للصالون...', 'شوفو معايا هاد الإطلالة...'). "
        f"If linguistic speech intent guidance is provided above, organically transform its intent into the spoken script. "
        f"The script duration MUST match the video length: approximately {target_words} words (around {video_duration:.1f} seconds at standard 2.2 words/sec speech rate).\n"
        f"2. 'emotional_tone': An emotional atmosphere / mood in Arabic (الحالة الشعورية), e.g. 'فاخر وهادئ', 'متحمس وحيوي', 'دافئ وأنيق', 'هادئ ومطمئن', 'حيوي وعصري'.\n"
        f"3. 'emotional_prompt': An acoustic style prompt in English for Gemini TTS guidance (e.g. 'Warm, luxurious, calm and prestigious tone with elegant cadence' or 'Bright, enthusiastic, welcoming real estate tour').\n"
        f"4. 'recommended_music': The single best matching music track ID from this exact list:\n"
        f"   - 'luxury_piano' (best for luxury apartments, penthouses, high-end architecture, elegant finishes)\n"
        f"   - 'acoustic_guitar' (best for cozy family homes, bright apartments, cheerful or modern spaces)\n"
        f"   - 'ambient_meditation' (best for villas, sea views, pools, gardens, serene or relaxation spaces)\n"
        f"5. 'highlights': Array of 1 to 3 short Arabic highlight captions for on-screen lower-third badges (e.g. ['صالون ملكي واسع', 'مطبخ عصري مجهز']). "
        f"If visual description guidance is provided, align these highlights directly with the key property areas described.\n\n"
        f"Return strictly valid JSON with keys: 'script', 'emotional_tone', 'emotional_prompt', 'recommended_music', 'highlights'."
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
    candidate_models = [
        "gemini-2.5-flash",
        "gemini-1.5-flash",
        "gemini-2.0-flash",
        "gemini-2.5-pro",
    ]

    import requests

    for model_name in candidate_models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        request_body = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "temperature": 0.35,
                "responseMimeType": "application/json",
            },
        }

        logger.info("Querying Gemini Vision model '%s' with %d keyframes...", model_name, len(selected_frames))
        try:
            resp = requests.post(url, json=request_body, timeout=20)
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
                    inferred_script = str(parsed.get("script", "")).strip()
                    emotional_tone = str(parsed.get("emotional_tone", "فاخر وهادئ")).strip()
                    emotional_prompt = str(parsed.get("emotional_prompt", "Warm, prestigious, and calm real estate tone")).strip()
                    recommended_music = str(parsed.get("recommended_music", "luxury_piano")).strip().lower()

                    if recommended_music not in ("luxury_piano", "acoustic_guitar", "ambient_meditation"):
                        recommended_music = "luxury_piano"

                    if inferred_script:
                        logger.info(
                            "Gemini Vision successfully inferred script (%d words, mood: %s, music: %s)",
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
                            "engine": "gemini_multimodal_vision",
                            "model_used": model_name,
                        }

            else:
                logger.warning("Gemini Vision model '%s' returned status %d: %s", model_name, resp.status_code, resp.text[:200])

        except Exception as exc:
            logger.warning("Failed querying Gemini Vision model '%s': %s", model_name, exc)

    # If all models fail, return smart fallback
    logger.warning("All Gemini Vision models failed or timed out. Activating smart fallback.")
    return _get_smart_fallback(
        duration=video_duration,
        preset_hint=preset_hint,
        speech_description=speech_description,
        visual_description=visual_description,
    )
