#!/usr/bin/env python3
"""
Mobile Post-Production Bridge & Assembly Engine (web/pipeline_bridge.py)
Part of the Video Post-Production & Mobile API Server Pipeline.

Author: MohammedBoure
Role: Backend Architecture & Processing Bridge (agy11)
Branch: backend/agy11-mobile-api-server
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
import shutil
import struct
import subprocess
import sys
import uuid
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Load environment configuration (.env)
def _ensure_env_loaded():
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

import frame_extractor

logger = logging.getLogger("mobile_pipeline_bridge")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s")


# ---------------------------------------------------------------------------
# Algerian Real Estate Presets
# ---------------------------------------------------------------------------

ALGERIAN_REAL_ESTATE_PRESETS: Dict[str, Dict[str, str]] = {
    "algiers_f4_luxury": {
        "id": "algiers_f4_luxury",
        "title_ar": "شقة فاخرة F4 - الجزائر العاصمة",
        "title_fr": "Appartement F4 Haut Standing - Alger",
        "description": "شقة فاخرة من أربع غرف بتشطيبات عالية الجودة في قلب العاصمة، إطلالة ساحرة وموقع هادئ قريب من كل المرافق الحيوية.",
        "recommended_music": "luxury_piano",
    },
    "oran_seaview_villa": {
        "id": "oran_seaview_villa",
        "title_ar": "فيلا عصرية بواجهة بحرية - وهران",
        "title_fr": "Villa Moderne Vue sur Mer - Oran",
        "description": "فيلا عصرية بواجهة بحرية خلابة في وهران، حديقة خاصة ومسبح وتصميم معماري رفيع يلبي أعلى معايير الرفاهية.",
        "recommended_music": "ambient_meditation",
    },
    "constantine_commercial": {
        "id": "constantine_commercial",
        "title_ar": "محل تجاري استراتيجي - قسنطينة",
        "title_fr": "Local Commercial Stratégique - Constantine",
        "description": "محل تجاري في موقع استراتيجي نشط بمدينة قسنطينة، واجهة واسعة وحركة تجارية ممتازة مناسب لكافة المشاريع.",
        "recommended_music": "acoustic_guitar",
    },
    "rental_apartment": {
        "id": "rental_apartment",
        "title_ar": "شقة مجهزة ومؤثثة للكراء",
        "title_fr": "Appartement Équipé en Location",
        "description": "شقة مؤثثة بالكامل ومجهزة بأحدث التجهيزات للكراء في موقع متميز، راحة وأمان لعائلتك.",
        "recommended_music": "acoustic_guitar",
    },
}

DEFAULT_PROMO_SCRIPT = (
    "عقار استثنائي بموقع استراتيجي وتشطيبات عصرية راقية، فرصة مثالية للاستثمار أو السكن العائلي الهادئ."
)

# ---------------------------------------------------------------------------
# Prompt Security Guardrails & Instruction Parser
# ---------------------------------------------------------------------------

DANGEROUS_PROMPT_PATTERNS = [
    (r"\.\.[\\/]", "File traversal attempt (../)"),
    (r"\$\([^)]*\)", "Shell command substitution ($(...))"),
    (r"`[^`]+`", "Shell backtick execution (`...`)"),
    (r"(?:^|[\s;&|`\"'$()<>])rm(?:\s+-[a-zA-Z]+|\s+)", "Destructive file removal command (rm)"),
    (r"(?:^|[\s;&|`\"'$()<>])(?:curl|wget)(?:\s+|$)", "Network utility execution (curl/wget)"),
    (r"(?:^|[\s;&|`\"'$()<>])(?:bash|zsh)(?:\s+|$)", "Shell process execution (bash)"),
    (r"(?:^|[\s;&|`\"'$()<>])sh(?:\s+-[a-zA-Z]+|\s+)", "Shell process execution (sh)"),
    (r"(?:^|[\s;&|`\"'$()<>])(?:eval|subprocess|os\.system|exec)\s*[\(\[]", "Dynamic code execution (eval/subprocess/exec)"),
    (r"(?:^|[\s;&|`\"'$()<>])(?:eval|subprocess)\b", "Dynamic code invocation (eval/subprocess)"),
    (r"(?:/etc/passwd|/etc/shadow|/bin/sh|/bin/bash)", "System binary or file path access"),
]


def sanitize_and_validate_prompt(prompt_text: Optional[str]) -> str:
    """
    Prompt Security Guardrail: Inspect prompt for dangerous injection patterns.
    Rejects directory traversal (../), shell command substitution ($(), ``),
    and system binary executions (rm, curl, wget, bash, sh, eval, subprocess).

    Raises ValueError with a descriptive security message if malicious payload is detected.
    Returns the sanitized stripped prompt string when valid.
    """
    if prompt_text is None:
        return ""

    text = str(prompt_text).strip()
    if not text:
        return ""

    for pattern, description in DANGEROUS_PROMPT_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            matched_segment = match.group(0).strip()
            raise ValueError(
                f"Security Guardrail Violation: Dangerous injection payload detected "
                f"[{description}: '{matched_segment}']. Request rejected for platform security."
            )

    return text


def parse_prompt_instructions(prompt_text: Optional[str]) -> Dict[str, Any]:
    """
    Safely parse user prompt instructions (speech speed, tone, descriptions)
    without permitting shell execution.
    """
    clean_text = sanitize_and_validate_prompt(prompt_text)
    instructions: Dict[str, Any] = {
        "raw_text": clean_text,
        "speed": 1.0,
        "tone": "engaging",
        "category": None,
        "emphasis": None,
    }

    if not clean_text:
        return instructions

    # Parse directives (meta-prompts, phone numbers, persistent overlays)
    dirs = extract_directives(clean_text)
    instructions.update(dirs)

    # Parse speed modifiers: e.g. "speed: 1.2" or "speed=0.9" or "سريع" / "بطيء"
    speed_match = re.search(r"\bspeed\s*[:=]\s*(\d+(?:\.\d+)?)\s*x?", clean_text, re.IGNORECASE)
    if speed_match:
        try:
            val = float(speed_match.group(1))
            instructions["speed"] = max(0.5, min(2.0, val))
        except ValueError:
            pass
    elif "سريع" in clean_text or "fast" in clean_text.lower():
        instructions["speed"] = 1.15
    elif "بطيء" in clean_text or "slow" in clean_text.lower():
        instructions["speed"] = 0.85

    # Parse tone modifiers: e.g. "tone: enthusiastic" or "حماسي", "هادئ", "رسمي"
    tone_match = re.search(r"\btone\s*[:=]\s*([a-zA-Z\u0600-\u06FF_-]+)", clean_text, re.IGNORECASE)
    if tone_match:
        instructions["tone"] = tone_match.group(1).lower()
    elif "حماسي" in clean_text or "enthusiastic" in clean_text.lower():
        instructions["tone"] = "enthusiastic"
    elif "هادئ" in clean_text or "calm" in clean_text.lower():
        instructions["tone"] = "calm"
    elif "فاخر" in clean_text or "luxury" in clean_text.lower():
        instructions["tone"] = "luxury"
    elif "رسمي" in clean_text or "professional" in clean_text.lower():
        instructions["tone"] = "professional"

    return instructions


# ---------------------------------------------------------------------------
# Prompt Intent & Directive Disentanglement System
# ---------------------------------------------------------------------------

ALGERIAN_PHONE_PATTERNS = [
    re.compile(r'(?:\+213|00213|213)[\s.-]?([567])[\s.-]?(\d{2})[\s.-]?(\d{2})[\s.-]?(\d{2})[\s.-]?(\d{2})'),
    re.compile(r'(?:\+213|00213|213)[\s.-]?([567]\d{8})'),
    re.compile(r'\b(0[567])[\s.-]?(\d{2})[\s.-]?(\d{2})[\s.-]?(\d{2})[\s.-]?(\d{2})\b'),
    re.compile(r'\b(0[567]\d{8})\b'),
]

META_DIRECTIVE_KEYWORDS = [
    "أريد", "اريد", "اجعل", "اكتب", "ضع", "حط", "أضف", "اضف", "خليه", "دير", "ديرلي",
    "تكلم", "احكي", "اعمل", "سوي", "ركز على", "يرجى", "الرجاء",
    "أسفل الفيديو", "اسفل الفيديو", "تحت في الفيديو", "في الأسفل", "في اسفل", "شريط سفلي", "نص أسفل",
    "طول ما الفيديو", "طوال الفيديو", "كامل الفيديو", "على مدار الفيديو", "شغال",
    "تعليق صوتي", "صوت مع الفيديو", "يتناسب مع الفيديو", "وصف صوتي", "فويس اوفر", "voiceover",
    "بالدارجة", "دارجة جزائرية", "لهجة جزائرية", "باللهجة",
    "به الرقم التالي", "رقم الهاتف", "رقم الاتصال", "الرقم التالي", "اتصل بنا", "للاتصال",
]


def extract_algerian_phone(text: Optional[str]) -> Optional[str]:
    """Extract and standardize Algerian mobile phone number (10 digits starting with 05, 06, or 07)."""
    if not text:
        return None
    clean = str(text).replace("\xa0", " ")
    for pattern in ALGERIAN_PHONE_PATTERNS:
        match = pattern.search(clean)
        if match:
            groups = match.groups()
            if len(groups) == 5:
                first = groups[0] if groups[0].startswith("0") else f"0{groups[0]}"
                return f"{first}{groups[1]}{groups[2]}{groups[3]}{groups[4]}"
            elif len(groups) == 1:
                num = groups[0]
                return num if num.startswith("0") else f"0{num}"
    return None


def is_meta_prompt(text: Optional[str]) -> bool:
    """
    Determine whether input represents meta-directions (instructions, phone overlay,
    Darja narration request) rather than a literal voiceover script to read word-for-word.
    """
    if not text:
        return False
    norm = str(text).strip().lower()
    if not norm:
        return False
    count = sum(1 for kw in META_DIRECTIVE_KEYWORDS if kw in norm)
    if count >= 1:
        return True
    cleaned_digits = re.sub(r"[\s.-]", "", norm)
    if re.search(r"(?:0|\+?213)[567]\d{8}", cleaned_digits):
        if any(w in norm for w in ["رقم", "هاتف", "اتصال", "اتصل", "نص", "فيديو", "اسفل", "أسفل", "طول", "شغال"]):
            return True
    return False


def extract_directives(text: Optional[str]) -> Dict[str, Any]:
    """
    Parse freeform creative user instructions, extracting meta-intent flags,
    phone number, persistent bottom overlay text, and styling preferences.
    """
    raw = str(text or "").strip()
    is_meta = is_meta_prompt(raw)
    phone = extract_algerian_phone(raw)

    bottom_text: Optional[str] = None
    if phone:
        bottom_text = phone

    if raw and is_meta:
        m_quoted = re.search(r'["“\']([^"”\']+)["”\']', raw)
        if m_quoted:
            bottom_text = m_quoted.group(1).strip()
        elif not phone:
            m_custom = re.search(r"(?:نص(?:اً)? أسفل الفيديو|الشريط السفلي|اكتب في الأسفل|ضع في الأسفل)(?:\s*به|\s*فيه|\s*:)?\s*([^\n.،]+)", raw)
            if m_custom:
                extracted_phrase = m_custom.group(1).strip()
                cleaned_phrase = re.sub(r"^(?:الرقم التالي|رقم|به الرقم التالي)\s*", "", extracted_phrase).strip()
                if cleaned_phrase:
                    bottom_text = cleaned_phrase

    darja_requested = any(w in raw.lower() for w in ["دارجة", "بالدارجة", "لهجة جزائرية", "جزائرية"])
    voiceover_requested = any(w in raw.lower() for w in ["تعليق صوتي", "صوت", "فويس اوفر", "voiceover", "نص يتناسب"])
    persistent_overlay = any(w in raw.lower() for w in ["طول ما الفيديو", "طوال الفيديو", "كامل الفيديو", "دائم", "طول الفيديو", "شغال"])

    return {
        "is_meta_prompt": is_meta,
        "phone_number": phone,
        "bottom_text": bottom_text,
        "darja_requested": darja_requested,
        "voiceover_requested": voiceover_requested,
        "persistent_overlay": persistent_overlay,
        "raw_text": raw,
    }


def sanitize_script_against_meta_prompts(
    script: Optional[str],
    fallback_hint: Optional[str] = None
) -> str:
    """
    Ensure the synthesized script does not leak user instructions, meta-prompts,
    or LLM labeling prefixes (e.g. 'السيناريو:', 'التعليق الصوتي:').
    If the script itself is a meta-prompt, returns a clean marketing narration in Algerian Darja.
    """
    default_darja = "شوفو معايا هاد العقار الاستثنائي بتصميم راقي وتشطيبات عصرية، موقع هادئ وقريب من كل المرافق الحيوية في قلب المدينة."
    if not script or not str(script).strip():
        return default_darja

    clean = str(script).strip()
    clean = re.sub(r"^```(?:json|text)?\s*", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\s*```$", "", clean)

    clean = re.sub(r"^(?:السيناريو|التعليق الصوتي|نص التعليق|نص الإعلان|Voiceover|Script)\s*[:：\-]\s*", "", clean, flags=re.IGNORECASE)
    clean = clean.strip(' "“\'')

    if is_meta_prompt(clean) and any(w in clean for w in ["أريد أن يظهر", "طول ما الفيديو شغال", "به الرقم التالي", "يظهر النص التالي"]):
        return default_darja

    return clean


def get_presets_list() -> List[Dict[str, str]]:
    """Return catalog of presets formatted for API responses."""
    return list(ALGERIAN_REAL_ESTATE_PRESETS.values())


# ---------------------------------------------------------------------------
# Open-Source Background Music Library
# ---------------------------------------------------------------------------

MUSIC_LIBRARY: Dict[str, Dict[str, Any]] = {
    "luxury_piano": {
        "id": "luxury_piano",
        "title": "Gymnopédie No. 1 (Erik Satie)",
        "title_ar": "بيانو كلاسيكي راقي (Gymnopédie) - للعقارات الفاخرة",
        "style": "Classical warm acoustic piano",
        "license": "Public Domain / CC0",
        "file": REPO_ROOT / "assets" / "music" / "luxury_piano.mp3",
    },
    "acoustic_guitar": {
        "id": "acoustic_guitar",
        "title": "Solo Acoustic Guitar (Jason Shaw)",
        "title_ar": "غيتار أكوستيك مشرق وهادئ - للمنازل والشقق العائلية",
        "style": "Uplifting melodic acoustic guitar",
        "license": "Creative Commons Attribution 3.0 (CC-BY 3.0)",
        "file": REPO_ROOT / "assets" / "music" / "acoustic_guitar.mp3",
    },
    "ambient_meditation": {
        "id": "ambient_meditation",
        "title": "Acoustic Meditation (Jason Shaw)",
        "title_ar": "موسيقى تأملية مهدئة بإطلالة بحرية - للفلل والشاليهات",
        "style": "Relaxed Mediterranean ambient guitar",
        "license": "Creative Commons Attribution 3.0 (CC-BY 3.0)",
        "file": REPO_ROOT / "assets" / "music" / "ambient_meditation.mp3",
    },
}


def get_music_tracks_list() -> List[Dict[str, str]]:
    """Return catalog of available open-source background music tracks."""
    tracks = []
    for m in MUSIC_LIBRARY.values():
        tracks.append({
            "id": m["id"],
            "title": m["title"],
            "title_ar": m["title_ar"],
            "style": m["style"],
            "license": m["license"],
        })
    return tracks


# ---------------------------------------------------------------------------
# Supported Real Estate Voice Profiles & Personas
# ---------------------------------------------------------------------------

SUPPORTED_VOICE_PROFILES: Dict[str, Dict[str, Any]] = {
    "ar-XA-Standard-A": {
        "id": "ar-XA-Standard-A",
        "gender": "female",
        "label": "أنثى - دافئ وطبيعي (Aoede)",
        "label_en": "Female, warm & natural (Aoede)",
        "gemini_voice": "Aoede",
        "description": "نبرة أنثوية دافئة وعفوية، مثالية لجولات الاستكشاف والشقق العائلية",
    },
    "ar-XA-Standard-B": {
        "id": "ar-XA-Standard-B",
        "gender": "male",
        "label": "ذكر - موثوق ورسمي (Charon)",
        "label_en": "Male, authoritative & confident (Charon)",
        "gemini_voice": "Charon",
        "description": "نبرة ذكورية فخمة ورزينة، ممتازة للعقارات التجارية والفلل الراقية",
    },
    "ar-XA-Standard-C": {
        "id": "ar-XA-Standard-C",
        "gender": "male",
        "label": "ذكر - حيوي وعصري (Fenrir)",
        "label_en": "Male, energetic & modern (Fenrir)",
        "gemini_voice": "Fenrir",
        "description": "نبرة ذكورية شابة وحيوية، رائعة للعروض الاستثمارية والمحلات النشطة",
    },
    "ar-XA-Standard-D": {
        "id": "ar-XA-Standard-D",
        "gender": "female",
        "label": "أنثى - أنيق وهادئ (Kore)",
        "label_en": "Female, elegant & calm (Kore)",
        "gemini_voice": "Kore",
        "description": "نبرة أنثوية هادئة وأنيقة، تناسب الإطلالات البحرية والمنتجعات",
    },
}

# Voice mapping from standard web identifiers to supported Gemini TTS voice personas
VOICE_MAPPING: Dict[str, str] = {
    "ar-xa-standard-a": "Aoede",
    "ar-xa-standard-b": "Charon",
    "ar-xa-standard-c": "Fenrir",
    "ar-xa-standard-d": "Kore",
    "ar-XA-Standard-A": "Aoede",
    "ar-XA-Standard-B": "Charon",
    "ar-XA-Standard-C": "Fenrir",
    "ar-XA-Standard-D": "Kore",
    "aoede": "Aoede",
    "charon": "Charon",
    "fenrir": "Fenrir",
    "kore": "Kore",
    "puck": "Puck",
    "leda": "Leda",
    "orus": "Orus",
    "zephyr": "Zephyr",
    "female": "Aoede",
    "male": "Charon",
}


def get_voice_profiles_list() -> List[Dict[str, Any]]:
    """Return catalog of supported real estate voice profiles."""
    return list(SUPPORTED_VOICE_PROFILES.values())


def resolve_voice_profile(voice_input: Optional[str]) -> Tuple[str, str]:
    """
    Resolve user voice input to a tuple of (standard_voice_id, gemini_persona).
    Supports standard ar-XA-Standard-A/B/C/D identifiers, Gemini personas, or custom strings.
    """
    if not voice_input or not str(voice_input).strip():
        return ("ar-XA-Standard-A", "Aoede")

    clean = str(voice_input).strip()
    clean_lower = clean.lower()

    # 1. Match standard profile id
    for vid, meta in SUPPORTED_VOICE_PROFILES.items():
        if vid.lower() == clean_lower:
            return (vid, meta["gemini_voice"])

    # 2. Match alias in VOICE_MAPPING
    if clean_lower in VOICE_MAPPING:
        persona = VOICE_MAPPING[clean_lower]
        for vid, meta in SUPPORTED_VOICE_PROFILES.items():
            if meta["gemini_voice"].lower() == persona.lower():
                return (vid, persona)
        return (clean, persona)

    # 3. Known Gemini persona
    for persona in ["Aoede", "Charon", "Fenrir", "Kore", "Puck", "Leda", "Orus", "Zephyr"]:
        if persona.lower() == clean_lower:
            return (persona, persona)

    # 4. Custom voice string
    return (clean, clean)


VOICE_SAMPLE_SCRIPTS: Dict[str, Dict[str, str]] = {
    "ar-XA-Standard-A": {
        "text": "مرحباً بكم، هذا نموذج صوتي أنثوي دافئ وطبيعي مصمم لجولات الاستكشاف والشقق العائلية والديكورات الهادئة، ليمنح إعلاناتكم لمسة راقية وجذابة.",
        "tone": "دافئ وأنيق",
        "style_prompt": "صوت أنثوي دافئ وطبيعي وواضح، نبرة تسويقية راقية ومريحة",
    },
    "ar-XA-Standard-B": {
        "text": "أهلاً وسهلاً، استمعوا إلى الصوت الذكوري الوقور والموثوق، الأنسب للفيلات الفخمة والمشاريع التجارية والاستثمارية الكبرى التي تتطلب هيبة وثقة.",
        "tone": "فاخر وهادئ",
        "style_prompt": "صوت ذكوري وقور ورسمي وقوي، نبرة رجال أعمال واستثمار فخم",
    },
    "ar-XA-Standard-C": {
        "text": "مرحباً بالجميع! إليكم الصوت الذكوري الحيوي والعصري، الأمثل للعروض الترويجية السريعة والتخفيضات الاستثنائية التي تلفت الانتباه وتصنع التفاعل.",
        "tone": "متحمس وحيوي",
        "style_prompt": "صوت ذكوري شاب وحيوي وعصري، نبرة إعلانية سريعة ومحفزة",
    },
    "ar-XA-Standard-D": {
        "text": "أهلاً بكم في عالم الفخامة والسكينة، صوت أنثوي راقٍ وهادئ يبرز أرقى الإقامات الشاطئية والمنتجعات الفاخرة بأعلى معايير الأناقة والجمال.",
        "tone": "فاخر وهادئ",
        "style_prompt": "صوت أنثوي راقٍ وهادئ ومليء بالأناقة، نبرة استرخاء ورفاهية",
    },
}


def get_or_create_voice_sample(voice_id: str, force_regenerate: bool = False) -> Path:
    """
    Return path to an audio reference sample file for voice audition preview,
    generating it via TTS speech synthesizer if not yet cached or if force_regenerate is True.
    """
    resolved_id, _ = resolve_voice_profile(voice_id)
    samples_dir = (REPO_ROOT / "outputs" / "voice_samples").resolve()
    samples_dir.mkdir(parents=True, exist_ok=True)
    sample_file = samples_dir / f"{resolved_id}.wav"

    if force_regenerate or not sample_file.is_file() or sample_file.stat().st_size == 0:
        meta = VOICE_SAMPLE_SCRIPTS.get(resolved_id, VOICE_SAMPLE_SCRIPTS["ar-XA-Standard-A"])
        synthesize_narration(
            script_text=meta["text"],
            output_path=sample_file,
            voice=resolved_id,
            style_prompt=meta.get("style_prompt"),
            emotional_tone=meta.get("tone"),
        )
    return sample_file


def generate_all_voice_reference_samples(force: bool = False) -> Dict[str, Path]:
    """
    Pre-generate realistic, high-fidelity promotional reference monologue audio clips
    for all 4 supported standard personas (ar-XA-Standard-A/B/C/D) via the TTS library.
    """
    generated: Dict[str, Path] = {}
    for voice_id in SUPPORTED_VOICE_PROFILES.keys():
        try:
            path = get_or_create_voice_sample(voice_id, force_regenerate=force)
            generated[voice_id] = path
            logger.info("Voice sample ready for %s: %s (%d bytes)", voice_id, path, path.stat().st_size)
        except Exception as exc:
            logger.warning("Failed to generate voice sample for %s: %s", voice_id, exc)
    return generated


def compute_dense_keyframe_timestamps(
    duration: float,
    min_count: int = 8,
    max_count: int = 16,
) -> List[float]:
    """
    Compute 8 to 16 uniformly distributed keyframe sampling timestamps across duration.
    Samples at representative percentages (e.g., 5%, 15%, 25%, ..., 95%) across video walkthrough.
    """
    if duration <= 0.5:
        return [0.0]
    target_count = min(max_count, max(min_count, int(round(duration))))
    if target_count <= 1:
        return [round(duration * 0.5, 3)]
    step = 0.90 / (target_count - 1)
    timestamps = [round(duration * (0.05 + i * step), 3) for i in range(target_count)]
    return sorted(list(set(timestamps)))


# ---------------------------------------------------------------------------
# Audio Synthesis & Fallback Helpers
# ---------------------------------------------------------------------------

def generate_synthetic_voice(
    text: str,
    output_path: Union[str, Path],
    sample_rate: int = 24000,
) -> float:
    """
    Generate harmonic formant-based voiceover audio when external TTS is unavailable.
    Produces spoken-word syllabic envelope with formant resonance and natural pacing.

    Args:
        text: Script text.
        output_path: Destination WAV file path.
        sample_rate: Output audio sample rate in Hz.

    Returns:
        Duration of generated audio in seconds.
    """
    out_file = Path(output_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)

    words = [w for w in text.strip().split() if w]
    word_count = max(1, len(words))

    # Syllabic acoustic timing: ~2.4 Arabic words per second
    duration = max(3.5, round(word_count / 2.3, 2))
    num_samples = int(duration * sample_rate)

    f0_base = 140.0
    formants = [(650.0, 0.45), (1700.0, 0.35), (2600.0, 0.20)]

    audio_samples = []
    for i in range(num_samples):
        t = i / sample_rate
        syllable_env = 0.55 + 0.45 * math.sin(2.0 * math.pi * 3.8 * t)
        breath_pause = 0.2 + 0.8 * abs(math.sin(2.0 * math.pi * 0.45 * t))
        mod_env = syllable_env * breath_pause

        sample_val = 0.0
        pitch_drift = 1.0 + 0.04 * math.sin(2.0 * math.pi * 0.6 * t)
        current_f0 = f0_base * pitch_drift

        sample_val += 0.40 * math.sin(2.0 * math.pi * current_f0 * t)
        for f_freq, f_amp in formants:
            sample_val += f_amp * math.sin(2.0 * math.pi * (f_freq + current_f0 * 0.1) * t)

        val = sample_val * mod_env * 0.38
        if t < 0.1:
            val *= (t / 0.1)
        elif t > (duration - 0.2):
            val *= ((duration - t) / 0.2)

        val = max(-0.95, min(0.95, val))
        audio_samples.append(int(val * 32767.0))

    with wave.open(str(out_file), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        packed_data = struct.pack(f"<{len(audio_samples)}h", *audio_samples)
        wf.writeframes(packed_data)

    return duration


def synthesize_narration(
    script_text: str,
    output_path: Union[str, Path],
    voice: str = "ar-XA-Standard-A",
    style_prompt: Optional[str] = None,
    emotional_tone: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Synthesize narration audio using GeminiSpeechClient via official Google Gemini API,
    or gracefully fall back to local synthetic audio engine if API is unreachable.
    Supports emotional tone steering and acoustic style prompt modulation.
    """
    _ensure_env_loaded()
    out_file = Path(output_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)

    synthesizer_engine = "synthetic_speech_engine"
    success = False

    # Resolve voice name to supported Gemini persona
    resolved_voice_id, gemini_voice = resolve_voice_profile(voice)

    # Check for Gemini API key
    has_api_key = bool(os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEYS"))

    if has_api_key:
        try:
            from tts.gemini_speech.client import GeminiSpeechClient
            logger.info(
                "Synthesizing speech via GeminiSpeechClient (Profile: %s -> Persona: %s, tone: %s, style: %s)...",
                resolved_voice_id,
                gemini_voice,
                emotional_tone,
                style_prompt,
            )
            client = GeminiSpeechClient()
            client.generate_speech(
                text=script_text,
                voice_name=gemini_voice,
                output_path=str(out_file),
                style_prompt=style_prompt,
                emotional_tone=emotional_tone,
            )
            if out_file.is_file() and out_file.stat().st_size > 0:
                synthesizer_engine = "gemini_tts"
                success = True
                logger.info("Gemini TTS synthesis completed: %s (%d bytes)", out_file, out_file.stat().st_size)
        except Exception as exc:
            logger.warning("GeminiSpeechClient failed or unreachable (%s). Using synthetic fallback.", exc)
            success = False

    if not success:
        logger.info("Generating synthetic voiceover narration fallback at %s...", out_file)
        generate_synthetic_voice(script_text, out_file)
        synthesizer_engine = "synthetic_speech_engine"

    # Probe duration
    audio_dur = get_media_duration(out_file)

    return {
        "audio_path": str(out_file),
        "duration": audio_dur,
        "synthesizer": synthesizer_engine,
        "voice": resolved_voice_id,
        "gemini_voice": gemini_voice,
        "requested_voice": voice,
        "script": script_text,
        "emotional_tone": emotional_tone,
        "style_prompt": style_prompt,
    }


def get_media_duration(file_path: Union[str, Path]) -> float:
    """Probe duration of an audio or video file using ffprobe."""
    path = Path(file_path).resolve()
    ffprobe_bin = shutil.which("ffprobe") or "ffprobe"
    cmd = [
        ffprobe_bin,
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return round(float(res.stdout.strip()), 3)
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# Core Mobile Video Processing Engine
# ---------------------------------------------------------------------------

def process_mobile_video(
    video_path: Union[str, Path],
    script: Optional[str] = None,
    preset_id: Optional[str] = None,
    voice: str = "ar-XA-Standard-A",
    duck_level: float = 0.25,
    music_track: Optional[str] = None,
    output_dir: Union[str, Path] = "outputs/mobile_cuts",
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    auto_mode: bool = False,
    emotional_tone: Optional[str] = None,
    style_prompt: Optional[str] = None,
    speech_description: Optional[str] = None,
    visual_description: Optional[str] = None,
    visual_lead_in: float = 1.2,
    outro_buffer: float = 1.2,
    fixed_text: Optional[str] = None,
    text_position: Optional[str] = "lower_third",
    text_style: Optional[str] = "modern_white",
    video_orientation: Optional[str] = None,
    bottom_text: Optional[str] = None,
    phone_number: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Process smartphone video recording into a polished marketing promo cut.

    Workflow:
      1. Probe input video properties and resolve target aspect ratio (9:16 or 16:9).
      2. Extract visual keyframes using frame_extractor into outputs/keyframes/mobile_<job_id>/
      3. Perform Autonomous Multimodal Vision Analysis (if auto_mode or no script/preset provided)
         to infer engaging Arabic real estate voiceover, emotional tone, and recommended music.
      4. Synthesize expressive neural narration voiceover with Gemini TTS API modulated by emotional tone.
      5. Assemble final video in FFmpeg with selected open-source royalty-free music and sidechain ducking.
      6. Return comprehensive execution summary dictionary.
    """
    input_path = Path(video_path).resolve()
    if not input_path.is_file():
        raise FileNotFoundError(f"Input video file not found: {input_path}")

    # Guardrail: sanitize and validate all user prompts and descriptions
    if script:
        script = sanitize_and_validate_prompt(script)
    if speech_description:
        speech_description = sanitize_and_validate_prompt(speech_description)
    if visual_description:
        visual_description = sanitize_and_validate_prompt(visual_description)
    if style_prompt:
        style_prompt = sanitize_and_validate_prompt(style_prompt)
    if fixed_text:
        fixed_text = sanitize_and_validate_prompt(fixed_text)
    if bottom_text:
        bottom_text = sanitize_and_validate_prompt(bottom_text)

    # Directive & Intent Disentanglement:
    # Check all incoming text fields for phone numbers and instructions
    all_incoming_texts = [t for t in [script, speech_description, visual_description, fixed_text, bottom_text] if t and str(t).strip()]
    merged_text = "\n".join(all_incoming_texts)
    parsed_dirs = extract_directives(merged_text)

    if not phone_number:
        phone_number = parsed_dirs.get("phone_number")
    if not bottom_text:
        bottom_text = parsed_dirs.get("bottom_text") or (phone_number if phone_number else None)

    # Disentangle script: if script was provided as a meta-instruction (e.g. asking for video text or phone overlay),
    # do NOT speak it! Redirect to speech_description and activate auto_mode.
    if script and is_meta_prompt(script):
        logger.info("Disentangling user meta-prompt instructions from narration script: %s", script[:80])
        if speech_description:
            speech_description = f"{speech_description}\n{script}"
        else:
            speech_description = script
        script = None
        auto_mode = True

    # Generate unique job identifier
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    unique_suffix = uuid.uuid4().hex[:6]
    job_id = f"{timestamp_str}_{unique_suffix}"

    out_cuts_dir = Path(output_dir).resolve()
    out_cuts_dir.mkdir(parents=True, exist_ok=True)

    keyframes_dest_dir = Path("outputs/keyframes").resolve() / f"mobile_{job_id}"
    keyframes_dest_dir.mkdir(parents=True, exist_ok=True)

    # Load customizable production principles
    from config.production_principles_manager import load_principles
    from web.video_annotator import annotate_video

    active_principles = load_principles()
    principles_voice = active_principles.get("voice_principles", {})
    principles_visual = active_principles.get("visual_principles", {})
    principles_annotation = active_principles.get("annotation_principles", {})

    # Telemetry helper
    def _notify(step: int, percent: int, message: str, log: str, extra: Optional[Dict[str, Any]] = None):
        if progress_callback:
            try:
                payload = {
                    "job_id": job_id,
                    "status": "processing",
                    "step": step,
                    "progress_percent": percent,
                    "message": message,
                    "log": log,
                }
                if extra:
                    payload.update(extra)
                progress_callback(payload)
            except Exception as e:
                logger.warning("Progress callback error: %s", e)

    # 1. Probe input video properties
    _notify(
        step=1,
        percent=15,
        message="وكيل الذكاء الاصطناعي يقوم بفحص أبعاد الفيديو واتجاهه...",
        log=f"[فحص الوسائط] تم استلام الفيديو '{input_path.name}'. جاري تحليل الأبعاد والمواصفات الفنية...",
    )

    meta = frame_extractor.get_video_metadata(input_path)
    src_width = int(meta.get("width", 1280))
    src_height = int(meta.get("height", 720))
    src_duration = float(meta.get("total_duration", 0.0))

    is_portrait = src_height > src_width
    orientation = "portrait" if is_portrait else "landscape"

    # Standardize output resolution with optional video_orientation override
    req_orient = str(video_orientation).lower().strip() if video_orientation else None
    if req_orient in ("square", "1:1"):
        target_w = 1080 if max(src_width, src_height) >= 900 else 720
        target_h = target_w
        orientation = "square"
        aspect_label = "1:1"
    elif req_orient in ("portrait", "9:16"):
        target_w = 1080 if src_width >= 900 else 720
        target_h = 1920 if src_width >= 900 else 1280
        orientation = "portrait"
        aspect_label = "9:16"
    elif req_orient in ("landscape", "16:9"):
        target_w = 1920 if src_width >= 1600 else 1280
        target_h = 1080 if src_width >= 1600 else 720
        orientation = "landscape"
        aspect_label = "16:9"
    elif is_portrait:
        target_w = 1080 if src_width >= 900 else 720
        target_h = 1920 if src_width >= 900 else 1280
        aspect_label = "9:16"
    else:
        target_w = 1920 if src_width >= 1600 else 1280
        target_h = 1080 if src_width >= 1600 else 720
        aspect_label = "16:9"

    logger.info(
        "Job %s: Input %s (%dx%d, %.2fs, orientation: %s -> %dx%d)",
        job_id,
        input_path.name,
        src_width,
        src_height,
        src_duration,
        orientation,
        target_w,
        target_h,
    )

    # 2. Extract visual keyframes
    _notify(
        step=2,
        percent=30,
        message="وكيل الذكاء الاصطناعي يستخرج اللقطات المفتاحية والمشاهد بدقة...",
        log="[رؤية حاسوبية] 🖼️ استخراج لقطات المعاينة البصرية من الفيديو...",
    )

    logger.info("Job %s: Extracting dense keyframes to %s...", job_id, keyframes_dest_dir)
    dense_timestamps = compute_dense_keyframe_timestamps(src_duration, min_count=8, max_count=16)
    keyframe_extraction = frame_extractor.extract_keyframes(
        video_path=input_path,
        timestamps=dense_timestamps,
        output_dir=keyframes_dest_dir,
        image_format="jpg",
    )
    raw_frames = keyframe_extraction.get("frames", [])

    formatted_keyframes: List[Dict[str, Any]] = []
    keyframe_files: List[Path] = []
    for f in raw_frames:
        file_path_obj = Path(f["file_path"])
        abs_path = Path(f.get("absolute_file_path", file_path_obj)).resolve()
        keyframe_files.append(abs_path)
        web_url = f"/outputs/keyframes/mobile_{job_id}/{file_path_obj.name}"
        formatted_keyframes.append({
            "frame_index": f.get("frame_index"),
            "timestamp": f.get("timestamp"),
            "url": web_url,
            "file_path": f.get("file_path"),
            "resolution": f.get("resolution"),
            "is_scene_transition": f.get("is_scene_transition", False),
        })

    # 3. Autonomous Vision Analysis & Script Determination
    # If speech_description or visual_description is provided, treat as linguistic intent guidance
    # and invoke the multimodal agent to generate the full natural spoken script and focus.
    is_auto_mode = bool(auto_mode or speech_description or (not script and not preset_id))
    inferred_script: Optional[str] = None
    vision_engine: Optional[str] = None
    inferred_music: Optional[str] = None

    if is_auto_mode:
        _notify(
            step=2,
            percent=45,
            message="تحليل المشاهد المعمارية عبر Gemini Multimodal Vision...",
            log="[رؤية حاسوبية] 🧠 تحليل المشاهد المعمارية عبر Gemini Multimodal Vision...",
        )
        try:
            from web.vision_analyzer import infer_video_script_and_mood
            vision_result = infer_video_script_and_mood(
                keyframe_paths=keyframe_files,
                video_duration=src_duration,
                preset_hint=preset_id,
                speech_description=speech_description,
                visual_description=visual_description,
                visual_lead_in=visual_lead_in,
                outro_buffer=outro_buffer,
            )
            inferred_script = sanitize_script_against_meta_prompts(vision_result.get("script"))
            selected_script = inferred_script or DEFAULT_PROMO_SCRIPT
            resolved_tone = emotional_tone or vision_result.get("emotional_tone") or principles_voice.get("active_tone_bias", "فاخر وهادئ")
            resolved_style_prompt = style_prompt or vision_result.get("emotional_prompt")
            inferred_music = vision_result.get("recommended_music")
            vision_engine = vision_result.get("engine")
            if not phone_number and vision_result.get("phone_number"):
                phone_number = vision_result.get("phone_number")
            if not bottom_text and vision_result.get("bottom_text"):
                bottom_text = vision_result.get("bottom_text")
        except Exception as exc:
            logger.warning("Vision analysis error: %s. Using fallback.", exc)
            from web.vision_analyzer import _get_smart_fallback
            fb_res = _get_smart_fallback(
                duration=src_duration,
                preset_hint=preset_id,
                speech_description=speech_description,
                visual_description=visual_description,
                visual_lead_in=visual_lead_in,
                outro_buffer=outro_buffer,
                keyframe_count=len(keyframe_files),
            )
            selected_script = sanitize_script_against_meta_prompts(fb_res.get("script")) or DEFAULT_PROMO_SCRIPT
            inferred_script = selected_script
            resolved_tone = emotional_tone or fb_res.get("emotional_tone") or principles_voice.get("active_tone_bias", "فاخر وهادئ")
            resolved_style_prompt = style_prompt or fb_res.get("emotional_prompt") or "Warm, luxurious and prestigious real estate tone"
            inferred_music = fb_res.get("recommended_music", "luxury_piano")
            vision_engine = "fallback_on_error"
            if not phone_number and fb_res.get("phone_number"):
                phone_number = fb_res.get("phone_number")
            if not bottom_text and fb_res.get("bottom_text"):
                bottom_text = fb_res.get("bottom_text")

        _notify(
            step=3,
            percent=60,
            message=f"تم استنتاج الوصف التسويقي بنجاح. الحالة الشعورية: {resolved_tone}",
            log=f"[تحليل شعوري] ✨ تم استنتاج الوصف التسويقي والحالة الشعورية: [{resolved_tone}] (تم تحليل {len(keyframe_files)} إطار بدقة)",
            extra={
                "emotional_tone": resolved_tone,
                "inferred_script": inferred_script,
                "analyzed_frames_count": len(keyframe_files),
                "visual_lead_in_seconds": visual_lead_in,
            },
        )
        selected_preset = preset_id if preset_id in ALGERIAN_REAL_ESTATE_PRESETS else None
    else:
        inferred_script = None
        inferred_music = None
        if script and script.strip():
            selected_script = sanitize_script_against_meta_prompts(script.strip())
            selected_preset = preset_id if preset_id in ALGERIAN_REAL_ESTATE_PRESETS else None
        elif preset_id and preset_id in ALGERIAN_REAL_ESTATE_PRESETS:
            selected_script = ALGERIAN_REAL_ESTATE_PRESETS[preset_id]["description"]
            selected_preset = preset_id
        else:
            selected_script = DEFAULT_PROMO_SCRIPT
            selected_preset = None

        preset_tones = {
            "algiers_f4_luxury": "فاخر وهادئ",
            "oran_seaview_villa": "دافئ ومشرق بإطلالة بحرية",
            "constantine_commercial": "متحمس وحيوي",
            "rental_apartment": "دافئ ومريح للعائلات",
        }
        resolved_tone = emotional_tone or preset_tones.get(selected_preset or "", principles_voice.get("active_tone_bias", "فاخر وهادئ"))
        resolved_style_prompt = style_prompt or f"Warm and prestigious real estate presentation in {resolved_tone}"

    # Resolve background music track
    resolved_music_key = principles_visual.get("selected_music_theme", "luxury_piano")
    if music_track and music_track in MUSIC_LIBRARY:
        resolved_music_key = music_track
    elif is_auto_mode and inferred_music and inferred_music in MUSIC_LIBRARY:
        resolved_music_key = inferred_music
    elif selected_preset and "recommended_music" in ALGERIAN_REAL_ESTATE_PRESETS.get(selected_preset, {}):
        resolved_music_key = ALGERIAN_REAL_ESTATE_PRESETS[selected_preset]["recommended_music"]
    music_meta = MUSIC_LIBRARY.get(resolved_music_key, MUSIC_LIBRARY["luxury_piano"])
    music_audio_file = music_meta["file"]

    # 4. Synthesize Narration Audio with Emotional Tone Steering
    resolved_voice_id, resolved_voice_name = resolve_voice_profile(voice)
    _notify(
        step=3,
        percent=70,
        message=f"توليد التعليق الصوتي العصبي عبر Gemini TTS ({resolved_voice_name}) بالحالة الشعورية ({resolved_tone})...",
        log="[توليد صوت] 🎙️ توليد التعليق الصوتي العصبي بالحالة الشعورية المحددة...",
        extra={"emotional_tone": resolved_tone, "inferred_script": inferred_script, "voice": resolved_voice_id},
    )

    from config.production_principles_manager import build_tts_style_principles
    tts_principles_style = build_tts_style_principles(emotional_tone=resolved_tone)
    final_style_prompt = f"{resolved_style_prompt}. {tts_principles_style}" if resolved_style_prompt else tts_principles_style

    narration_wav = out_cuts_dir / f"narration_{job_id}.wav"
    narration_info = synthesize_narration(
        script_text=selected_script,
        output_path=narration_wav,
        voice=voice,
        style_prompt=final_style_prompt,
        emotional_tone=resolved_tone,
    )
    narration_duration = narration_info["duration"]

    # 5. Timeline & Outro Calculations (Lead-In Delay & Outro Music Swell)
    visual_lead_in = max(0.0, float(visual_lead_in if visual_lead_in is not None else 1.2))
    outro_buffer = max(0.5, float(outro_buffer if outro_buffer is not None else 1.2))
    visual_lead_in_ms = int(round(visual_lead_in * 1000))
    narration_delay = f"adelay={visual_lead_in_ms}|{visual_lead_in_ms}," if visual_lead_in_ms > 0 else ""

    min_required_duration = round(visual_lead_in + narration_duration + outro_buffer, 2)
    total_duration = max(round(src_duration, 2), min_required_duration)
    total_duration = max(5.0, total_duration)

    pad_needed = max(0.0, round(total_duration - src_duration, 2))
    fade_out_start = max(0.5, round(total_duration - 1.8, 2))

    logger.info(
        "Job %s: Timeline - Video: %.2fs, Lead-In: %.2fs, Narration: %.2fs, Outro: %.2fs, Total: %.2fs (Pad: %.2fs)",
        job_id,
        src_duration,
        visual_lead_in,
        narration_duration,
        outro_buffer,
        total_duration,
        pad_needed,
    )

    # 6. Sidechain Compression & Dynamic Ducking Settings
    target_duck = principles_visual.get("smart_ducking_volume", duck_level) if duck_level == 0.25 else duck_level
    effective_duck_level = max(0.05, min(0.60, float(target_duck)))
    duck_threshold = 0.030
    duck_ratio = max(4.0, min(24.0, round(1.0 / effective_duck_level, 1)))
    duck_attack = 80
    duck_release = 450
    ambient_volume = 0.38

    _notify(
        step=4,
        percent=85,
        message=f"دمج الموسيقى التصويرية ({music_meta['title']}) وتطبيق خفض الصوت التلقائي (Sidechain Ducking)...",
        log=f"[مكساج صوتي] تم إنتاج الصوت ({narration_duration:.1f}s - {narration_info['synthesizer']}). دمج الموسيقى وتطبيق الخفض الذكي ({effective_duck_level:.2f}).",
    )

    # 7. Construct FFmpeg Filter Graph
    video_filters: List[str] = [
        f"scale={target_w}:{target_h}:force_original_aspect_ratio=decrease",
        f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2",
        "setsar=1",
    ]
    if pad_needed > 0:
        video_filters.append(f"tpad=stop_mode=clone:stop_duration={pad_needed}")
    video_filters.append("fade=t=in:st=0:d=0.5")
    video_filters.append(f"fade=t=out:st={round(total_duration - 1.0, 2)}:d=1.0")
    video_filters.append("format=yuv420p")
    v_graph = ",".join(video_filters) + "[vout]"

    # Audio pipeline: Use real open-source music file if available, with mathematical fallback
    use_real_music = music_audio_file.is_file()
    ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
    final_cut_path = out_cuts_dir / f"cut_{job_id}.mp4"

    if use_real_music:
        filter_complex = f"""
        [0:v]{v_graph};
        [2:a]aloop=loop=-1:size=2e+09,atrim=0:{total_duration},afade=t=in:ss=0:d=1.0,afade=t=out:st={fade_out_start}:d=1.8,aformat=sample_rates=48000:channel_layouts=stereo[music];
        [1:a]aformat=sample_rates=48000:channel_layouts=stereo,{narration_delay}apad=whole_dur={total_duration},asplit=2[v_sc][v_mix];
        [music][v_sc]sidechaincompress=threshold={duck_threshold}:ratio={duck_ratio}:attack={duck_attack}:release={duck_release}:makeup=1[ducked_music];
        [v_mix]volume=1.0[v_clean];
        [ducked_music]volume={ambient_volume}[m_clean];
        [v_clean][m_clean]amix=inputs=2:duration=first:normalize=0[aout]
        """
        ffmpeg_cmd = [
            ffmpeg_bin, "-y",
            "-i", str(input_path),
            "-i", str(narration_wav),
            "-i", str(music_audio_file),
            "-filter_complex", filter_complex,
            "-map", "[vout]",
            "-map", "[aout]",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "20",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-t", str(total_duration),
            str(final_cut_path),
        ]
    else:
        # Fallback harmonic synth pad
        filter_complex = f"""
        [0:v]{v_graph};
        sine=f=146.83:d={total_duration},volume=0.22[d3];
        sine=f=174.61:d={total_duration},volume=0.18[f3];
        sine=f=220.00:d={total_duration},volume=0.16[a3];
        sine=f=261.63:d={total_duration},volume=0.12[c4];
        sine=f=293.66:d={total_duration},volume=0.14[d4];
        sine=f=349.23:d={total_duration},volume=0.10[f4];
        anoisesrc=d={total_duration}:c=pink:r=48000:a=0.005,lowpass=f=900[warm_air];
        [d3][f3][a3][c4][d4][f4][warm_air]amix=inputs=7:normalize=0,lowpass=f=2000,afade=t=in:ss=0:d=1.5,afade=t=out:st={fade_out_start}:d=1.8,aformat=sample_rates=48000:channel_layouts=stereo[music];
        [1:a]aformat=sample_rates=48000:channel_layouts=stereo,{narration_delay}apad=whole_dur={total_duration},asplit=2[v_sc][v_mix];
        [music][v_sc]sidechaincompress=threshold={duck_threshold}:ratio={duck_ratio}:attack={duck_attack}:release={duck_release}:makeup=1[ducked_music];
        [v_mix]volume=1.0[v_clean];
        [ducked_music]volume={ambient_volume}[m_clean];
        [v_clean][m_clean]amix=inputs=2:duration=first:normalize=0[aout]
        """
        ffmpeg_cmd = [
            ffmpeg_bin, "-y",
            "-i", str(input_path),
            "-i", str(narration_wav),
            "-filter_complex", filter_complex,
            "-map", "[vout]",
            "-map", "[aout]",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "20",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-t", str(total_duration),
            str(final_cut_path),
        ]

    logger.info("Job %s: Rendering final cut with FFmpeg -> %s", job_id, final_cut_path)
    start_render = datetime.now(timezone.utc)
    try:
        subprocess.run(ffmpeg_cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        logger.error("FFmpeg render failed: %s", e.stderr)
        raise RuntimeError(f"FFmpeg assembly failed: {e.stderr.strip()}") from e

    render_seconds = (datetime.now(timezone.utc) - start_render).total_seconds()
    logger.info("Job %s: Final cut rendered in %.2fs (%d bytes)", job_id, render_seconds, final_cut_path.stat().st_size)

    # 8. Apply Smart Video Annotations, Lower-Third Banners & Merchant Fixed Text Overlays
    applied_annotations_count = 0
    annotations_list: List[Dict[str, Any]] = []

    # Insert persistent bottom text / phone number overlay
    effective_bottom = bottom_text or (phone_number if phone_number else None)
    if effective_bottom and str(effective_bottom).strip():
        annotations_list.append({
            "text": str(effective_bottom).strip(),
            "start_sec": 0.0,
            "end_sec": total_duration,
            "position": "bottom_banner",
            "style": "persistent_bottom",
            "font_size": 28,
            "boxborderw": 8,
            "persistent": True,
        })

    # Insert fixed promotional text if supplied by merchant
    if fixed_text and str(fixed_text).strip() and str(fixed_text).strip() != str(effective_bottom or "").strip():
        annotations_list.append({
            "text": str(fixed_text).strip(),
            "start_sec": 0.0,
            "end_sec": total_duration,
            "position": text_position or "lower_third",
            "style": text_style or "modern_white",
            "font_size": 34,
        })

    if principles_annotation.get("enable_auto_annotations", True):
        banner_title = ""
        if selected_preset and selected_preset in ALGERIAN_REAL_ESTATE_PRESETS:
            banner_title = ALGERIAN_REAL_ESTATE_PRESETS[selected_preset]["title_ar"]
        elif is_auto_mode and inferred_script:
            banner_title = f"عقار استثنائي • {resolved_tone}"
        elif not (fixed_text and str(fixed_text).strip()):
            banner_title = "فرصة تجارية راقية"

        if banner_title and not (fixed_text and str(fixed_text).strip()):
            annotations_list.append({
                "text": banner_title,
                "start_sec": 0.5,
                "end_sec": min(4.5, total_duration),
                "position": principles_annotation.get("position", "lower_third"),
                "style": principles_annotation.get("font_style", "luxury_gold"),
            })

        if is_auto_mode and "vision_result" in locals() and isinstance(vision_result, dict):
            hl_items = vision_result.get("highlights", [])
            for idx, hl in enumerate(hl_items[:3]):
                hl_text = hl if isinstance(hl, str) else hl.get("title", str(hl))
                start_t = 4.5 + (idx * 3.0)
                if start_t < total_duration - 1.0:
                    annotations_list.append({
                        "text": hl_text,
                        "start_sec": round(start_t, 1),
                        "end_sec": round(min(start_t + 2.5, total_duration - 0.5), 1),
                        "position": "lower_third",
                        "style": "emerald_badge",
                    })

    if annotations_list:
        annotated_tmp = out_cuts_dir / f"annotated_{job_id}.mp4"
        try:
            annot_res = annotate_video(
                input_video_path=final_cut_path,
                output_video_path=annotated_tmp,
                annotations=annotations_list,
            )
            ok = isinstance(annot_res, dict) and annot_res.get("status") in ("ok", "completed")
            if ok and annotated_tmp.is_file() and annotated_tmp.stat().st_size > 1000:
                annotated_tmp.replace(final_cut_path)
                applied_annotations_count = len(annotations_list)
                logger.info("Job %s: Video annotations applied successfully (%d overlays)", job_id, applied_annotations_count)
                _notify(
                    step=5,
                    percent=95,
                    message="تمت إضافة الملصقات والنصوص التوضيحية على الفيديو بنجاح.",
                    log=f"[ملصقات الفيديو] تم تطبيق {applied_annotations_count} نصوص وشارات توضيحية ذكية على المشاهد.",
                )
        except Exception as annot_err:
            logger.warning("Job %s: Annotation pass encountered non-fatal error: %s", job_id, annot_err)

    # Verify final cut is completely written and non-empty
    if not final_cut_path.is_file() or final_cut_path.stat().st_size == 0:
        raise RuntimeError(f"Rendered video cut file was not found or is empty: {final_cut_path}")

    # Atomically update legacy outputs/final_cut.mp4 so legacy endpoints work
    try:
        legacy_dir = REPO_ROOT / "outputs"
        legacy_dir.mkdir(parents=True, exist_ok=True)
        legacy_cut_path = legacy_dir / "final_cut.mp4"
        legacy_cut_tmp = legacy_dir / f"final_cut_{job_id}.mp4.tmp"
        shutil.copyfile(final_cut_path, legacy_cut_tmp)
        legacy_cut_tmp.replace(legacy_cut_path)
        logger.info("Job %s: Atomically updated legacy cut -> %s (%d bytes)", job_id, legacy_cut_path, legacy_cut_path.stat().st_size)
    except Exception as copy_err:
        logger.warning("Job %s: Failed to copy to legacy final_cut.mp4: %s", job_id, copy_err)

    # 9. Compile Complete Execution Summary
    video_web_url = f"/outputs/mobile_cuts/cut_{job_id}.mp4"
    summary: Dict[str, Any] = {
        "job_id": job_id,
        "status": "completed",
        "progress": 100,
        "progress_percent": 100,
        "video_url": video_web_url,
        "output_video_url": video_web_url,
        "output_video": video_web_url,
        "output_path": str(final_cut_path),
        "absolute_output_path": str(final_cut_path.resolve()),
        "file_size_bytes": final_cut_path.stat().st_size,
        "duration": total_duration,
        "orientation": orientation,
        "video_orientation": orientation,
        "aspect_ratio": aspect_label,
        "resolution": f"{target_w}x{target_h}",
        "fixed_text": fixed_text,
        "bottom_text": effective_bottom,
        "phone_number": phone_number,
        "text_position": text_position,
        "text_style": text_style,
        "auto_mode": is_auto_mode,
        "emotional_tone": resolved_tone,
        "speech_description": speech_description,
        "visual_description": visual_description,
        "inferred_script": inferred_script,
        "vision_engine": vision_engine,
        "style_prompt": resolved_style_prompt,
        "script": selected_script,
        "preset_id": selected_preset,
        "voice": resolved_voice_id,
        "gemini_voice": resolved_voice_name,
        "visual_lead_in_seconds": visual_lead_in,
        "outro_buffer_seconds": outro_buffer,
        "analyzed_frames_count": len(keyframe_files),
        "duck_level": effective_duck_level,
        "synthesizer": narration_info["synthesizer"],
        "narration_audio_url": f"/outputs/mobile_cuts/narration_{job_id}.wav",
        "annotations_applied": applied_annotations_count,
        "music_track": {
            "id": music_meta["id"],
            "title": music_meta["title"],
            "license": music_meta["license"],
        },
        "keyframes": formatted_keyframes,
        "total_keyframes": len(formatted_keyframes),
        "metadata": {
            "source_video": str(input_path),
            "source_duration": src_duration,
            "source_resolution": f"{src_width}x{src_height}",
            "visual_lead_in_seconds": visual_lead_in,
            "outro_buffer_seconds": outro_buffer,
            "analyzed_frames_count": len(keyframe_files),
            "voice_profile": resolved_voice_id,
            "gemini_voice": resolved_voice_name,
            "narration_duration": narration_duration,
            "render_seconds": round(render_seconds, 2),
            "annotations_count": applied_annotations_count,
            "sidechain_compression": {
                "music_track": music_meta["title"],
                "duck_threshold": duck_threshold,
                "duck_ratio": duck_ratio,
                "duck_attack_ms": duck_attack,
                "duck_release_ms": duck_release,
            },
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Persist summary JSON
    summary_path = out_cuts_dir / f"summary_{job_id}.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    _notify(
        step=5,
        percent=100,
        message="اكتمل إنتاج الفيديو التسويقي بنجاح! جاهز للمعاينة والتحميل.",
        log=f"[إخراج نهائي] تم تصدير الفيديو النهائي ({summary['resolution']}, {total_duration:.1f}s) بنجاح. جاهز للمعاينة والتحميل.",
    )

    return summary
