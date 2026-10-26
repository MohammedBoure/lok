# Gemini Speech Client (`tts`)

A production-ready, modular client library for natural Text-to-Speech (TTS) using Google AI Studio / Gemini APIs, featuring automatic API key rotation, quota failover, model discovery, and acoustic steering.

## Key Features

1. **Flexible API Key Management**:
   - Supports `.env` loading using `python-dotenv` (with built-in standard library fallback).
   - Supports comma-separated keys (`GEMINI_API_KEYS=key1,key2,key3`), indexed variables (`GEMINI_API_KEY_1`, `GEMINI_API_KEY_2`, etc.), or single keys (`GEMINI_API_KEY`).
   - Supports explicit constructor injection override.

2. **Automatic Key Rotation & Health Tracking**:
   - Tracks per-key quota status and failure count.
   - Automatically places keys on cooldown upon receiving HTTP `429` (Quota/Rate limit) or transient errors, seamlessly retrying with the next healthy key.
   - Disables revoked/invalid keys upon HTTP `401`/`403`.
   - Exponential backoff and jitter for transient network glitches.
   - Transparent multi-model fallback rotation (`gemini-3.1-flash-tts-preview`, `gemini-3.8-flash-lite-tts`, `gemini-2.5-flash-preview-tts`, `gemini-3.8-flash-tts`) when free-tier per-model quotas are exhausted.

3. **Dedicated Speech Model Discovery**:
   - `list_speech_models()` queries the Gemini `models.list` API.
   - Filters results to return **only** speech-generation and TTS-capable models.

4. **Acoustic Styling & Expression Steering**:
   - `generate_speech()` supports `voice_style_prompt` (tone, pacing, delivery) and `expressions` (nuanced emotion).
   - Automatically wraps raw PCM audio streams into valid 16-bit 24kHz playable `.wav` containers.

5. **Rich Prebuilt Voice Personas**:
   - Includes `Puck`, `Charon`, `Kore`, `Fenrir`, `Aoede`, `Leda`, `Zephyr`, and `Orus` with character metadata.

## Directory Structure

- [`goal.md`](goal.md): Specification and requirements document for the Gemini TTS client library.
- [`.env.example`](.env.example): Template demonstrating supported API key environment formats.
- [`requirements.txt`](requirements.txt): Python dependency definitions.
- [`gemini_speech/`](gemini_speech/): Core modular library package. See [`gemini_speech/README.md`](gemini_speech/README.md).
  - [`__init__.py`](gemini_speech/__init__.py): Exposes top-level classes and functions.
  - [`client.py`](gemini_speech/client.py): Main [`GeminiSpeechClient`](gemini_speech/client.py#L65) class.
  - [`config.py`](gemini_speech/config.py): [`KeyManager`](gemini_speech/config.py#L75) and key pool management.
  - [`models.py`](gemini_speech/models.py): Data transfer and metadata containers.
  - [`voices.py`](gemini_speech/voices.py): Voice catalog and lookup functions.
  - [`exceptions.py`](gemini_speech/exceptions.py): Custom error types.
- [`examples/`](examples/): Executable demonstration scripts. See [`examples/README.md`](examples/README.md).
  - [`list_models_demo.py`](examples/list_models_demo.py): Speech model discovery demo.
  - [`list_voices_demo.py`](examples/list_voices_demo.py): Preset voices catalog inspection demo.
  - [`generate_speech_demo.py`](examples/generate_speech_demo.py): End-to-end TTS generation with acoustic styling.
- [`__init__.py`](__init__.py): Root package initialization exporting library components.
- [`__main__.py`](__main__.py): Command-line interface entry point for `python -m test_generate_sound`.
- [`create_story_voices.py`](create_story_voices.py): Script generating emotional Arabic and English children's story voiceovers.
- [`tests/`](tests/): Unit test suite covering key rotation, error handling, audio decoding, and CLI commands. See [`tests/README.md`](tests/README.md).

## Command-Line Interface (`python -m tts`)

You can invoke the library directly from any Bash or Terminal console:

### 1. Synthesize Speech (`generate`)
```bash
# Basic synthesis (defaults: Aoede voice, gemini-3.8-flash-tts model, output.wav)
python -m tts generate "Hello world, this is a test!"

# Advanced synthesis with custom voice, style prompt, and JSON output
python -m tts generate "Once upon a time in a whispering valley..." \
  -o bedtime_story.wav \
  -v Puck \
  -m gemini-3.8-flash-tts \
  -s "Enchanted bedtime storyteller" \
  -e "wonder, soothing cadence" \
  --json
```

### 2. List Voices (`list-voices`)
```bash
python -m tts list-voices
python -m tts list-voices --json
```

### 3. List Speech Models (`list-models`)
```bash
python -m tts list-models
python -m tts list-models --json
```

## Quick Start

### 1. Configuration
Copy `.env.example` to `.env` and insert your Gemini API key(s):
```bash
cp .env.example .env
```

### 2. Synthesize Speech
```python
from gemini_speech import GeminiSpeechClient

client = GeminiSpeechClient(default_model="gemini-3.8-flash-tts")

result = client.generate_speech(
    text="Once upon a time in a whispering grove, a tiny sparrow found a golden acorn.",
    voice_name="Puck",
    voice_style_prompt="Warm, relaxed bedtime storyteller",
    expressions="Gentle wonder and soothing cadence",
    output_path="story.wav"
)

print(f"Generated {result.size_bytes} bytes saved to {result.output_path}")
```

### 3. Run Unit Tests
```bash
python tts/tests/test_key_manager.py
python tts/tests/test_client.py
python tts/tests/test_cli.py
```
