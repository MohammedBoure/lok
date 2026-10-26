# Test Suite Directory (`tests/`)

## Architectural Role & Scope
This directory contains automated unit and integration tests for the visual frame extraction engine, video metadata analysis, batch processing, Model Context Protocol (MCP) tool registrations, and editorial video assembly with audio ducking.

## Itemized File Breakdown
- [`conftest.py`](conftest.py): Pytest configuration script that adds the project repository root to `sys.path`, ensuring local module discovery across test environments.
- [`test_frame_extractor.py`](test_frame_extractor.py): Test suite verifying:
  - Technical metadata probing (`test_get_video_metadata_success`, `test_get_video_metadata_file_not_found`).
  - Native I-frame and scene cut transition detection (`test_detect_scene_cut_timestamps`, `test_detect_keyframe_timestamps`).
  - Frame extraction at explicit timestamps (`test_extract_frames_with_timestamps`).
  - Frame extraction using continuous sampling rates (`test_extract_frames_with_fps_sample`).
  - MCP programmatic tool invocation via `mcp_get_image_from_video` (`test_mcp_get_image_from_video_api`).
  - Command Line Interface execution and structured JSON stdout (`test_cli_invocation_json`).
  - Multi-video batch processing and index file generation (`test_process_videos_batch`).
  - MCP server initialization and tool registration (`test_mcp_server_tool_registration`).
- [`test_assemble_video.py`](test_assemble_video.py): Test suite verifying:
  - Source video stream and format probing (`test_probe_file_inputs`).
  - Voiceover narration audio properties, duration, and sampling (`test_ensure_narration_audio_metadata`).
  - Keyframe matching against `outputs/keyframes/frame_index.json` (`test_find_matching_keyframes`).
  - Video assembly execution, stream rendering, and summary output (`test_assemble_video_execution`).
  - Primary production deliverables verification (`test_production_final_cut_deliverables`).

## Running Tests
Run all tests via pytest from the repository root:
```bash
pytest tests/ -v
# or
python3 -m pytest tests/ -v
```

## Dependencies & Environment
- **Python:** 3.12+
- **Testing Framework:** `pytest >= 8.0`
- **System Binaries:** `ffmpeg`, `ffprobe` in system PATH (`/usr/bin/ffmpeg`, `/usr/bin/ffprobe`).
- **Required Environment Variables:** None (all paths are relative to workspace root).
