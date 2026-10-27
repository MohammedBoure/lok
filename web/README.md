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
| [`auth_db.py`](file:///home/pluto/projects/lok/web/auth_db.py) | Multi-tenant SaaS SQLite database managing user authentication, admin governance, expiration tracking, daily/weekly generation quotas, and audit logs at `outputs/saas_platform.db`. |
| [`prompt_db.py`](file:///home/pluto/projects/lok/web/prompt_db.py) | SQLite persistence layer for prompt descriptions history, managing visual & speech intent descriptions, pre-seeded Algerian presets, and script storage at `outputs/prompts.db`. |
| [`pipeline_bridge.py`](file:///home/pluto/projects/lok/web/pipeline_bridge.py) | Core post-production pipeline engine orchestrating keyframe extraction, narration synthesis, audio ducking, auto-annotations, linguistic intent processing, and video assembly. |
| [`vision_analyzer.py`](file:///home/pluto/projects/lok/web/vision_analyzer.py) | Gemini Multimodal Vision analysis module for inferring Arabic real estate marketing scripts, emotional atmosphere / mood, property highlights, and recommended music steered by linguistic speech and visual intent. |
| [`video_annotator.py`](file:///home/pluto/projects/lok/web/video_annotator.py) | Fast hardware-accelerated video annotation engine using FFmpeg drawtext filters for luxury badges, price tags, and lower-third captions. |
| [`video_annotator_mcp.py`](file:///home/pluto/projects/lok/web/video_annotator_mcp.py) | MCP (Model Context Protocol) tool bridge and CLI interface exposing `annotate_video_cut` via stdio JSON-RPC. |
| [`server.py`](file:///home/pluto/projects/lok/web/server.py) | Starlette ASGI application exposing REST endpoints, static asset mounting (`/outputs`, `/static`), principles endpoints, prompt history management, and CORS middleware. |
| [`run_server.py`](file:///home/pluto/projects/lok/web/run_server.py) | Production CLI launcher that detects host LAN IP (`192.168.1.7`), generates terminal ASCII QR code, and boots Uvicorn. |
| [`static/index.html`](file:///home/pluto/projects/lok/web/static/index.html) | Mobile-first responsive web studio supporting live camera capture, preset selection, custom script editing, principles modal, live telemetry logs, and video preview. |
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

### `GET /api/voices`
Returns catalog of supported Algerian real estate voice profiles.
- **Response (200 OK)**:
  ```json
  {
    "status": "ok",
    "voices": [
      {
        "id": "ar-XA-Standard-A",
        "name_ar": "صوت أنثوي دافئ وطبيعي (Aoede)",
        "name_fr": "Voix féminine chaleureuse et naturelle",
        "gender": "female",
        "persona": "Aoede",
        "recommended_for": "شقق فاخرة وديكورات هادئة"
      },
      {
        "id": "ar-XA-Standard-B",
        "name_ar": "صوت رجالي وقور وواثق (Charon)",
        "name_fr": "Voix masculine posée et confiante",
        "gender": "male",
        "persona": "Charon",
        "recommended_for": "فيلات فخمة وعقارات تجارية واستثمارية"
      },
      {
        "id": "ar-XA-Standard-C",
        "name_ar": "صوت رجالي حيوي وعصري (Fenrir)",
        "name_fr": "Voix masculine dynamique et moderne",
        "gender": "male",
        "persona": "Fenrir",
        "recommended_for": "عروض ترويجية سريعة وشقق شبابية"
      },
      {
        "id": "ar-XA-Standard-D",
        "name_ar": "صوت أنثوي راقٍ وهادئ (Kore)",
        "name_fr": "Voix féminine élégante et calme",
        "gender": "female",
        "persona": "Kore",
        "recommended_for": "إقامات شاطئية وبنتهاوس فخم"
      }
    ]
  }
  ```

### `GET /api/voices/{voice_id}/sample`
Streams real-time or cached WAV audio audition sample for the requested voice persona (`outputs/voice_samples/{voice_id}.wav`).
- **Path Parameters**:
  - `voice_id` (*Text*): Supported voice identifier (`ar-XA-Standard-A`, `ar-XA-Standard-B`, `ar-XA-Standard-C`, `ar-XA-Standard-D`, or custom voice name).
- **Response (200 OK)**: Binary audio stream (`audio/wav`) containing a professional 3-4 second audition monologue tailored to that voice persona.

### `POST /api/auth/login`
Authenticates a user via username or auth token string.
- **Payload**:
  ```json
  {
    "username": "algiers_luxury_re"
  }
  ```
  *(Or `{"auth_token": "token_algiers_re"}`)*
- **Response (200 OK)**:
  ```json
  {
    "status": "ok",
    "token": "token_algiers_re",
    "user": {
      "id": 2,
      "username": "algiers_luxury_re",
      "business_name": "عقارات الجزائر الفاخرة",
      "business_category": "real_estate",
      "role": "merchant",
      "is_active": true,
      "expires_at": "2027-12-31",
      "daily_quota": 8,
      "weekly_quota": 40
    },
    "quota": {
      "allowed": true,
      "reason": "",
      "daily_used": 0,
      "daily_quota": 8,
      "daily_remaining": 8,
      "weekly_used": 0,
      "weekly_quota": 40,
      "weekly_remaining": 40,
      "expires_at": "2027-12-31"
    }
  }
  ```

### `GET /api/auth/me`
Fetches authenticated user profile, active status, expiration date, and real-time daily/weekly quota allowance.
- **Authentication**: `Authorization: Bearer <token>`, form field `auth_token`, query param `?token=...`, or header `x-auth-token`.
- **Response (200 OK)**: JSON object with `status: "ok"`, `user`, and `quota` details.

### `GET /api/auth/demo-accounts`
Returns the public list of pre-seeded demo accounts (1 admin and 10 commercial merchants across distinct industries) for instant 1-click studio switching.
- **Response (200 OK)**:
  ```json
  {
    "status": "ok",
    "accounts": [
      {
        "username": "admin",
        "business_name": "إدارة منصة الفيديو الذكية",
        "business_category": "platform_admin",
        "role": "admin",
        "daily_quota": 999,
        "weekly_quota": 9999,
        "auth_token": "token_admin_master"
      },
      ...
    ]
  }
  ```

### `GET /api/admin/users`
Admin-only endpoint listing all registered platform accounts with real-time generation metrics (`videos_today`, `videos_this_week`, `total_videos`).
- **Authentication**: Requires admin role token (`token_admin_master`).
- **Response (200 OK)**: JSON array of users with quota usage metrics.
- **Response (403 Forbidden)**: `{"status": "error", "message": "Admin authorization required."}`

### `POST /api/admin/users`
Admin-only endpoint provisioning a new merchant account with custom quotas and expiry.
- **Authentication**: Requires admin role token.
- **Payload**:
  ```json
  {
    "username": "oran_boutique_hotel",
    "business_name": "فندق ومسبح الباهية وهران",
    "business_category": "tourism",
    "role": "merchant",
    "daily_quota": 10,
    "weekly_quota": 50,
    "expires_at": "2028-06-30"
  }
  ```
- **Response (201 Created)**: Created user record with generated `auth_token`.

### `PATCH /api/admin/users/{user_id}`
Admin-only endpoint updating quotas, expiration date, business metadata, or active status.
- **Authentication**: Requires admin role token.
- **Payload**: Any of `{"daily_quota": 15, "weekly_quota": 70, "expires_at": "2028-12-31", "is_active": true}`
- **Response (200 OK)**: `{"status": "ok", "message": "User 3 updated successfully."}`

### `GET /api/admin/stats`
Admin-only endpoint returning high-level platform SaaS analytics.
- **Authentication**: Requires admin role token.
- **Response (200 OK)**:
  ```json
  {
    "status": "ok",
    "stats": {
      "total_users": 11,
      "active_users": 11,
      "total_videos_generated": 42,
      "videos_today": 8,
      "videos_this_week": 34
    }
  }
  ```

### `GET /api/principles`
Returns currently active production principles (voice, narrative, visual/music, and video annotations).
- **Response (200 OK)**: JSON object containing active principles schema.

### `POST /api/principles`
Updates and persists production principles configured by the user from the frontend modal.
- **Payload**: JSON dictionary with updated principle sections.
- **Response (200 OK)**: `{"status": "ok", "message": "تم تحديث معايير الإنتاج بنجاح", "principles": {...}}`

### `POST /api/principles/reset`
Restores factory default production principles.
- **Response (200 OK)**: `{"status": "ok", "message": "تمت استعادة معايير الإنتاج الافتراضية بنجاح", "principles": {...}}`

### `POST /api/video/annotate`
Direct fast video annotation endpoint to overlay text banners and badges.
- **Payload**: JSON object `{"input_video": "...", "output_video": "...", "annotations": [...]}`
- **Response (200 OK)**: `{"status": "ok", "annotations_applied": N, "output_video": "..."}`

### `GET /api/prompts/history`
Returns history of recent prompt descriptions stored in SQLite database (`outputs/prompts.db`).
- **Query Parameters**:
  - `limit` (*Integer, optional*): Maximum records to retrieve (default: `50`).
- **Response (200 OK)**:
  ```json
  {
    "status": "ok",
    "prompts": [
      {
        "id": 1,
        "created_at": "2026-10-27 11:26:11",
        "title": "فيلا عصرية فاخرة بواجهة بحرية - وهران",
        "visual_description": "فيلا عصرية فاخرة مطلة على البحر...",
        "speech_description": "التركيز على الفخامة والسكينة...",
        "inferred_script": "شوفو معايا هاد الفيلا الساحرة في عين الترك...",
        "metadata": "{\"preset\": \"oran_seaview_villa\"}"
      }
    ]
  }
  ```

### `POST /api/prompts`
Saves new prompt descriptions into SQLite prompt history.
- **Payload**:
  ```json
  {
    "title": "Downtown Penthouse",
    "visual_description": "Luxury duplex penthouse with panoramic bay views",
    "speech_description": "Focus on high-end prestige, master bedroom suite, and open terrace",
    "inferred_script": "Optional pre-inferred script",
    "metadata": {"city": "Algiers"}
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "status": "ok",
    "id": 4,
    "prompt": { "id": 4, "title": "Downtown Penthouse", ... }
  }
  ```

### `DELETE /api/prompts/{prompt_id}`
Deletes a prompt description record from SQLite database.
- **Response (200 OK)**: `{"status": "ok", "message": "Prompt 4 deleted successfully.", "deleted": true}`
- **Response (404 Not Found)**: `{"status": "error", "message": "Prompt with ID 4 not found.", "deleted": false}`

### `POST /api/jobs/create`
Asynchronous upload and processing endpoint. Accepts video and options, authenticates merchant credentials, enforces daily/weekly quotas, auto-saves prompt descriptions to SQLite, audits generations to SaaS platform DB, returns `202 Accepted` with `job_id`, and begins processing with live progress updates.
- **Headers / Query / Form**:
  - `Authorization: Bearer <token>` or form field `auth_token` (*Text, optional*): Merchant authentication token. Defaults to first active merchant if omitted.
- **Fields**:
  - `video` (*File, required*): Smartphone video recording (MP4, MOV).
  - `visual_description` (*Text, optional*): Visual intent guidance of what appears in footage (auto-saved to SQLite).
  - `speech_description` (*Text, optional*): Linguistic speech guidance for voiceover intent (auto-saved to SQLite).
  - `auto_mode` (*Boolean/Text, optional*): Enable AI Multimodal Vision inference.
  - `voice` (*Text, optional*): Voice profile (`ar-XA-Standard-A`, `ar-XA-Standard-B`, `ar-XA-Standard-C`, `ar-XA-Standard-D`, or custom string; default: `ar-XA-Standard-A`).
  - `visual_lead_in` (*Float, optional*): Establishing visual lead-in delay in seconds (default: `1.2`, range: `0.0` - `5.0`).
  - `fixed_text` (*Text, optional*): Persistent commercial text overlay (e.g. business name, phone number, slogan, pricing).
  - `text_position` (*Text, optional*): Overlay placement: `lower_third`, `top_banner`, or `badge` (default: `lower_third`).
  - `text_style` (*Text, optional*): Graphic color theme: `modern_white`, `luxury_gold`, or `commercial_red` (default: `modern_white`).
  - `video_orientation` (*Text, optional*): Frame aspect ratio override: `portrait` (9:16), `landscape` (16:9), or `square` (1:1).
- **Responses**:
  - **202 Accepted**: Job accepted and processing initiated.
    ```json
    {
      "job_id": "20261027_085000_1a2b3c",
      "status": "processing",
      "message": "بدأ وكيل الذكاء الاصطناعي معالجة الفيديو بنجاح.",
      "status_url": "/api/status/20261027_085000_1a2b3c",
      "prompt_id": 5,
      "voice": "ar-XA-Standard-A",
      "visual_lead_in_seconds": 1.2,
      "merchant": { "id": 2, "business_name": "عقارات الجزائر الفاخرة" },
      "quota": { "allowed": true, "daily_remaining": 7, "weekly_remaining": 39 }
    }
    ```
  - **403 Forbidden**: Quota exceeded or account expired.
    ```json
    {
      "status": "error",
      "error": "quota_exceeded",
      "message": "عذراً، لقد استهلكت كامل حصتك اليومية المحددة بـ 5 فيديوهات اليوم.",
      "quota": { "allowed": false, "daily_used": 5, "daily_quota": 5, "daily_remaining": 0 }
    }
    ```

### `POST /api/upload-and-process`
Multipart form upload endpoint for synchronous video processing with authentication and quota verification.
- **Content-Type**: `multipart/form-data`
- **Fields**:
  - `video` (*File, required*): Smartphone video recording (MP4, MOV).
  - `auth_token` (*Text, optional*): Merchant authentication bearer token.
  - `visual_description` (*Text, optional*): Visual description describing scenes, architecture, and focal points.
  - `speech_description` (*Text, optional*): Linguistic speech intent guidance describing what should be narrated (not literal text).
  - `auto_mode` (*Boolean/Text, optional*): When `true` (or when `speech_description` is supplied), triggers Gemini Multimodal Vision to infer script, emotional tone, badges, and music.
  - `script` (*Text, optional*): Custom Arabic or French narration script (literal text).
  - `preset` or `preset_id` (*Text, optional*): Preset identifier (`algiers_f4_luxury`, etc.).
  - `emotional_tone` (*Text, optional*): Explicit emotional tone steering (e.g. "فاخر وهادئ", "متحمس وحيوي", "دافئ وأنيق").
  - `voice` (*Text, optional*): Voice profile (`ar-XA-Standard-A`, `ar-XA-Standard-B`, `ar-XA-Standard-C`, `ar-XA-Standard-D`, or custom; default: `ar-XA-Standard-A`).
  - `visual_lead_in` (*Float, optional*): Visual establishing lead-in delay in seconds before speech starts (default: `1.2`).
  - `duck_level` (*Float, optional*): Ambient music volume ratio during speech (default: `0.25`).
  - `music` or `music_track` (*Text, optional*): Music identifier (`luxury_piano`, `acoustic_guitar`, `ambient_meditation`).
  - `fixed_text` (*Text, optional*): Persistent promotional text banner or commercial watermark.
  - `text_position` (*Text, optional*): `lower_third`, `top_banner`, or `badge`.
  - `text_style` (*Text, optional*): `modern_white`, `luxury_gold`, or `commercial_red`.
  - `video_orientation` (*Text, optional*): Target framing (`portrait`, `landscape`, `square`).
- **Response (200 OK)**: Includes `auto_mode`, `emotional_tone`, `inferred_script`, `prompt_id`, `visual_description`, `speech_description`, `video_url`, `job_id`, `keyframes`, `analyzed_frames_count`, `visual_lead_in_seconds`, `voice`, `merchant_user_id`, `fixed_text`, `video_orientation`, and `duration`.
- **Response (403 Forbidden)**: Returned immediately if account is expired, inactive, or daily/weekly generation quota is depleted.
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

---

## 8. Mobile Front-End, 1-Click UX & Session Persistence

The static mobile studio in [`web/static/`](file:///home/pluto/projects/lok/web/static/) is engineered for maximum field efficiency:
1. **1-Click AI Video Production**:
   - Zero-effort default path: user records/selects footage and triggers full processing via a single prominent button (**"✨ إنتاج الفيديو تلقائياً بالذكاء الاصطناعي بنقرة واحدة"**).
   - Optional parameters (script, voice, presets, music) are housed inside a collapsible accordion (`#advancedAccordion`). When collapsed or empty, the frontend sends `auto_mode=true`, letting the backend AI vision agent infer script, mood, and music automatically.
2. **Session Persistence & Reconnection**:
   - Stores active job IDs in `localStorage['active_job_id']`.
   - On page reload (`DOMContentLoaded`), `restoreSavedSession()` queries `/api/status/{job_id}`, resuming 600ms polling for in-flight tasks or displaying completed video cuts and keyframes immediately.
   - Dedicated **"🔄 معالجة فيديو جديد"** buttons clear storage and reset the workspace.
3. **Emotional Tone & Vision Telemetry**:
   - Inferred emotional tones (e.g. *فاخر وهادئ*) are showcased via dedicated spotlight cards and telemetry badges.

---

## 9. SQLite Prompt History & Linguistic Description Agent

### Storage Architecture (`outputs/prompts.db`)
Prompt descriptions and generated scripts are automatically persisted in SQLite table `prompt_history`:
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `created_at` (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
- `title` (TEXT)
- `visual_description` (TEXT: وصف ما يظهر في الفيديو)
- `speech_description` (TEXT: وصف ما سيقال في التعليق الصوتي)
- `inferred_script` (TEXT)
- `metadata` (TEXT: JSON string)

### Pre-Seeded Realistic Algerian Real Estate Prompts
When `outputs/prompts.db` is initialized, it automatically seeds 3 realistic Algerian market templates if empty:
1. **Oran Luxury Seaview Villa**: Mediterranean sea view, infinity pool, luxury finishes, Algerian Darja walkthrough tone.
2. **Sidi Yahia Downtown Penthouse (Algiers)**: Duplex terrace, marble salon, modern open kitchen, panoramic bay view.
3. **Constantine Strategic Commercial Hub**: Double-story avenue storefront, security setup, high-footprint commercial pitch.

### Linguistic Intent Guidance ("وصف لغوي لما تريده أن يقال وليس نصاً حرفياً")
- When `speech_description` is provided, the multimodal vision agent treats it as **creative intent and semantic direction**, rather than reading it verbatim.
- The agent expands this guidance into a natural, spoken marketing script matching the visual camera walkthrough and target duration (~2.2 words/sec) in authentic **Algerian Darja** (`الدارجة الجزائرية`).
- When `visual_description` is provided, the agent uses it to guide architectural focus, visual scene interpretation, and dynamically generates on-screen lower-third subtitle badges for the highlighted areas.
- **Graceful Fallback**: If Gemini Vision API is unreachable or offline, `_get_smart_fallback` synthesizes an Algerian Darja walkthrough script derived from `speech_description` and extracts lower-third badges directly from `visual_description`.

---

## 10. Audio-Visual Synchronization, Dense Vision Sampling & Voice Profiles

### Audio-Visual Synchronization (Audio Must Not Precede Visuals)
In traditional video production, audio starting at `0.0s` rushes ahead of video establishing shots. To ensure professional broadcast pacing:
1. **Establishing Visual Lead-In Delay (`visual_lead_in = 1.2s`)**:
   - Default: `1.2` seconds (configurable between `0.0s` and `5.0s`, recommended `1.0s` to `1.5s`).
   - Mixed into final video via FFmpeg audio filter `adelay={lead_in_ms}|{lead_in_ms}` applied to the narration stream (`[2:a]` or `[1:a]`).
   - Ambient background music begins immediately at `0.0s`, establishing the luxury atmosphere before the narrator begins speaking at `1.2s`.
   - Sidechain ducking is delayed synchronously with the voiceover, ensuring background music remains at full volume during the establishing shot.
2. **Outro Swell Buffer (`outro_buffer = 1.2s`)**:
   - Leaves an intentional buffer after speech finishes so background music swells back to full volume before the video fades out.
3. **Net Speaking Duration & Word Pacing**:
   - The multimodal script generation engine calculates net available speaking time:
     $$\text{speech\_duration} = \max(2.0, \text{total\_duration} - \text{visual\_lead\_in} - \text{outro\_buffer})$$
   - Target script word count is calculated strictly from this window at ~2.2 words/sec:
     $$\text{target\_words} = \max(6, \min(65, \text{int}(\text{speech\_duration} \times 2.2)))$$
   - This mathematical guarantee prevents voiceover from ever rushing ahead of scenes or exceeding video length.

### Dense Multimodal Keyframe Extraction (8-16 Keyframes)
To ensure the AI vision agent thoroughly inspects every room and transition in the property:
- **Uniform Distribution Sampling**: `compute_dense_keyframe_timestamps` calculates 8 to 16 uniformly distributed timestamps across the full video duration (e.g., at 5%, 15%, 25%, ..., 95% of duration).
- **Scene Cut Merging**: Uniform samples are merged with detected scene transitions from `frame_extractor.py`.
- **Multimodal Delivery**: All extracted keyframes (up to 16 images) are passed directly to Gemini Multimodal Vision (`vision_analyzer.py`), enabling granular scene-by-scene property analysis.
- **Telemetry Reporting**: The exact number of analyzed frames is tracked in `analyzed_frames_count` and reported in job status, execution summary, and API telemetry.

### Algerian Real Estate Voice Profiles Catalog
Four dedicated voices optimized for Algerian real estate marketing are exposed via `GET /api/voices`:

| Voice ID | Gender | Persona | Recommended Use Case |
| :--- | :--- | :--- | :--- |
| **`ar-XA-Standard-A`** | Female | Aoede | Warm, natural, and inviting for luxury apartments and interior design walkthroughs. |
| **`ar-XA-Standard-B`** | Male | Charon | Deep, authoritative, and confident for luxury villas, commercial developments, and investments. |
| **`ar-XA-Standard-C`** | Male | Fenrir | Energetic, modern, and engaging for quick promotional reels, student housing, and vibrant neighborhoods. |
| **`ar-XA-Standard-D`** | Female | Kore | Elegant, tranquil, and prestigious for high-end beachfront residences and penthouses. |

Custom voice strings (e.g., `Puck`, `Zephyr`, `ar-XA-Wavenet-A`) are automatically supported and routed to `GeminiSpeechClient` or the local synthesizer.

---

## 11. Multi-Tenant SaaS Architecture, Quotas, Admin Governance & Voice Preview

### Multi-Tenant Database Schema (`outputs/saas_platform.db`)
Multi-tenant identity, subscription status, and usage telemetry are persisted in SQLite at `outputs/saas_platform.db`:

#### `users` Table
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    business_name TEXT NOT NULL,
    business_category TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'merchant',
    is_active INTEGER NOT NULL DEFAULT 1,
    expires_at TEXT,
    daily_quota INTEGER NOT NULL DEFAULT 5,
    weekly_quota INTEGER NOT NULL DEFAULT 25,
    auth_token TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_users_token ON users(auth_token);
CREATE INDEX idx_users_username ON users(username);
```

#### `video_generations` Table
```sql
CREATE TABLE video_generations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    job_id TEXT NOT NULL,
    video_url TEXT,
    title TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX idx_generations_user_created ON video_generations(user_id, created_at);
```

### Pre-Seeded Catalog of Commercial Merchants
The database automatically seeds 1 Master Administrator and 10 Commercial Merchants across diverse economic sectors upon initialization:

| Username | Business Name | Category | Role | Daily Quota | Weekly Quota | Auth Token |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `admin` | إدارة منصة الفيديو الذكية | `platform_admin` | `admin` | 999 | 9999 | `token_admin_master` |
| `algiers_luxury_re` | عقارات الجزائر الفاخرة | `real_estate` | `merchant` | 8 | 40 | `token_algiers_re` |
| `oran_seafood_bistro` | مطعم وهران للمأكولات البحرية | `restaurant` | `merchant` | 6 | 30 | `token_oran_bistro` |
| `annaba_elegance_couture` | أزياء عنابة الراقية | `fashion` | `merchant` | 5 | 25 | `token_annaba_fashion` |
| `constantine_smart_tech` | قسنطينة للأجهزة الذكية | `tech` | `merchant` | 5 | 25 | `token_constantine_tech` |
| `batna_auto_showroom` | معرض باتنة للسيارات | `automotive` | `merchant` | 4 | 20 | `token_batna_auto` |
| `ghardaia_oasis_carpets` | زرابي وواحات غرداية التقليدية | `handcrafts` | `merchant` | 3 | 15 | `token_ghardaia_crafts` |
| `bejaia_coast_tours` | وكالة بجاية للسياحة البحرية | `tourism` | `merchant` | 5 | 25 | `token_bejaia_tours` |
| `setif_home_decor` | سطيف للمفروشات والديكور المنزلي | `ecommerce` | `merchant` | 6 | 30 | `token_setif_decor` |
| `blida_wellness_clinic` | عيادة البليدة الطبية والصحية | `clinic` | `merchant` | 4 | 20 | `token_blida_clinic` |
| `algiers_pro_fitness` | نادي العاصمة للرشاقة واللياقة | `fitness` | `merchant` | 5 | 25 | `token_algiers_fitness` |

### Quota Enforcement & Subscription Lifecycle Governance
The `check_quota(user_id)` function enforces four cascading layers of validation before any video post-production job is accepted:
1. **Active Account Check**: Verifies `is_active == 1`. Inactive accounts are blocked immediately with Arabic notification `الحساب معطل حالياً`.
2. **Expiration Lifecycle Check**: If `expires_at` is set, compares against current date (`YYYY-MM-DD`). Expired subscriptions receive HTTP 403 Forbidden with `انتهت صلاحية اشتراك هذا الحساب بتاريخ ...`.
3. **Daily Quota Ceiling**: Queries `video_generations` where `date(created_at) = date('now')`. If count reaches or exceeds `daily_quota`, request is rejected with `عذراً، لقد استهلكت كامل حصتك اليومية المحددة بـ N فيديوهات اليوم`.
4. **Rolling Weekly Quota Ceiling**: Queries `video_generations` where `created_at >= datetime('now', '-7 days')`. If count reaches or exceeds `weekly_quota`, request is rejected with `عذراً، لقد استهلكت كامل حصتك الأسبوعية المحددة بـ N فيديوهات للأيام السبعة الماضية`.

### Voice Audition Sample Preview System
To allow merchants to audition voices before committing a video render, `GET /api/voices/{voice_id}/sample` serves cached high-fidelity WAV samples (`outputs/voice_samples/{voice_id}.wav`):
- **Aoede (`ar-XA-Standard-A`)**: Warm luxury interior design pitch.
- **Charon (`ar-XA-Standard-B`)**: Authoritative commercial investment pitch.
- **Fenrir (`ar-XA-Standard-C`)**: Modern fast-paced dynamic offer pitch.
- **Kore (`ar-XA-Standard-D`)**: Elegant tranquil sea-view panoramic pitch.
- Synthesized on-demand via `GeminiSpeechClient` or mathematical harmonic formant engine, then cached permanently to avoid redundant API or CPU cycles.

### Fixed Commercial Overlays & Video Formatting
The pipeline supports persistent branding overlays and versatile aspect ratio reframing:
- **Placement**:
  - `lower_third`: Centered lower banner (`y=h-th-80`).
  - `top_banner`: Centered header banner (`y=80`).
  - `badge`: Top-left corner promotional badge (`x=40`, `y=50`).
- **Color Themes**:
  - `modern_white`: Clean white lettering on charcoal black box (`0x111827@0.85`).
  - `luxury_gold`: Warm golden text (`#F59E0B`) on dark gold/navy background (`0x1E1B18@0.90`).
  - `commercial_red`: High-visibility white lettering on vibrant red promotional badge (`0xDC2626@0.90`).
- **Video Framing & Aspect Ratios**:
  - `portrait` (9:16): 1080x1920 or 720x1280 (vertical reels, TikTok, Instagram stories).
  - `landscape` (16:9): 1920x1080 or 1280x720 (YouTube, website banners, desktop displays).
  - `square` (1:1): 1080x1080 or 720x720 with uniform scaling and padding (Instagram grid, Facebook feeds).


