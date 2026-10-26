# Test Suite Directory (`tests/`)

## Architectural Role & Scope
This directory contains automated unit, integration, and end-to-end pipeline verification tests for the video post-production system. It serves as the pragmatic quality gatekeeper validating visual frame extraction, MCP tool interfaces, neural TTS voiceover synthesis, synchronized video assembly, dynamic background music ducking, and metadata integrity.

## Itemized File Breakdown
- [`conftest.py`](conftest.py): Pytest configuration script that adds the project repository root to `sys.path`, ensuring local module discovery across test runners.
- [`test_pipeline.py`](test_pipeline.py): End-to-end pragmatic pipeline integration suite authored by Quality Gatekeeper `agy100`.
  - `TestMCPVisualExtractionTool`:
    - `test_video_metadata_parsing`: Validates video duration, frame rate, resolution, codec, and file size on source videos.
    - `test_mcp_get_image_from_video_programmatic`: Validates programmatic invocation of `mcp_get_image_from_video` with custom timestamps.
    - `test_mcp_cli_execution`: Validates command-line interface execution (`python -m frame_extractor`) and JSON schema output.
    - `test_keyframe_index_artifacts`: Verifies that `outputs/keyframes/frame_index.json` indexes all footage and all extracted image files exist and are non-empty.
  - `TestTTSVoiceoverGeneration`:
    - `test_narration_file_exists`: Verifies `outputs/narration.wav` exists and meets the file size threshold.
    - `test_narration_audio_specs_via_wave`: Verifies 16-bit PCM header, 24000Hz sampling rate, valid channels, and ~16.8s non-zero duration.
    - `test_tts_module_importable`: Verifies `tts` package integrity and local configuration.
  - `TestAssembledFinalCutVideo`:
    - `test_final_cut_exists`: Verifies `outputs/final_cut.mp4` exists and exceeds minimum deliverable size.
    - `test_final_cut_probe_streams`: Probes video (H.264, 1280x720, YUV420p, 16:9 aspect ratio) and audio (AAC, 48000Hz stereo) streams.
    - `test_final_cut_duration_sync`: Verifies video duration matches narrative pacing (~17.0 seconds).
    - `test_ducked_audio_track_levels`: Analyzes audio volume dynamics via `ffmpeg volumedetect` filter ensuring non-silent mixed sound with dynamic ducking.
  - `TestExecutionSummary`:
    - `test_execution_summary_schema`: Verifies all required fields (`output_video`, `narration`, `source_clips`, `editorial_timeline`, `audio_mixing_parameters`, `editorial_collective`) in `outputs/execution_summary.json`.
- [`test_frame_extractor.py`](test_frame_extractor.py): Visual extraction engine test suite verifying:
  - Technical metadata probing (`test_get_video_metadata_success`, `test_get_video_metadata_file_not_found`).
  - Native I-frame and scene cut transition detection (`test_detect_scene_cut_timestamps`, `test_detect_keyframe_timestamps`).
  - Frame extraction at explicit timestamps (`test_extract_frames_with_timestamps`).
  - Frame extraction using continuous sampling rates (`test_extract_frames_with_fps_sample`).
  - MCP programmatic tool invocation via `mcp_get_image_from_video` (`test_mcp_get_image_from_video_api`).
  - Command Line Interface execution and structured JSON stdout (`test_cli_invocation_json`).
  - Multi-video batch processing and index file generation (`test_process_videos_batch`).
  - MCP server initialization and tool registration (`test_mcp_server_tool_registration`).
- [`test_mobile_api.py`](test_mobile_api.py): Mobile API server and post-production bridge test suite verifying:
  - Algerian real estate presets catalog and bilingual metadata (`test_algerian_presets_catalog`).
  - Synthetic voiceover generation with harmonic formants and valid WAV headers (`test_synthetic_voice_generation`).
  - Portrait (9:16) video processing, keyframe extraction, and ducking assembly (`test_process_mobile_video_portrait`).
  - Landscape (16:9) video processing with custom narration script (`test_process_mobile_video_landscape_custom_script`).
  - Health check endpoint `GET /api/health` (`test_api_health_endpoint`).
  - Presets catalog endpoint `GET /api/presets` (`test_api_presets_endpoint`).
  - Mobile web studio frontend serving `GET /` (`test_api_index_endpoint`).
  - Multipart upload and post-production execution `POST /api/upload-and-process` (`test_api_upload_and_process_endpoint`).
  - Job status tracking `GET /api/status/{job_id}` and not-found handling (`test_api_status_not_found`).
  - Upload validation and error response for missing video (`test_api_upload_missing_video`).
  - Host LAN IP detection and format validation (`test_detect_lan_ip`).
  - Terminal QR code and banner generator execution (`test_server_banner_execution`).
- [`test_frontend_assets.py`](test_frontend_assets.py): Mobile web UI static asset and typography validation suite verifying:
  - Static asset files existence (`index.html`, `app.js`, `style.css`).
  - Required DOM elements for recording, presets, and studio controls.
  - DOM event listener references in `app.js`.
  - User Rule 5 character mapping compliance (no unmapped '٩').
  - Starlette static route file serving and content-type headers.
- [`test_mobile_verification.py`](test_mobile_verification.py): Pragmatic mobile pipeline gatekeeper verification suite authored by Quality Gatekeeper `agy100` verifying:
  - Algerian real estate preset catalog integrity, bilingual metadata, and descriptions (`test_algerian_presets_metadata_completeness`, `test_algerian_presets_descriptions_arabic`).
  - Synthetic harmonic voiceover generation, WAV headers, 24kHz PCM, and duration boundaries (`test_synthetic_voice_wav_header_and_duration`, `test_synthetic_voice_empty_text_fallback`).
  - Presets catalog serialization for web client consumption (`test_pipeline_bridge_get_presets_list_structure`).
  - Mobile video post-production error handling and missing file detection (`test_process_mobile_video_missing_file_raises_error`).
  - Graceful fallback for unsupported preset IDs (`test_process_mobile_video_unsupported_preset_fallback`).
  - Mobile cut execution summary schema and keyframe metadata persistence (`test_mobile_video_summary_metadata_schema`).
  - Custom audio ducking level override dynamics (`test_mobile_video_custom_ducking_volume`).
  - Host LAN IP detection and fallback socket error handling (`test_lan_ip_detection_format`, `test_lan_ip_fallback_handling`).
  - Starlette application route registration across all endpoints and static mounts (`test_server_app_routes_registered`).
  - Mobile responsive viewport and PWA metadata compliance (`test_mobile_html_responsive_viewport_and_pwa_tags`).
  - RTL directionality and User Rule 5 Arabic typography compliance (`test_mobile_html_arabic_rtl_and_character_mapping`).
  - Smartphone CSS media queries and luxury theme variables (`test_mobile_css_responsive_media_queries`).
  - Thread-safe parallel generation of synthetic audio (`test_concurrent_synthetic_voice_generation`).
- [`test_assemble_video.py`](test_assemble_video.py): Video editorial assembly test suite verifying:
  - Source video stream and format probing (`test_probe_file_inputs`).
  - Voiceover narration audio properties, duration, and sampling (`test_ensure_narration_audio_metadata`).
  - Keyframe matching against `outputs/keyframes/frame_index.json` (`test_find_matching_keyframes`).
  - Video assembly execution, stream rendering, and summary output (`test_assemble_video_execution`).
  - Primary production deliverables verification (`test_production_final_cut_deliverables`).

## Running Tests Locally
Run all test suites via pytest from the workspace root:
```bash
pytest tests/ -v
# or targeting specific test modules
pytest tests/test_pipeline.py -v
pytest tests/test_assemble_video.py -v
pytest tests/test_frame_extractor.py -v
```

## Critical Boundaries & Edge Cases
1. **Audio Sampling Alignment:** TTS narration is generated at 24000Hz mono PCM, which must be resampled and aligned to 48000Hz stereo AAC during final cut assembly.
2. **Music Ducking Verification:** Audio track utilizes FFmpeg sidechain compression (`sidechaincompress`) ducking the background music under voiceover bursts, ensuring voiceover clarity while allowing ambient swelling during pauses.
3. **Keyframe Resolution & Aspect Ratio:** Extracted keyframes maintain original 1280x720 16:9 aspect ratio and are formatted with proper timestamp indices.
4. **Clean Merge Integrity:** Incoming feature branches must pass all unit and integration tests prior to gatekeeper clearance.

## Dependencies & Environment
- **Python:** 3.12+
- **Testing Framework:** `pytest >= 8.0`
- **System Binaries:** `ffmpeg`, `ffprobe` in system PATH (`/usr/bin/ffmpeg`, `/usr/bin/ffprobe`).
- **Required Environment Variables:** Handled by `.env` for speech generation services.
