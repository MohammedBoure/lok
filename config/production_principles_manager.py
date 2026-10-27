#!/usr/bin/env python3
"""
Production Principles & Voice Guidelines Manager.
Persists and manages customizable rules for AI video vision analysis,
Arabic real estate narration, emotional tone biasing, and visual overlay styles.

Author: MohammedBoure
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict

CONFIG_DIR = Path(__file__).resolve().parent
PRINCIPLES_FILE = CONFIG_DIR / "production_principles.json"

DEFAULT_PRINCIPLES: Dict[str, Any] = {
    "version": "1.0.0",
    "voice_principles": {
        "title": "مبادئ ومعايير التعليق الصوتي العصبي",
        "guidelines": "تحدث بنبرة عربية فصيحة، مع إبراز الفخامة والأناقة في وصف العقارات الراقية، والحماس والحيوية في العروض الترويجية والأسعار التنافسية. اجعل مخارج الحروف واضحة ومريحة وموزونة مع المشاهد.",
        "pacing": "معتدل (حوالي 120 إلى 140 كلمة في الدقيقة مع فترات صمت هادفة مدتها 0.5 إلى 1.0 ثانية بين الفقرات لتنفس الموسيقى)",
        "pronunciation": "نطق أسماء المدن والأحياء والمصطلحات العقارية (F3, F4, دوبلكس, فيلا, صالون ملكي) بفصاحة ودقة تامة.",
        "active_tone_bias": "فاخر وهادئ"
    },
    "narrative_principles": {
        "title": "مبادئ الوصف المعماري والترويج العقاري",
        "guidelines": "التركيز على نقاط القوة الحقيقية: المساحة الواسعة، الإضاءة الطبيعية المشمسة، جودة التشطيب، المطبخ المجهز، الإطلالة البانورامية، والقرب من المرافق الحيوية.",
        "length_alignment": "مواءمة طول النص بدقة مع مدة الفيديو المستخرجة بحيث ينتهي التعليق مع آخر مشهد قبل النهاية بثانيتين.",
        "target_audience": "المشترون والمستثمرون الباحثون عن الجودة والرفاهية والفرص العقارية النادرة."
    },
    "visual_principles": {
        "title": "مبادئ الإخراج الصوتي والموسيقي",
        "smart_ducking_volume": 0.15,
        "selected_music_theme": "luxury_piano",
        "auto_music_matching": True
    },
    "annotation_principles": {
        "title": "مبادئ الكتابات والملصقات التوضيحية على الفيديو",
        "enable_auto_annotations": True,
        "font_style": "bold_gold_badge",
        "position": "lower_third",
        "banner_opacity": 0.85
    }
}


def load_principles() -> Dict[str, Any]:
    """Load principles from persistent storage, falling back to defaults if missing or corrupted."""
    if PRINCIPLES_FILE.is_file():
        try:
            with open(PRINCIPLES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "voice_principles" in data:
                    return copy.deepcopy(data)
        except Exception:
            pass

    # Save defaults if file doesn't exist
    save_principles(copy.deepcopy(DEFAULT_PRINCIPLES))
    return copy.deepcopy(DEFAULT_PRINCIPLES)


def save_principles(new_principles: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and persist new principles to disk."""
    if not isinstance(new_principles, dict):
        raise ValueError("Principles must be a dictionary")

    # Merge with defaults to ensure all required keys exist
    merged = copy.deepcopy(DEFAULT_PRINCIPLES)
    for section in ["voice_principles", "narrative_principles", "visual_principles", "annotation_principles"]:
        if section in new_principles and isinstance(new_principles[section], dict):
            merged[section].update(new_principles[section])
        elif section in new_principles:
            merged[section] = new_principles[section]

    if "version" in new_principles:
        merged["version"] = new_principles["version"]

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(PRINCIPLES_FILE, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    return copy.deepcopy(merged)


def reset_principles() -> Dict[str, Any]:
    """Reset principles to defaults and persist."""
    # Remove file if exists to wipe out mutations
    if PRINCIPLES_FILE.is_file():
        try:
            PRINCIPLES_FILE.unlink()
        except OSError:
            pass
    return save_principles(copy.deepcopy(DEFAULT_PRINCIPLES))


def build_vision_prompt_principles() -> str:
    """Format narrative and voice principles into a prompt section for Gemini Vision."""
    p = load_principles()
    narrative = p.get("narrative_principles", {})
    voice = p.get("voice_principles", {})

    return (
        f"معايير ومبادئ الصياغة والتسويق العقاري المعتمدة:\n"
        f"- قواعد الوصف: {narrative.get('guidelines', '')}\n"
        f"- مواءمة المدة: {narrative.get('length_alignment', '')}\n"
        f"- الجمهور المستهدف: {narrative.get('target_audience', '')}\n"
        f"- إرشادات نبرة الصوت: {voice.get('guidelines', '')}\n"
        f"- الإيقاع: {voice.get('pacing', '')}\n"
        f"- النطق والمخارج: {voice.get('pronunciation', '')}\n"
        f"- التفضيل الشعوري الافتراضي: {voice.get('active_tone_bias', 'فاخر وهادئ')}\n"
    )


def build_tts_style_principles(emotional_tone: str | None = None) -> str:
    """Format voice principles into an expressive style directive for Gemini TTS."""
    p = load_principles()
    voice = p.get("voice_principles", {})
    base_guidelines = voice.get("guidelines", "")
    pacing = voice.get("pacing", "")
    tone = emotional_tone or voice.get("active_tone_bias", "فاخر وهادئ")

    return f"الحالة الشعورية المطلوبة: {tone}. {base_guidelines} الإيقاع: {pacing}."
