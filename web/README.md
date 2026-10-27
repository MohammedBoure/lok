# Mobile Video API Server & Post-Production Bridge (`web/`)

## 1. Architectural Role & Overview
The `web/` module serves as the primary mobile ingestion and automated post-production gateway for smartphone video recordings. It bridges raw mobile camera footage (both portrait 9:16 and landscape 16:9) into broadcast-ready promotional marketing packages for the Algerian real estate market.

The system combines:
1. **Asynchronous Starlette REST API & Web Server**: High-throughput multipart upload, preset serving, and real-time job telemetry.
2. **Keyframe Extraction Pipeline**: Native I-frame and sampled visual keyframe extraction via `frame_extractor.py`.
3. **Dual-Engine Narration Voiceover**: Gemini Speech (`GeminiSpeechClient`) with automatic failover to a mathematical harmonic formant speech synthesis engine.
4. **Dynamic Sidechain Ducking & Ambient Synthesis**: Generation of ambient synth pad drones in D minor (`D3, F3, A3, C4, D4, F4`) ducked smoothly under voiceover via FFmpeg `sidechaincompress`.
5. **Zero-Configuration LAN QR Code Launcher**: Instant smartphone camera connectivity via terminal ASCII QR codes.

---

## 2. Directory Layout & File Manifest

| File | Purpose |
| :--- | :--- |
| [`pipeline_bridge.py`](file:///home/pluto/projects/lok/web/pipeline_bridge.py) | Core post-production pipeline engine orchestrating keyframe extraction, narration synthesis, audio ducking, and video assembly. |
| [`server.py`](file:///home/pluto/projects/lok/web/server.py) | Starlette ASGI application exposing REST endpoints, static asset mounting (`/outputs`, `/static`), and CORS middleware. |
| [`run_server.py`](file:///home/pluto/projects/lok/web/run_server.py) | Production CLI launcher that detects host LAN IP (`192.168.1.7`), generates terminal ASCII QR code, and boots Uvicorn. |
| [`static/index.html`](file:///home/pluto/projects/lok/web/static/index.html) | Mobile-first responsive web studio supporting live camera capture, preset selection, custom script editing, and video preview. |
| [`static/README.md`](file:///home/pluto/projects/lok/web/static/README.md) | Documentation for static frontend assets and mobile camera interface. |
| [`README.md`](file:///home/pluto/projects/lok/web/README.md) | This master documentation document. |

---

## 3. Algerian Real Estate Presets
The pipeline features four Algerian real estate presets with bilingual metadata (Arabic & French):

1. **`algiers_f4_luxury`**:
   - *Title (AR)*: شقة فاخرة F4 - الجزائر العاصمة
   - *Title (FR)*: Appartement F4 Haut Standing - Alger
   - *Script*: "شقة فاخرة من أربع غرف بتشطيبات عالية الجودة في قلب العاصمة، إطلالة ساحرة وموقع هادئ قريب من كل المرافق الحيوية."
2. **`oran_seaview_villa`**:
   - *Title (AR)*: فيلا عصرية بواجهة بحرية - وهران
   - *Title (FR)*: Villa Moderne Vue sur Mer - Oran
   - *Script*: "فيلا عصرية بواجهة بحرية خلابة في وهران، حديقة خاصة ومسبح وتصميم معماري رفيع يلبي أعلى معايير الرفاهية."
3. **`constantine_commercial`**:
   - *Title (AR)*: محل تجاري استراتيجي - قسنطينة
   - *Title (FR)*: Local Commercial Stratégique - Constantine
   - *Script*: "محل تجاري في موقع استراتيجي نشط بمدينة قسنطينة، واجهة واسعة وحركة تجارية ممتازة مناسب لكافة المشاريع."
4. **`rental_apartment`**:
   - *Title (AR)*: شقة مجهزة ومؤثثة للكراء
   - *Title (FR)*: Appartement Équipé en Location
   - *Script*: "شقة مؤثثة بالكامل ومجهزة بأحدث التجهيزات للكراء في موقع متميز، راحة وأمان لعائلتك."

---

## 4. REST API Specification

### `GET /api/health`
Health and telemetry check for load balancers and orchestrators.
- **Response**:
  ```json
  {
    "status": "ok",
    "service": "mobile-video-processing-api",
    "agent": "agy11",
    "role": "Backend Architecture & Processing Bridge",
    "timestamp": "2026-10-26T19:13:36.537063+00:00"
  }
  ```

### `GET /api/presets`
Returns all available Algerian real estate presets.
- **Response**: JSON array of preset objects containing `id`, `title_ar`, `title_fr`, and `description`.

### `GET /api/music-tracks`
Returns all available open-source royalty-free background music tracks.
- **Response**: JSON array of track objects containing `id`, `title`, `title_ar`, `style`, and `license`.

### `POST /api/jobs/create`
Asynchronous upload and processing endpoint. Accepts video and options, returns `202 Accepted` with `job_id`, and begins processing with live progress updates.
- **Response (202 Accepted)**:
  ```json
  {
    "job_id": "20261027_085000_1a2b3c",
    "status": "processing",
    "message": "بدأ وكيل الذكاء الاصطناعي معالجة الفيديو بنجاح.",
    "status_url": "/api/status/20261027_085000_1a2b3c"
  }
  ```

### `POST /api/upload-and-process`
Multipart form upload endpoint for video processing.
- **Content-Type**: `multipart/form-data`
- **Fields**:
  - `video` (*File, required*): Smartphone video recording (MP4, MOV).
  - `script` (*Text, optional*): Custom Arabic or French narration script.
  - `preset` or `preset_id` (*Text, optional*): Preset identifier (`algiers_f4_luxury`, etc.).
  - `voice` (*Text, optional*): Voice profile (default: `ar-XA-Standard-A`).
  - `duck_level` (*Float, optional*): Ambient music volume ratio during speech (default: `0.25`).
- **Response (200 OK)**:
  ```json
  {
    "job_id": "20261026_191406_3ac71e",
    "status": "completed",
    "video_url": "/outputs/mobile_cuts/cut_20261026_191406_3ac71e.mp4",
    "output_path": "/home/pluto/projects/lok/outputs/mobile_cuts/cut_20261026_191406_3ac71e.mp4",
    "file_size_bytes": 270393,
    "duration": 10.85,
    "orientation": "portrait",
    "aspect_ratio": "9:16",
    "resolution": "720x1280",
    "script": "فيلا عصرية بواجهة بحرية خلابة في وهران...",
    "preset_id": "oran_seaview_villa",
    "voice": "ar-XA-Standard-A",
    "duck_level": 0.25,
    "synthesizer": "synthetic_speech_engine",
    "narration_audio_url": "/outputs/mobile_cuts/narration_20261026_191406_3ac71e.wav",
    "keyframes": [
      {
        "frame_index": 0,
        "timestamp": 0.0,
        "url": "/outputs/keyframes/mobile_20261026_191406_3ac71e/frame_0000_000.00s.jpg",
        "file_path": "outputs/keyframes/mobile_20261026_191406_3ac71e/frame_0000_000.00s.jpg",
        "resolution": "720x1280",
        "is_scene_transition": true
      }
    ],
    "total_keyframes": 2,
    "metadata": { ... },
    "created_at": "2026-10-26T19:14:09.123456+00:00"
  }
  ```

### `GET /api/status/{job_id}`
Queries job status and execution summary from memory or disk cache (`summary_{job_id}.json`).

### Static Mounts:
- `GET /outputs/*`: Serves rendered cuts, keyframe stills, and narration audio.
- `GET /static/*`: Serves frontend CSS, JS, and HTML.
- `GET /`: Serves mobile web studio (`web/static/index.html`).

---

## 5. Execution Pipeline Calculation Flows

```
[Mobile Phone Recording] (Portrait 9:16 or Landscape 16:9)
         │
         ▼
[POST /api/upload-and-process]
         │
         ├── 1. Ingestion: Saved to inputs/mobile_uploads/
         │
         ├── 2. Visual Extraction: frame_extractor.extract_keyframes()
         │      └── outputs/keyframes/mobile_<job_id>/
         │
         ├── 3. Speech Synthesis:
         │      ├── Try GeminiSpeechClient(voice, script)
         │      └── Fallback: harmonic formant voice synthesis engine
         │
         ├── 4. Audio Ducking & Music Synthesis:
         │      ├── Warm D Minor Synth Pad (D3, F3, A3, C4, D4, F4 + Pink Noise)
         │      └── FFmpeg sidechaincompress (duck under voice, swell on outro)
         │
         ├── 5. Video Assembly & Standardized Framing:
         │      ├── Portrait: 1080x1920 or 720x1280 (setsar=1, pad/letterbox)
         │      ├── Landscape: 1920x1080 or 1280x720
         │      ├── Freeze last frame if video < speech + outro
         │      └── Fade in (0.5s) & Fade out (1.0s)
         │
         ▼
[Broadcast Cut: outputs/mobile_cuts/cut_<job_id>.mp4]
```

---

## 6. CLI Usage & Server Launch

### Launch with Automatic LAN Detection & QR Code:
```bash
python3 -m web.run_server
```
Options:
- `--host`: Bind host (default: `0.0.0.0`)
- `--port`: Bind port (default: `8000`)
- `--lan-ip`: Explicit LAN IP override (e.g., `192.168.1.7`)
- `--reload`: Enable hot reload for local development

### Direct Python API Usage:
```python
from web.pipeline_bridge import process_mobile_video

summary = process_mobile_video(
    video_path="inputs/mobile_uploads/sample.mp4",
    preset_id="algiers_f4_luxury",
    duck_level=0.25,
)
print("Rendered video at:", summary["video_url"])
```

---

## 7. Dependencies & Configuration
- **Python**: `3.10+`
- **External Binaries**: `ffmpeg`, `ffprobe`
- **Python Packages**: `starlette`, `uvicorn`, `python-multipart`, `qrcode`
- **Environment Variables**:
  - `GEMINI_API_KEY` or `GEMINI_API_KEYS`: Optional. Enables neural voiceover synthesis via `GeminiSpeechClient`. If absent, the engine gracefully falls back to synthetic formant speech audio.
