# Video Post-Production & MCP Orchestration Pipeline

An autonomous end-to-end video post-production system powered by Antigravity multi-agent orchestration. The system processes raw video clips, extracts visual frames via a custom Model Context Protocol (MCP) server, generates expressive neural voiceovers via local Gemini TTS, and splices/assembles synchronized final cuts with ducked audio.

## Pipeline Architecture
1. **MCP Tooling & Visual Extraction (`mcp_get_image_from_video`)**: Extracts keyframes, scene transitions, and video metadata from input footage with high visual fidelity.
2. **Audio & Narration**: Integrates local `tts` module to generate natural voiceovers matched to narration scripts.
3. **Editorial & Video Assembly (`assemble_video.py`)**: Orchestrates clip cutting, narrative pacing, audio sync, harmonic ambient synth generation, and dynamic music ducking via FFmpeg.
4. **Quality Control & Delivery**: Renders production video, executes integration tests, and logs metadata.

## Video Assembly & Editorial Decision Engine

The editorial assembly subsystem is implemented in [`assemble_video.py`](assemble_video.py) and provides automated video editing, scene transitions, and dynamic sidechain audio ducking.

### Key Capabilities
- **Synchronized Narrative Pacing**: Aligns visual cuts with narration dialogue and natural speech pauses.
  - *Segment 1*: Young fox cub exploring the autumn woodland (0.0s - 8.5s).
  - *Transition*: Smooth crossfade (0.5s duration at offset 8.0s) occurring during the narrative pause (7.90s - 8.71s).
  - *Segment 2*: Energetic squirrel dashing through autumn leaves (0.5s - 9.5s).
- **Harmonic Ambient Music Synthesis**: Synthesizes a warm woodland ambient pad drone using FFmpeg audio filter primitives (Open D pentatonic chord: D3, A3, D4, F#4, A4 layered with pink noise woodland breeze).
- **Dynamic Sidechain Ducking**: Uses FFmpeg `sidechaincompress` to duck ambient music ~18dB under spoken voiceover and allow gentle music swells during speech pauses and outro.
- **Universal Production Format**: Exports 1080p/720p H.264 video (`yuv420p`, 24 fps) and stereo AAC audio (48kHz, 192 kbps).
- **Execution Summary Logging**: Exports structured metadata to `outputs/execution_summary.json` matching editorial cuts with keyframe extraction indices.

### CLI Usage
```bash
# Run complete video assembly with default settings
python3 assemble_video.py

# Custom assembly with specific clip ranges and ducking parameters
python3 assemble_video.py \
  --fox-video inputs/source_fox_cub.mp4 \
  --squirrel-video inputs/source_squirrel.mp4 \
  --narration outputs/narration.wav \
  --output outputs/final_cut.mp4 \
  --summary outputs/execution_summary.json \
  --fox-start 0.0 --fox-end 8.5 \
  --squirrel-start 0.5 --squirrel-end 9.5 \
  --transition fade --transition-duration 0.5 \
  --duck-threshold 0.030 --duck-ratio 8.0 \
  --ambient-volume 0.45 --voice-volume 1.0
```

### Python Programmatic API
```python
import assemble_video

# Execute full assembly pipeline programmatically
summary = assemble_video.assemble_video(
    fox_video="inputs/source_fox_cub.mp4",
    squirrel_video="inputs/source_squirrel.mp4",
    narration_audio="outputs/narration.wav",
    output_video="outputs/final_cut.mp4",
    summary_output="outputs/execution_summary.json",
    fox_start=0.0,
    fox_end=8.5,
    squirrel_start=0.5,
    squirrel_end=9.5,
    transition_type="fade",
    transition_duration=0.5,
)
print("Rendered video duration:", summary["output_video"]["duration_seconds"])
print("Matched keyframes:", len(summary["source_clips"][0]["keyframes"]))
```

## Visual Frame Extractor & MCP Tool

The frame extraction subsystem is implemented in [`frame_extractor.py`](frame_extractor.py) and exposed as both a programmatic Python module and an MCP server.

### Key Capabilities
- **MCP Tool `mcp_get_image_from_video`**: Accepts `video_path`, optional `timestamps`, `fps_sample`, and `output_dir`.
- **High Visual Fidelity**: Extracts JPEG frames using FFmpeg high-quality quantization (`-q:v 2`) or lossless PNG.
- **Scene & Keyframe Detection**: Detects I-frames and scene cut boundaries using FFmpeg filter analytics.
- **Structured JSON Schema**: Returns extracted frame descriptors with indices, timestamps, resolutions, and file sizes alongside complete video stream metadata.

### CLI Usage
```bash
# Single video extraction with 1 fps sampling
python3 -m frame_extractor inputs/source_fox_cub.mp4 --fps-sample 1.0 --output-dir outputs/keyframes

# Single video extraction at specific timestamps
python3 -m frame_extractor inputs/source_squirrel.mp4 --timestamps 0.0,1.5,4.5,7.5 --json

# Batch processing multiple source clips and generating master frame index
python3 -m frame_extractor --batch inputs/source_fox_cub.mp4 inputs/source_squirrel.mp4 --fps-sample 1.0 --output-dir outputs/keyframes --index-file outputs/keyframes/frame_index.json

# Launch as Model Context Protocol (MCP) server over stdio
python3 -m frame_extractor --mcp
```

## Directory Structure
- [`.agent/`](.agent/): Operational directives and agent principles (`agy1.md`, `agy11.md`, `agy51.md`).
- [`inputs/`](inputs/): Raw incoming video footage (`source_fox_cub.mp4`, `source_squirrel.mp4`) and production requests.
- [`outputs/`](outputs/): Rendered assets, keyframes, TTS audio, and final cut exports.
  - [`outputs/keyframes/`](outputs/keyframes/): Extracted keyframe images and `frame_index.json`.
  - [`outputs/narration.wav`](outputs/narration.wav): High-quality Gemini TTS voiceover track.
  - [`outputs/final_cut.mp4`](outputs/final_cut.mp4): Completed 17-second synchronized video with ducked audio.
  - [`outputs/execution_summary.json`](outputs/execution_summary.json): Complete editorial and audio mixing metadata.
- [`tests/`](tests/): Automated test suite for frame extraction, MCP tool, and video processing.
- [`tts/`](tts/): Local Gemini TTS speech synthesis client library.
- [`assemble_video.py`](assemble_video.py): Editorial decision engine and FFmpeg video assembly script.
- [`frame_extractor.py`](frame_extractor.py): Visual extraction engine, CLI, and MCP tool provider.
- [`mcp_config.json`](mcp_config.json): MCP server registration configuration.
- [`agent_assignments.json`](agent_assignments.json): Task registry tracking agent IDs, branches, and statuses.

## Testing & Verification
Execute the test suite with pytest:
```bash
pytest tests/ -v
```
