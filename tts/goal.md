# Gemini Text-to-Speech (TTS) SDK & CLI

Modular Text-to-Speech client library and standalone Command-Line Interface (CLI) integrating Google AI Studio Gemini APIs, targeting the `gemini-3.8-flash-tts` model endpoint.

## Specifications

### Environment & Authentication
- Automatic `.env` ingestion supporting:
  - Multi-key string: `GEMINI_API_KEYS=key1,key2,key3`
  - Indexed keys: `GEMINI_API_KEY_1`, `GEMINI_API_KEY_2`, etc.
  - Runtime override via constructor parameters or CLI `--api-key`
- Key health tracking pool with automated rotation and exponential backoff cooldown upon HTTP 429 / RESOURCE_EXHAUSTED errors
- Transparent failover retry mechanism with stderr rotation logging

### Library Interface
- `list_speech_models()`: Queries API models and filters exclusively for TTS/speech capabilities.
- `list_available_voices()`: Returns supported voices with metadata (gender, language tags, vocal characteristics).
- `generate_speech(text, model="gemini-3.8-flash-tts", voice_name="Puck", voice_style_prompt=None, expressions=None, output_path="output.mp3")`: Synthesizes audio payloads using stylistic natural-language directing instructions and persists binary outputs to disk.

### Command-Line Interface
- Executable binary/script exposing:
  - `list-models`: Tabular display of available TTS endpoints.
  - `list-voices`: Formatted display of available voices and characteristics.
  - `generate <text>`: Synthesizes input text to audio file.
    - `--model` (Default: `gemini-3.8-flash-tts`)
    - `--voice` (Default: `Puck`)
    - `--style` (Optional: natural language voice directing)
    - `-o, --output` (Default: `output.mp3`)
- POSIX-compliant exit codes, progress feedback, and POSIX signal trapping (SIGINT/SIGTERM).

### System Architecture
- Multi-tier decoupling:
  - `KeyManager`: State machine for key pool lifecycle, cooldown timeouts, and cursor rotation.
  - `TTSClient`: Transport layer managing payload framing, model routing, and binary stream decoding.
  - `CLI`: Presentation and arguments parsing layer decoupled from client logic.