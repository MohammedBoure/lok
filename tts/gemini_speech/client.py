"""Gemini Speech Client: Production-ready modular client for Google Gemini Text-to-Speech."""

import base64
import io
import json
import logging
import os
import random
import re
import time
import wave
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union
import urllib.error
import urllib.parse
import urllib.request

try:
    import requests
except ImportError:
    requests = None

from .config import KeyManager, KeyState
from .exceptions import (
    AuthenticationError,
    GeminiSpeechError,
    KeyPoolExhaustedError,
    ModelNotFoundError,
    QuotaExceededError,
    SynthesisError,
)
from .models import SpeechModelInfo, SynthesisResult, VoiceProfile
from .voices import get_voice_profile, list_preset_voices

logger = logging.getLogger("gemini_speech.client")

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_TTS_MODEL = os.getenv("DEFAULT_SPEECH_MODEL", "gemini-3.1-flash-tts-preview")
DEFAULT_VOICE = os.getenv("DEFAULT_VOICE_NAME", "Puck")



@dataclass
class _HttpResponse:
    status_code: int
    text: str

    def json(self) -> Any:
        return json.loads(self.text)


def _pcm_to_wav(
    audio_bytes: bytes,
    mime_type: str,
    default_sample_rate: int = 24000,
    channels: int = 1,
    sample_width: int = 2,
) -> bytes:
    """Convert raw PCM audio bytes to standard WAV format if missing header."""
    # If already formatted container (WAV RIFF, MP3 ID3, or OGG/FLAC)
    if (
        audio_bytes.startswith(b"RIFF")
        or audio_bytes.startswith(b"ID3")
        or audio_bytes.startswith(b"\xff\xfb")
        or audio_bytes.startswith(b"OggS")
    ):
        return audio_bytes

    sample_rate = default_sample_rate
    if "rate=" in mime_type:
        match = re.search(r"rate=(\d+)", mime_type)
        if match:
            sample_rate = int(match.group(1))

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_out:
        wav_out.setnchannels(channels)
        wav_out.setsampwidth(sample_width)
        wav_out.setframerate(sample_rate)
        wav_out.writeframes(audio_bytes)
    return buffer.getvalue()


class GeminiSpeechClient:
    """High-level client for Google Gemini speech synthesis and model discovery.

    Supports multi-key rotation, automatic quota failover, rich acoustic prompts,
    preset voice profiles, and flexible output destinations.
    """

    def __init__(
        self,
        api_keys: Optional[List[str]] = None,
        default_model: Optional[str] = None,
        default_voice: Optional[str] = None,
        key_cooldown_seconds: float = 60.0,
        max_retries_per_request: int = 3,
        request_timeout: float = 45.0,
        env_file: Optional[str] = None,
    ) -> None:
        self.key_manager = KeyManager(
            api_keys=api_keys,
            base_cooldown_seconds=key_cooldown_seconds,
            env_file=env_file,
        )
        self.default_model = (
            default_model
            or os.getenv("DEFAULT_SPEECH_MODEL")
            or DEFAULT_TTS_MODEL
        )
        self.default_voice = (
            default_voice
            or os.getenv("DEFAULT_VOICE_NAME")
            or DEFAULT_VOICE
        )
        self.max_retries_per_request = max_retries_per_request
        self.request_timeout = request_timeout
        self._session = requests.Session() if requests is not None else None

    def _execute_with_failover(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
    ) -> _HttpResponse:
        """Execute HTTP request with automatic multi-key rotation, failover, and backoff."""
        attempt = 0
        last_error: Optional[Exception] = None
        params = params or {}

        # Error tuple for network failures
        network_errors: tuple = (urllib.error.URLError, TimeoutError, OSError)
        if requests is not None:
            network_errors = (requests.RequestException, *network_errors)

        while attempt < self.max_retries_per_request * max(1, self.key_manager.total_keys):
            attempt += 1
            key_state: Optional[KeyState] = None

            try:
                key_state = self.key_manager.get_active_key()
            except KeyPoolExhaustedError as exc:
                logger.error("Request aborted: %s", exc)
                raise

            request_params = dict(params)
            request_params["key"] = key_state.key
            url = f"{GEMINI_API_BASE}/{path.lstrip('/')}"

            try:
                response: _HttpResponse
                if self._session is not None:
                    raw_resp = self._session.request(
                        method=method,
                        url=url,
                        params=request_params,
                        json=json_body,
                        timeout=self.request_timeout,
                    )
                    response = _HttpResponse(status_code=raw_resp.status_code, text=raw_resp.text)
                else:
                    query_str = urllib.parse.urlencode(request_params)
                    full_url = f"{url}?{query_str}" if query_str else url
                    req_data = json.dumps(json_body).encode("utf-8") if json_body is not None else None
                    req = urllib.request.Request(full_url, data=req_data, method=method)
                    if json_body is not None:
                        req.add_header("Content-Type", "application/json")
                    try:
                        with urllib.request.urlopen(req, timeout=self.request_timeout) as http_resp:
                            text_content = http_resp.read().decode("utf-8")
                            response = _HttpResponse(status_code=http_resp.status, text=text_content)
                    except urllib.error.HTTPError as http_err:
                        text_content = http_err.read().decode("utf-8")
                        response = _HttpResponse(status_code=http_err.code, text=text_content)

                # HTTP 200 OK
                if response.status_code == 200:
                    self.key_manager.mark_success(key_state.index)
                    return response

                # Handle Quota / Rate Limiting (429)
                if response.status_code == 429:
                    error_msg = response.text
                    logger.warning(
                        "Quota exceeded (HTTP 429) on Key #%d (%s). Rotating key...",
                        key_state.index,
                        key_state.masked_key,
                    )
                    self.key_manager.mark_failure(
                        key_index=key_state.index,
                        status_code=429,
                        error_message="Quota/Rate limit exceeded (HTTP 429)",
                    )
                    time.sleep(random.uniform(0.5, 1.5))
                    continue

                # Handle Invalid / Revoked Key (401 / 403 with API_KEY_INVALID)
                if response.status_code in (401, 403):
                    resp_text = response.text
                    if "api key" in resp_text.lower() or "permission_denied" in resp_text.lower():
                        logger.error(
                            "Auth failure (HTTP %d) on Key #%d (%s).",
                            response.status_code,
                            key_state.index,
                            key_state.masked_key,
                        )
                        self.key_manager.mark_failure(
                            key_index=key_state.index,
                            status_code=response.status_code,
                            is_permanent=True,
                            error_message=resp_text,
                        )
                        continue

                # Handle Transient Server Error (500, 503)
                if response.status_code in (500, 502, 503, 504):
                    logger.warning(
                        "Transient server error %d on Key #%d. Retrying...",
                        response.status_code,
                        key_state.index,
                    )
                    self.key_manager.mark_failure(
                        key_index=key_state.index,
                        status_code=response.status_code,
                        error_message=f"Server error {response.status_code}",
                    )
                    backoff = (2 ** min(attempt, 3)) + random.uniform(0.1, 0.5)
                    time.sleep(backoff)
                    continue

                # Client error (400, 404, etc.)
                if response.status_code == 404:
                    raise ModelNotFoundError(f"Model or resource not found: {response.text}", status_code=404)

                raise GeminiSpeechError(
                    f"Gemini API request failed with status {response.status_code}: {response.text}",
                    status_code=response.status_code,
                )

            except network_errors as req_err:
                logger.warning(
                    "Network error with Key #%d (%s): %s",
                    key_state.index,
                    key_state.masked_key,
                    req_err,
                )
                self.key_manager.mark_failure(
                    key_index=key_state.index,
                    status_code=None,
                    error_message=str(req_err),
                )
                last_error = req_err
                time.sleep(random.uniform(0.5, 1.5))

        raise GeminiSpeechError(
            f"Exceeded maximum retries ({attempt} attempts) across key pool. Last error: {last_error}"
        )

    def list_speech_models(self) -> List[SpeechModelInfo]:
        """Fetch models from Google AI Studio / Gemini API, strictly filtering for speech/TTS-capable models.

        Returns:
            List[SpeechModelInfo]: Metadata of speech-capable models.
        """
        response = self._execute_with_failover(method="GET", path="models")
        payload = response.json()
        raw_models = payload.get("models", [])

        speech_models: List[SpeechModelInfo] = []
        speech_keywords = {"speech", "tts", "audio", "voice", "live"}

        for item in raw_models:
            model_id = item.get("name", "")
            display_name = item.get("displayName", "")
            description = item.get("description", "")
            methods = item.get("supportedGenerationMethods", [])

            # Check for speech/TTS indicators in name, display name, description, or output modalities
            combined_text = f"{model_id} {display_name} {description}".lower()
            is_speech_capable = any(kw in combined_text for kw in speech_keywords)

            # Specific known Gemini multimodal live/audio or TTS models
            clean_id = model_id.removeprefix("models/").lower()
            if "flash" in clean_id and ("tts" in clean_id or "audio" in clean_id or "live" in clean_id):
                is_speech_capable = True
            elif clean_id in {"gemini-3.8-flash-tts", "gemini-2.0-flash", "gemini-2.0-flash-exp", "gemini-2.5-flash"}:
                is_speech_capable = True

            if is_speech_capable:
                speech_models.append(
                    SpeechModelInfo(
                        model_id=model_id,
                        display_name=display_name or clean_id,
                        description=description,
                        supported_methods=methods,
                        input_token_limit=item.get("inputTokenLimit"),
                        output_token_limit=item.get("outputTokenLimit"),
                    )
                )

        # Fallback ensuring default model representation if endpoint returns limited catalog
        if not any(m.clean_id == self.default_model for m in speech_models):
            speech_models.insert(
                0,
                SpeechModelInfo(
                    model_id=f"models/{self.default_model}",
                    display_name="Gemini 3.8 Flash Text-to-Speech",
                    description="Optimized high-fidelity natural speech synthesis model.",
                    supported_methods=["generateContent"],
                ),
            )

        return speech_models

    def list_available_voices(self) -> List[VoiceProfile]:
        """Return the preset voice catalog containing vocal profiles and tone attributes."""
        return list_preset_voices()

    def generate_speech(
        self,
        text: str,
        model: Optional[str] = None,
        voice_name: Optional[str] = None,
        voice_style_prompt: Optional[str] = None,
        expressions: Optional[str] = None,
        output_path: Optional[str] = None,
        style_prompt: Optional[str] = None,
        emotional_tone: Optional[str] = None,
    ) -> SynthesisResult:
        """Synthesize natural speech from input text with acoustic steering and failover.

        Args:
            text: The narrative text to synthesize.
            model: Optional model override (defaults to gemini-3.8-flash-tts).
            voice_name: Voice name persona (defaults to Puck).
            voice_style_prompt: Natural acoustic prompt (tone, mood, pacing, delivery).
            expressions: Nuanced emotion and delivery directives.
            output_path: Optional destination file path to save audio (.wav).
            style_prompt: Optional alias for voice_style_prompt.
            emotional_tone: Optional emotional atmosphere / mood description (e.g. 'فاخر وهادئ').

        Returns:
            SynthesisResult: Container with audio bytes, MIME type, and telemetry.
        """
        if not text or not text.strip():
            raise SynthesisError("Input text to synthesize cannot be empty.")

        target_model = (model or self.default_model).strip()
        clean_model_id = target_model.removeprefix("models/")
        selected_voice = (voice_name or self.default_voice).strip()

        # Validate voice against preset catalog
        voice_info = get_voice_profile(selected_voice)
        effective_voice_name = voice_info.name if voice_info else selected_voice

        # Resolve effective style prompt and emotional tone directives
        effective_style = voice_style_prompt or style_prompt
        directives: List[str] = []
        if effective_style:
            directives.append(f"Style: {effective_style.strip()}")
        if emotional_tone:
            directives.append(f"Tone: {emotional_tone.strip()}")
        if expressions:
            directives.append(f"Expressions: {expressions.strip()}")

        # Build speech content with acoustic style steering
        prompt_text = text.strip()
        if directives:
            prompt_text = f"({', '.join(directives)})\n{prompt_text}"

        request_body: Dict[str, Any] = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt_text}
                    ]
                }
            ],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": {
                            "voiceName": effective_voice_name
                        }
                    }
                },
            },
        }

        fallback_models = [
            "gemini-3.1-flash-tts-preview",
            "gemini-3.8-flash-lite-tts",
            "gemini-2.5-flash-preview-tts",
            "gemini-3.8-flash-tts",
        ]
        candidate_models = [clean_model_id] + [m for m in fallback_models if m != clean_model_id]

        last_error = None
        for candidate in candidate_models:
            endpoint_path = f"models/{candidate}:generateContent"
            logger.info(
                "Synthesizing speech via '%s' (Voice: %s)...",
                candidate,
                effective_voice_name,
            )
            try:
                response = self._execute_with_failover(
                    method="POST",
                    path=endpoint_path,
                    json_body=request_body,
                )
                data = response.json()
                audio_bytes, mime_type = self._extract_audio_payload(data)

                # Convert raw PCM data to standard playable WAV container if needed
                wav_audio = _pcm_to_wav(audio_bytes=audio_bytes, mime_type=mime_type)

                result = SynthesisResult(
                    audio_bytes=wav_audio,
                    mime_type="audio/wav" if wav_audio.startswith(b"RIFF") else mime_type,
                    model_used=candidate,
                    voice_used=effective_voice_name,
                    key_index_used=self.key_manager._current_index,
                )

                if output_path:
                    result.save(output_path)
                    logger.info("Saved synthesized audio to '%s' (%d bytes).", output_path, len(wav_audio))

                return result
            except (KeyPoolExhaustedError, QuotaExceededError, GeminiSpeechError) as exc:
                last_error = exc
                logger.warning(
                    "Model '%s' failed (%s). Resetting key cooldown and trying fallback...",
                    candidate,
                    exc,
                )
                self.key_manager.reset_cooldowns()

        if last_error:
            raise last_error
        raise SynthesisError(f"Failed to synthesize speech across candidate models: {candidate_models}")


    @staticmethod
    def _extract_audio_payload(response_json: Dict[str, Any]) -> tuple[bytes, str]:
        """Extract base64-encoded audio bytes and MIME type from Gemini response."""
        candidates = response_json.get("candidates", [])
        if not candidates:
            feedback = response_json.get("promptFeedback", {})
            raise SynthesisError(
                f"No candidates returned by Gemini API. Feedback: {json.dumps(feedback)}"
            )

        content = candidates[0].get("content", {})
        parts = content.get("parts", [])

        for part in parts:
            inline_data = part.get("inlineData")
            if inline_data:
                mime = inline_data.get("mimeType", "audio/wav")
                raw_b64 = inline_data.get("data", "")
                if raw_b64:
                    return base64.b64decode(raw_b64), mime

        raise SynthesisError(
            f"No audio payload found in model candidates response: {json.dumps(parts)[:200]}"
        )
