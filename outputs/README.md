# Outputs Directory

This directory stores rendered intermediate assets, extracted keyframes, TTS audio files, and final exported video cuts produced by the video post-production pipeline.

## Directory Structure & Deliverables

### 1. Keyframes Directory (`keyframes/`)
- Contains sampled visual keyframes (`.jpg`) extracted from raw input videos (`source_fox_cub.mp4` and `source_squirrel.mp4`).
- [`frame_index.json`](keyframes/frame_index.json): Master metadata extraction index capturing frame indices, exact timestamps, resolutions, scene transitions, and file sizes.

### 2. Neural Voiceover Track (`narration.wav`)
- **Format**: WAV / Waveform Audio (PCM signed 16-bit little-endian, `pcm_s16le`).
- **Sample Rate**: 24,000 Hz, Mono (1 channel).
- **Exact Duration**: 16.800000 seconds.
- **Synthesized Voice**: `Aoede` (Melodic, expressive, polished, thoughtful cadence).
- **Model**: `gemini-3.8-flash-tts` via local `tts` module (`python -m tts generate`).
- **Script**:
  > *"Deep in the heart of the golden autumn forest, a young fox cub takes his first adventurous steps into the quiet wild. Nearby, a spirited baby squirrel dashes through the fallen leaves, celebrating another bright morning in nature's sanctuary."*

### 3. Final Production Cut (`final_cut.mp4`)
- **Container**: MP4 (QuickTime / MOV container).
- **Duration**: 17.000000 seconds (408 frames @ 24 fps).
- **Video Stream**:
  - Codec: H.264 / AVC (`libx264`, High Profile).
  - Resolution: 1280x720 (16:9 widescreen).
  - Frame Rate: 24.0 fps progressive.
  - Pixel Format: `yuv420p` (universal device and web player compatibility).
- **Audio Stream**:
  - Codec: AAC (Advanced Audio Coding, LC).
  - Sample Rate: 48,000 Hz, Stereo (2 channels).
  - Bit Rate: 192 kbps.
  - Mix Structure: Front-centered voiceover dynamically sidechained over a harmonic woodland ambient synth pad drone (Open D pentatonic chord with pink noise breeze texture).

### 4. Shared Execution Summary (`execution_summary.json`)
- Comprehensive post-production record containing:
  - Source clips used, selected segment start/end timestamps.
  - TTS voiceover metadata, duration, and pacing analysis.
  - Editorial cut points, crossfade offsets, and scene transitions.
  - Audio mixing and dynamic ducking parameters (threshold, ratio, attack/release times).
  - Keyframe references linked to `outputs/keyframes/frame_index.json`.

## Maintenance & Governance
- **Audio & Video Assembly**: Implemented and rendered by Editorial Collective `agy51`.
- **Keyframe Extraction**: Extracted and indexed by Squad `agy11`.
- **Verification & Gatekeeping**: Tested and validated by Quality Control Squad `agy100`.
