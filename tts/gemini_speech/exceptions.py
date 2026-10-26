"""Custom exceptions for the Gemini Speech Client library."""

from typing import Optional


class GeminiSpeechError(Exception):
    """Base exception for all Gemini speech library errors."""

    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class ConfigurationError(GeminiSpeechError):
    """Raised when environment or constructor configuration is invalid or missing."""
    pass


class KeyPoolExhaustedError(GeminiSpeechError):
    """Raised when all configured API keys are on cooldown or exhausted."""
    pass


class AuthenticationError(GeminiSpeechError):
    """Raised when an API key is invalid, unauthorized, or revoked."""
    pass


class QuotaExceededError(GeminiSpeechError):
    """Raised when API key usage limit or rate limit (HTTP 429) is encountered."""
    pass


class ModelNotFoundError(GeminiSpeechError):
    """Raised when requested model is not found or unsupported."""
    pass


class SynthesisError(GeminiSpeechError):
    """Raised when audio synthesis fails or response data cannot be parsed."""
    pass
