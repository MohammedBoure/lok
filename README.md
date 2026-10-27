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

## 1-Command Startup: Root Platform Runner (`app.py`)

Run the entire platform with one single command:
```bash
python app.py
```
This automatically:
- Detects your local LAN IP (e.g. `192.168.1.7`).
- Generates an ASCII QR code in your terminal pointing to `http://<LAN_IP>:8000`.
- Starts the production Uvicorn server on `0.0.0.0:8000` with graceful shutdown handling.

## Multi-Tenant SaaS Platform & Merchant Studio

The platform features a multi-tenant SaaS architecture supporting autonomous commercial video generation across diverse merchant sectors with enterprise administrative controls:

### Key SaaS Capabilities
1. **Session-Based Authentication & Gateway**:
   - Master Administrator account (`admin`) with default password (`admin123`), full tenant governance, and session persistence.
   - Session authentication endpoints: `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/session`, and `GET /api/auth/me`.
   - **Gated Service Execution**: Actual video post-production endpoints (`/api/upload-and-process`, `/api/jobs/create`) strictly require an authenticated active session or valid bearer token, rejecting unauthorized requests with HTTP 401.
   - Interactive Login Gateway Modal: Switch seamlessly between Admin Login and 1-tap demo merchant quick login with visual credential hints.
2. **Admin Governance & Tenant Quotas**:
   - Master Administrator account (`admin`) with full tenant management.
   - Per-merchant quota ceilings: configurable daily video quota (`daily_quota`) and rolling 7-day weekly quota (`weekly_quota`).
   - Subscription lifecycle control: custom expiration dates (`expires_at`), instant account activation/suspension (`is_active`).
   - Real-time administrative metrics via `GET /api/admin/stats` and user usage audits via `GET /api/admin/users`.
3. **Pre-Seeded Multi-Vertical Commercial Personas**:
   - Out-of-the-box pre-configured accounts across 10 distinct commercial sectors with custom branding, quotas, and expiration:
     1. *Real Estate (عقارات فاخرة)*: `merchant_realestate`
     2. *Seafood Restaurant (مطعم وبسترو مأكولات بحرية)*: `merchant_restaurant`
     3. *Luxury Fashion (أزياء وملابس راقية)*: `merchant_fashion`
     4. *Smart Tech & Electronics (تقنية وإلكترونيات ذكية)*: `merchant_tech`
     5. *Auto Showroom (معرض سيارات ومركبات)*: `merchant_auto`
     6. *Traditional Handcrafts (صناعات تقليدية وزرابي)*: `merchant_crafts`
     7. *Coastal Tourism & Travel (سياحة وأسفار ساحلية)*: `merchant_tourism`
     8. *Modern Home Decor (أثاث وديكور منزلي عصري)*: `merchant_decor`
     9. *Medical & Aesthetics Clinic (عيادة طبية وتجميلية)*: `merchant_clinic`
     10. *Fitness & Sports Club (نادي رياضي ولياقة بدنية)*: `merchant_gym`
4. **TTS Voice Reference Benchmarks & Live Audition Player**:
   - High-fidelity voice reference audio synthesized directly via the project's internal `tts` library (`from tts import synthesize_narration` / `gemini_speech`) for all voice personas (`ar-XA-Standard-A/B/C/D`) and stored in `outputs/voice_samples/`.
   - Merchants can click "▶ استمع للصوت" to stream the exact acoustic reference benchmark via `GET /api/voices/{voice_id}/sample` before selecting their narrator.
5. **Commercial Video Framing & Fixed Screen Overlays**:
   - Aspect ratio formatting: Portrait (9:16 vertical for smartphones/Reels), Landscape (16:9 widescreen), and Square (1:1 feed).
   - Fixed text overlay customization: Merchant slogan, contact phone, or call-to-action placed in lower-third banner, top banner, or floating badge.
   - High-contrast visual themes: Modern White (أبيض عصري), Luxury Gold (ذهبي فاخر), and Commercial Red (تجاري بارز).
6. **Decluttered Non-Technical Merchant Studio UI**:
   - Completely removes restrictive real estate presets and verbatim script inputs from the visible studio DOM.
   - Empowers merchants to define visual scene intent and speech tone guidance with multi-sector recommendation chips (عقارات, مطاعم, أزياء, تقنية, سيارات).
   - Ultra-Lightweight 3-Tab Interface:
     - *Tab 1: Production Studio (استوديو الإنتاج)*: Clean 1-click video generation flow with live voice previews and dynamic overlay controls.
     - *Tab 2: Merchant Dashboard (لوحة التاجر)*: Real-time quota meters (daily/weekly usage) and recent video archive.
     - *Tab 3: Admin Dashboard (لوحة تحكم الأدمن)*: Tenant creation modal with custom quotas, expiration date picker, and platform-wide statistics.
     - *Quick Switcher & Session Bar*: Displays current active user, role, remaining quota, and instant logout button.

## Autonomous Vision Script & Emotional Tone Inference
- **Multimodal Video Analysis & Dense Vision Sampling**: Uses Gemini 2.5 Flash / Gemini Vision (`web/vision_analyzer.py`) to analyze extracted visual keyframes. Now extracts 8 to 16 keyframes uniformly distributed across the video timeline (5% to 95%), ensuring comprehensive visual comprehension across every room and architectural detail.
- **Audio-Visual Lead-In Sync**: Automatically introduces a configurable audio lead-in delay (default 1.2s via FFmpeg `adelay=1200|1200`), ensuring visual footage and ambient music swell to establish the scene before voice narration begins.
- **Voice Selection & Custom Profiles**: Native voice selector supporting 4 distinct Arabic voice profiles (`ar-XA-Standard-A` Female warm, `Standard-B` Male authoritative, `Standard-C` Male energetic, `Standard-D` Female elegant & calm) mapped to neural TTS, exposed via `GET /api/voices` and persisted client-side.
- **Decluttered Mobile Studio UI**: Streamlined interface eliminating redundant production buttons, reorganizing advanced telemetry into collapsible drawers, and focusing on an intuitive 1-click video generation workflow.
- **Linguistic Guidance & Intent Processing**: Accepts natural language visual descriptions (`visual_description`) and speech intent guidance (`speech_description` - linguistic intent rather than verbatim text).
- **SQLite Prompt History & Recovery**: Dedicated SQLite database (`web/prompt_db.py` at `outputs/prompts.db`) storing linguistic visual prompts, speech descriptions, generated narration scripts, and metadata for instant 1-tap user retrieval via `GET /api/prompts/history`.
- **Mobile-Optimized Principles UI Theme**: Sleek, fully responsive production principles modal styled with high-contrast glassmorphism, responsive viewports (`@media (max-width: 640px)` / `480px`), and smooth touch scrolling.
- **Emotional Tone Modulation**: Extracts the architectural atmosphere / mood (الحالة الشعورية - e.g. "فاخر وهادئ", "متحمس وحيوي", "دافئ وأنيق") and steers Gemini 3.8 Flash TTS via acoustic style prompts.
- **Curated Music Matching**: Auto-selects the optimal soundtrack from the open-source library (`luxury_piano`, `acoustic_guitar`, `ambient_meditation`).
- **Smart Fallback Safety**: If offline or API unavailable, automatically activates intelligent heuristic fallback so video processing never halts.

## Mobile API Server & Smartphone Video Post-Production (`web/`)

The mobile gateway subsystem in [`web/`](web/) enables real-time ingestion, processing, and assembly of smartphone camera recordings into Algerian real estate promotional videos.

### Key Capabilities
- **Universal Mobile Video Support**: Automatically formats portrait (9:16 vertical) and landscape (16:9 widescreen) mobile recordings.
- **Algerian Real Estate Presets**: Built-in bilingual templates (`algiers_f4_luxury`, `oran_seaview_villa`, `constantine_commercial`, `rental_apartment`).
- **Dynamic Synth Music & Ducking**: Layered D minor ambient synth pad with `sidechaincompress` ducking under Arabic voiceover narration, swelling during pauses and outro.
- **Zero-Config LAN Access**: Terminal launcher with ASCII QR code pointing to `http://<LAN_IP>:8000` for instant smartphone camera connectivity.
- **REST API & Web Studio**: Starlette backend with CORS, multipart upload (`/api/upload-and-process`), preset listing (`/api/presets`), and interactive mobile interface (`/`).

### Launching Mobile Server
```bash
python3 -m web.run_server
```

## Directory Structure
- [`app.py`](app.py): 1-command platform runner with LAN IP detection, QR code generation, and Uvicorn server launcher.
- [`.agent/`](.agent/): Operational directives and agent principles (`agy1.md`, `agy11.md`, `agy51.md`).
- [`inputs/`](inputs/): Raw incoming video footage (`source_fox_cub.mp4`, `source_squirrel.mp4`), mobile uploads, and production requests.
- [`outputs/`](outputs/): Rendered assets, keyframes, mobile cuts, TTS audio, and final cut exports.
  - [`outputs/keyframes/`](outputs/keyframes/): Extracted keyframe images and `frame_index.json`.
  - [`outputs/mobile_cuts/`](outputs/mobile_cuts/): Rendered mobile promo cuts (`cut_<job_id>.mp4`) and summaries.
  - [`outputs/narration.wav`](outputs/narration.wav): High-quality Gemini TTS voiceover track.
  - [`outputs/final_cut.mp4`](outputs/final_cut.mp4): Completed 17-second synchronized video with ducked audio.
  - [`outputs/execution_summary.json`](outputs/execution_summary.json): Complete editorial and audio mixing metadata.
- [`web/`](web/): Mobile API server, post-production bridge, QR launcher, and mobile web studio.
  - [`web/auth_db.py`](web/auth_db.py): Multi-tenant SQLite database manager for tenant authentication, quotas, and admin operations.
  - [`web/pipeline_bridge.py`](web/pipeline_bridge.py): Core mobile video processing and FFmpeg assembly engine.
  - [`web/prompt_db.py`](web/prompt_db.py): SQLite database manager for linguistic prompt descriptions and user history.
  - [`web/vision_analyzer.py`](web/vision_analyzer.py): Gemini Multimodal Vision analysis module for script & mood inference.
  - [`web/server.py`](web/server.py): Starlette REST API server with CORS and static file mounting.
  - [`web/run_server.py`](web/run_server.py): LAN IP detector and ASCII QR code launcher.
  - [`web/static/`](web/static/): Mobile web studio single-page application.
- [`tests/`](tests/): Automated test suite for frame extraction, MCP tool, video processing, and mobile API.
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
