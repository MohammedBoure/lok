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
- [`test_vision_script_and_app.py`](test_vision_script_and_app.py): Multimodal vision inference, emotional tone passing, and root runner test suite verifying:
  - Smart vision fallback logic and preset mapping (`test_smart_vision_fallback_logic`).
  - Multimodal vision script and mood inference (`test_infer_video_script_and_mood_execution`).
  - GeminiSpeechClient emotional tone and style prompt keyword parameters (`test_gemini_speech_client_emotional_tone_parameters`).
  - Autonomous pipeline execution (`auto_mode=True`) and verification of the 4 required agent telemetry logs (`test_process_mobile_video_auto_mode`).
  - Synchronous upload endpoint in auto_mode (`test_api_upload_and_process_auto_mode`).
  - Asynchronous job creation in auto_mode and status polling (`test_api_jobs_create_auto_mode`).
  - Host LAN IP detection in root `app.py` (`test_app_py_lan_ip_detection`).
  - Terminal banner and QR code generator in root `app.py` (`test_app_py_banner_output`).
- [`test_frontend_assets.py`](test_frontend_assets.py): Mobile web UI static asset and typography validation suite verifying:
  - Static asset files existence (`index.html`, `app.js`, `style.css`).
  - Required DOM elements for recording, presets, and studio controls.
  - DOM event listener references in `app.js`.
  - User Rule 5 character mapping compliance (no unmapped '٩').
  - Starlette static route file serving and content-type headers.
- [`test_mobile_enhancements.py`](test_mobile_enhancements.py): Enhancement verification suite verifying:
  - Open-source royalty-free background music library catalog, licenses, and file existence (`test_music_library_catalog`).
  - Voice mapping from web client identifiers to official Google Gemini TTS voice personas (`test_voice_mapping_to_gemini`).
  - REST endpoint `GET /api/music-tracks` serving open-source track catalog (`test_api_music_tracks_endpoint`).
  - Asynchronous background job creation via `POST /api/jobs/create` and status telemetry polling (`test_api_async_job_creation_and_telemetry`).
  - End-to-end video processing and dynamic ducking with real open-source acoustic piano music (`test_process_mobile_video_with_real_music`).
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
- [`test_production_principles.py`](test_production_principles.py): Production principles and dynamic AI governance test suite verifying:
  - Loading principles with default schema integrity and deep copy isolation (`test_load_principles_defaults`).
  - Saving customized voice, narrative, visual, and annotation principles (`test_save_principles_updates_memory_and_file`).
  - Factory reset of principles back to default rules (`test_reset_principles_restores_defaults`).
  - Gemini Vision prompt construction containing active production principles (`test_build_vision_prompt_principles_output`).
  - Gemini TTS voice directive prompt generation with emotional tone biasing (`test_build_tts_style_principles_output`).
  - REST endpoints `GET /api/principles`, `POST /api/principles`, and `POST /api/principles/reset` (`test_api_get_principles`, `test_api_post_principles`, `test_api_reset_principles`).
- [`test_video_annotation_mcp.py`](test_video_annotation_mcp.py): Video annotations and fast MCP tool test suite verifying:
  - FFmpeg `drawtext` filter text escaping (`test_escape_ffmpeg_drawtext`).
  - MCP tool schema definition for `annotate_video_cut` (`test_mcp_tool_definition`).
  - MCP JSON-RPC protocol support for `tools/list` and `tools/call` (`test_handle_mcp_call_tools_list`, `test_handle_mcp_call_missing_input_file`).
  - REST endpoint `POST /api/video/annotate` validation and file missing handling (`test_api_video_annotate_validation_error`).
- [`test_prompt_descriptions_and_agent.py`](test_prompt_descriptions_and_agent.py): SQLite prompt persistence and linguistic description processing agent test suite authored by `agy11`:
  - SQLite DB auto-seeding with realistic Algerian real estate prompts (`test_prompt_db_preseed`).
  - Prompt persistence, retrieval by ID, and metadata verification (`test_save_and_fetch_prompt`).
  - Record deletion and 404 validation (`test_delete_prompt`).
  - Asynchronous script updates (`test_update_prompt_script`).
  - REST endpoints `GET /api/prompts/history`, `POST /api/prompts`, and `DELETE /api/prompts/{id}` (`test_api_prompts_history`, `test_api_prompts_post_and_delete`).
  - Automated prompt recording during asynchronous job processing (`test_api_jobs_create_with_descriptions`).
  - Linguistic intent transformation and lower-third badge extraction (`test_smart_fallback_linguistic_speech_intent`, `test_smart_fallback_visual_intent_badges`).
- [`test_audio_sync_and_dense_vision.py`](test_audio_sync_and_dense_vision.py): Audio-visual lead-in synchronization, dense keyframe sampling, and Algerian voice profiles catalog test suite authored by `agy11`:
  - Real estate voice profiles catalog and Gemini persona mapping (`test_supported_voice_profiles_catalog`).
  - Voice profile resolution across standard aliases and custom personas (`test_resolve_voice_profile`).
  - REST API endpoint `GET /api/voices` returning structured voice profiles (`test_get_voices_rest_endpoint`).
  - Voice persona routing in `synthesize_narration` to GeminiSpeechClient (`test_synthesize_narration_voice_routing`).
  - Dense keyframe extraction timestamp distribution (8-16 frames uniformly sampled) across video durations (`test_compute_dense_keyframe_timestamps_distribution`).
  - Speaking window calculation with visual lead-in and outro swell buffer in vision analyzer (`test_vision_dense_sampling_and_speaking_window`).
  - Dense multimodal keyframe subsampling capped at 16 frames (`test_infer_video_script_dense_subsampling`).
  - FFmpeg `adelay` filter verification in `assemble_video.py` ensuring voiceover starts after visual establishing (`test_assemble_video_adelay_filter`).
  - Full pipeline bridge lead-in audio delay, outro music swell, and dense frame telemetry (`test_pipeline_bridge_adelay_audio_sync`).
  - Asynchronous video ingestion with custom voice and lead-in duration via `POST /api/jobs/create` (`test_api_jobs_create_with_voice_and_lead_in`).
- [`test_gatekeeper_audio_sync_and_voice.py`](test_gatekeeper_audio_sync_and_voice.py): Gatekeeper integration test suite for audio-visual sync, dense vision sampling, voice profiles, and mobile UI declutter authored by Quality Gatekeeper `agy100`:
  - Audio-visual lead-in delay filter insertion via FFmpeg `adelay` in `assemble_video.py` (`TestAudioVisualLeadInSync::test_assemble_video_adelay_filter_insertion`).
  - Mobile pipeline bridge default 1.2s visual lead-in and filtergraph generation (`TestAudioVisualLeadInSync::test_pipeline_bridge_adelay_and_default_lead_in`).
  - Dense keyframe timestamp distribution and boundary verification (8-16 frames) across video durations (`TestDenseVisionSampling::test_compute_dense_keyframe_timestamps_bounds`).
  - Speaking window calculation (`duration - visual_lead_in - outro_buffer`) and keyframe downsampling to 16 frames (`TestDenseVisionSampling::test_dense_sampling_speaking_window_and_prompt_injection`).
  - Algerian real estate voice catalog (ar-XA-Standard-A/B/C/D) and Gemini persona mapping (`TestVoiceSelectorAndApiContract::test_supported_voice_catalog_and_personas`).
  - Voice profile resolution with whitespace, case normalization, and fallbacks (`TestVoiceSelectorAndApiContract::test_resolve_voice_profile_normalizations`).
  - REST endpoint contract for `GET /api/voices` (`TestVoiceSelectorAndApiContract::test_get_voices_endpoint`).
  - Asynchronous job ingestion with voice selection and custom visual lead-in via `POST /api/jobs/create` (`TestVoiceSelectorAndApiContract::test_post_jobs_create_receives_voice_and_lead_in`).
  - Streamlined mobile UI layout: prominent voice selection card grid, single primary produce CTA button, and accessible `#submitBtn` alias (`TestMobileUiDeclutter::test_index_html_voice_cards_and_single_produce_cta`).
  - Responsive CSS styling for voice cards and collapsible option cards (`TestMobileUiDeclutter::test_style_css_voice_and_declutter_classes`).
  - Frontend voice state management, localStorage persistence, and `FormData` appending in `app.js` (`TestMobileUiDeclutter::test_app_js_voice_binding_and_localstorage_persistence`).
  - User Rule 5 typography and character mapping compliance prohibiting U+0669 (`TestTypographyCharacterMapping::test_no_forbidden_arabic_character`).
- [`test_gatekeeper_prompts_and_mobile_theme.py`](test_gatekeeper_prompts_and_mobile_theme.py): Comprehensive integration test suite authored by Quality Gatekeeper `agy100`:
  - Pragmatic SQLite CRUD operations and auto-seeding (`test_sqlite_auto_seed`, `test_sqlite_save_and_get_prompt`, `test_sqlite_get_recent_prompts_ordering`, `test_sqlite_update_prompt_script`, `test_sqlite_delete_prompt`).
  - REST API endpoint contracts and HTTP lifecycle (`test_api_prompts_history_endpoint`, `test_api_prompts_crud_lifecycle`).
  - Linguistic speech and visual intent conversion to narrative scripts and dynamic badges (`test_linguistic_speech_intent_conversion_to_narrative`, `test_visual_intent_badges_extraction`).
  - Automatic prompt persistence in SQLite upon video job creation (`test_automatic_prompt_recording_upon_video_job`).
  - Front-end mobile modal DOM structure and restoration controls in `index.html` (`test_frontend_html_mobile_modal_and_prompt_elements`).
  - Responsive CSS breakpoints (`max-width: 768px`, `max-width: 480px`), touch scrolling, and viewport sizing in `style.css` (`test_frontend_css_responsive_rules_and_modal_sizing`).
  - Front-end logic, prompt caching, restoration, saving, and dual button event bindings in `app.js` (`test_frontend_app_js_prompts_history_and_formdata_bindings`).
  - User Rule 5 Arabic typography compliance (`test_no_forbidden_arabic_character_compliance`).

## Running Tests Locally
Run all test suites via pytest from the workspace root:
```bash
pytest tests/ -v
# Targeted Gatekeeper sprint verification suite:
pytest tests/test_gatekeeper_audio_sync_and_voice.py tests/test_audio_sync_and_dense_vision.py tests/test_frontend_assets.py -v
# Prior sprint verification:
pytest tests/test_gatekeeper_prompts_and_mobile_theme.py tests/test_prompt_descriptions_and_agent.py -v
# Core pipeline integration:
pytest tests/test_pipeline.py -v
pytest tests/test_assemble_video.py -v
pytest tests/test_frame_extractor.py -v
```

## Critical Boundaries & Edge Cases
1. **Audio Sampling Alignment:** TTS narration is generated at 24000Hz mono PCM, which must be resampled and aligned to 48000Hz stereo AAC during final cut assembly.
2. **Music Ducking Verification:** Audio track utilizes FFmpeg sidechain compression (`sidechaincompress`) ducking the background music under voiceover bursts, ensuring voiceover clarity while allowing ambient swelling during pauses.
3. **Audio-Visual Lead-In Timing:** Video and background music establish for a configurable lead-in duration (default 1.2s - 1.5s) using FFmpeg `adelay` on narration audio before speech begins, preventing speech from preceding visual cues.
4. **Dense Multimodal Vision Bounds:** Keyframe extraction dynamically samples 8 to 16 frames uniformly across the video timeline, guaranteeing comprehensive architectural context without exceeding vision API token limits.
5. **Keyframe Resolution & Aspect Ratio:** Extracted keyframes maintain original 1280x720 16:9 aspect ratio and are formatted with proper timestamp indices.
6. **SQLite Concurrency & Auto-Seeding:** Prompt database initializes table structure and populates initial Algerian real estate prompts with atomic transactions (`timeout=15.0`).
7. **Linguistic Intent vs. Verbatim Text:** User prompt descriptions provide thematic guidance and intent; the vision agent weaves them into spoken Darja narrative scripts rather than reciting them literally.
8. **Mobile Touch & Viewport Boundaries:** The principles modal is bounded to `88vh`-`90vh` viewport heights with `-webkit-overflow-scrolling: touch` ensuring seamless scrolling on small mobile screens (360px-480px) and tablets (768px).
9. **Clean Merge Integrity:** Incoming feature branches must pass all unit and integration tests prior to gatekeeper clearance.

## Dependencies & Environment
- **Python:** 3.12+
- **Testing Framework:** `pytest >= 8.0`
- **System Binaries:** `ffmpeg`, `ffprobe` in system PATH (`/usr/bin/ffmpeg`, `/usr/bin/ffprobe`).
- **Required Environment Variables:** Handled by `.env` for speech generation services.
