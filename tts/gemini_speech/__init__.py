"""Google Gemini Speech Client Library for production Text-to-Speech."""

from .client import GeminiSpeechClient
from .config import KeyManager, KeyState
from .exceptions import (
    AuthenticationError,
    ConfigurationError,
    GeminiSpeechError,
    KeyPoolExhaustedError,
    ModelNotFoundError,
    QuotaExceededError,
    SynthesisError,
)
from .models import SpeechModelInfo, SynthesisResult, VoiceProfile
from .voices import PRESET_VOICES, get_voice_profile, list_preset_voices

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
