"""test_generate_sound: High-quality Text-to-Speech library using Google Gemini."""

from .gemini_speech import (
    AuthenticationError,
    ConfigurationError,
    GeminiSpeechClient,
    GeminiSpeechError,
    KeyManager,
    KeyPoolExhaustedError,
    KeyState,
    ModelNotFoundError,
    PRESET_VOICES,
    QuotaExceededError,
    SpeechModelInfo,
    SynthesisError,
    SynthesisResult,
    VoiceProfile,
    get_voice_profile,
    list_preset_voices,
)

__all__ = [
    "GeminiSpeechClient",
    "KeyManager",
    "KeyState",
    "SpeechModelInfo",
    "SynthesisResult",
    "VoiceProfile",
    "PRESET_VOICES",
    "get_voice_profile",
    "list_preset_voices",
    "GeminiSpeechError",
    "ConfigurationError",
    "KeyPoolExhaustedError",
    "AuthenticationError",
    "QuotaExceededError",
    "ModelNotFoundError",
    "SynthesisError",
]
