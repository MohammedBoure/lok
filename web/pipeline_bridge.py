#!/usr/bin/env python3
"""
Mobile Post-Production Bridge & Assembly Engine (web/pipeline_bridge.py)
Part of the Video Post-Production & Mobile API Server Pipeline.

Author: MouhammedBoure
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
from tts.gemini_speech.client import strip_tts_vocal_tags
from web.video_annotator import annotate_video, find_system_font

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
    "قص", "اقتطع", "احذف", "ازل", "أزل", "مونتاج", "تقطيع", "اقتصاص", "لقطات", "مشاهد",
    "trim", "cut", "crop", "duration", "مدة", "ثواني", "ثانية",
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


def parse_time_directive(s: str) -> float:
    """Parse time string in seconds or MM:SS format to float seconds."""
    s = str(s).strip()
    if ":" in s:
        p = s.split(":")
        if len(p) == 2:
            return float(p[0]) * 60 + float(p[1])
        elif len(p) == 3:
            return float(p[0]) * 3600 + float(p[1]) * 60 + float(p[2])
    return float(s)


def parse_montage_directives(text: Optional[str]) -> Dict[str, Any]:
    """
    Parse video montage, trimming, and shot selection directives from user prompt.
    Supports Arabic, Algerian Darja, English, and French natural language formats.
    """
    plan: Dict[str, Any] = {
        "requested": False,
        "mode": "none",
        "trim_start": None,
        "trim_end": None,
        "trim_end_offset": None,
        "target_duration": None,
        "smart_montage": False,
        "raw_directive": None,
    }
    if not text:
        return plan

    norm = str(text).strip().lower()
    time_rx = r"(\d+:\d+(?::\d+)?|\d+(?:\.\d+)?)"

    # 1. Range / Interval: e.g. "قص من 2 إلى 8 ثواني" or "احتفظ من 3 لـ 12" or "trim from 0:02 to 0:15"
    m_range = re.search(
        rf"(?:من|from|between|entre)\s*(?:الثانية|ثانية|الدقيقة|second|sec)?\s*{time_rx}\s*(?:ثانية|ثواني|s|sec)?\s*(?:إلى|الى|حتى|لـ|لغاية|to|until|et|-)\s*(?:الثانية|ثانية|second|sec)?\s*{time_rx}",
        norm,
    )
    if m_range:
        try:
            st = parse_time_directive(m_range.group(1))
            en = parse_time_directive(m_range.group(2))
            if en > st:
                plan["requested"] = True
                plan["trim_start"] = st
                plan["trim_end"] = en
                plan["mode"] = "interval"
                plan["raw_directive"] = m_range.group(0)
        except (ValueError, TypeError):
            pass

    # 2. Trim start: e.g. "قص أول 3 ثواني" or "احذف البداية 4 ثواني" or "cut the first 4s"
    m_start = re.search(
        rf"(?:قص|احذف|ازل|أزل|اقتطع|تجاوز|تخطى|نحي|بدون|cut|trim|remove|skip)\s*(?:the\s+)?(?:أول|اول|بداية|الـ|first|start)?\s*{time_rx}\s*(?:ثانية|ثواني|ثوانٍ|s|sec|seconds)(?:\s*(?:الأولى|الاولى|من البداية|في البداية))?",
        norm,
    )
    if m_start and plan["mode"] != "interval":
        # Ensure it's not actually a trim_end match
        if not any(w in m_start.group(0) for w in ["آخر", "اخر", "نهاية", "last", "end"]):
            try:
                val = parse_time_directive(m_start.group(1))
                plan["requested"] = True
                plan["trim_start"] = val
                if plan["mode"] == "none":
                    plan["mode"] = "trim_start"
                    plan["raw_directive"] = m_start.group(0)
            except (ValueError, TypeError):
                pass

    # 3. Trim end: e.g. "قص آخر 5 ثواني" or "احذف النهاية 4 ثواني" or "cut the last 5s"
    m_end = re.search(
        rf"(?:قص|احذف|ازل|أزل|اقتطع|نحي|بدون|cut|trim|remove)\s*(?:the\s+)?(?:آخر|اخر|نهاية|end|last)\s*{time_rx}\s*(?:ثانية|ثواني|ثوانٍ|s|sec|seconds)?",
        norm,
    )
    if m_end:
        try:
            val = parse_time_directive(m_end.group(1))
            plan["requested"] = True
            plan["trim_end_offset"] = val
            if plan["mode"] == "none":
                plan["mode"] = "trim_end"
                plan["raw_directive"] = m_end.group(0)
        except (ValueError, TypeError):
            pass

    # 4. Target duration: e.g. "مدة الفيديو 15 ثانية" or "لا يتجاوز 12 ثانية" or "اختصر الفيديو إلى 10 ثواني"
    m_dur = re.search(
        rf"(?:مدة|المدة|طول|احتفظ بـ|خليه|اجعل|اجعله|اختصر(?:ه| الفيديو)?(?:\s+إلى|\s+الى|\s+في)?|لا يتجاوز|لا تتجاوز|أقل من|اقل من|في حدود|duration|target duration|keep|shorten to)(?:\s+(?:الفيديو|المقطع|مدة|طول|video))*\s*(?:تكون|هي|:|=)?\s*{time_rx}\s*(?:ثانية|ثواني|ثوانٍ|s|sec|seconds)?",
        norm,
    )
    if m_dur:
        try:
            val = parse_time_directive(m_dur.group(1))
            if val >= 2.0:
                plan["requested"] = True
                plan["target_duration"] = val
                if plan["mode"] == "none":
                    plan["mode"] = "target_duration"
                    plan["raw_directive"] = m_dur.group(0)
        except (ValueError, TypeError):
            pass

    # 5. Smart montage / highlight extraction: e.g. "مونتاج ذكي لأفضل اللقطات"
    smart_montage_keywords = [
        "مونتاج", "اقتطاع اللقطات", "قص اللقطات", "أفضل اللقطات", "افضل اللقطات",
        "افضل المشاهد", "أفضل المشاهد", "أهم اللقطات", "اهم اللقطات", "أهم المشاهد",
        "اختصر الفيديو", "تلخيص الفيديو", "ملخص الفيديو", "حذف اللقطات المملة",
        "تشذيب تلقائي", "تقطيع ذكي", "دمج اللقطات", "smart montage", "highlight montage", "montage",
    ]
    if any(k in norm for k in smart_montage_keywords):
        plan["requested"] = True
        plan["smart_montage"] = True
        if plan["mode"] == "none":
            plan["mode"] = "smart_montage"

    return plan


def extract_property_features(text: Optional[str]) -> Dict[str, Any]:
    """
    Extract property specifications and selling points from user prompt.
    Captures:
      - unit: e.g. F1, F2, F3, F4, F5, F6, duplex, studio
      - sea_view: True if mentions overlooking sea / coastal view
      - property_type: 'منزل', 'شقة', 'فيلا', 'عقار', 'محل'
      - keywords: list of matched architectural selling points
    """
    if not text:
        return {"unit": None, "sea_view": False, "property_type": None, "keywords": []}

    clean = str(text).lower()
    keywords = []

    # Unit type: F1..F6 or S+1..S+4
    m_unit = re.search(r"\b(f[1-6]|s\+[1-4])\b", clean, re.IGNORECASE)
    unit_val = m_unit.group(1).upper() if m_unit else None
    if unit_val:
        keywords.append(unit_val)

    # Sea view patterns
    sea_patterns = [
        r"(?:مطل|مطلة|تطل|يطل)(?:\s+مباشرة)?\s+على\s+البحر",
        r"إطلالة(?:\s+على|\s+بحرية|\s+بانورامية)?\s+على\s+البحر",
        r"واجهة\s+بحرية",
        r"بحرية",
        r"vue\s+sur\s+mer",
        r"sea\s+view",
    ]
    has_sea_view = any(re.search(pat, clean) for pat in sea_patterns)
    if has_sea_view:
        keywords.append("مطل على البحر")

    # Property type
    property_type = None
    for pt in ["فيلا", "منزل", "شقة", "دار", "دوبلكس", "استوديو", "محل تجاري", "محل", "عقار", "villa", "appartement", "maison"]:
        if pt in clean:
            property_type = pt
            keywords.append(pt)
            break

    return {
        "unit": unit_val,
        "sea_view": has_sea_view,
        "property_type": property_type,
        "keywords": keywords,
    }


def parse_music_directives(text: Optional[str]) -> Dict[str, Any]:
    """
    Parse soundtrack directives from user prompt:
      - Strict Opt-In Architecture: Music is OFF / muted by default.
      - mute_music: True by default; False ONLY if music is explicitly requested.
      - music_requested: True if user explicitly opted in to background music.
      - music_track: explicit selection of music theme ('luxury_piano', 'acoustic_guitar', 'ambient_meditation')
      - music_volume: target ambient music volume (e.g. 0.08 for quiet music)
    """
    res: Dict[str, Any] = {
        "mute_music": True,
        "explicit_mute": False,
        "music_requested": False,
        "music_track": None,
        "music_volume": None,
    }
    if not text:
        return res

    text_l = str(text).lower()

    # 1. Check for explicit mute / removal requests
    mute_keywords = [
        "بدون موسيقى", "بلا موسيقى", "من غير موسيقى", "ازالة الموسيقى",
        "إزالة الموسيقى", "حذف الموسيقى", "كتم الموسيقى", "بدون صوت خلفية",
        "بدون صوت الموسيقى", "بدون أغاني", "بدون اغاني", "no music",
        "mute music", "without music", "remove music", "sans musique",
    ]
    is_explicitly_muted = any(k in text_l for k in mute_keywords)
    if is_explicitly_muted:
        res["mute_music"] = True
        res["explicit_mute"] = True
        res["music_requested"] = False
        return res

    # 2. Track selection
    if any(k in text_l for k in ["موسيقى بيانو", "صوت بيانو", "بيانو", "piano", "موسيقى فاخرة"]):
        res["music_track"] = "luxury_piano"
    elif any(k in text_l for k in ["موسيقى جيتار", "صوت جيتار", "جيتار", "guitar", "موسيقى حيوية"]):
        res["music_track"] = "acoustic_guitar"
    elif any(k in text_l for k in ["موسيقى تأمل", "موسيقى هادئة", "موسيقى بحر", "موسيقى هادئه", "meditation", "ambient"]):
        res["music_track"] = "ambient_meditation"

    # 3. Volume
    m_vol = re.search(r"(?:صوت\s+الموسيقى|مستوى\s+الموسيقى|حجم\s+الموسيقى|music\s+volume)\s*(?:يكون|تكون|:|=)?\s*(\d+(?:\.\d+)?)\s*(%|بالمئة)?", text_l)
    if m_vol:
        try:
            val = float(m_vol.group(1))
            if m_vol.group(2) or val > 1.0:
                res["music_volume"] = max(0.02, min(0.60, val / 100.0))
            else:
                res["music_volume"] = max(0.02, min(0.60, val))
        except (ValueError, TypeError):
            pass
    elif any(k in text_l for k in ["موسيقى هادئة جدا", "موسيقى خفيفة جدا", "موسيقى خفيفة", "خفض الموسيقى", "صوت الموسيقى منخفض", "موسيقى واطية", "low music", "soft music"]):
        res["music_volume"] = 0.08

    # 4. Opt-In validation: Check if user explicitly asked for music
    music_optin_keywords = [
        "موسيقى", "music", "بيانو", "جيتار", "piano", "guitar", "لحن",
        "خلفية موسيقية", "نغمة", "soundtrack", "instrumental", "مع موسيقى",
        "أضف موسيقى", "اضف موسيقى", "تشغيل الموسيقى", "موسيقى خلفية"
    ]
    if any(k in text_l for k in music_optin_keywords) or res["music_track"] or res["music_volume"] is not None:
        res["music_requested"] = True
        res["mute_music"] = False

    return res


def analyze_source_audio_for_speech(video_path: Union[str, Path], max_duration: float = 30.0) -> Optional[str]:
    """
    Inspect source video audio stream for speech or spoken remarks by the videographer.
    If speech is detected, transcribes and summarizes remarks using Gemini API.
    """
    api_raw = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEYS") or ""
    api_key = next((p.strip().strip("\"'") for p in api_raw.split(",") if p.strip()), "")
    if not api_key:
        return None

    v_path = Path(video_path).resolve()
    if not v_path.is_file():
        return None

    # 1. Check if audio stream exists via ffprobe
    try:
        probe_cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=codec_type",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(v_path),
        ]
        probe_res = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
        if "audio" not in probe_res.stdout.lower():
            return None
    except Exception:
        return None

    # 2. Extract mono audio slice
    temp_wav = v_path.parent / f"_probe_audio_{v_path.stem}.wav"
    try:
        extract_cmd = [
            "ffmpeg", "-y",
            "-i", str(v_path),
            "-vn",
            "-ar", "16000",
            "-ac", "1",
            "-t", str(max_duration),
            str(temp_wav),
        ]
        subprocess.run(extract_cmd, capture_output=True, text=True, check=True)
        if not temp_wav.is_file() or temp_wav.stat().st_size < 1000:
            return None

        # 3. Check audio volume level to avoid silent audio
        vol_cmd = [
            "ffmpeg", "-i", str(temp_wav),
            "-filter:a", "volumedetect",
            "-f", "null", "/dev/null",
        ]
        vol_res = subprocess.run(vol_cmd, capture_output=True, text=True)
        vol_out = vol_res.stderr.lower()
        if "max_volume: -inf" in vol_out or "mean_volume: -inf" in vol_out:
            return None

        # 4. Transcribe via Gemini if API key is present
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEYS")
        if not api_key:
            return None

        import base64
        import requests

        with open(temp_wav, "rb") as af:
            audio_b64 = base64.b64encode(af.read()).decode("utf-8")

        prompt_text = (
            "Listen to this audio recorded by the videographer during a real estate walkthrough. "
            "If the person filming speaks in Arabic or Algerian Darja about the property or rooms, "
            "transcribe or summarize their spoken remarks in 1-2 concise Arabic sentences. "
            "If there is no clear human speech (only silence, background steps, or ambient noise), "
            "return an empty string \"\"."
        )

        body = {
            "contents": [{
                "parts": [
                    {"text": prompt_text},
                    {"inlineData": {"mimeType": "audio/wav", "data": audio_b64}},
                ]
            }],
            "generationConfig": {
                "temperature": 0.2,
            }
        }

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={api_key}"
        resp = requests.post(url, json=body, timeout=(5.0, 20.0))
        if resp.status_code == 200:
            cands = resp.json().get("candidates", [])
            if cands:
                speech_text = cands[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
                clean_speech = speech_text.replace("```", "").strip()
                if clean_speech and len(clean_speech) > 3 and not any(kw in clean_speech.lower() for kw in ["no speech", "empty", "silent", "لا يوجد كلام"]):
                    return clean_speech
    except Exception as exc:
        logger.debug("Source audio speech detection skipped: %s", exc)
    finally:
        try:
            if temp_wav.is_file():
                temp_wav.unlink()
        except OSError:
            pass

    return None


def is_meta_prompt(text: Optional[str]) -> bool:
    """
    Determine whether input represents meta-directions (instructions, phone overlay,
    Darja narration request, trimming/montage commands, music preferences, font styling)
    rather than a literal voiceover script to be read word-for-word.
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
        if any(w in norm for w in ["رقم", "هاتف", "اتصال", "اتصل", "نص", "فيديو", "اسفل", "أسفل", "طول", "شغال", "خط"]):
            return True
    # Check if montage directive is present
    m_plan = parse_montage_directives(norm)
    if m_plan.get("requested"):
        return True
    # Check if music directive is explicitly present
    if any(k in norm for k in ["بدون موسيقى", "بلا موسيقى", "من غير موسيقى", "no music", "mute music", "كتم الموسيقى", "حذف الموسيقى"]):
        return True
    mus_dir = parse_music_directives(norm)
    if mus_dir.get("music_requested") or mus_dir.get("music_volume") is not None or mus_dir.get("music_track"):
        return True
    # Check if font styling directive is present
    if any(w in norm for w in ["بخط كبير", "خط كبير", "كبير وواضح", "كبير و واضح", "واضح وكبير", "كبير", "بارز", "عريض"]):
        return True
    # Check if property talking points are requested
    p_feats = extract_property_features(norm)
    if p_feats.get("keywords") and re.search(r"\b(?:يتكلم|تكلم|احكي|قول|يقول|صف|نوصف|المعلق|المعلقة)\b", norm):
        return True
    return False


def extract_directives(text: Optional[str]) -> Dict[str, Any]:
    """
    Parse freeform creative user instructions, extracting meta-intent flags,
    phone number, persistent bottom overlay text, styling preferences, music controls,
    voice preferences, highlight badge opt-in, orientation, and montage/trimming plans.
    """
    raw = str(text or "").strip()
    raw_lower = raw.lower()
    is_meta = is_meta_prompt(raw)
    phone = extract_algerian_phone(raw)
    montage_plan = parse_montage_directives(raw)
    music_directives = parse_music_directives(raw)
    property_features = extract_property_features(raw)

    bottom_text: Optional[str] = None
    if phone:
        bottom_text = phone

    if raw and is_meta:
        m_quoted = re.search(r'["“\']([^"”\']+)["”\']', raw)
        if m_quoted:
            bottom_text = m_quoted.group(1).strip()
        elif not phone:
            m_custom = re.search(
                r"(?:نص(?:اً)? أسفل الفيديو|الشريط السفلي|اكتب في الأسفل|ضع في الأسفل|اكتب على الفيديو|ضع نص|أضف كتابة)(?:\s*به|\s*فيه|\s*:)?\s*([^\n.،]+)",
                raw,
            )
            if m_custom:
                extracted_phrase = m_custom.group(1).strip()
                cleaned_phrase = re.sub(r"^(?:الرقم التالي|رقم|به الرقم التالي)\s*", "", extracted_phrase).strip()
                if cleaned_phrase:
                    bottom_text = cleaned_phrase

    darja_requested = any(w in raw_lower for w in ["دارجة", "بالدارجة", "لهجة جزائرية", "جزائرية"])
    voiceover_requested = any(w in raw_lower for w in ["تعليق صوتي", "صوت", "فويس اوفر", "voiceover", "نص يتناسب"])
    persistent_overlay = any(w in raw_lower for w in ["طول ما الفيديو", "طوال الفيديو", "كامل الفيديو", "دائم", "طول الفيديو", "شغال"])

    # Font sizing & prominence
    large_font = any(w in raw_lower for w in ["بخط كبير", "خط كبير", "كبير وواضح", "كبير و واضح", "واضح وكبير", "كبير", "بارز", "عريض", "large font", "big font", "bold"])

    # Opt-In Subtitles / Synchronized Captions directive detection
    subtitles_requested = any(w in raw_lower for w in [
        "أضف ترجمة", "اضف ترجمة", "شريط ترجمة", "ترجمة فورية", "ترجمة متزامنة",
        "كتابة متزامنة", "مع ترجمة", "اكتب الكلام في الأسفل", "اكتب الكلام في الاسفل",
        "اكتب الكلام", "ترجمة الكلام", "ترجمة الفيديو", "إظهار الترجمة", "اظهار الترجمة",
        "مع الكلمات", "كلمات متزامنة", "نص مع الصوت", "النص مع الصوت", "كتابة النص مع الصوت",
        "subtitles", "captions", "subtitle",
    ])

    # Opt-In Highlight Badges detection
    highlights_requested = any(w in raw_lower for w in [
        "شارات", "عناوين فرعية", "إظهار المميزات", "اظهار المميزات", "كتابة المميزات",
        "ملصقات المميزات", "نقاط القوة على الفيديو", "أبرز المميزات على الشاشة", "highlights", "badges",
    ])

    # Voice persona / gender directive detection
    requested_voice: Optional[str] = None
    if any(w in raw_lower for w in ["صوت شاب", "بصوت شاب", "صوت حيوي", "صوت حماسي", "fenrir"]):
        requested_voice = "ar-XA-Standard-C"
    elif any(w in raw_lower for w in ["صوت رجل", "بصوت رجل", "صوت ذكوري", "بصوت ذكوري", "صوت فخم", "صوت وقور", "charon", "male voice"]):
        requested_voice = "ar-XA-Standard-B"
    elif any(w in raw_lower for w in ["صوت هادئ", "أنثى هادئة", "صوت أنثوي هادئ", "kore"]):
        requested_voice = "ar-XA-Standard-D"
    elif any(w in raw_lower for w in ["صوت امرأة", "بصوت امرأة", "صوت أنثوي", "بصوت أنثوي", "صوت بنت", "صوت فتاة", "aoede", "female voice"]):
        requested_voice = "ar-XA-Standard-A"

    # Video orientation directive detection
    orientation_requested: Optional[str] = None
    if any(w in raw_lower for w in ["عمودي", "طولي", "ريلز", "تيك توك", "ستوري", "9:16", "portrait", "vertical"]):
        orientation_requested = "portrait"
    elif any(w in raw_lower for w in ["أفقي", "افقي", "عرضي", "يوتيوب", "16:9", "landscape", "horizontal"]):
        orientation_requested = "landscape"
    elif any(w in raw_lower for w in ["مربع", "1:1", "square"]):
        orientation_requested = "square"

    # Overlay positioning
    if any(w in raw_lower for w in ["في الوسط", "في منتصف الفيديو", "منتصف", "center"]):
        overlay_position = "center"
    elif any(w in raw_lower for w in ["في الأعلى", "أعلى الفيديو", "top"]):
        overlay_position = "top_banner"
    else:
        overlay_position = "bottom_banner"

    return {
        "is_meta_prompt": is_meta,
        "phone_number": phone,
        "bottom_text": bottom_text,
        "darja_requested": darja_requested,
        "voiceover_requested": voiceover_requested,
        "persistent_overlay": persistent_overlay,
        "subtitles_requested": subtitles_requested,
        "highlights_requested": highlights_requested,
        "requested_voice": requested_voice,
        "orientation_requested": orientation_requested,
        "montage_plan": montage_plan,
        "music_directives": music_directives,
        "music": music_directives,
        "property_features": property_features,
        "large_font": large_font,
        "overlay_position": overlay_position,
        "raw_text": raw,
    }


def sanitize_script_against_meta_prompts(
    script: Optional[str],
    fallback_hint: Optional[str] = None
) -> str:
    """
    Ensure the synthesized script does not leak user instructions, meta-prompts,
    or LLM labeling prefixes (e.g. 'السيناريو:', 'التعليق الصوتي:').
    If the script itself is a meta-prompt, returns a clean marketing narration in Algerian Darja
    tailored to the customer's topic or default presentation.
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
        try:
            from web.vision_analyzer import _extract_clean_user_topic, _is_real_estate_context
            topic = _extract_clean_user_topic(fallback_hint or clean)
            if topic and not _is_real_estate_context(fallback_hint or clean):
                return f"شوفو معايا {topic} بجودة استثنائية وتفاصيل متقنة تلبي كل تطلعاتكم، تواصلوا معنا الآن للحجز والاستفسار."
        except Exception:
            pass
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


MUSIC_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}


def _build_music_catalog() -> Dict[str, Dict[str, Any]]:
    """Combine curated built-in tracks with any extra audio files placed in assets/music/."""
    catalog: Dict[str, Dict[str, Any]] = {}
    for mid, meta in MUSIC_LIBRARY.items():
        file_path = Path(meta["file"])
        entry = dict(meta)
        entry["filename"] = file_path.name
        entry["audio_url"] = f"/api/music-tracks/{mid}/audio"
        catalog[mid] = entry

    music_dir = REPO_ROOT / "assets" / "music"
    if music_dir.is_dir():
        for audio_file in sorted(music_dir.iterdir(), key=lambda p: p.name.lower()):
            if not audio_file.is_file() or audio_file.suffix.lower() not in MUSIC_AUDIO_EXTENSIONS:
                continue
            track_id = audio_file.stem
            if track_id in catalog:
                continue
            pretty_title = track_id.replace("_", " ").replace("-", " ").strip().title() or audio_file.name
            catalog[track_id] = {
                "id": track_id,
                "title": pretty_title,
                "title_ar": f"مقطوعة محلية: {pretty_title}",
                "style": "Local track (assets/music)",
                "license": "Local Asset",
                "file": audio_file,
                "filename": audio_file.name,
                "audio_url": f"/api/music-tracks/{track_id}/audio",
            }
    return catalog


def resolve_music_track(
    track_id: Optional[str],
    fallback_id: str = "luxury_piano",
    strict: bool = False,
) -> Optional[Dict[str, Any]]:
    """Resolve a track ID or filename against the built-in library and assets/music/ files."""
    catalog = _build_music_catalog()
    key = str(track_id or "").strip()
    if key:
        if key in catalog:
            return catalog[key]
        key_lower = key.lower()
        for cid, entry in catalog.items():
            if cid.lower() == key_lower or str(entry.get("filename", "")).lower() == key_lower:
                return entry
    if strict:
        return None
    return catalog.get(fallback_id) or next(iter(catalog.values()), MUSIC_LIBRARY["luxury_piano"])


def get_music_tracks_list() -> List[Dict[str, str]]:
    """Return catalog of available background music tracks (built-in + assets/music)."""
    tracks = []
    for m in _build_music_catalog().values():
        tracks.append({
            "id": m["id"],
            "title": m["title"],
            "title_ar": m["title_ar"],
            "style": m["style"],
            "license": m["license"],
            "filename": m.get("filename", Path(m["file"]).name),
            "audio_url": m.get("audio_url", f"/api/music-tracks/{m['id']}/audio"),
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
    voice: str = "ar-XA-Standard-A",
    emotional_tone: Optional[str] = None,
) -> float:
    """
    Generate harmonic formant-based voiceover audio when external TTS is unavailable.
    Produces spoken-word syllabic envelope with persona-specific fundamental frequency (F0),
    formant resonance, emotional cadence, and natural pacing.

    Args:
        text: Script text.
        output_path: Destination WAV file path.
        sample_rate: Output audio sample rate in Hz.
        voice: Voice profile identifier or Gemini persona name.
        emotional_tone: Optional emotional tone descriptor for cadence/pitch modulation.

    Returns:
        Duration of generated audio in seconds.
    """
    out_file = Path(output_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)

    words = [w for w in text.strip().split() if w]
    word_count = max(1, len(words))

    _, persona = resolve_voice_profile(voice)
    persona_l = persona.lower()

    # Persona-specific acoustic profiles (F0 Hz, Formant tuples, words-per-second rate)
    persona_acoustics = {
        "aoede": (212.0, [(780.0, 0.45), (1950.0, 0.35), (2850.0, 0.20)], 2.30),
        "charon": (122.0, [(580.0, 0.48), (1520.0, 0.34), (2420.0, 0.18)], 2.18),
        "fenrir": (152.0, [(660.0, 0.44), (1740.0, 0.36), (2650.0, 0.22)], 2.52),
        "kore": (228.0, [(820.0, 0.46), (2050.0, 0.33), (2950.0, 0.21)], 2.15),
    }
    f0_base, formants, wps_rate = persona_acoustics.get(
        persona_l,
        (140.0, [(650.0, 0.45), (1700.0, 0.35), (2600.0, 0.20)], 2.30),
    )

    # Emotional tone modulation
    tone_str = str(emotional_tone or "").lower()
    syllable_freq = 3.8
    if any(k in tone_str for k in ["متحمس", "حيوي", "سريع", "enthusiastic", "energetic"]):
        f0_base *= 1.06
        wps_rate *= 1.08
        syllable_freq = 4.3
    elif any(k in tone_str for k in ["هادئ", "تأمل", "سكينة", "calm", "relaxed"]):
        f0_base *= 0.96
        wps_rate *= 0.94
        syllable_freq = 3.3

    # Subtle deterministic text-prosody offset so different scripts produce distinct acoustic contours
    text_seed = sum((idx + 1) * ord(ch) for idx, ch in enumerate(text[:120])) % 97
    f0_base += (text_seed % 11) - 5.0
    phase_offset = (text_seed % 31) * 0.1

    # Syllabic acoustic timing
    duration = max(3.5, round(word_count / wps_rate, 2))
    num_samples = int(duration * sample_rate)

    audio_samples = []
    for i in range(num_samples):
        t = i / sample_rate
        syllable_env = 0.55 + 0.45 * math.sin(2.0 * math.pi * syllable_freq * t + phase_offset)
        breath_pause = 0.2 + 0.8 * abs(math.sin(2.0 * math.pi * 0.45 * t + phase_offset * 0.5))
        mod_env = syllable_env * breath_pause

        sample_val = 0.0
        pitch_drift = 1.0 + 0.04 * math.sin(2.0 * math.pi * 0.6 * t + phase_offset)
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


def _split_tts_chunks(text: str, max_words_per_chunk: int = 95) -> List[str]:
    """Split long narration scripts at natural sentence pauses for reliable TTS calls."""
    clean = " ".join(str(text or "").split())
    words = clean.split()
    if len(words) <= max_words_per_chunk:
        return [clean] if clean else []

    sentences = [s.strip() for s in re.split(r"(?<=[.!?؟،;])\s+", clean) if s.strip()]
    chunks: List[str] = []
    cur_words: List[str] = []
    for sent in sentences:
        s_words = sent.split()
        if cur_words and len(cur_words) + len(s_words) > max_words_per_chunk:
            chunks.append(" ".join(cur_words))
            cur_words = list(s_words)
        else:
            cur_words.extend(s_words)
        while len(cur_words) > max_words_per_chunk:
            chunks.append(" ".join(cur_words[:max_words_per_chunk]))
            cur_words = cur_words[max_words_per_chunk:]
    if cur_words:
        chunks.append(" ".join(cur_words))
    return chunks or [clean]


def _concatenate_wav_files(chunk_paths: List[Path], output_path: Path, gap_sec: float = 0.16) -> None:
    """Concatenate PCM WAV narration chunks with brief natural pauses."""
    if not chunk_paths:
        raise ValueError("No WAV chunks provided to concatenate.")
    with wave.open(str(chunk_paths[0]), "rb") as first:
        params = first.getparams()
        silence = b"\x00" * (int(params.framerate * gap_sec) * params.nchannels * params.sampwidth)

    with wave.open(str(output_path), "wb") as out_w:
        out_w.setparams(params)
        for idx, cp in enumerate(chunk_paths):
            with wave.open(str(cp), "rb") as in_w:
                if idx > 0 and gap_sec > 0:
                    out_w.writeframes(silence)
                out_w.writeframes(in_w.readframes(in_w.getnframes()))


_NATURAL_CUE_PATTERNS = (
    (re.compile(r"\[(?:short[\s_-]*)?pause\]|\((?:short[\s_-]*)?pause\)", re.IGNORECASE), "<short pause>"),
    (re.compile(r"\[breath\]|\(breath\)", re.IGNORECASE), "<breath>"),
    (re.compile(r"\[sigh\]|\(sigh\)", re.IGNORECASE), "<sigh>"),
    (re.compile(r"\[laugh\]|\(laugh\)", re.IGNORECASE), "<laugh>"),
)
_GENERIC_TIMELINE_TITLE_RE = re.compile(
    r"^(?:Scene\s+\d+|لقطة\s+مختارة|لقطة\s+عالية\s+الوضوح|اللقطة\s+\d+|لقطة\s+\d+|المشهد\s+\d+)",
    re.IGNORECASE,
)


def _soften_theatrical_punctuation(text: str) -> str:
    """Dampen excessive exclamation/ellipsis marks so Gemini TTS does not over-act."""
    cleaned = re.sub(r"[!]{2,}", ".", text)
    cleaned = re.sub(r"[؟?]{2,}", "؟", cleaned)
    cleaned = re.sub(r"\.{3,}|…+", "،", cleaned)
    # Replace excited trailing exclamation marks with a calm period unless question
    cleaned = re.sub(r"!", ".", cleaned)
    return re.sub(r"\s+([.،؟])", r"\1", cleaned).strip()


def _pick_semantic_scene_title(*candidates: Any, fallback: str) -> str:
    """Return the first non-generic Arabic scene/room name, stripping bracketed timestamps."""
    first_non_empty = ""
    for cand in candidates:
        raw = re.sub(r"\s*\[[^\]]*\d+\.\d+s\s*-\s*\d+\.\d+s[^\]]*\]\s*$", "", str(cand or "").strip()).strip(" -:")
        if not raw:
            continue
        if not first_non_empty:
            first_non_empty = raw
        if not _GENERIC_TIMELINE_TITLE_RE.match(raw):
            return raw
    return first_non_empty or fallback


def format_natural_speech_text(
    text: str,
    *,
    scene_index: int = 0,
    total_scenes: int = 1,
) -> str:
    """Keep speech script clean, calm, and naturally paced with subtle <short pause> cues when helpful."""
    normalized = " ".join(str(text or "").split()).strip()
    if not normalized:
        return ""
    for pattern, tag in _NATURAL_CUE_PATTERNS:
        normalized = pattern.sub(tag, normalized)
    normalized = _soften_theatrical_punctuation(normalized)
    if re.search(r"<(?:breath|short\s+pause|sigh|gasp|laugh|chuckle|cough|whisper)>", normalized, re.IGNORECASE):
        return normalized

    words = normalized.split()
    if len(words) < 9:
        return normalized

    # Multi-sentence input: add one calm, subtle <short pause> instead of a dramatic breath
    sentences = [s.strip() for s in re.split(r"(?<=[.!؟?])\s+", normalized) if s.strip()]
    if len(sentences) >= 2:
        if len(sentences) == 2:
            return f"{sentences[0]} <short pause> {sentences[1]}"
        return f"{sentences[0]} <short pause> " + " ".join(sentences[1:])

    # Long single run (>= 12 words): place at most one gentle <short pause> on a comma
    if len(words) < 12:
        return normalized
    start_idx = max(4, len(words) // 3)
    end_idx = min(len(words) - 3, (2 * len(words)) // 3)
    for idx in range(start_idx, end_idx + 1):
        if words[idx - 1].endswith(("،", ",")):
            return " ".join([*words[:idx], "<short pause>", *words[idx:]]).strip()
    return normalized


def build_scene_delivery_style(
    base_style: Optional[str] = None,
    *,
    emotional_tone: Optional[str] = None,
    scene_index: int = 0,
    total_scenes: int = 1,
    slot_text: str = "",
    slot_budget_sec: Optional[float] = None,
) -> str:
    """Build grounded, anti-theatrical vocal style metadata synchronized to each visual cut."""
    clean_text = strip_tts_vocal_tags(slot_text)
    segments: List[str] = []
    if base_style and base_style.strip():
        segments.append(base_style.strip())

    # Avoid duplicating delivery directives when synthesize_narration calls this idempotently
    already_styled = bool(base_style and any(tok in base_style for tok in (
        "أداء هادئ وطبيعي", "افتتاحية هادئة", "خاتمة هادئة", "سرد واقعي هادئ", "نبرة حيوية صادقة",
    )))
    wants_hype = any(tok in str(emotional_tone or "") for tok in ("متحمس", "حماسي", "مشوق", "مثير", "عالي الطاقة"))
    if not already_styled:
        if wants_hype and scene_index == 0:
            arc_hint = "نبرة حيوية صادقة ومباشرة بدون صراخ أو تصنع مسرحي"
        elif total_scenes <= 1:
            arc_hint = "أداء هادئ وطبيعي بنبرة إنسان يتحدث بعفوية وصدق، بدون مبالغة مسرحية أو تصنع"
        elif scene_index == 0:
            arc_hint = "افتتاحية هادئة وطبيعية بدون تكلف أو ارتفاع مبالغ في الصوت"
        elif scene_index >= total_scenes - 1:
            arc_hint = "خاتمة هادئة ومريحة بنبرة واضحة وبسيطة بدون تشديد مسرحي"
        else:
            arc_hint = "سرد واقعي هادئ ومتزن بكلام بسيط وقريب من المستمع"
        segments.append(arc_hint)

    word_count = len(clean_text.split())
    if slot_budget_sec and slot_budget_sec > 0 and word_count > 0:
        wps = word_count / float(slot_budget_sec)
        if wps > 2.35 and "إيقاع متماسك" not in (base_style or ""):
            segments.append("إيقاع متماسك وواضح ينتهي قبل تغير اللقطة مباشرة")
        elif wps < 1.25 and word_count >= 3 and "إيقاع مريح" not in (base_style or ""):
            segments.append("إيقاع مريح وهادئ مع فواصل طبيعية خفيفة")

    return ". ".join(s.rstrip(".") for s in segments if s).strip()


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
    Supports emotional tone steering, acoustic style prompt modulation, and automatic
    chunking for long scripts (up to 4-minute videos).
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
    natural_script = format_natural_speech_text(script_text) or script_text
    effective_style_prompt = build_scene_delivery_style(
        style_prompt,
        emotional_tone=emotional_tone,
        scene_index=0,
        total_scenes=1,
        slot_text=script_text,
    )

    if has_api_key:
        try:
            from tts.gemini_speech.client import GeminiSpeechClient
            logger.info(
                "Synthesizing speech via GeminiSpeechClient (Profile: %s -> Persona: %s, tone: %s, style: %s)...",
                resolved_voice_id,
                gemini_voice,
                emotional_tone,
                effective_style_prompt,
            )
            client = GeminiSpeechClient()
            chunks = _split_tts_chunks(natural_script, max_words_per_chunk=95)
            if len(chunks) <= 1:
                client.generate_speech(
                    text=natural_script,
                    voice_name=gemini_voice,
                    output_path=str(out_file),
                    style_prompt=effective_style_prompt,
                    emotional_tone=emotional_tone,
                )
            else:
                logger.info("Long narration split into %d chunks for reliable TTS synthesis.", len(chunks))
                chunk_files: List[Path] = []
                try:
                    for c_idx, chunk_text in enumerate(chunks):
                        chunk_wav = out_file.parent / f"{out_file.stem}_chunk_{c_idx}.wav"
                        client.generate_speech(
                            text=chunk_text,
                            voice_name=gemini_voice,
                            output_path=str(chunk_wav),
                            style_prompt=effective_style_prompt,
                            emotional_tone=emotional_tone,
                        )
                        if not chunk_wav.is_file() or chunk_wav.stat().st_size == 0:
                            raise RuntimeError(f"Empty WAV chunk {c_idx}")
                        chunk_files.append(chunk_wav)
                    _concatenate_wav_files(chunk_files, out_file)
                finally:
                    for cf in chunk_files:
                        cf.unlink(missing_ok=True)

            if out_file.is_file() and out_file.stat().st_size > 0:
                synthesizer_engine = "gemini_tts"
                success = True
                logger.info("Gemini TTS synthesis completed: %s (%d bytes)", out_file, out_file.stat().st_size)
        except Exception as exc:
            logger.warning("GeminiSpeechClient failed or unreachable (%s). Using synthetic fallback.", exc)
            success = False

    if not success:
        logger.info("Generating synthetic voiceover narration fallback at %s (voice=%s)...", out_file, resolved_voice_id)
        generate_synthetic_voice(
            script_text,
            out_file,
            voice=resolved_voice_id,
            emotional_tone=emotional_tone,
        )
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


def _trim_wav_silence(wav_path: Path, rms_threshold: int = 180, pad_sec: float = 0.05) -> float:
    """
    Strip leading and trailing dead silence from a PCM WAV file in pure Python,
    preserving brief ``pad_sec`` margins so consonants never clip.
    Returns updated WAV duration in seconds.
    """
    if not wav_path.is_file() or wav_path.stat().st_size <= 44:
        return get_media_duration(wav_path)
    try:
        with wave.open(str(wav_path), "rb") as w_in:
            n_channels = w_in.getnchannels()
            sampwidth = w_in.getsampwidth()
            framerate = w_in.getframerate()
            n_frames = w_in.getnframes()
            if sampwidth != 2 or n_frames <= 0 or framerate <= 0:
                return round(n_frames / max(1, framerate), 3)
            raw = w_in.readframes(n_frames)
            params = w_in.getparams()

        samples = struct.unpack(f"<{len(raw) // 2}h", raw)
        step = max(1, n_channels)
        win_frames = max(1, int(framerate * 0.02))
        win_stride = win_frames * step
        total_samples = len(samples)

        first_active = None
        last_active = None
        for idx in range(0, total_samples, win_stride):
            chunk = samples[idx : idx + win_stride]
            if not chunk:
                continue
            mean_sq = sum(s * s for s in chunk) / len(chunk)
            if math.sqrt(mean_sq) >= rms_threshold:
                if first_active is None:
                    first_active = idx
                last_active = idx + len(chunk)

        if first_active is None or last_active is None:
            return round(n_frames / float(framerate), 3)

        pad_samples = int(framerate * pad_sec) * step
        cut_start = max(0, first_active - pad_samples)
        cut_end = min(total_samples, last_active + pad_samples)
        if cut_start <= win_stride and (total_samples - cut_end) <= win_stride:
            return round(n_frames / float(framerate), 3)

        trimmed_bytes = raw[cut_start * 2 : cut_end * 2]
        if not trimmed_bytes:
            return round(n_frames / float(framerate), 3)

        tmp_wav = wav_path.with_name(f"{wav_path.stem}_trimtmp.wav")
        with wave.open(str(tmp_wav), "wb") as w_out:
            w_out.setparams(params)
            w_out.writeframes(trimmed_bytes)
        tmp_wav.replace(wav_path)
        return round((cut_end - cut_start) / float(step * framerate), 3)
    except Exception:
        return get_media_duration(wav_path)


def _build_atempo_chain(tempo: float) -> str:
    """Build a valid FFmpeg pitch-preserving ``atempo`` filter chain for any speed >= 0.5."""
    t = max(0.5, float(tempo))
    parts: List[str] = []
    while t > 1.95:
        parts.append("atempo=1.9500")
        t /= 1.95
    parts.append(f"atempo={t:.4f}")
    return ",".join(parts)


def _fit_audio_tempo(
    wav_path: Path,
    max_duration: float,
    max_tempo: float = 1.55,
    min_duration: float = 0.0,
    min_tempo: float = 0.88,
) -> float:
    """
    Adjust WAV playback speed cleanly via FFmpeg ``atempo`` (without changing pitch):
    compresses when audio exceeds ``max_duration``, and gently relaxes down to ``min_tempo``
    when ``min_duration > 0`` and audio finishes noticeably early, eliminating dead air.
    """
    cur_dur = get_media_duration(wav_path)
    if cur_dur <= 0.0 or max_duration <= 0.4:
        return cur_dur

    eff_tempo = 1.0
    if cur_dur > max_duration * 1.01:
        desired_tempo = cur_dur / float(max_duration)
        eff_tempo = min(float(max_tempo), max(1.01, desired_tempo))
    elif min_duration > 0.4 and cur_dur < min_duration * 0.94:
        target_dur = min(float(max_duration) * 0.96, float(min_duration))
        if target_dur > cur_dur * 1.04:
            desired_tempo = cur_dur / target_dur
            eff_tempo = max(float(min_tempo), min(0.98, desired_tempo))

    if 0.985 <= eff_tempo <= 1.01:
        return cur_dur

    ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
    tmp_wav = wav_path.with_name(f"{wav_path.stem}_fit.wav")
    cmd = [
        ffmpeg_bin, "-y",
        "-i", str(wav_path),
        "-filter:a", _build_atempo_chain(eff_tempo),
        "-c:a", "pcm_s16le",
        str(tmp_wav),
    ]
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=45)
        if tmp_wav.is_file() and tmp_wav.stat().st_size > 44:
            tmp_wav.replace(wav_path)
            new_dur = get_media_duration(wav_path)
            logger.info("Fitted narration WAV via atempo=%.3f (%.2fs -> %.2fs)", eff_tempo, cur_dur, new_dur)
            return new_dur or round(cur_dur / eff_tempo, 3)
    except Exception as exc:
        logger.warning("Audio tempo fitting failed (%s); keeping original WAV.", exc)
    finally:
        tmp_wav.unlink(missing_ok=True)
    return cur_dur


def synthesize_scene_aligned_narration(
    scene_segments: List[Dict[str, Any]],
    output_path: Union[str, Path],
    voice: str = "ar-XA-Standard-A",
    style_prompt: Optional[str] = None,
    emotional_tone: Optional[str] = None,
    visual_lead_in: float = 1.2,
) -> Dict[str, Any]:
    """
    Synthesize each visual scene's spoken sentence separately (in parallel) and place it
    onto its exact visual window ``[start_sec, end_sec]``, fitting per-scene speed cleanly
    so cumulative drift cannot push later callouts out of sync.
    """
    from concurrent.futures import ThreadPoolExecutor

    out_file = Path(output_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)

    valid_slots: List[Dict[str, Any]] = []
    for item in scene_segments:
        raw_line = " ".join(str(item.get("text") or item.get("narration_line") or "").split()).strip()
        clean_line = strip_tts_vocal_tags(raw_line)
        if not raw_line or not clean_line:
            continue
        try:
            st = max(0.0, float(item.get("start_sec", 0.0)))
            en = max(st + 0.8, float(item.get("end_sec", st + 2.5)))
        except (TypeError, ValueError):
            continue
        clean_title = _pick_semantic_scene_title(
            item.get("title"),
            item.get("room_or_subject"),
            fallback="",
        )
        valid_slots.append({"start_sec": st, "end_sec": en, "title": clean_title, "text": raw_line, "clean_text": clean_line})

    combined_script = " ".join(s["clean_text"] for s in valid_slots)
    has_api_key = bool(os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEYS"))
    if len(valid_slots) < 2 or not has_api_key:
        return synthesize_narration(
            script_text=" ".join(s["text"] for s in valid_slots) or combined_script,
            output_path=out_file,
            voice=voice,
            style_prompt=style_prompt,
            emotional_tone=emotional_tone,
        )

    chunk_paths: List[Path] = [out_file.parent / f"{out_file.stem}_scene_{idx}.wav" for idx in range(len(valid_slots))]
    scene_results: Dict[int, Dict[str, Any]] = {}
    total_slots = len(valid_slots)
    base_lead = max(0.0, float(visual_lead_in))

    def _synth_one(idx: int) -> Dict[str, Any]:
        slot = valid_slots[idx]
        c_path = chunk_paths[idx]
        slot_start = slot["start_sec"]
        slot_end = slot["end_sec"]
        eff_start = max(base_lead, slot_start) if (idx == 0 and slot_start < base_lead) else (slot_start if idx == 0 else slot_start + 0.04)
        end_guard = 0.14 if idx < total_slots - 1 else 0.06
        slot_budget = max(0.55, (slot_end - end_guard) - eff_start)
        spoken_text = format_natural_speech_text(
            slot["text"],
            scene_index=idx,
            total_scenes=total_slots,
        )
        scene_style = build_scene_delivery_style(
            style_prompt,
            emotional_tone=emotional_tone,
            scene_index=idx,
            total_scenes=total_slots,
            slot_text=slot["text"],
            slot_budget_sec=slot_budget,
        )
        res = synthesize_narration(
            script_text=spoken_text,
            output_path=c_path,
            voice=voice,
            style_prompt=scene_style,
            emotional_tone=emotional_tone,
        )
        _trim_wav_silence(c_path)
        fitted_dur = _fit_audio_tempo(
            c_path,
            max_duration=slot_budget,
            max_tempo=1.72,
            min_duration=slot_budget * 0.60,
            min_tempo=0.95,
        )
        res["duration"] = fitted_dur
        return res

    try:
        with ThreadPoolExecutor(max_workers=min(3, len(valid_slots))) as pool:
            futs = {pool.submit(_synth_one, idx): idx for idx in range(len(valid_slots))}
            for fut, idx in futs.items():
                scene_results[idx] = fut.result()

        # Verify uniform PCM WAV parameters and stitch at exact visual start offsets
        with wave.open(str(chunk_paths[0]), "rb") as w0:
            params = w0.getparams()
        if params.sampwidth != 2 or params.framerate <= 0:
            raise ValueError("Unsupported WAV format for scene alignment.")

        base_offset = max(0.0, float(visual_lead_in))
        cursor_sec = 0.0
        scene_timings: List[Dict[str, Any]] = []
        bytes_per_sec = params.framerate * params.nchannels * params.sampwidth

        with wave.open(str(out_file), "wb") as out_w:
            out_w.setparams(params)
            for idx, slot in enumerate(valid_slots):
                c_path = chunk_paths[idx]
                with wave.open(str(c_path), "rb") as w_chunk:
                    if (w_chunk.getframerate(), w_chunk.getnchannels(), w_chunk.getsampwidth()) != (
                        params.framerate,
                        params.nchannels,
                        params.sampwidth,
                    ):
                        # Resample/normalize to base params via FFmpeg if mismatched
                        raise ValueError("Mismatched WAV stream params across scene chunks.")
                    raw_frames = w_chunk.readframes(w_chunk.getnframes())
                    c_dur = w_chunk.getnframes() / float(params.framerate)

                # Lock Scene 1 cleanly and cue each subsequent cut +0.04s after its visual transition
                # so room dialogue never leaks prematurely or carries over into the next space.
                desired_abs = base_offset if (idx == 0 and slot["start_sec"] < base_offset) else (slot["start_sec"] if idx == 0 else slot["start_sec"] + 0.04)
                target_rel = max(0.0, desired_abs - base_offset) if idx == 0 else max(cursor_sec + 0.04, desired_abs - base_offset)
                gap_sec = max(0.0, target_rel - cursor_sec)
                if gap_sec >= 0.02:
                    gap_frames = int(round(gap_sec * params.framerate))
                    out_w.writeframes(b"\x00" * (gap_frames * params.nchannels * params.sampwidth))
                    cursor_sec += gap_frames / float(params.framerate)

                out_w.writeframes(raw_frames)
                actual_start = round(base_offset + cursor_sec, 2)
                cursor_sec += c_dur
                actual_end = round(base_offset + cursor_sec, 2)
                timing_entry: Dict[str, Any] = {
                    "segment_index": idx + 1,
                    "start_sec": actual_start,
                    "end_sec": actual_end,
                    "text": slot["clean_text"],
                    "scene_index": idx + 1,
                }
                if slot.get("title"):
                    timing_entry["title"] = slot["title"]
                scene_timings.append(timing_entry)

        total_dur = get_media_duration(out_file)
        first_meta = scene_results.get(0, {})
        return {
            "audio_path": str(out_file),
            "duration": total_dur,
            "synthesizer": first_meta.get("synthesizer", "gemini_tts"),
            "voice": first_meta.get("voice"),
            "gemini_voice": first_meta.get("gemini_voice"),
            "requested_voice": voice,
            "script": combined_script,
            "emotional_tone": emotional_tone,
            "style_prompt": style_prompt,
            "scene_timings": scene_timings,
        }
    except Exception as exc:
        logger.warning("Scene-aligned parallel synthesis fell back to single-track TTS (%s).", exc)
        return synthesize_narration(
            script_text=combined_script,
            output_path=out_file,
            voice=voice,
            style_prompt=style_prompt,
            emotional_tone=emotional_tone,
        )
    finally:
        for cp in chunk_paths:
            cp.unlink(missing_ok=True)


def _compute_timeline_fit(
    narration_wav: Path,
    initial_narration_dur: float,
    src_duration: float,
    visual_lead_in: float,
    outro_buffer: float,
) -> Dict[str, float]:
    """Trim silence, fit overflowing audio with pitch-safe tempo, and cap last-frame freeze."""
    lead_in = max(0.0, float(visual_lead_in if visual_lead_in is not None else 1.2))
    outro = max(0.5, float(outro_buffer if outro_buffer is not None else 1.2))
    trimmed_dur = _trim_wav_silence(narration_wav) if narration_wav.is_file() else 0.0
    narration_duration = trimmed_dur if trimmed_dur > 0 else float(initial_narration_dur or 0.0)

    eff_outro = outro
    if src_duration >= 4.0 and narration_duration > 0.0 and (lead_in + narration_duration > src_duration + 0.5):
        eff_outro = min(outro, 0.25)
        max_speech_win = max(2.0, src_duration - lead_in - eff_outro)
        narration_duration = _fit_audio_tempo(narration_wav, max_duration=max_speech_win, max_tempo=1.55)
        if (lead_in + narration_duration > src_duration + 0.3) and lead_in > 0.25:
            lead_in = round(max(0.25, src_duration - narration_duration - eff_outro), 2)

    max_end_freeze_sec = 0.8
    min_required_duration = round(lead_in + narration_duration + eff_outro, 2)
    if src_duration >= 4.0:
        raw_pad = max(0.0, round(min_required_duration - src_duration, 2))
        pad_needed = min(max_end_freeze_sec, raw_pad)
        total_duration = round(src_duration + pad_needed, 2)
    else:
        total_duration = max(round(src_duration, 2), min_required_duration)
        pad_needed = max(0.0, round(total_duration - src_duration, 2))
    total_duration = max(5.0, total_duration)
    fade_out_start = max(0.5, round(total_duration - 1.8, 2))

    return {
        "narration_duration": narration_duration,
        "visual_lead_in": lead_in,
        "eff_outro": eff_outro,
        "total_duration": total_duration,
        "pad_needed": pad_needed,
        "fade_out_start": fade_out_start,
    }


def _render_mixed_cut(
    *,
    input_path: Path,
    narration_wav: Path,
    output_path: Path,
    target_w: int,
    target_h: int,
    total_duration: float,
    pad_needed: float,
    fade_out_start: float,
    visual_lead_in: float,
    mute_music: bool,
    music_audio_file: Path,
    duck_threshold: float,
    duck_ratio: float,
    duck_attack: int,
    duck_release: int,
    ambient_volume: float,
) -> float:
    """Mux visual track with narration WAV and optional ducked music via FFmpeg."""
    visual_lead_in_ms = int(round(max(0.0, float(visual_lead_in)) * 1000))
    narration_delay = f"adelay={visual_lead_in_ms}|{visual_lead_in_ms}," if visual_lead_in_ms > 0 else ""

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

    ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if mute_music:
        filter_complex = f"""
        [0:v]{v_graph};
        [1:a]aformat=sample_rates=48000:channel_layouts=stereo,{narration_delay}apad=whole_dur={total_duration},volume=1.0[aout]
        """
        ffmpeg_cmd = [
            ffmpeg_bin, "-y",
            "-i", str(input_path),
            "-i", str(narration_wav),
            "-filter_complex", filter_complex,
            "-map", "[vout]",
            "-map", "[aout]",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "23",
            "-threads", "0",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-t", str(total_duration),
            str(output_path),
        ]
    elif music_audio_file.is_file():
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
            "-preset", "ultrafast",
            "-crf", "23",
            "-threads", "0",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-t", str(total_duration),
            str(output_path),
        ]
    else:
        filter_complex = f"""
        [0:v]{v_graph};
        sine=f=146.83:d={total_duration},volume=0.14[d3];
        sine=f=174.61:d={total_duration},volume=0.12[f3];
        sine=f=220.00:d={total_duration},volume=0.10[a3];
        sine=f=261.63:d={total_duration},volume=0.08[c4];
        anoisesrc=d={total_duration}:c=pink:r=48000:a=0.003,lowpass=f=900[warm_air];
        [d3][f3][a3][c4][warm_air]amix=inputs=5:normalize=0,lowpass=f=2000,afade=t=in:ss=0:d=1.5,afade=t=out:st={fade_out_start}:d=1.8,aformat=sample_rates=48000:channel_layouts=stereo[music];
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
            "-preset", "ultrafast",
            "-crf", "22",
            "-threads", "0",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-t", str(total_duration),
            str(output_path),
        ]

    start_render = datetime.now(timezone.utc)
    try:
        subprocess.run(ffmpeg_cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        logger.error("FFmpeg render failed: %s", e.stderr)
        raise RuntimeError(f"FFmpeg assembly failed: {e.stderr.strip()}") from e
    return (datetime.now(timezone.utc) - start_render).total_seconds()


def _apply_subtitles_and_annotations(
    *,
    final_cut_path: Path,
    job_id: str,
    job_sandbox_dir: Path,
    total_duration: float,
    target_w: int,
    target_h: int,
    subtitles_opt_in: bool,
    narration_info: Dict[str, Any],
    selected_script: str,
    narration_duration: float,
    visual_lead_in: float,
    shot_timeline_data: List[Dict[str, Any]],
    caption_options: Optional[Dict[str, Any]],
    base_annotations: List[Dict[str, Any]],
    fallback_subtitles: Optional[List[Dict[str, Any]]] = None,
    notify_fn: Optional[Callable[..., None]] = None,
) -> tuple[List[Dict[str, Any]], Optional[Dict[str, Any]], int]:
    """Build synced subtitles + CapCut ASS caption track and burn overlays onto ``final_cut_path``."""
    annotations_list: List[Dict[str, Any]] = [
        {**ann, "end_sec": min(total_duration, float(ann.get("end_sec", total_duration)))}
        for ann in base_annotations
    ]
    subtitles_list: List[Dict[str, Any]] = []

    if subtitles_opt_in:
        from web.vision_analyzer import generate_synchronized_subtitles
        measured_scene_timings = narration_info.get("scene_timings") if isinstance(narration_info, dict) else None
        if measured_scene_timings:
            seg_counter = 1
            for st_item in measured_scene_timings:
                s_dur = max(0.6, float(st_item["end_sec"]) - float(st_item["start_sec"]))
                chunk_subs = generate_synchronized_subtitles(
                    script=st_item["text"],
                    narration_duration=s_dur,
                    visual_lead_in=float(st_item["start_sec"]),
                )
                for cs in chunk_subs:
                    cs["segment_index"] = seg_counter
                    cs["scene_index"] = st_item.get("scene_index")
                    subtitles_list.append(cs)
                    seg_counter += 1
        else:
            subtitles_list = generate_synchronized_subtitles(
                script=selected_script,
                narration_duration=narration_duration,
                visual_lead_in=visual_lead_in,
                shot_timeline=shot_timeline_data,
            )
        if not subtitles_list and fallback_subtitles:
            subtitles_list = list(fallback_subtitles)

        for sub in subtitles_list:
            sub_txt = str(sub.get("text", "")).strip()
            if sub_txt:
                sub_st = max(0.0, float(sub.get("start_sec", visual_lead_in)))
                sub_et = min(total_duration, float(sub.get("end_sec", sub_st + 2.0)))
                if sub_et > sub_st:
                    annotations_list.append({
                        "text": sub_txt,
                        "start_sec": round(sub_st, 2),
                        "end_sec": round(sub_et, 2),
                        "position": "subtitle",
                        "style": "subtitle",
                        "safe_margin": max(185, int(target_h * 0.145)),
                        "font_size": max(30, min(42, int(target_h * 0.026))),
                    })

    caption_track_meta: Optional[Dict[str, Any]] = None
    if caption_options:
        custom_caption_text = strip_tts_vocal_tags(caption_options.get("custom_text") or "") or None
        narration_segments = subtitles_list if (not custom_caption_text and subtitles_list) else None
        if custom_caption_text or narration_segments:
            try:
                from web.caption_templates import prepare_caption_track
                caption_track_meta = prepare_caption_track(
                    job_sandbox_dir / f"captions_{job_id}.ass",
                    total_duration=total_duration,
                    video_width=target_w,
                    video_height=target_h,
                    template=caption_options.get("template"),
                    custom_text=custom_caption_text,
                    segments=narration_segments,
                    position=caption_options.get("position"),
                    size=caption_options.get("size"),
                    shot_timeline=shot_timeline_data,
                    font_path=find_system_font(),
                )
            except Exception as cap_err:
                logger.warning("Job %s: Animated caption track preparation failed: %s", job_id, cap_err)
                caption_track_meta = None
        if caption_track_meta:
            annotations_list = [a for a in annotations_list if a.get("position") != "subtitle"]
            logger.info(
                "Job %s: Animated captions ready (template=%s, chunks=%d, split=%s)",
                job_id, caption_track_meta["template"], caption_track_meta["chunks_count"], caption_track_meta["engine"],
            )
            if notify_fn:
                notify_fn(
                    step=5,
                    percent=88,
                    message="جاري تطبيق النصوص المتحركة بالقالب المختار...",
                    log=(
                        f"[نصوص متحركة] القالب: {caption_track_meta['template_name_ar']} | "
                        f"عدد المقاطع: {caption_track_meta['chunks_count']} | "
                        f"التقسيم: {'ذكاء اصطناعي' if caption_track_meta['engine'] == 'gemini' else 'تقسيم ذكي محلي' if caption_track_meta['engine'] == 'heuristic' else 'متزامن مع التعليق الصوتي'}"
                    ),
                )

    applied_annotations_count = 0
    if annotations_list or caption_track_meta:
        annotated_tmp = job_sandbox_dir / f"annotated_{job_id}.mp4"
        try:
            annot_kwargs: Dict[str, Any] = {}
            if caption_track_meta:
                annot_kwargs["ass_file"] = caption_track_meta["ass_path"]
            annot_res = annotate_video(
                input_video_path=final_cut_path,
                output_video_path=annotated_tmp,
                annotations=annotations_list,
                video_width=target_w,
                video_height=target_h,
                **annot_kwargs,
            )
            ok = isinstance(annot_res, dict) and annot_res.get("status") in ("ok", "completed")
            if not ok and caption_track_meta:
                logger.warning("Job %s: Caption burn failed: %s", job_id, str(annot_res.get("error", ""))[-800:])
                caption_track_meta["applied"] = False
            if ok and annotated_tmp.is_file() and annotated_tmp.stat().st_size > 1000:
                annotated_tmp.replace(final_cut_path)
                applied_annotations_count = len(annotations_list) + (caption_track_meta["chunks_count"] if caption_track_meta else 0)
                if caption_track_meta:
                    caption_track_meta["applied"] = True
                logger.info("Job %s: Video annotations applied successfully (%d overlays)", job_id, applied_annotations_count)
                if notify_fn:
                    notify_fn(
                        step=5,
                        percent=95,
                        message="تمت إضافة الملصقات والترجمة المتزامنة على الفيديو بنجاح.",
                        log=f"[ملصقات الفيديو] تم تطبيق {applied_annotations_count} نصوص وشارات وترجمات متزامنة على المشاهد.",
                    )
        except Exception as annot_err:
            logger.warning("Job %s: Annotation pass encountered non-fatal error: %s", job_id, annot_err)

    return subtitles_list, caption_track_meta, applied_annotations_count


def _mirror_outputs(final_cut_path: Path, narration_wav: Path, out_cuts_dir: Path, job_id: str) -> Path:
    """Copy finalized video cut and WAV narration into shared outputs and atomic legacy target."""
    if not final_cut_path.is_file() or final_cut_path.stat().st_size == 0:
        raise RuntimeError(f"Rendered video cut file was not found or is empty: {final_cut_path}")

    out_cuts_dir.mkdir(parents=True, exist_ok=True)
    mirror_cut_path = out_cuts_dir / f"cut_{job_id}.mp4"
    if str(final_cut_path.resolve()) != str(mirror_cut_path.resolve()):
        shutil.copyfile(final_cut_path, mirror_cut_path)

    mirror_narration_path = out_cuts_dir / f"narration_{job_id}.wav"
    if narration_wav.is_file() and str(narration_wav.resolve()) != str(mirror_narration_path.resolve()):
        shutil.copyfile(narration_wav, mirror_narration_path)

    try:
        legacy_dir = REPO_ROOT / "outputs"
        legacy_dir.mkdir(parents=True, exist_ok=True)
        legacy_cut_path = legacy_dir / "final_cut.mp4"
        legacy_cut_tmp = legacy_dir / f"final_cut_{job_id}.mp4.tmp"
        shutil.copyfile(final_cut_path, legacy_cut_tmp)
        legacy_cut_tmp.replace(legacy_cut_path)
    except Exception as copy_err:
        logger.warning("Job %s: Failed to copy to legacy final_cut.mp4: %s", job_id, copy_err)

    return mirror_cut_path


def _pick_closest_thumb(keyframes: List[Dict[str, Any]], mid_sec: float) -> str:
    """Return URL of the keyframe nearest to ``mid_sec``."""
    best_url = ""
    best_dist = float("inf")
    for kf in keyframes:
        u = str(kf.get("url") or kf.get("sandboxed_url") or "")
        if not u:
            continue
        try:
            d = abs(float(kf.get("timestamp", 0.0)) - mid_sec)
        except (TypeError, ValueError):
            continue
        if d < best_dist:
            best_dist = d
            best_url = u
    return best_url


def _split_script_across_slots(script_text: str, count: int) -> List[str]:
    """Split a continuous script cleanly into ``count`` balanced spoken phrases."""
    clean = " ".join(str(script_text or "").split()).strip()
    if count <= 1 or not clean:
        return [clean] if clean else []

    raw_sentences = [s.strip() for s in re.split(r"(?<=[.!؟?،,])\s+", clean) if s.strip()]
    if len(raw_sentences) == count:
        return raw_sentences

    words = clean.split()
    if not words:
        return [""] * count
    chunks: List[str] = []
    for i in range(count):
        a = int(round(i * len(words) / count))
        b = int(round((i + 1) * len(words) / count))
        chunks.append(" ".join(words[a:b]).strip())
    return [c for c in chunks if c]


def _build_editable_cuts(
    *,
    aligned_scene_plan: List[Dict[str, Any]],
    montage_details: Optional[Dict[str, Any]],
    shot_timeline_data: List[Dict[str, Any]],
    formatted_keyframes: List[Dict[str, Any]],
    selected_script: str,
    src_duration: float,
) -> List[Dict[str, Any]]:
    """Build normalized per-cut cards pairing timestamps, titles, thumbnails, and editable spoken text."""
    out_segs = (montage_details or {}).get("output_segments") or []
    cuts: List[Dict[str, Any]] = []

    if aligned_scene_plan:
        for idx, slot in enumerate(aligned_scene_plan):
            st = round(float(slot.get("start_sec", 0.0)), 2)
            en = round(max(st + 0.5, float(slot.get("end_sec", st + 2.5))), 2)
            out_title = out_segs[idx].get("title") if idx < len(out_segs) else ""
            tl_title = shot_timeline_data[idx].get("title") if idx < len(shot_timeline_data) else ""
            title = _pick_semantic_scene_title(
                slot.get("title"),
                slot.get("room_or_subject"),
                out_title,
                tl_title,
                fallback=f"المشهد {idx + 1}",
            )
            cuts.append({
                "scene_index": idx + 1,
                "start_sec": st,
                "end_sec": en,
                "title": title,
                "room_or_subject": title,
                "text": strip_tts_vocal_tags(str(slot.get("text") or "").strip()),
                "thumb": _pick_closest_thumb(formatted_keyframes, (st + en) * 0.5),
            })
        return cuts

    base_slots = out_segs or shot_timeline_data
    if base_slots:
        texts = _split_script_across_slots(selected_script, len(base_slots))
        for idx, seg in enumerate(base_slots):
            st = round(float(seg.get("start_sec", seg.get("timestamp", idx * 3.0))), 2)
            en = round(max(st + 0.5, float(seg.get("end_sec", st + 3.0))), 2)
            tl_title = shot_timeline_data[idx].get("title") if idx < len(shot_timeline_data) else ""
            title = _pick_semantic_scene_title(
                seg.get("title"),
                seg.get("room_or_subject"),
                tl_title,
                fallback=f"المشهد {idx + 1}",
            )
            cuts.append({
                "scene_index": idx + 1,
                "start_sec": st,
                "end_sec": en,
                "title": title,
                "room_or_subject": title,
                "text": texts[idx] if idx < len(texts) else str(seg.get("narration_line") or seg.get("description") or "").strip(),
                "thumb": str(seg.get("thumbnail") or "") or _pick_closest_thumb(formatted_keyframes, (st + en) * 0.5),
            })
        return cuts

    # Single-shot video: break narration into 2–3 logical phrase cards for easy word editing
    target_chunks = 3 if len(selected_script.split()) >= 18 else (2 if len(selected_script.split()) >= 10 else 1)
    phrases = _split_script_across_slots(selected_script, target_chunks) or [selected_script]
    dur = max(2.0, float(src_duration or 8.0))
    span = dur / len(phrases)
    for idx, phrase in enumerate(phrases):
        st = round(idx * span, 2)
        en = round(min(dur, (idx + 1) * span), 2)
        cuts.append({
            "scene_index": idx + 1,
            "start_sec": st,
            "end_sec": en,
            "title": f"اللقطة {idx + 1}",
            "text": phrase,
            "thumb": _pick_closest_thumb(formatted_keyframes, (st + en) * 0.5),
        })
    return cuts


def update_cuts_text_and_rerender(
    job_id: str,
    edited_cuts: Optional[List[Dict[str, Any]]] = None,
    edited_script: Optional[str] = None,
    output_dir: Union[str, Path] = "outputs/mobile_cuts",
    voice: Optional[str] = None,
    music_track: Optional[str] = None,
    enable_music: Optional[bool] = None,
    screen_overlay: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Re-synthesize edited per-cut text and re-render audio + captions directly onto an existing job's
    already-cut visual track without re-running Gemini Vision or re-cutting raw footage.
    """
    out_cuts_dir = Path(output_dir).resolve()
    job_sandbox_dir = REPO_ROOT / "outputs" / "jobs" / job_id / "sandbox"

    summary_path = next(
        (
            p for p in [
                job_sandbox_dir / f"summary_{job_id}.json",
                out_cuts_dir / f"summary_{job_id}.json",
            ]
            if p.is_file()
        ),
        None,
    )
    if summary_path is None:
        raise FileNotFoundError(f"Job summary not found for '{job_id}'.")

    with open(summary_path, "r", encoding="utf-8") as f:
        summary = json.load(f)

    cfg = dict(summary.get("render_config") or {})
    visual_candidates = [
        summary.get("clean_visual_source"),
        str(job_sandbox_dir / f"montaged_{job_id}.mp4"),
        (summary.get("metadata") or {}).get("source_video"),
    ]
    visual_source = next((Path(c) for c in visual_candidates if c and Path(c).is_file()), None)
    if visual_source is None:
        raise FileNotFoundError(f"Visual source video missing for job '{job_id}'.")

    if not job_sandbox_dir.exists():
        job_sandbox_dir.mkdir(parents=True, exist_ok=True)

    meta = frame_extractor.get_video_metadata(visual_source)
    src_duration = float(cfg.get("src_duration") or meta.get("total_duration") or summary.get("duration") or 10.0)
    target_w = int(cfg.get("target_w") or meta.get("width") or 720)
    target_h = int(cfg.get("target_h") or meta.get("height") or 1280)

    resolved_voice_id, resolved_voice_name = resolve_voice_profile(
        voice or cfg.get("voice") or summary.get("voice") or "ar-XA-Standard-A"
    )
    resolved_tone = cfg.get("emotional_tone") or summary.get("emotional_tone") or "فاخر وهادئ"
    style_prompt = cfg.get("style_prompt") or summary.get("style_prompt")
    visual_lead_in = float(cfg.get("visual_lead_in") if cfg.get("visual_lead_in") is not None else summary.get("visual_lead_in_seconds", 0.35))
    outro_buffer = float(cfg.get("outro_buffer") if cfg.get("outro_buffer") is not None else summary.get("outro_buffer_seconds", 1.2))

    # Build sanitized scene plan from edited cuts (or fallback to existing cuts / edited script)
    existing_cuts = list(summary.get("editable_cuts") or [])
    normalized_cuts: List[Dict[str, Any]] = []
    source_list = edited_cuts if (edited_cuts is not None and len(edited_cuts) > 0) else existing_cuts

    for idx, item in enumerate(source_list):
        txt = sanitize_script_against_meta_prompts(str(item.get("text") or "").strip())
        base = existing_cuts[idx] if idx < len(existing_cuts) else {}
        try:
            st = max(0.0, float(item.get("start_sec") if item.get("start_sec") is not None else base.get("start_sec", 0.0)))
            en = max(st + 0.5, float(item.get("end_sec") if item.get("end_sec") is not None else base.get("end_sec", st + 3.0)))
        except (TypeError, ValueError):
            st, en = 0.0, max(1.0, src_duration)
        title = _pick_semantic_scene_title(
            item.get("title"),
            item.get("room_or_subject"),
            base.get("title"),
            fallback=f"المشهد {idx + 1}",
        )
        thumb = str(item.get("thumb") or base.get("thumb") or "")
        normalized_cuts.append({
            "scene_index": idx + 1,
            "start_sec": round(st, 2),
            "end_sec": round(en, 2),
            "title": title,
            "room_or_subject": title,
            "text": txt,
            "thumb": thumb,
        })

    non_empty_slots = [c for c in normalized_cuts if c.get("text")]
    combined_script = sanitize_script_against_meta_prompts(
        edited_script.strip() if (edited_script and edited_script.strip() and not non_empty_slots)
        else " ".join(c["text"] for c in non_empty_slots)
    ) or str(summary.get("script") or DEFAULT_PROMO_SCRIPT)

    narration_wav = job_sandbox_dir / f"narration_{job_id}.wav"
    if len(non_empty_slots) >= 2:
        scene_lead_in = min(max(0.0, visual_lead_in), 0.12) if visual_lead_in > 0 else 0.0
        narration_info = synthesize_scene_aligned_narration(
            scene_segments=non_empty_slots,
            output_path=narration_wav,
            voice=resolved_voice_id,
            style_prompt=style_prompt,
            emotional_tone=resolved_tone,
            visual_lead_in=scene_lead_in,
        )
        visual_lead_in = scene_lead_in
        if narration_info.get("script"):
            combined_script = narration_info["script"]
    else:
        narration_info = synthesize_narration(
            script_text=combined_script,
            output_path=narration_wav,
            voice=resolved_voice_id,
            style_prompt=style_prompt,
            emotional_tone=resolved_tone,
        )

    timeline_fit = _compute_timeline_fit(
        narration_wav=narration_wav,
        initial_narration_dur=narration_info["duration"],
        src_duration=src_duration,
        visual_lead_in=visual_lead_in,
        outro_buffer=outro_buffer,
    )
    narration_duration = timeline_fit["narration_duration"]
    visual_lead_in = timeline_fit["visual_lead_in"]
    total_duration = timeline_fit["total_duration"]
    pad_needed = timeline_fit["pad_needed"]
    fade_out_start = timeline_fit["fade_out_start"]

    requested_track = (
        str(music_track).strip()
        if music_track and str(music_track).strip().lower() not in ("none", "null", "false", "")
        else None
    )
    music_key = str(requested_track or cfg.get("music_track_id") or (summary.get("music_track") or {}).get("id") or "luxury_piano")
    music_meta = resolve_music_track(music_key)
    music_key = music_meta["id"]
    if enable_music is not None:
        mute_music = not bool(enable_music)
    else:
        mute_music = bool(cfg.get("mute_music") if "mute_music" in cfg else summary.get("music_muted", True))
    ambient_volume = float(cfg.get("ambient_volume") if "ambient_volume" in cfg else summary.get("music_volume", 0.16))
    cfg["music_track_id"] = music_key
    cfg["mute_music"] = mute_music

    final_cut_path = job_sandbox_dir / f"cut_{job_id}.mp4"
    render_seconds = _render_mixed_cut(
        input_path=visual_source,
        narration_wav=narration_wav,
        output_path=final_cut_path,
        target_w=target_w,
        target_h=target_h,
        total_duration=total_duration,
        pad_needed=pad_needed,
        fade_out_start=fade_out_start,
        visual_lead_in=visual_lead_in,
        mute_music=mute_music,
        music_audio_file=music_meta["file"],
        duck_threshold=float(cfg.get("duck_threshold", 0.015)),
        duck_ratio=float(cfg.get("duck_ratio", 12.0)),
        duck_attack=int(cfg.get("duck_attack", 60)),
        duck_release=int(cfg.get("duck_release", 350)),
        ambient_volume=ambient_volume,
    )

    shot_timeline_data = list(summary.get("shot_timeline") or [])
    for idx, c in enumerate(normalized_cuts):
        if idx < len(shot_timeline_data):
            if c.get("title"):
                shot_timeline_data[idx]["title"] = c["title"]
                shot_timeline_data[idx]["room_or_subject"] = c["title"]
            if c.get("text"):
                shot_timeline_data[idx]["description"] = c["text"]
                shot_timeline_data[idx]["narration_line"] = c["text"]

    subtitles_opt_in = bool(cfg.get("subtitles_enabled") if "subtitles_enabled" in cfg else summary.get("subtitles_enabled", False))
    caption_options = cfg.get("caption_options")
    base_annotations = list(cfg.get("base_annotations") or [])
    effective_screen_overlay = (
        normalize_screen_overlay_options(screen_overlay)
        if screen_overlay is not None
        else cfg.get("screen_overlay")
    )
    if screen_overlay is not None:
        base_annotations = [a for a in base_annotations if not a.get("is_screen_overlay")]
        if effective_screen_overlay:
            base_annotations.insert(
                0,
                build_screen_overlay_annotation(
                    effective_screen_overlay,
                    total_duration=total_duration,
                    target_h=target_h,
                ),
            )
            cfg["screen_overlay"] = effective_screen_overlay
            summary["screen_overlay"] = effective_screen_overlay
            summary["bottom_text"] = effective_screen_overlay["text"]
        else:
            cfg["screen_overlay"] = None
            summary["screen_overlay"] = None
    cfg["base_annotations"] = base_annotations

    subtitles_list, caption_track_meta, applied_annotations_count = _apply_subtitles_and_annotations(
        final_cut_path=final_cut_path,
        job_id=job_id,
        job_sandbox_dir=job_sandbox_dir,
        total_duration=total_duration,
        target_w=target_w,
        target_h=target_h,
        subtitles_opt_in=subtitles_opt_in,
        narration_info=narration_info,
        selected_script=combined_script,
        narration_duration=narration_duration,
        visual_lead_in=visual_lead_in,
        shot_timeline_data=shot_timeline_data,
        caption_options=caption_options,
        base_annotations=base_annotations,
    )

    mirror_cut_path = _mirror_outputs(final_cut_path, narration_wav, out_cuts_dir, job_id)

    summary["script"] = combined_script
    summary["inferred_script"] = combined_script
    summary["editable_cuts"] = normalized_cuts
    summary["shot_timeline"] = shot_timeline_data
    summary["subtitles"] = subtitles_list
    summary["subtitles_count"] = len(subtitles_list)
    summary["animated_captions"] = caption_track_meta
    summary["annotations_applied"] = applied_annotations_count
    summary["duration"] = total_duration
    summary["end_freeze_seconds"] = pad_needed
    summary["visual_lead_in_seconds"] = visual_lead_in
    summary["voice"] = resolved_voice_id
    summary["gemini_voice"] = resolved_voice_name
    summary["file_size_bytes"] = final_cut_path.stat().st_size
    summary["output_path"] = str(mirror_cut_path)
    summary["absolute_output_path"] = str(mirror_cut_path.resolve())
    summary["music_muted"] = mute_music
    summary["music_track"] = {
        "id": music_meta["id"],
        "title": music_meta["title"],
        "license": music_meta["license"],
        "muted": mute_music,
        "volume": ambient_volume,
    }
    summary["render_config"] = cfg
    summary["updated_at"] = datetime.now(timezone.utc).isoformat()
    if isinstance(summary.get("metadata"), dict):
        summary["metadata"]["narration_duration"] = narration_duration
        summary["metadata"]["render_seconds"] = round(render_seconds, 2)
        summary["metadata"]["visual_lead_in_seconds"] = visual_lead_in
        summary["metadata"]["shot_timeline"] = shot_timeline_data
        if isinstance(summary["metadata"].get("subtitles"), dict):
            summary["metadata"]["subtitles"]["count"] = len(subtitles_list)
            summary["metadata"]["subtitles"]["items"] = subtitles_list

    for sp in {job_sandbox_dir / f"summary_{job_id}.json", out_cuts_dir / f"summary_{job_id}.json"}:
        sp.parent.mkdir(parents=True, exist_ok=True)
        with open(sp, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

    logger.info("Job %s: Re-rendered video after cut text edit cleanly in %.2fs", job_id, render_seconds)
    return summary


# ---------------------------------------------------------------------------
# Core Mobile Video Processing Engine
# ---------------------------------------------------------------------------

def _extract_formatted_keyframes(
    video_path: Path,
    duration: float,
    job_id: str,
    keyframes_dest_dir: Path,
    legacy_keyframes_dir: Path,
) -> tuple[List[Path], List[Dict[str, Any]]]:
    """Extract dense keyframes and format sandbox/legacy URL entries."""
    dense_timestamps = compute_dense_keyframe_timestamps(duration, min_count=8, max_count=16)
    keyframe_extraction = frame_extractor.extract_keyframes(
        video_path=video_path,
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
        legacy_kf_path = legacy_keyframes_dir / file_path_obj.name
        if abs_path.is_file() and not legacy_kf_path.is_file():
            try:
                shutil.copyfile(abs_path, legacy_kf_path)
            except Exception:
                pass
        web_url = f"/outputs/keyframes/mobile_{job_id}/{file_path_obj.name}"
        sandboxed_kf_url = f"/outputs/jobs/{job_id}/sandbox/keyframes/{file_path_obj.name}"
        formatted_keyframes.append({
            "frame_index": f.get("frame_index"),
            "timestamp": f.get("timestamp"),
            "url": web_url,
            "sandboxed_url": sandboxed_kf_url,
            "file_path": f.get("file_path"),
            "resolution": f.get("resolution"),
            "is_scene_transition": f.get("is_scene_transition", False),
        })
    return keyframe_files, formatted_keyframes


def normalize_screen_overlay_options(
    screen_overlay: Optional[Dict[str, Any]],
    *,
    fallback_text: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Normalize interactive persistent screen overlay text, coordinates, font, and effect."""
    if not isinstance(screen_overlay, dict):
        return None
    if screen_overlay.get("enabled") is False:
        return None
    raw_text = sanitize_and_validate_prompt(str(screen_overlay.get("text") or fallback_text or "").strip())
    if not raw_text:
        return None
    try:
        x_pct = float(screen_overlay.get("x_pct") if screen_overlay.get("x_pct") is not None else 0.5)
    except (TypeError, ValueError):
        x_pct = 0.5
    try:
        y_pct = float(screen_overlay.get("y_pct") if screen_overlay.get("y_pct") is not None else 0.84)
    except (TypeError, ValueError):
        y_pct = 0.84
    size = str(screen_overlay.get("size") or "medium").strip().lower()
    if size not in ("small", "medium", "large"):
        size = "medium"
    return {
        "enabled": True,
        "text": raw_text[:220],
        "x_pct": round(max(0.05, min(0.95, x_pct)), 4),
        "y_pct": round(max(0.05, min(0.95, y_pct)), 4),
        "font": str(screen_overlay.get("font") or screen_overlay.get("font_id") or "arial_bold").strip().lower(),
        "effect": str(screen_overlay.get("effect") or "solid_dark").strip().lower(),
        "size": size,
        "text_color": str(screen_overlay.get("text_color") or screen_overlay.get("color") or "default").strip().lower(),
    }


def build_screen_overlay_annotation(
    overlay_cfg: Dict[str, Any],
    *,
    total_duration: float,
    target_h: int,
) -> Dict[str, Any]:
    """Convert normalized screen overlay config into an FFmpeg drawtext annotation dictionary."""
    size_key = overlay_cfg.get("size", "medium")
    is_large = size_key == "large"
    if is_large:
        font_size = max(48, min(64, int(target_h * 0.042)))
        box_border = 16
    elif size_key == "small":
        font_size = max(28, min(38, int(target_h * 0.024)))
        box_border = 10
    else:
        font_size = max(38, min(50, int(target_h * 0.034)))
        box_border = 14
    return {
        "text": overlay_cfg["text"],
        "start_sec": 0.0,
        "end_sec": total_duration,
        "position": "custom_xy",
        "style": "persistent_bottom",
        "font_id": overlay_cfg.get("font", "arial_bold"),
        "effect": overlay_cfg.get("effect", "solid_dark"),
        "size": size_key,
        "text_color": overlay_cfg.get("text_color", "default"),
        "x_pct": overlay_cfg.get("x_pct", 0.5),
        "y_pct": overlay_cfg.get("y_pct", 0.84),
        "font_size": font_size,
        "boxborderw": box_border,
        "large_font": is_large,
        "persistent": True,
        "is_screen_overlay": True,
    }


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
    enable_subtitles: Optional[bool] = None,
    enable_music: Optional[bool] = None,
    job_id: Optional[str] = None,
    caption_options: Optional[Dict[str, Any]] = None,
    screen_overlay: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Process smartphone video recording into a polished marketing promo cut.

    Workflow:
      1. Probe input video properties and resolve target aspect ratio (9:16 or 16:9).
      2. Extract visual keyframes into per-job isolated sandbox directory outputs/jobs/<job_id>/sandbox/keyframes.
      3. Perform Autonomous Multimodal Vision Analysis (if auto_mode or no script/preset provided)
         to infer engaging Arabic real estate voiceover, emotional tone, and recommended music.
      4. Synthesize expressive neural narration voiceover with Gemini TTS API modulated by emotional tone.
      5. Assemble final video in FFmpeg with clean voiceover (or optional background music and ducking).
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
    if parsed_dirs.get("requested_voice") and (not voice or voice == "ar-XA-Standard-A"):
        voice = parsed_dirs["requested_voice"]
    if parsed_dirs.get("orientation_requested") and not video_orientation:
        video_orientation = parsed_dirs["orientation_requested"]

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

    # Resolve unique job identifier
    if not job_id:
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        unique_suffix = uuid.uuid4().hex[:6]
        job_id = f"{timestamp_str}_{unique_suffix}"
    else:
        job_id = str(job_id).strip()

    out_cuts_dir = Path(output_dir).resolve()
    out_cuts_dir.mkdir(parents=True, exist_ok=True)

    # Multi-Tenant Job Sandbox: Isolate all temporary artifacts, keyframes, audio slices, and renders
    job_sandbox_dir = (REPO_ROOT / "outputs" / "jobs" / job_id / "sandbox").resolve()
    job_sandbox_dir.mkdir(parents=True, exist_ok=True)

    keyframes_dest_dir = job_sandbox_dir / "keyframes"
    keyframes_dest_dir.mkdir(parents=True, exist_ok=True)

    # Legacy keyframes directory for backwards compatibility with existing static routes
    legacy_keyframes_dir = Path("outputs/keyframes").resolve() / f"mobile_{job_id}"
    legacy_keyframes_dir.mkdir(parents=True, exist_ok=True)

    # Load customizable production principles
    from config.production_principles_manager import load_principles

    active_principles = load_principles()
    principles_voice = active_principles.get("voice_principles", {})
    principles_visual = active_principles.get("visual_principles", {})
    principles_annotation = active_principles.get("annotation_principles", {})

    # Telemetry helper
    def _notify(step: int, percent: int, message: str, log: str, extra: Optional[Dict[str, Any]] = None):
        if progress_callback:
            try:
                status_label = "completed" if percent >= 100 else "processing"
                payload = {
                    "job_id": job_id,
                    "status": status_label,
                    "step": step,
                    "current_step": step,
                    "progress": percent,
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

    # 1.2. Build Lightweight 480p Analysis Proxy & Local Scene/Quality Map
    # Analyze the full uncut video quickly via proxy while keeping original 1080p for cutting/export.
    montage_plan = parsed_dirs.get("montage_plan", {})
    montage_applied = False
    montage_details: Dict[str, Any] = {}
    original_source_duration = src_duration
    is_auto_mode = bool(auto_mode or speech_description or (not script and not preset_id))

    planned_target_dur: Optional[float] = None
    if montage_plan.get("requested"):
        t_start_p = montage_plan.get("trim_start")
        t_end_p = montage_plan.get("trim_end")
        t_off_p = montage_plan.get("trim_end_offset")
        if montage_plan.get("mode") == "interval" and t_start_p is not None and t_end_p is not None:
            planned_target_dur = max(1.0, min(float(t_end_p), src_duration) - max(0.0, float(t_start_p)))
        elif montage_plan.get("target_duration") is not None:
            planned_target_dur = float(montage_plan["target_duration"])
        elif montage_plan.get("smart_montage"):
            planned_target_dur = float(min(15.0, src_duration))
        elif t_start_p is not None:
            planned_target_dur = max(1.0, src_duration - float(t_start_p))
        elif t_off_p is not None:
            planned_target_dur = max(1.0, src_duration - float(t_off_p))

    proxy_path: Optional[Path] = None
    proxy_used = False
    proxy_scene_cuts: Optional[List[float]] = None
    proxy_quality_segments: Optional[List[Dict[str, Any]]] = None
    analysis_mode: Optional[str] = None
    ai_recommended_cuts: Optional[List[Dict[str, Any]]] = None
    vision_scene_scripts: Optional[List[Dict[str, Any]]] = None
    inferred_script: Optional[str] = None
    vision_engine: Optional[str] = None
    inferred_music: Optional[str] = None

    try:
        if src_duration >= 5.0 and (is_auto_mode or montage_plan.get("requested")):
            _notify(
                step=1,
                percent=18,
                message="إنشاء نسخة تحليل خفيفة وسريعة مع الحفاظ على دقة الأصل 1080p للتصدير...",
                log=f"[وكيل التحليل] 🎞️ تجهيز نسخة تحليل خفيفة (480p @ 2fps) لفحص كامل الفيديو ({src_duration:.1f}ث)...",
            )
            try:
                proxy_candidate = job_sandbox_dir / f"analysis_proxy_{job_id}.mp4"
                proxy_info = frame_extractor.create_analysis_proxy(
                    input_path,
                    output_path=proxy_candidate,
                    max_short_side=480,
                    fps=2.0,
                )
                p_out = Path(proxy_info["proxy_path"])
                if p_out.is_file() and p_out.stat().st_size > 0:
                    proxy_path = p_out
                    proxy_used = True
                    logger.info(
                        "Job %s: Created 480p proxy (%dx%d, %.2fMB)",
                        job_id,
                        proxy_info.get("width", 0),
                        proxy_info.get("height", 0),
                        proxy_info.get("size_bytes", 0) / (1024 * 1024),
                    )
            except Exception as p_err:
                logger.warning("Job %s: Proxy creation skipped (%s); analyzing input directly.", job_id, p_err)
                proxy_path = None

        analysis_video = proxy_path if (proxy_path and proxy_path.is_file()) else input_path

        if montage_plan.get("requested") or src_duration >= 8.0:
            try:
                proxy_scene_cuts = frame_extractor.detect_scene_cut_timestamps(analysis_video)
                proxy_quality_segments = frame_extractor.score_video_segments(
                    analysis_video,
                    segment_duration=2.5,
                    sample_fps=2.0,
                    scene_cuts=proxy_scene_cuts,
                )
            except Exception as q_err:
                logger.warning("Job %s: Local scene/quality scoring skipped (%s).", job_id, q_err)

        # 2. Extract visual keyframes from fast analysis video (used by UI gallery & vision fallback)
        _notify(
            step=2,
            percent=28,
            message="استخراج اللقطات المفتاحية وفحص جودة المشاهد عبر كامل الفيديو...",
            log="[رؤية حاسوبية] 🖼️ استخراج لقطات المعاينة البصرية لفحص كامل الفيديو...",
        )
        logger.info("Job %s: Extracting dense keyframes from '%s' -> %s...", job_id, analysis_video.name, keyframes_dest_dir)
        keyframe_files, formatted_keyframes = _extract_formatted_keyframes(
            video_path=analysis_video,
            duration=original_source_duration,
            job_id=job_id,
            keyframes_dest_dir=keyframes_dest_dir,
            legacy_keyframes_dir=legacy_keyframes_dir,
        )

        # 3. Full-Video Autonomous Vision Analysis FIRST (plans recommended_cuts + narration before cutting 1080p)
        videographer_speech = analyze_source_audio_for_speech(analysis_video)
        if videographer_speech:
            logger.info("Job %s: Extracted videographer field speech: %s", job_id, videographer_speech)

        if is_auto_mode:
            _notify(
                step=2,
                percent=42,
                message="تحليل الفيديو كاملاً عبر Gemini Vision لاختيار أفضل اللقطات وتوليد النص...",
                log="[رؤية حاسوبية] 🧠 تحليل الفيديو كاملاً عبر Gemini Multimodal Vision...",
            )
            try:
                import inspect as _inspect
                from web.vision_analyzer import infer_video_script_and_mood
                _vision_kwargs: Dict[str, Any] = {
                    "keyframe_paths": keyframe_files,
                    "video_duration": original_source_duration,
                    "preset_hint": preset_id,
                    "speech_description": speech_description,
                    "visual_description": visual_description,
                    "visual_lead_in": visual_lead_in,
                    "outro_buffer": outro_buffer,
                    "keyframes_metadata": formatted_keyframes,
                    "videographer_speech": videographer_speech,
                    "proxy_video_path": proxy_path,
                    "quality_segments": proxy_quality_segments,
                    "target_montage_duration": planned_target_dur,
                }
                _sig_target = infer_video_script_and_mood
                _side_eff = getattr(_sig_target, "side_effect", None)
                if callable(_side_eff):
                    _sig_target = _side_eff
                try:
                    _sig_params = _inspect.signature(_sig_target).parameters
                    _accepts_kwargs = any(
                        p.kind == _inspect.Parameter.VAR_KEYWORD for p in _sig_params.values()
                    )
                    if _accepts_kwargs or "scene_cuts" in _sig_params:
                        _vision_kwargs["scene_cuts"] = proxy_scene_cuts
                except (ValueError, TypeError):
                    _vision_kwargs["scene_cuts"] = proxy_scene_cuts
                try:
                    vision_result = infer_video_script_and_mood(**_vision_kwargs)
                except TypeError as _te:
                    if "scene_cuts" in str(_te) and "scene_cuts" in _vision_kwargs:
                        _vision_kwargs.pop("scene_cuts", None)
                        vision_result = infer_video_script_and_mood(**_vision_kwargs)
                    else:
                        raise
                inferred_script = sanitize_script_against_meta_prompts(vision_result.get("script"))
                selected_script = inferred_script or DEFAULT_PROMO_SCRIPT
                resolved_tone = emotional_tone or vision_result.get("emotional_tone") or principles_voice.get("active_tone_bias", "فاخر وهادئ")
                resolved_style_prompt = style_prompt or vision_result.get("emotional_prompt")
                inferred_music = vision_result.get("recommended_music")
                vision_engine = vision_result.get("engine")
                analysis_mode = vision_result.get("analysis_mode")
                ai_recommended_cuts = vision_result.get("recommended_cuts")
                vision_scene_scripts = vision_result.get("scene_scripts")
                if not phone_number and vision_result.get("phone_number"):
                    phone_number = vision_result.get("phone_number")
                if not bottom_text and vision_result.get("bottom_text"):
                    bottom_text = vision_result.get("bottom_text")
            except Exception as exc:
                logger.warning("Vision analysis error: %s. Using fallback.", exc)
                from web.vision_analyzer import _get_smart_fallback, build_shot_timeline, extract_keyframe_records
                fb_res = _get_smart_fallback(
                    duration=planned_target_dur or original_source_duration,
                    preset_hint=preset_id,
                    speech_description=speech_description,
                    visual_description=visual_description,
                    visual_lead_in=visual_lead_in,
                    outro_buffer=outro_buffer,
                    keyframe_count=len(keyframe_files),
                    shot_timeline=build_shot_timeline(
                        extract_keyframe_records(keyframe_files, keyframes_metadata=formatted_keyframes, video_duration=original_source_duration),
                        video_duration=original_source_duration,
                    ),
                    videographer_speech=videographer_speech,
                    quality_segments=proxy_quality_segments,
                )
                selected_script = sanitize_script_against_meta_prompts(fb_res.get("script")) or DEFAULT_PROMO_SCRIPT
                inferred_script = selected_script
                resolved_tone = emotional_tone or fb_res.get("emotional_tone") or principles_voice.get("active_tone_bias", "فاخر وهادئ")
                resolved_style_prompt = style_prompt or fb_res.get("emotional_prompt") or "Warm, luxurious and prestigious real estate tone"
                inferred_music = fb_res.get("recommended_music", "luxury_piano")
                vision_engine = "fallback_on_error"
                analysis_mode = "fallback"
                ai_recommended_cuts = fb_res.get("recommended_cuts")
                if not phone_number and fb_res.get("phone_number"):
                    phone_number = fb_res.get("phone_number")
                if not bottom_text and fb_res.get("bottom_text"):
                    bottom_text = fb_res.get("bottom_text")

            _notify(
                step=3,
                percent=55,
                message=f"تم تحليل الفيديو واستنتاج الوصف التسويقي. الحالة الشعورية: {resolved_tone}",
                log=f"[تحليل شعوري] ✨ تم استنتاج الوصف التسويقي ({analysis_mode or 'keyframes'}) والحالة: [{resolved_tone}]",
                extra={
                    "emotional_tone": resolved_tone,
                    "inferred_script": inferred_script,
                    "analyzed_frames_count": len(keyframe_files),
                    "visual_lead_in_seconds": visual_lead_in,
                },
            )
            selected_preset = preset_id if preset_id in ALGERIAN_REAL_ESTATE_PRESETS else None

        # 3.5. Execute Montage Cutting ONCE on Original 1080p Source Guided by Vision recommended_cuts
        if montage_plan.get("requested"):
            _notify(
                step=3,
                percent=60,
                message="وكيل الذكاء الاصطناعي يقص ويركب أفضل اللقطات مباشرة من الفيديو الأصلي 1080p...",
                log=f"[مونتاج ذكي] ✂️ بدء القص المباشر من الأصل ({target_w}x{target_h}) بالنمط ({montage_plan.get('mode')})...",
            )
            try:
                from web.video_editor import trim_video_clip, auto_smart_montage
                montaged_output_file = job_sandbox_dir / f"montaged_{job_id}.mp4"

                mode = montage_plan.get("mode", "interval")
                t_start = montage_plan.get("trim_start")
                t_end = montage_plan.get("trim_end")
                t_offset = montage_plan.get("trim_end_offset")
                target_dur = montage_plan.get("target_duration")
                is_smart = montage_plan.get("smart_montage", False)

                if mode == "interval" or (t_start is not None and t_end is not None):
                    st = max(0.0, float(t_start or 0.0))
                    en = min(float(t_end if t_end is not None else src_duration), src_duration)
                    m_res = trim_video_clip(
                        input_path=input_path,
                        output_path=montaged_output_file,
                        start_sec=st,
                        end_sec=en,
                        target_w=target_w,
                        target_h=target_h,
                    )
                    montage_applied = True
                    montage_details = {
                        "mode": "interval_trim",
                        "start_sec": st,
                        "end_sec": en,
                        "duration": m_res["duration"],
                        "original_duration": original_source_duration,
                        "segments": [(st, en)],
                    }
                elif mode == "trim_start" or (t_start is not None and t_end is None and not is_smart and not target_dur):
                    st = max(0.0, min(float(t_start), max(0.0, src_duration - 1.0)))
                    m_res = trim_video_clip(
                        input_path=input_path,
                        output_path=montaged_output_file,
                        start_sec=st,
                        end_sec=src_duration,
                        target_w=target_w,
                        target_h=target_h,
                    )
                    montage_applied = True
                    montage_details = {
                        "mode": "trim_start",
                        "trimmed_lead_sec": st,
                        "duration": m_res["duration"],
                        "original_duration": original_source_duration,
                        "segments": [(st, src_duration)],
                    }
                elif mode == "trim_end" or (t_offset is not None and t_start is None and not is_smart and not target_dur):
                    en = max(1.0, src_duration - float(t_offset))
                    m_res = trim_video_clip(
                        input_path=input_path,
                        output_path=montaged_output_file,
                        start_sec=0.0,
                        end_sec=en,
                        target_w=target_w,
                        target_h=target_h,
                    )
                    montage_applied = True
                    montage_details = {
                        "mode": "trim_end",
                        "trimmed_tail_sec": float(t_offset),
                        "duration": m_res["duration"],
                        "original_duration": original_source_duration,
                        "segments": [(0.0, en)],
                    }
                elif is_smart or target_dur is not None:
                    eff_dur = float(target_dur if target_dur else min(15.0, src_duration))
                    m_res = auto_smart_montage(
                        input_path=input_path,
                        output_path=montaged_output_file,
                        target_duration=eff_dur,
                        preferred_scenes=ai_recommended_cuts,
                        target_w=target_w,
                        target_h=target_h,
                        scene_cuts=proxy_scene_cuts,
                        quality_segments=proxy_quality_segments,
                        proxy_path=proxy_path,
                        transition="cut" if ai_recommended_cuts else "fade",
                        transition_dur=0.0 if ai_recommended_cuts else 0.35,
                    )
                    montage_applied = True
                    montage_details = {
                        "mode": "smart_ai_montage",
                        "target_duration": eff_dur,
                        "used_ai_cuts": bool(ai_recommended_cuts),
                        "segments": m_res.get("segments", []),
                        "output_segments": m_res.get("output_segments", []),
                        "duration": m_res["duration"],
                        "original_duration": original_source_duration,
                    }

                if montage_applied and montaged_output_file.is_file() and montaged_output_file.stat().st_size > 0:
                    input_path = montaged_output_file
                    meta = frame_extractor.get_video_metadata(input_path)
                    src_width = int(meta.get("width", target_w))
                    src_height = int(meta.get("height", target_h))
                    src_duration = float(meta.get("total_duration", m_res["duration"]))
                    # Refresh gallery keyframes so UI timeline mirrors the cut video
                    keyframe_files, formatted_keyframes = _extract_formatted_keyframes(
                        video_path=input_path,
                        duration=src_duration,
                        job_id=job_id,
                        keyframes_dest_dir=keyframes_dest_dir,
                        legacy_keyframes_dir=legacy_keyframes_dir,
                    )
                    logger.info(
                        "Job %s: Montage applied cleanly (%s, ai_cuts=%s). New duration: %.2fs (was %.2fs)",
                        job_id,
                        montage_details.get("mode"),
                        bool(ai_recommended_cuts),
                        src_duration,
                        original_source_duration,
                    )
                    _notify(
                        step=3,
                        percent=64,
                        message=f"اكتمل القص الذكي بدقة {target_w}x{target_h}: المدة الجديدة {src_duration:.1f}ث.",
                        log=f"[مونتاج ذكي] ✅ اكتمل القص من الأصل 1080p ({montage_details.get('mode')}). المدة: {src_duration:.1f}s.",
                        extra={"montage_details": montage_details},
                    )
            except Exception as m_err:
                logger.warning("Job %s: Montage step encountered non-fatal error: %s. Continuing with original footage.", job_id, m_err)
                montage_applied = False
    finally:
        if proxy_path and proxy_path.exists():
            try:
                proxy_path.unlink(missing_ok=True)
            except Exception:
                pass

    if not is_auto_mode:
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
        resolved_style_prompt = style_prompt or f"Calm, genuine everyday conversational voiceover in {resolved_tone}, grounded human delivery without theatrical exaggeration"

    # Resolve background music track and user music directives (Strict Opt-In Architecture)
    music_directives = parsed_dirs.get("music_directives", {})
    clean_music_arg = (
        str(music_track).strip()
        if music_track and str(music_track).strip().lower() not in ("none", "null", "false", "")
        else ""
    )
    user_requested_music = bool(
        enable_music is True
        or music_directives.get("music_requested", False)
        or (enable_music is not False and bool(clean_music_arg))
    )
    explicitly_muted = bool(music_directives.get("explicit_mute", False)) or (
        enable_music is False and not music_directives.get("music_requested", False)
    )
    mute_music = explicitly_muted or (not user_requested_music)
    resolved_music_key = principles_visual.get("selected_music_theme", "luxury_piano")

    if music_directives.get("music_track") and resolve_music_track(music_directives["music_track"], strict=True):
        resolved_music_key = resolve_music_track(music_directives["music_track"])["id"]
    elif clean_music_arg and resolve_music_track(clean_music_arg, strict=True):
        resolved_music_key = resolve_music_track(clean_music_arg)["id"]
    elif is_auto_mode and inferred_music and resolve_music_track(inferred_music, strict=True):
        resolved_music_key = resolve_music_track(inferred_music)["id"]
    elif selected_preset and "recommended_music" in ALGERIAN_REAL_ESTATE_PRESETS.get(selected_preset, {}):
        resolved_music_key = ALGERIAN_REAL_ESTATE_PRESETS[selected_preset]["recommended_music"]
    elif parsed_dirs.get("property_features", {}).get("sea_view"):
        resolved_music_key = "ambient_meditation"

    music_meta = resolve_music_track(resolved_music_key)
    resolved_music_key = music_meta["id"]
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

    # Build scene-locked narration plan when multi-scene scripts exist and user didn't supply manual verbatim text
    aligned_scene_plan: List[Dict[str, Any]] = []
    if is_auto_mode and not (script and script.strip()):
        out_segs = montage_details.get("output_segments") if montage_applied else None
        if out_segs:
            for seg_idx, o_seg in enumerate(out_segs):
                line = str(o_seg.get("narration_line") or "").strip()
                matched_sc = None
                mid_src = (float(o_seg.get("src_start_sec", 0.0)) + float(o_seg.get("src_end_sec", 0.0))) * 0.5
                if vision_scene_scripts:
                    matched_sc = next(
                        (vs for vs in vision_scene_scripts if float(vs["start_sec"]) <= mid_src <= float(vs["end_sec"])),
                        None,
                    )
                    if not line and matched_sc:
                        line = str(matched_sc.get("text") or "").strip()
                matched_cut = None
                if ai_recommended_cuts:
                    matched_cut = next(
                        (rc for rc in ai_recommended_cuts if float(rc["start_sec"]) <= mid_src <= float(rc["end_sec"])),
                        None,
                    )
                scene_title = _pick_semantic_scene_title(
                    o_seg.get("title"),
                    matched_sc.get("title") if matched_sc else "",
                    matched_sc.get("room_or_subject") if matched_sc else "",
                    matched_cut.get("title") if matched_cut else "",
                    fallback=f"المشهد {seg_idx + 1}",
                )
                if line:
                    aligned_scene_plan.append({
                        "start_sec": o_seg["start_sec"],
                        "end_sec": o_seg["end_sec"],
                        "title": scene_title,
                        "room_or_subject": scene_title,
                        "text": line,
                    })
        elif vision_scene_scripts:
            aligned_scene_plan = list(vision_scene_scripts)

    narration_wav = job_sandbox_dir / f"narration_{job_id}.wav"
    if len(aligned_scene_plan) >= 2:
        raw_lead = max(0.0, float(visual_lead_in if visual_lead_in is not None else 1.2))
        scene_lead_in = min(raw_lead, 0.12) if raw_lead > 0 else 0.0
        narration_info = synthesize_scene_aligned_narration(
            scene_segments=aligned_scene_plan,
            output_path=narration_wav,
            voice=voice,
            style_prompt=final_style_prompt,
            emotional_tone=resolved_tone,
            visual_lead_in=scene_lead_in,
        )
        visual_lead_in = scene_lead_in
        if narration_info.get("script"):
            selected_script = narration_info["script"]
    else:
        narration_info = synthesize_narration(
            script_text=selected_script,
            output_path=narration_wav,
            voice=voice,
            style_prompt=final_style_prompt,
            emotional_tone=resolved_tone,
        )
    narration_duration = narration_info["duration"]

    # 5. Timeline Synchronization, Silence Trim, Tempo Fit & Zero Long End-Freeze
    timeline_fit = _compute_timeline_fit(
        narration_wav=narration_wav,
        initial_narration_dur=narration_duration,
        src_duration=src_duration,
        visual_lead_in=visual_lead_in,
        outro_buffer=outro_buffer,
    )
    narration_duration = timeline_fit["narration_duration"]
    visual_lead_in = timeline_fit["visual_lead_in"]
    eff_outro = timeline_fit["eff_outro"]
    total_duration = timeline_fit["total_duration"]
    pad_needed = timeline_fit["pad_needed"]
    fade_out_start = timeline_fit["fade_out_start"]

    logger.info(
        "Job %s: Timeline - Video: %.2fs, Lead-In: %.2fs, Narration: %.2fs, Outro: %.2fs, Total: %.2fs (Pad: %.2fs)",
        job_id,
        src_duration,
        visual_lead_in,
        narration_duration,
        eff_outro,
        total_duration,
        pad_needed,
    )

    # 6. Sidechain Compression & Dynamic Ducking Settings
    target_duck = principles_visual.get("smart_ducking_volume", duck_level) if duck_level == 0.25 else duck_level
    effective_duck_level = max(0.05, min(0.60, float(target_duck)))
    duck_threshold = 0.015
    duck_ratio = 12.0
    duck_attack = 60
    duck_release = 350
    ambient_volume = float(music_directives.get("music_volume") or principles_visual.get("ambient_music_volume") or 0.16)

    if mute_music:
        music_meta = {
            "id": "none",
            "title": "بدون موسيقى (صوت نقي)",
            "license": "None",
        }
        _notify(
            step=4,
            percent=85,
            message="كتم الموسيقى التصويرية وتصدير الصوت النقي بناءً على رغبة المستخدم...",
            log=f"[مكساج صوتي] 🔇 تم إلغاء الموسيقى الخلفية بنجاح بناءً على التوجيهات المدخلة. الصوت الصافي نشط.",
        )
    else:
        _notify(
            step=4,
            percent=85,
            message=f"دمج الموسيقى التصويرية ({music_meta['title']}) وتطبيق خفض الصوت التلقائي (Sidechain Ducking)...",
            log=f"[مكساج صوتي] تم إنتاج الصوت ({narration_duration:.1f}s - {narration_info['synthesizer']}). دمج الموسيقى بمستوى متوازن ({ambient_volume:.2f}) وخفض ذكي ({effective_duck_level:.2f}).",
        )

    # 7. Render Mixed Video Cut via shared helper
    final_cut_path = job_sandbox_dir / f"cut_{job_id}.mp4"
    _notify(
        step=5,
        percent=90,
        message="ريندر وتجميع مشاهد الفيديو والصوت عبر FFmpeg...",
        log=f"[ريندر الفيديو] 🎬 بدء تصدير الفيديو النهائي بدقة {target_w}x{target_h} ودمج الصوت والمشاهد...",
    )
    logger.info("Job %s: Rendering final cut with FFmpeg -> %s", job_id, final_cut_path)
    render_seconds = _render_mixed_cut(
        input_path=input_path,
        narration_wav=narration_wav,
        output_path=final_cut_path,
        target_w=target_w,
        target_h=target_h,
        total_duration=total_duration,
        pad_needed=pad_needed,
        fade_out_start=fade_out_start,
        visual_lead_in=visual_lead_in,
        mute_music=mute_music,
        music_audio_file=music_audio_file,
        duck_threshold=duck_threshold,
        duck_ratio=duck_ratio,
        duck_attack=duck_attack,
        duck_release=duck_release,
        ambient_volume=ambient_volume,
    )
    logger.info("Job %s: Final cut rendered in %.2fs (%d bytes)", job_id, render_seconds, final_cut_path.stat().st_size)

    # Compile shot timeline prior to annotations & subtitle synchronization
    shot_timeline_data: List[Dict[str, Any]] = []
    if montage_applied and aligned_scene_plan:
        shot_timeline_data = [
            {
                "scene_index": idx + 1,
                "start_sec": round(float(slot.get("start_sec", 0.0)), 2),
                "end_sec": round(float(slot.get("end_sec", 0.0)), 2),
                "duration": round(max(0.5, float(slot.get("end_sec", 0.0)) - float(slot.get("start_sec", 0.0))), 2),
                "title": _pick_semantic_scene_title(slot.get("title"), slot.get("room_or_subject"), fallback=f"المشهد {idx + 1}"),
                "room_or_subject": _pick_semantic_scene_title(slot.get("title"), slot.get("room_or_subject"), fallback=f"المشهد {idx + 1}"),
                "description": strip_tts_vocal_tags(str(slot.get("text") or "").strip()),
                "narration_line": strip_tts_vocal_tags(str(slot.get("text") or "").strip()),
                "thumbnail": _pick_closest_thumb(
                    formatted_keyframes,
                    (float(slot.get("start_sec", 0.0)) + float(slot.get("end_sec", 0.0))) * 0.5,
                ),
            }
            for idx, slot in enumerate(aligned_scene_plan)
        ]
    elif is_auto_mode and "vision_result" in locals() and isinstance(vision_result, dict) and vision_result.get("shot_timeline"):
        shot_timeline_data = vision_result["shot_timeline"]
    elif is_auto_mode and "fb_res" in locals() and isinstance(fb_res, dict) and fb_res.get("shot_timeline"):
        shot_timeline_data = fb_res["shot_timeline"]
    else:
        from web.vision_analyzer import build_shot_timeline, extract_keyframe_records
        shot_timeline_data = build_shot_timeline(
            extract_keyframe_records(keyframe_files, keyframes_metadata=formatted_keyframes, video_duration=src_duration),
            video_duration=src_duration,
        )

    # 8. Apply Smart Video Annotations, Lower-Third Banners & Merchant Fixed Text Overlays (Strict Opt-In)
    applied_annotations_count = 0
    annotations_list: List[Dict[str, Any]] = []

    # Insert interactive drag-placed screen overlay OR legacy persistent bottom text / phone overlay
    normalized_screen_overlay = normalize_screen_overlay_options(
        screen_overlay,
        fallback_text=bottom_text or phone_number or fixed_text,
    )
    effective_bottom = (
        normalized_screen_overlay["text"]
        if normalized_screen_overlay
        else (bottom_text or (phone_number if phone_number else None))
    )
    if normalized_screen_overlay:
        annotations_list.append(
            build_screen_overlay_annotation(
                normalized_screen_overlay,
                total_duration=total_duration,
                target_h=target_h,
            )
        )
    elif effective_bottom and str(effective_bottom).strip():
        is_large_font = bool(parsed_dirs.get("large_font", False))
        target_overlay_pos = parsed_dirs.get("overlay_position") or "bottom_banner"

        if is_large_font:
            calculated_fs = max(48, min(64, int(target_h * 0.042)))
            calculated_boxborder = 16
        else:
            calculated_fs = max(38, min(50, int(target_h * 0.034)))
            calculated_boxborder = 12

        annotations_list.append({
            "text": str(effective_bottom).strip(),
            "start_sec": 0.0,
            "end_sec": total_duration,
            "position": target_overlay_pos,
            "style": "persistent_bottom",
            "font_size": calculated_fs,
            "boxborderw": calculated_boxborder,
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

    # Preset title badge ONLY if preset is explicitly selected
    if selected_preset and principles_annotation.get("enable_auto_annotations", True):
        banner_title = ALGERIAN_REAL_ESTATE_PRESETS.get(selected_preset, {}).get("title_ar", "")
        if banner_title and not (fixed_text and str(fixed_text).strip()):
            annotations_list.append({
                "text": banner_title,
                "start_sec": 0.5,
                "end_sec": min(4.5, total_duration),
                "position": principles_annotation.get("position", "lower_third"),
                "style": principles_annotation.get("font_style", "luxury_gold"),
            })

    # Opt-In Highlight Badges if requested by user
    if parsed_dirs.get("highlights_requested"):
        raw_highlights: List[str] = []
        if is_auto_mode and "vision_result" in locals() and isinstance(vision_result, dict) and vision_result.get("highlights"):
            raw_highlights = [str(h).strip() for h in vision_result["highlights"] if str(h).strip()]
        elif is_auto_mode and "fb_res" in locals() and isinstance(fb_res, dict) and fb_res.get("highlights"):
            raw_highlights = [str(h).strip() for h in fb_res["highlights"] if str(h).strip()]
        if raw_highlights:
            top_highlights = raw_highlights[:3]
            usable_span = max(3.0, total_duration - visual_lead_in - 0.5)
            slot_dur = round(usable_span / len(top_highlights), 2)
            for h_idx, h_text in enumerate(top_highlights):
                h_start = round(visual_lead_in + h_idx * slot_dur, 2)
                h_end = round(min(total_duration - 0.3, h_start + max(1.8, slot_dur - 0.2)), 2)
                if h_end > h_start:
                    annotations_list.append({
                        "text": h_text,
                        "start_sec": h_start,
                        "end_sec": h_end,
                        "position": "top_right",
                        "style": "highlight_badge",
                    })

    base_annotations = list(annotations_list)

    # Strict Opt-In for synchronized captions / subtitles: Default OFF
    subtitles_opt_in = bool(
        enable_subtitles if enable_subtitles is not None
        else parsed_dirs.get("subtitles_requested", False)
    )

    fallback_subs: List[Dict[str, Any]] = []
    if is_auto_mode:
        if "vision_result" in locals() and isinstance(vision_result, dict) and vision_result.get("subtitles"):
            fallback_subs = list(vision_result["subtitles"])
        elif "fb_res" in locals() and isinstance(fb_res, dict) and fb_res.get("subtitles"):
            fallback_subs = list(fb_res["subtitles"])

    subtitles_list, caption_track_meta, applied_annotations_count = _apply_subtitles_and_annotations(
        final_cut_path=final_cut_path,
        job_id=job_id,
        job_sandbox_dir=job_sandbox_dir,
        total_duration=total_duration,
        target_w=target_w,
        target_h=target_h,
        subtitles_opt_in=subtitles_opt_in,
        narration_info=narration_info,
        selected_script=selected_script,
        narration_duration=narration_duration,
        visual_lead_in=visual_lead_in,
        shot_timeline_data=shot_timeline_data,
        caption_options=caption_options,
        base_annotations=base_annotations,
        fallback_subtitles=fallback_subs,
        notify_fn=_notify,
    )

    mirror_cut_path = _mirror_outputs(final_cut_path, narration_wav, out_cuts_dir, job_id)

    editable_cuts = _build_editable_cuts(
        aligned_scene_plan=aligned_scene_plan,
        montage_details=montage_details,
        shot_timeline_data=shot_timeline_data,
        formatted_keyframes=formatted_keyframes,
        selected_script=selected_script,
        src_duration=src_duration,
    )
    for idx, ec in enumerate(editable_cuts):
        if idx < len(shot_timeline_data):
            if ec.get("title"):
                shot_timeline_data[idx]["title"] = ec["title"]
                shot_timeline_data[idx]["room_or_subject"] = ec["title"]
            if ec.get("text"):
                shot_timeline_data[idx]["description"] = ec["text"]
                shot_timeline_data[idx]["narration_line"] = ec["text"]

    # 9. Compile Complete Execution Summary
    video_web_url = f"/outputs/mobile_cuts/cut_{job_id}.mp4"
    sandboxed_video_url = f"/outputs/jobs/{job_id}/sandbox/cut_{job_id}.mp4"
    summary: Dict[str, Any] = {
        "job_id": job_id,
        "status": "completed",
        "progress": 100,
        "progress_percent": 100,
        "video_url": video_web_url,
        "output_video_url": video_web_url,
        "output_video": video_web_url,
        "sandboxed_video_url": sandboxed_video_url,
        "sandbox_dir": str(job_sandbox_dir),
        "clean_visual_source": str(input_path),
        "output_path": str(mirror_cut_path),
        "absolute_output_path": str(mirror_cut_path.resolve()),
        "file_size_bytes": final_cut_path.stat().st_size,
        "duration": total_duration,
        "end_freeze_seconds": pad_needed,
        "orientation": orientation,
        "video_orientation": orientation,
        "aspect_ratio": aspect_label,
        "resolution": f"{target_w}x{target_h}",
        "fixed_text": fixed_text,
        "bottom_text": effective_bottom,
        "phone_number": phone_number,
        "screen_overlay": normalized_screen_overlay,
        "subtitles": subtitles_list,
        "subtitles_count": len(subtitles_list),
        "subtitles_enabled": subtitles_opt_in,
        "subtitles_requested": subtitles_opt_in,
        "animated_captions": caption_track_meta,
        "shot_timeline": shot_timeline_data,
        "editable_cuts": editable_cuts,
        "render_config": {
            "target_w": target_w,
            "target_h": target_h,
            "src_duration": src_duration,
            "voice": resolved_voice_id,
            "emotional_tone": resolved_tone,
            "style_prompt": final_style_prompt,
            "visual_lead_in": visual_lead_in,
            "outro_buffer": outro_buffer,
            "duck_level": effective_duck_level,
            "duck_threshold": duck_threshold,
            "duck_ratio": duck_ratio,
            "duck_attack": duck_attack,
            "duck_release": duck_release,
            "mute_music": mute_music,
            "music_track_id": resolved_music_key,
            "ambient_volume": ambient_volume,
            "subtitles_enabled": subtitles_opt_in,
            "caption_options": caption_options,
            "screen_overlay": normalized_screen_overlay,
            "base_annotations": base_annotations,
        },
        "videographer_speech": videographer_speech,
        "customer_specifications": {
            "phone_number": phone_number,
            "property_type": parsed_dirs.get("property_features", {}).get("property_type"),
            "unit": parsed_dirs.get("property_features", {}).get("unit"),
            "sea_view": parsed_dirs.get("property_features", {}).get("sea_view", False),
            "mute_music": mute_music,
            "large_font": bool(parsed_dirs.get("large_font", False)),
            "subtitles_requested": subtitles_opt_in,
        },
        "text_position": text_position,
        "text_style": text_style,
        "auto_mode": is_auto_mode,
        "emotional_tone": resolved_tone,
        "speech_description": speech_description,
        "visual_description": visual_description,
        "inferred_script": inferred_script,
        "vision_engine": vision_engine,
        "analysis_mode": analysis_mode,
        "proxy_used": proxy_used,
        "recommended_cuts": ai_recommended_cuts,
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
        "montage_applied": montage_applied,
        "montage_details": montage_details if montage_applied else None,
        "music_muted": mute_music,
        "music_requested": user_requested_music,
        "music_volume": ambient_volume,
        "large_font_applied": bool(parsed_dirs.get("large_font", False)),
        "property_features": parsed_dirs.get("property_features", {}),
        "music_track": {
            "id": music_meta["id"],
            "title": music_meta["title"],
            "license": music_meta["license"],
            "muted": mute_music,
            "volume": ambient_volume,
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
            "subtitles": {
                "count": len(subtitles_list),
                "items": subtitles_list,
                "enabled": subtitles_opt_in,
            },
            "sandbox": {
                "sandbox_dir": str(job_sandbox_dir),
                "sandboxed_video_url": sandboxed_video_url,
            },
            "shot_timeline": shot_timeline_data,
            "videographer_speech": videographer_speech,
            "montage": {
                "applied": montage_applied,
                "original_duration": original_source_duration,
                "post_montage_duration": src_duration,
                "reduction_seconds": round(original_source_duration - src_duration, 2) if montage_applied else 0.0,
                "details": montage_details,
            },
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

    # Persist summary JSON in both job sandbox and output directory
    summary_path_sandbox = job_sandbox_dir / f"summary_{job_id}.json"
    with open(summary_path_sandbox, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    summary_path_legacy = out_cuts_dir / f"summary_{job_id}.json"
    if str(summary_path_sandbox.resolve()) != str(summary_path_legacy.resolve()):
        with open(summary_path_legacy, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

    summary_extra = {
        "video_url": video_web_url,
        "output_video_url": video_web_url,
        "output_video": video_web_url,
        "sandboxed_video_url": sandboxed_video_url,
        "output_path": str(mirror_cut_path),
        "absolute_output_path": str(mirror_cut_path.resolve()),
        "result": summary,
    }

    _notify(
        step=5,
        percent=100,
        message="اكتمل إنتاج الفيديو التسويقي بنجاح! جاهز للمعاينة والتحميل.",
        log=f"[إخراج نهائي] تم تصدير الفيديو النهائي ({summary['resolution']}, {total_duration:.1f}s) بنجاح. جاهز للمعاينة والتحميل.",
        extra=summary_extra,
    )

    return summary
