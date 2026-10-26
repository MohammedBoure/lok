# Lead Orchestrator Directive (`agy1`)

## Mission
Orchestrate the multi-agent video post-production fleet to deliver an end-to-end video pipeline:
1. Dispatch backend agent `agy11` (`worker-1`) to build the visual frame extraction MCP tool (`mcp_get_image_from_video`) and video analysis utility.
2. Dispatch UI/Editorial agent `agy51` (`worker-2`) to implement the editorial decision engine, TTS narration generator interface, and FFmpeg video assembly with ducked background music.
3. Dispatch testing agent `agy100` (`worker-3`) to run integration validation tests and act as gatekeeper for merging into `develop`.
4. Orchestrate final verification and release merge into `main`.
