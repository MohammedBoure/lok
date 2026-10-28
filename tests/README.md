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
  - User Rule 5 character mapping compliance (strictly mapping U+0669 to Arabic 'ج').
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
- [`test_clean_studio_and_session_ui.py`](test_clean_studio_and_session_ui.py): Decluttered studio interface, multi-sector linguistic guidance chips, and session login modal test suite authored by `agy51`:
  - UI decluttering verifying legacy `#presetSection` and `#customScriptContainer` are hidden from visible DOM (`test_studio_decluttering_legacy_controls_hidden`).
  - Linguistic guidance inputs (`#visualDescription`, `#speechDescription`) and commercial sector chips (real estate, restaurants, fashion, tech, auto) (`test_linguistic_guidance_inputs_and_merchant_chips_highlighted`).
  - Session login gateway modal, role toggle tabs, admin default credentials hint (`admin` / `admin123`), and merchant quick login buttons (`test_session_login_gateway_modal_and_default_credentials`).
  - Frontend auth lifecycle, session token persistence, and gated production check in `app.js` (`test_app_js_session_auth_and_gated_production_logic`).
  - Voice audition player controls and Web Audio fallback triggers (`test_voice_audition_player_elements_and_logic`).
  - CSS styling for login modals, soundwave animations, and guidance highlights (`test_css_login_and_soundwave_styles`).
  - Typography compliance ensuring no forbidden character U+0669 (`test_character_mapping_strict_compliance`).
  - HTTP index route delivery containing decluttered studio and auth components (`test_http_serving_of_clean_studio_and_login_modal`).
- [`test_gatekeeper_session_auth_and_tts.py`](test_gatekeeper_session_auth_and_tts.py): Comprehensive gatekeeper integration test suite for session authentication, service gating, clean studio, and TTS voice samples authored by Quality Gatekeeper `agy100`:
  - UI decluttering verifying `#presetSection` and `#customScriptContainer` are hidden with `display: none !important` (`TestUiDeclutteringAndLinguisticGuidance::test_legacy_controls_hidden_or_removed`).
  - Presence of multi-sector linguistic guidance inputs and recommendation chips (`TestUiDeclutteringAndLinguisticGuidance::test_multisector_linguistic_guidance_inputs_and_chips`).
  - Session login modal structure and admin credentials note (`TestUiDeclutteringAndLinguisticGuidance::test_session_login_modal_structure_and_admin_helper`).
  - CSS decluttering and modal styling rules (`TestUiDeclutteringAndLinguisticGuidance::test_css_decluttering_and_modal_styling`).
  - Session authentication verifying default admin credentials (`admin` / `admin123`) return session token and `admin` role (`TestSessionAuthenticationAndCredentials::test_admin_default_credentials_login_success`).
  - Merchant credentials login returning merchant session token (`TestSessionAuthenticationAndCredentials::test_merchant_default_credentials_login_success`).
  - Rejection of invalid credentials with HTTP 401 (`TestSessionAuthenticationAndCredentials::test_invalid_credentials_rejected`).
  - Session cookie and Bearer token retrieval via `/api/auth/session` (`TestSessionAuthenticationAndCredentials::test_session_cookie_and_bearer_token_retrieval`).
  - Session logout endpoint invalidating active sessions (`TestSessionAuthenticationAndCredentials::test_session_logout`).
  - Gated video production security: strictly rejecting unauthenticated requests to `/api/upload-and-process` and `/api/jobs/create` with HTTP 401 Unauthorized (`TestGatedServiceExecution::test_upload_and_process_unauthenticated_rejected_401`, `test_jobs_create_unauthenticated_rejected_401`).
  - Successful authorized video production with valid session cookie or Bearer token (`TestGatedServiceExecution::test_upload_and_process_authenticated_session_cookie_accepted`, `test_jobs_create_authenticated_bearer_token_accepted`).
  - TTS voice catalog integrity verifying all 4 personas (`ar-XA-Standard-A/B/C/D`) with custom scripts (`TestTtsVoiceReferenceSamples::test_voices_catalog_has_all_personas`, `test_voice_sample_scripts_and_no_character_u0669`).
  - Real TTS reference WAV audio generation (>2.0s duration, 24kHz PCM header) via internal TTS engine (`TestTtsVoiceReferenceSamples::test_get_or_create_voice_sample_generates_valid_wav`).
  - Audio streaming endpoint `GET /api/voices/{voice_id}/sample` and file caching (`TestTtsVoiceReferenceSamples::test_voice_sample_rest_api_endpoint`, `test_voice_sample_caching`).
  - Repository-wide typography compliance ensuring zero occurrences of forbidden character U+0669 (`TestCharacterMappingStrictCompliance::test_zero_forbidden_arabic_character_across_repo`).
- [`test_prompt_descriptions_and_agent.py`](test_prompt_descriptions_and_agent.py): SQLite prompt persistence and linguistic description processing agent test suite authored by `agy11`:
  - SQLite DB auto-seeding with realistic Algerian real estate prompts (`test_prompt_db_preseed`).
  - Prompt persistence, retrieval by ID, and metadata verification (`test_save_and_fetch_prompt`).
  - Record deletion and 404 validation (`test_delete_prompt`).
  - Asynchronous script updates (`test_update_prompt_script`).
  - REST endpoints `GET /api/prompts/history`, `POST /api/prompts`, and `DELETE /api/prompts/{id}` (`test_api_prompts_history`, `test_api_prompts_post_and_delete`).
  - Automated prompt recording during asynchronous job processing (`test_api_jobs_create_with_descriptions`).
  - Linguistic intent transformation and lower-third badge extraction (`test_smart_fallback_linguistic_speech_intent`, `test_smart_fallback_visual_intent_badges`).
- [`test_saas_dashboard_ui.py`](test_saas_dashboard_ui.py): Multi-tenant merchant studio, SaaS dashboard, voice preview player, and account switcher UI test suite authored by `agy51`:
  - Platform branding, active persona badge, and 3-tab navigation (`test_saas_branding_and_navigation`).
  - Pre-seeded merchant personas definitions and sector categorization in `app.js` (`test_saas_preseeded_merchant_personas`).
  - Merchant studio quota warning banners, aspect ratio selectors (9:16, 16:9, 1:1), and fixed text inputs in `index.html` (`test_merchant_studio_quota_and_appearance_controls`).
  - Merchant dashboard profile card, quota progress meters, and video library grid (`test_merchant_dashboard_elements`).
  - Admin dashboard platform metrics, users data table, and user creation modal forms (`test_admin_dashboard_and_user_management`).
  - Voice audition HTML5 audio streaming and Web Audio synthesizer fallback logic (`test_audio_audition_player_logic`).
  - Production quota enforcement and FormData binding for commercial text and orientation (`test_app_js_quota_enforcement_and_formdata_bindings`).
  - Responsive CSS rules for SaaS navigation tabs, cards, tables, and audition buttons (`test_css_saas_rules_and_responsiveness`).
  - Typography compliance ensuring no forbidden Arabic numeral U+0669 (`test_saas_character_mapping_compliance`).
  - HTTP index route delivery containing all SaaS front-end components (`test_saas_dashboard_http_serving`).
- [`test_session_auth_and_tts_samples.py`](test_session_auth_and_tts_samples.py): Comprehensive test suite for session-based authentication, default admin credentials, strictly gated video production, and real Google Gemini TTS voice reference samples authored by `agy11`:
  - Password hashing via PBKDF2-HMAC-SHA256 with cryptographically random salts and constant-time verification (`TestPasswordHashingAndVerification`).
  - Pre-seeded default Admin credentials (`admin` / `admin123`) and default merchant credentials (`merchant123`) verification (`TestPreseededCredentials`).
  - Session lifecycle management in SQLite `sessions` table (creation, retrieval, expiration, and deletion) (`TestSessionLifecycleDB`).
  - Session REST endpoints (`POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/session`, `GET /api/auth/me`) validating session cookies and Bearer tokens (`TestRestApiAuthEndpoints`).
  - Strictly gated service execution rejecting unauthenticated video generation calls with HTTP 401 Unauthorized, and accepting valid session and permanent tokens (`TestGatedServiceExecution`).
  - Real TTS voice reference samples validation on disk for all 4 personas with valid WAV headers and duration > 2.0s (`TestTtsVoiceReferenceSamples`).
  - Voice preview audio streaming endpoint verification (`GET /api/voices/{voice_id}/sample`) (`TestTtsVoiceReferenceSamples`).
  - Absence of forbidden character U+0669 in all voice sample scripts and responses (`TestCharacterMappingCompliance`).
- [`test_gatekeeper_saas_platform.py`](test_gatekeeper_saas_platform.py): Comprehensive gatekeeper integration test suite for multi-tenant SaaS platform authored by Quality Gatekeeper `agy100`:
  - Multi-tenant admin user creation with custom expiration (`expires_at`), daily/weekly quotas (`daily_quota`, `weekly_quota`), and user patching (`TestAdminUserCreationAndQuotas`).
  - Quota exhaustion enforcement returning HTTP 403 Forbidden for daily and weekly limits (`TestQuotaEnforcement`).
  - Subscription expiration and deactivated account access denial returning HTTP 403 (`TestAccountExpirationAndDeactivation`).
  - Full catalog verification of 10 commercial merchant personas covering 10 business sectors plus 1 Master Admin (`TestPreseededMerchantPersonas`).
  - Live voice audition preview audio streaming (`GET /api/voices/{voice_id}/sample`) and cache validation (`TestLiveVoiceAuditionPreview`).
  - Commercial video options including fixed text, badge/banner positions, color styling, and video orientation (`TestCommercialVideoOptions`).
  - Front-end SaaS UI DOM elements, state transitions, tab switching, and quota meters (`TestFrontendSaasUiContracts`).
  - Strict character mapping compliance prohibiting Arabic numeral U+0669 across all project files (`TestStrictCharacterMapping`).
- [`test_saas_auth_and_quotas.py`](test_saas_auth_and_quotas.py): Multi-tenant SaaS authentication, quota enforcement, admin governance, and voice audition preview test suite authored by `agy11`:
  - Pre-seeding master admin and 10 commercial merchants across distinct industries (`test_auth_db_initial_preseed`).
  - Token and credential authentication resolution (`test_auth_db_authenticate_token_and_credentials`).
  - Daily and rolling weekly quota limit verification with Arabic messages (`test_auth_db_check_quota_logic`).
  - Account deactivation and subscription expiration blocking (`test_auth_db_check_quota_expired_and_inactive`).
  - Admin account CRUD lifecycle, user updates, and platform stats (`test_auth_db_admin_user_crud`).
  - Auth REST API endpoints `POST /api/auth/login`, `GET /api/auth/me`, and `GET /api/auth/demo-accounts` (`test_api_auth_endpoints`).
  - Admin REST API endpoints `GET /api/admin/users`, `POST /api/admin/users`, `PATCH /api/admin/users/{user_id}`, and `GET /api/admin/stats` with token gatekeeping (`test_api_admin_management_endpoints`).
  - Voice audition preview endpoint `GET /api/voices/{voice_id}/sample` returning cached WAV audio (`test_api_voice_sample_preview_endpoint`).
  - End-to-end video job creation with merchant token authentication, fixed text banner overlay, aspect ratio framing, and generation audit logging (`test_video_generation_with_auth_and_quota_audit`).
  - Video job quota ceiling enforcement returning HTTP 403 Forbidden upon exhaustion (`test_video_generation_quota_rejection`).
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

- [`test_admin_portal_and_security.py`](test_admin_portal_and_security.py): Admin portal backend & Prompt Security Guardrail test suite authored by Lead Backend Engineer `agy11`:
  - Master administrator provisioning and PBKDF2 authentication (`pluto` / `plutosw4`) with role `admin`.
  - Admin login endpoint `POST /api/admin/login` issuing active session token.
  - Dedicated Bootstrap admin dashboard serving `GET /admin` with 200 OK HTML.
  - Full accounts CRUD and date validity management (`GET /api/admin/accounts`, `POST /api/admin/accounts`, `PATCH /api/admin/accounts/{user_id}`).
  - Account lifecycle tracking in SQLite table `user_activity_logs` (`GET /api/admin/accounts/{user_id}/logs`).
  - Quota enforcement gating accounts by active status, future start date (`valid_from`), and expiration date (`expires_at`).
  - Prompt security guardrails (`sanitize_and_validate_prompt`) blocking directory traversal (`../`), command substitution (`$(...)`, `` `...` ``), destructive commands (`rm`), network utilities (`curl`, `wget`), and shell evaluation (`bash`, `sh`, `eval`, `subprocess`).
  - Safe prompt instruction extraction (`parse_prompt_instructions`) for speech speed and emotional tone without shell execution.
  - API endpoint injection rejection with HTTP 400 Bad Request on `POST /api/jobs/create` and `POST /api/upload-and-process`.
  - User Rule 5 Arabic typography compliance (strictly zero occurrences of character U+0669).

- [`test_minimal_lok_and_admin_ui.py`](test_minimal_lok_and_admin_ui.py): Frontend minimalist 'lok' client UI & Bootstrap admin portal test suite authored by Lead Frontend Engineer `agy51`:
  - 'lok' studio branding, typography tokens, and RTL interface structure (`TestMinimalLokClientUi`).
  - Gated authentication view (#loginView) before studio access with merchant credential login.
  - Minimal studio essential controls: pre-recorded video upload dropzone (no webcam recording), detailed prompt textarea with speed/tone/visuals guidance, settings button, and produce video CTA.
  - Settings modal with Back button, daily/weekly balance indicators, recommendations manager (CRUD), Algerian Darja voice audition player (`ar-XA-Standard-A/B/C/D`), and logout action.
  - Authentic high-contrast monochrome Black & White theme tokens (`TestModernBlackAndWhiteTheme`).
  - Dedicated Bootstrap 5 admin portal markup verification (`TestDedicatedBootstrapAdminPortal`).
  - Standalone embedded CSS stylesheet verification (`test_admin_standalone_embedded_css_stylesheet`): self-contained grid (`.container`, `.row`, `.col-*`), cards, responsive tables, badge statuses (`.bg-success`, `.bg-danger`, `.badge-active`, etc.), form controls, alerts, and high-z-index modal dialogs without CDN dependencies.
  - Offline standalone JS polyfill verification (`test_admin_standalone_offline_js_polyfill`): native fallback implementation for `window.bootstrap.Modal` and `window.bootstrap.Toast` for complete offline air-gapped functionality.
  - Strict typography compliance prohibiting forbidden Arabic character U+0669 (`TestStrictTypographyCompliance`).

- [`test_gatekeeper_admin_and_minimal_ui.py`](test_gatekeeper_admin_and_minimal_ui.py): Comprehensive integration gatekeeper verification suite authored by Quality Gatekeeper `agy100`:
  - Bootstrap 5 Admin Portal HTTP serving (`GET /admin`) and master admin credentials authentication (`POST /api/admin/login` with `pluto` / `plutosw4`).
  - HTTP 401 Unauthorized rejection for invalid credentials and non-admin logins.
  - Accounts management lifecycle: listing accounts with valid_from, expires_at, daily/weekly quotas, status (`GET /api/admin/accounts`), account creation (`POST /api/admin/accounts`), updates (`PATCH /api/admin/accounts/{user_id}`), and activity logs (`GET /api/admin/accounts/{user_id}/logs`).
  - Global platform telemetry endpoint (`GET /api/admin/stats`).
  - Prompt Security Guardrail (`sanitize_and_validate_prompt`) rejecting command injections (`;`, `&&`, `|`), destructive utilities (`rm`), downloaders (`curl`, `wget`), shells (`bash`, `sh`), evaluation (`eval`, `subprocess`), and path traversal (`../`) with `ValueError` and API HTTP 400 Bad Request.
  - Verification of safe parameter extraction (`parse_prompt_instructions`) for speech speed and emotional tone.
  - Gated authentication and decluttered minimalist 'lok' Studio UI contracts.
  - Settings view contracts: current balance indicator, recommendations manager, Algerian Darja audition player, and logout.
  - Repository-wide character mapping compliance confirming zero occurrences of forbidden Arabic character U+0669.

## Running Tests Locally
Run all test suites via pytest from the workspace root:
```bash
pytest tests/ -v
# Targeted Admin Portal, Prompt Security Guardrail, and Minimalist 'lok' Studio sprint verification suite:
pytest tests/test_gatekeeper_admin_and_minimal_ui.py tests/test_admin_portal_and_security.py tests/test_minimal_lok_and_admin_ui.py -v
# Targeted Session Auth, Gated Services, and Clean Studio sprint verification suite:
pytest tests/test_gatekeeper_session_auth_and_tts.py tests/test_session_auth_and_tts_samples.py tests/test_clean_studio_and_session_ui.py -v
# Targeted SaaS Platform Gatekeeper sprint verification suite:
pytest tests/test_gatekeeper_saas_platform.py tests/test_saas_auth_and_quotas.py tests/test_saas_dashboard_ui.py tests/test_frontend_assets.py -v
# Prior sprint verifications:
pytest tests/test_gatekeeper_audio_sync_and_voice.py tests/test_audio_sync_and_dense_vision.py -v
pytest tests/test_gatekeeper_prompts_and_mobile_theme.py tests/test_prompt_descriptions_and_agent.py -v
# Core pipeline integration:
pytest tests/test_pipeline.py -v
pytest tests/test_assemble_video.py -v
pytest tests/test_frame_extractor.py -v
```

## Critical Boundaries & Edge Cases
1. **Service Gating & Session Authentication:** Video production endpoints (`/api/upload-and-process`, `/api/jobs/create`) strictly enforce authentication; requests missing a valid session cookie or Bearer token are rejected immediately with HTTP 401 Unauthorized.
2. **Default Admin & Merchant Credential Boundaries:** The system auto-provisions master admin (`admin` / `admin123`) and merchant accounts (`merchant123`) using PBKDF2-HMAC-SHA256 password hashing.
3. **TTS Voice Reference Audio Generation:** Reference audio samples for all 4 supported voices (`ar-XA-Standard-A/B/C/D`) are synthesized with real acoustic formants (>2.0s duration, 24000Hz mono PCM WAV header) and served via `/api/voices/{voice_id}/sample`.
4. **Studio UI Decluttering & Guidance:** Real estate presets and verbatim script inputs are hidden (`display: none !important; aria-hidden="true"`), prioritizing visual scene intent and spoken tone direction with commercial recommendation chips.
5. **Multi-Tenant Quota Ceilings:** Merchant accounts are bounded by daily and rolling weekly quota ceilings; any generation exceeding these ceilings returns HTTP 403 Forbidden with actionable Arabic error telemetry.
6. **Subscription Expiration Enforcement:** Accounts whose `expires_at` timestamp is in the past or whose `is_active` flag is 0 are immediately barred from generation operations.
7. **Multi-Aspect Ratio Framing:** Commercial video framing supports portrait (9:16), landscape (16:9), and square (1:1) video orientations without distorting source footage.
8. **Audio Sampling Alignment:** TTS narration is generated at 24000Hz mono PCM, which must be resampled and aligned to 48000Hz stereo AAC during final cut assembly.
9. **Music Ducking Verification:** Audio track utilizes FFmpeg sidechain compression (`sidechaincompress`) ducking the background music under voiceover bursts, ensuring voiceover clarity while allowing ambient swelling during pauses.
10. **Audio-Visual Lead-In Timing:** Video and background music establish for a configurable lead-in duration (default 1.2s - 1.5s) using FFmpeg `adelay` on narration audio before speech begins, preventing speech from preceding visual cues.
11. **Dense Multimodal Vision Bounds:** Keyframe extraction dynamically samples 8 to 16 frames uniformly across the video timeline, guaranteeing comprehensive architectural context without exceeding vision API token limits.
12. **Keyframe Resolution & Aspect Ratio:** Extracted keyframes maintain original 1280x720 16:9 aspect ratio and are formatted with proper timestamp indices.
13. **SQLite Concurrency & Auto-Seeding:** Prompt and auth databases initialize table structures and populate initial personas with atomic transactions (`timeout=15.0`).
14. **Linguistic Intent vs. Verbatim Text:** User prompt descriptions provide thematic guidance and intent; the vision agent weaves them into spoken Darja narrative scripts rather than reciting them literally.
15. **Mobile Touch & Viewport Boundaries:** The principles modal is bounded to `88vh`-`90vh` viewport heights with `-webkit-overflow-scrolling: touch` ensuring seamless scrolling on small mobile screens (360px-480px) and tablets (768px).
16. **Clean Merge Integrity:** Incoming feature branches must pass all unit and integration tests prior to gatekeeper clearance.

## Dependencies & Environment
- **Python:** 3.12+
- **Testing Framework:** `pytest >= 8.0`
- **System Binaries:** `ffmpeg`, `ffprobe` in system PATH (`/usr/bin/ffmpeg`, `/usr/bin/ffprobe`).
- **Required Environment Variables:** Handled by `.env` for speech generation services.
