# Gemini Speech Module (`gemini_speech`)

Modular Python client library providing high-quality Text-to-Speech (TTS) using Google AI Studio / Gemini APIs, with multi-key failover rotation and acoustic steering.

## Files
- [`__init__.py`](__init__.py): Package entry point exposing client classes, models, and custom exceptions.
- [`client.py`](client.py): Main [`GeminiSpeechClient`](client.py#L65) implementation managing model discovery (`list_speech_models`), speech generation (`generate_speech`), acoustic styling, and automatic request failover.
- [`config.py`](config.py): API key management, environment variable parsing (`GEMINI_API_KEYS`, indexed keys), key health monitoring, cooldown logic, and key rotation.
- [`models.py`](models.py): Data models representing speech models ([`SpeechModelInfo`](models.py#L8)), voice personas ([`VoiceProfile`](models.py#L25)), and audio synthesis outputs ([`SynthesisResult`](models.py#L38)).
- [`voices.py`](voices.py): Voice persona catalog and metadata covering prebuilt voices (`Puck`, `Charon`, `Kore`, `Fenrir`, `Aoede`, etc.).
- [`exceptions.py`](exceptions.py): Custom exceptions hierarchy including [`KeyPoolExhaustedError`](exceptions.py#L19), [`QuotaExceededError`](exceptions.py#L29), and [`SynthesisError`](exceptions.py#L39).
