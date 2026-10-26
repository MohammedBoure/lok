"""Preset voice catalog and metadata for Gemini Text-to-Speech."""

from typing import Dict, List, Optional
from .models import VoiceProfile

# Official and recognized Gemini prebuilt voice personas
PRESET_VOICES: Dict[str, VoiceProfile] = {
    "Puck": VoiceProfile(
        name="Puck",
        gender="Neutral / Youthful",
        tone="Playful, upbeat, animated, curious",
        description="Engaging and lively voice, ideal for children's stories, educational content, and cheerful characters.",
        language="en-US",
        recommended_for=["children_stories", "cartoons", "dialogues", "adventures"],
    ),
    "Charon": VoiceProfile(
        name="Charon",
        gender="Masculine",
        tone="Deep, grounded, calm, authoritative",
        description="Low, reassuring resonance suited for documentary narration, solemn narratives, and wise characters.",
        language="en-US",
        recommended_for=["narration", "documentaries", "wisdom_quotes", "bedtime_calm"],
    ),
    "Kore": VoiceProfile(
        name="Kore",
        gender="Feminine",
        tone="Warm, soothing, gentle, friendly",
        description="Inviting and tender delivery, perfect for bedtime story reading, meditations, and comforting dialogue.",
        language="en-US",
        recommended_for=["bedtime_stories", "meditation", "gentle_guides", "empathetic_dialogue"],
    ),
    "Fenrir": VoiceProfile(
        name="Fenrir",
        gender="Masculine",
        tone="Energetic, robust, dynamic, assertive",
        description="High-energy and driving cadence, fitting for action stories, announcements, and bold characters.",
        language="en-US",
        recommended_for=["action_scenes", "dynamic_narration", "heroic_dialogue"],
    ),
    "Aoede": VoiceProfile(
        name="Aoede",
        gender="Feminine",
        tone="Melodic, expressive, polished, thoughtful",
        description="Articulate and musical storytelling voice with refined cadence for classic tales and poetry.",
        language="en-US",
        recommended_for=["classic_fairytales", "poetry", "educational_explainers"],
    ),
    "Leda": VoiceProfile(
        name="Leda",
        gender="Feminine",
        tone="Soft, poetic, delicate",
        description="Lyrical and soft-spoken delivery suitable for subtle, atmospheric scenes.",
        language="en-US",
        recommended_for=["lullabies", "soft_narration", "emotional_scenes"],
    ),
    "Zephyr": VoiceProfile(
        name="Zephyr",
        gender="Neutral",
        tone="Crisp, modern, airy, natural",
        description="Modern conversational flow suitable for assistant personas and modern storytelling.",
        language="en-US",
        recommended_for=["modern_dialogue", "conversational_agents", "podcasts"],
    ),
    "Orus": VoiceProfile(
        name="Orus",
        gender="Masculine",
        tone="Resonant, steady, clear",
        description="Balanced, clear delivery with steady pacing for instructional and narrative voiceovers.",
        language="en-US",
        recommended_for=["explanations", "steady_narration", "audiobooks"],
    ),
}


def list_preset_voices() -> List[VoiceProfile]:
    """Return all available preset voice identities."""
    return list(PRESET_VOICES.values())


def get_voice_profile(voice_name: str) -> Optional[VoiceProfile]:
    """Retrieve voice profile by name (case-insensitive)."""
    for name, profile in PRESET_VOICES.items():
        if name.lower() == voice_name.strip().lower():
            return profile
    return None
