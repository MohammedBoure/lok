# Video Post-Production & MCP Orchestration Pipeline

An autonomous end-to-end video post-production system powered by Antigravity multi-agent orchestration. The system processes raw video clips, extracts visual frames via a custom Model Context Protocol (MCP) server, generates expressive neural voiceovers via local Gemini TTS, and splices/assembles synchronized final cuts with ducked audio.

## Pipeline Architecture
1. **MCP Tooling & Visual Extraction (`mcp_get_image_from_video`)**: Extracts keyframes and scene timestamps from input videos.
2. **Audio & Narration**: Integrates local `tts` module to generate natural voiceovers matched to narration scripts.
3. **agy Decision & Editing Collective**: Orchestrates clip cutting, visual rhythm, audio sync, and dynamic music ducking via FFmpeg.
4. **Quality Control & Delivery**: Renders production video and logs metadata.

## Directory Structure
- [`inputs/`](inputs/): Raw incoming video files and script descriptions.
- [`outputs/`](outputs/): Rendered assets, keyframes, voiceovers, and final cuts.
- [`tts/`](tts/): Local Gemini TTS speech synthesis client library.
- [`agent_assignments.json`](agent_assignments.json): Task registry tracking agent IDs, branches, and statuses.
