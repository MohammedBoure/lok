"""Data transfer models and metadata containers for Gemini Speech."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class SpeechModelInfo:
    """Metadata representing a speech-generation or TTS-capable Gemini model."""

    model_id: str
    display_name: str
    description: str
    supported_methods: List[str] = field(default_factory=list)
    input_token_limit: Optional[int] = None
    output_token_limit: Optional[int] = None

    @property
    def clean_id(self) -> str:
        """Strip 'models/' prefix if present."""
        return self.model_id.removeprefix("models/")


@dataclass(frozen=True)
class VoiceProfile:
    """Metadata representing a preset Gemini voice identity."""

    name: str
    gender: str
    tone: str
    description: str
    language: str = "en-US"
    recommended_for: List[str] = field(default_factory=list)


@dataclass
class SynthesisResult:
    """Container holding synthesized audio data and request telemetry."""

    audio_bytes: bytes
    mime_type: str
    model_used: str
    voice_used: str
    key_index_used: int
    output_path: Optional[str] = None

    def save(self, file_path: str) -> str:
        """Save raw audio data to the designated file path."""
        with open(file_path, "wb") as f:
            f.write(self.audio_bytes)
        self.output_path = file_path
        return file_path

    @property
    def size_bytes(self) -> int:
        """Return total size of the audio payload in bytes."""
        return len(self.audio_bytes)
