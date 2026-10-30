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
| [`auth_db.py`](file:///home/pluto/projects/lok/web/auth_db.py) | Multi-tenant SaaS SQLite database managing user authentication, PBKDF2 password hashing, master admin (`pluto` / `plutosw4`), start validity (`valid_from`), expiration date (`expires_at`), account status lifecycle (`active`, `suspended`, `expired`, `pending`), daily/weekly quotas, and audit events at `outputs/saas_platform.db` (`user_activity_logs`). |
| [`prompt_db.py`](file:///home/pluto/projects/lok/web/prompt_db.py) | SQLite persistence layer for prompt descriptions history, managing visual & speech intent descriptions, pre-seeded Algerian presets, and script storage at `outputs/prompts.db`. |
| [`pipeline_bridge.py`](file:///home/pluto/projects/lok/web/pipeline_bridge.py) | Core post-production pipeline engine orchestrating keyframe extraction, narration synthesis, audio ducking, auto-annotations, linguistic intent processing, video assembly, explicit `job_id` propagation, and Prompt Security Guardrails (`sanitize_and_validate_prompt`, `parse_prompt_instructions`). |
| [`vision_analyzer.py`](file:///home/pluto/projects/lok/web/vision_analyzer.py) | Gemini Multimodal Vision analysis module for inferring Arabic real estate marketing scripts, emotional atmosphere / mood, property highlights, and recommended music steered by linguistic speech and visual intent. |
| [`video_annotator.py`](file:///home/pluto/projects/lok/web/video_annotator.py) | Fast hardware-accelerated video annotation engine using FFmpeg drawtext filters for luxury badges, price tags, and lower-third captions. |
| [`video_annotator_mcp.py`](file:///home/pluto/projects/lok/web/video_annotator_mcp.py) | MCP (Model Context Protocol) tool bridge and CLI interface exposing `annotate_video_cut` via stdio JSON-RPC. |
| [`video_editor.py`](file:///home/pluto/projects/lok/web/video_editor.py) | Autonomous Video Montage & Editorial Decision Engine providing frame-accurate video trimming, multi-segment shot concatenation, and smart highlight montage assembly. |
| [`video_montage_mcp.py`](file:///home/pluto/projects/lok/web/video_montage_mcp.py) | Fast Video Montage MCP Server exposing `montage_cut_and_trim`, `smart_ai_montage`, and `detect_video_scenes` via standard JSON-RPC. |
| [`server.py`](file:///home/pluto/projects/lok/web/server.py) | Starlette ASGI application exposing REST endpoints, admin portal backend (`/admin`, `/api/admin/*`), root static aliases (`/style.css`, `/app.js`, `/favicon.ico`), prompt security guardrails, static asset mounting (`/outputs`, `/static`), principles endpoints, and CORS middleware. |
| [`run_server.py`](file:///home/pluto/projects/lok/web/run_server.py) | Production CLI launcher that detects host LAN IP (`192.168.1.7`), generates terminal ASCII QR code, and boots Uvicorn. |
| [`static/admin.html`](file:///home/pluto/projects/lok/web/static/admin.html) | Dedicated Bootstrap 5 responsive Admin Dashboard for account management, password updates, date validity configuration, quota adjustments, and activity event auditing. |
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
- **Response (200 OK)**: High-fidelity binary audio stream (`audio/wav`) generated via the Google Gemini TTS library (`tts/gemini_speech`), providing a definitive 10-15 second promotional monologue reference clip for that persona.

### `POST /api/auth/login`
Authenticates a user via username and password (or permanent auth token), provisions a secure session token (`sess_*`), and sets an HTTP-only session cookie.
- **Payload**:
  ```json
  {
    "username": "admin",
    "password": "admin123"
  }
  ```
  *(Or `{"username": "algiers_luxury_re", "password": "merchant123"}` or `{"auth_token": "token_admin_master"}`)*
- **Response (200 OK)**:
  ```json
  {
    "status": "ok",
    "message": "تم تسجيل الدخول بنجاح.",
    "session_token": "sess_7b9d62d0438a4d4ea0ba3701243171aa_a1b2c3d4e5f67890",
    "token": "sess_7b9d62d0438a4d4ea0ba3701243171aa_a1b2c3d4e5f67890",
    "auth_token": "token_admin_master",
    "expires_at": "2026-11-03 21:30:00",
    "user": {
      "id": 1,
      "username": "admin",
      "business_name": "منصة إدارة النظام (SaaS Master Admin)",
      "business_category": "tech",
      "role": "admin",
      "is_active": true,
      "expires_at": "2099-12-31",
      "daily_quota": 9999,
      "weekly_quota": 99999
    },
    "quota": {
      "allowed": true,
      "reason": "حساب مسؤول النظام - استخدام غير محدود",
      "daily_used": 0,
      "daily_quota": 9999,
      "daily_remaining": 9999,
      "weekly_used": 0,
      "weekly_quota": 99999,
      "weekly_remaining": 99999
    }
  }
  ```
- **Set-Cookie**: `session_token=sess_*; Path=/; HttpOnly; SameSite=Lax; Max-Age=604800`

### `POST /api/auth/logout`
Terminates the active session in SQLite and clears the `session_token` cookie.
- **Authentication**: Bearer session token, cookie, or payload `{"session_token": "..."}`.
- **Response (200 OK)**:
  ```json
  {
    "status": "ok",
    "message": "تم تسجيل الخروج بنجاح."
  }
  ```

### `GET /api/auth/session`
Validates the current authenticated session from session cookie or `Authorization: Bearer <session_token>`.
- **Response (200 OK)**: Returns authenticated user profile, session details, and quota stats.
- **Response (401 Unauthorized)**: `{"status": "error", "authenticated": false, "message": "غير مصرح به. يرجى تسجيل الدخول أولاً."}`

### `GET /api/auth/me`
Fetches authenticated user profile, active status, expiration date, and real-time daily/weekly quota allowance.
- **Authentication**: `Authorization: Bearer <token_or_session>`, form field `auth_token`, query param `?token=...`, or header `X-Auth-Token`.
- **Response (200 OK)**: JSON object with `status: "ok"`, `user`, `session`, `quota`, and recent generation `history`.
- **Response (401 Unauthorized)**: Returned if no valid authentication credentials are provided.

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

### `GET /admin`
Serves the dedicated Bootstrap 5 Admin Portal interface (`web/static/admin.html`).

### `POST /api/admin/login`
Master admin login endpoint. Validates username `pluto` and password `plutosw4` (or any active administrator account) and generates a session token.
- **Payload**:
  ```json
  {
    "username": "pluto",
    "password": "plutosw4"
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "status": "ok",
    "message": "تم تسجيل دخول المسؤول بنجاح",
    "session_token": "sess_...",
    "user": {
      "id": 1,
      "username": "pluto",
      "role": "admin",
      "status": "active"
    }
  }
  ```

### `GET /api/admin/accounts` (Alias: `GET /api/admin/users`)
Admin endpoint listing all accounts with quotas, validity dates (`valid_from`, `expires_at`), status (`active`, `suspended`, `expired`, `pending`), and usage metrics.
- **Response (200 OK)**: JSON array of all accounts.

### `POST /api/admin/accounts` (Alias: `POST /api/admin/users`)
Creates a new merchant or administrator account with custom password, validity dates, quotas, and status. Automatically logs `account_created` audit event.
- **Payload**:
  ```json
  {
    "username": "oran_boutique_hotel",
    "business_name": "فندق ومسبح الباهية وهران",
    "business_category": "tourism",
    "role": "merchant",
    "password": "custom_password_123",
    "valid_from": "2026-01-01",
    "expires_at": "2028-06-30",
    "daily_quota": 10,
    "weekly_quota": 50,
    "status": "active"
  }
  ```
- **Response (201 Created)**: Created account object.

### `PATCH /api/admin/accounts/{user_id}` (Alias: `PATCH /api/admin/users/{user_id}`)
Updates password (hashed securely via PBKDF2), status (`active`, `suspended`), valid_from, expires_at, or daily/weekly quotas. Automatically logs `account_updated` audit event.
- **Payload**: Any combination of:
  ```json
  {
    "password": "new_secure_password",
    "status": "suspended",
    "valid_from": "2026-01-01",
    "expires_at": "2028-12-31",
    "daily_quota": 20,
    "weekly_quota": 100
  }
  ```
- **Response (200 OK)**: Updated account object.

### `GET /api/admin/accounts/{user_id}/logs` (Alias: `GET /api/admin/users/{user_id}/logs`)
Retrieves audit events from `user_activity_logs` recorded for the account (e.g. `account_created`, `account_updated`, `admin_login`).
- **Query Params**: `limit` (default: 50).
- **Response (200 OK)**:
  ```json
  {
    "status": "ok",
    "user_id": 12,
    "count": 2,
    "logs": [
      {
        "id": 1,
        "user_id": 12,
        "event_type": "account_created",
        "details": "{\"username\": \"oran_boutique_hotel\", ...}",
        "created_at": "2026-10-28 18:30:00"
      }
    ]
  }
  ```

### `GET /api/admin/stats`
Returns macro-level platform SaaS statistics: total users, active merchants, total admins, total generations, and category breakdown.

---

## 5. Security & Prompt Guardrails (`sanitize_and_validate_prompt`)

To safeguard the platform against prompt injection, shell command execution, and unauthorized file access, `web/pipeline_bridge.py` enforces active input validation:

1. **Dangerous Pattern Inspection**:
   - **Path Traversal**: Blocks `../`, `..\\`, `/etc/passwd`, `/etc/shadow`.
   - **Shell Command Substitution**: Blocks `$(...)` and `` `...` ``.
   - **Destructive File Commands**: Blocks `rm`, `rm -rf`, `rm -r`.
   - **Network Fetch Tools**: Blocks `curl`, `wget`.
   - **Process Execution**: Blocks `bash`, `sh`, `zsh`.
   - **Dynamic Evaluation**: Blocks `eval(`, `subprocess`, `os.system`, `exec(`.

2. **Execution Flow**:
   - Validated on `/api/jobs/create` and `/api/upload-and-process`.
   - If an injection payload is detected, the API rejects the request immediately with **HTTP 400 Bad Request** and `{"status": "error", "error": "security_violation", "message": "..."}`.
   - Safe prompt instructions (speech speed `speed: 1.2x`, tone `tone: enthusiastic` or Arabic intent `حماسي`, `هادئ`) are safely extracted via `parse_prompt_instructions()` without shell invocation.

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
  - **401 Unauthorized**: Missing or invalid session/auth token (strictly gated).
    ```json
    {
      "status": "error",
      "error": "unauthorized",
      "message": "غير مصرح به. يتطلب إنتاج الفيديو تسجيل دخول نشط أو رمز مصادقة صالح."
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
Multi-tenant identity, session state, subscription status, and usage telemetry are persisted in SQLite at `outputs/saas_platform.db`:

#### `users` Table
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT,
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

#### `sessions` Table
```sql
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_token TEXT UNIQUE NOT NULL,
    user_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX idx_sessions_token ON sessions(session_token);
CREATE INDEX idx_sessions_user ON sessions(user_id);
CREATE INDEX idx_sessions_expires ON sessions(expires_at);
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

### Pre-Seeded Catalog of Commercial Merchants & Default Credentials
The database automatically seeds 1 Master Administrator and 10 Commercial Merchants across diverse economic sectors upon initialization. Passwords are securely hashed with PBKDF2-HMAC-SHA256 (100,000 iterations):

| Username | Default Password | Business Name | Category | Role | Daily Quota | Weekly Quota | Auth Token |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `admin` | `admin123` | إدارة منصة الفيديو الذكية | `platform_admin` | `admin` | 999 | 9999 | `token_admin_master` |
| `algiers_luxury_re` | `merchant123` | عقارات الجزائر الفاخرة | `real_estate` | `merchant` | 8 | 40 | `token_algiers_re` |
| `oran_seafood_bistro` | `merchant123` | مطعم وهران للمأكولات البحرية | `restaurant` | `merchant` | 6 | 30 | `token_oran_bistro` |
| `annaba_elegance_couture` | `merchant123` | أزياء عنابة الراقية | `fashion` | `merchant` | 5 | 25 | `token_annaba_fashion` |
| `constantine_smart_tech` | `merchant123` | قسنطينة للأجهزة الذكية | `tech` | `merchant` | 5 | 25 | `token_constantine_tech` |
| `batna_auto_showroom` | `merchant123` | معرض باتنة للسيارات | `automotive` | `merchant` | 4 | 20 | `token_batna_auto` |
| `ghardaia_oasis_carpets` | `merchant123` | زرابي وواحات غرداية التقليدية | `handcrafts` | `merchant` | 3 | 15 | `token_ghardaia_crafts` |
| `bejaia_coast_tours` | `merchant123` | وكالة بجاية للسياحة البحرية | `tourism` | `merchant` | 5 | 25 | `token_bejaia_tours` |
| `setif_home_decor` | `merchant123` | سطيف للمفروشات والديكور المنزلي | `ecommerce` | `merchant` | 6 | 30 | `token_setif_decor` |
| `blida_wellness_clinic` | `merchant123` | عيادة البليدة الطبية والصحية | `clinic` | `merchant` | 4 | 20 | `token_blida_clinic` |
| `algiers_pro_fitness` | `merchant123` | نادي العاصمة للرشاقة واللياقة | `fitness` | `merchant` | 5 | 25 | `token_algiers_fitness` |

### Quota Enforcement & Subscription Lifecycle Governance
The `check_quota(user_id)` function enforces four cascading layers of validation before any video post-production job is accepted:
1. **Active Account Check**: Verifies `is_active == 1`. Inactive accounts are blocked immediately with Arabic notification `الحساب معطل حالياً`.
2. **Expiration Lifecycle Check**: If `expires_at` is set, compares against current date (`YYYY-MM-DD`). Expired subscriptions receive HTTP 403 Forbidden with `انتهت صلاحية اشتراك هذا الحساب بتاريخ ...`.
3. **Daily Quota Ceiling**: Queries `video_generations` where `date(created_at) = date('now')`. If count reaches or exceeds `daily_quota`, request is rejected with `عذراً، لقد استهلكت كامل حصتك اليومية المحددة بـ N فيديوهات اليوم`.
4. **Rolling Weekly Quota Ceiling**: Queries `video_generations` where `created_at >= datetime('now', '-7 days')`. If count reaches or exceeds `weekly_quota`, request is rejected with `عذراً، لقد استهلكت كامل حصتك الأسبوعية المحددة بـ N فيديوهات للأيام السبعة الماضية`.

### Voice Audition Reference Monologue Preview System
To allow merchants to audition voices before committing a video render, `GET /api/voices/{voice_id}/sample` serves high-fidelity reference WAV samples (`outputs/voice_samples/{voice_id}.wav`) generated via the Google Gemini TTS library (`tts/gemini_speech`):
- **Aoede (`ar-XA-Standard-A`)**: Warm luxury interior design and family apartment walkthrough pitch (769KB, 24kHz PCM).
- **Charon (`ar-XA-Standard-B`)**: Authoritative commercial investment, penthouse, and corporate pitch (700KB, 24kHz PCM).
- **Fenrir (`ar-XA-Standard-C`)**: Dynamic modern fast-paced flash offer and high-energy pitch (534KB, 24kHz PCM).
- **Kore (`ar-XA-Standard-D`)**: Elegant tranquil sea-view panoramic and luxury resort pitch (724KB, 24kHz PCM).
- Pre-generated via `web.pipeline_bridge.generate_all_voice_reference_samples()` and cached persistently on disk, serving immediate previews to frontend audition audio players.

### Gated Service Execution
Video production endpoints (`POST /api/upload-and-process`, `POST /api/jobs/create`) are strictly gated by active authentication:
- Require a valid active session token (`sess_*`) via `session_token` cookie, `Authorization: Bearer <token>`, or `X-Session-Token` header, or a permanent merchant bearer token.
- Requests without valid authentication immediately return HTTP 401 Unauthorized with Arabic error notification:
  `{"status": "error", "error": "unauthorized", "message": "غير مصرح به. يتطلب إنتاج الفيديو تسجيل دخول نشط أو رمز مصادقة صالح."}`.

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

---

## 10. Unified Authentication & Quota Architecture

### Master Administrator & Multi-Endpoint Authentication
The platform provides a unified authentication subsystem where master administrators and merchants can authenticate interchangeably across API surfaces:
1. **Master Admin (`pluto` / `plutosw4`)**:
   - Master account configured with username `pluto` and default password `plutosw4` hashed via PBKDF2-HMAC-SHA256.
   - Fully recognized by **both** `/api/admin/login` and `/api/auth/login`.
   - Granted the `admin` role with unlimited video post-production quotas (`unlimited: true`, `daily_limit: 9999`, `weekly_limit: 99999`).
2. **Harmonized Merchant Accounts**:
   - Accounts created via the Admin Portal (`POST /api/admin/accounts`) and pre-seeded merchant accounts authenticate seamlessly via `/api/auth/login`.
   - Password hashing and verification are fully harmonized using PBKDF2-HMAC-SHA256 with 100,000 iterations and 16-byte cryptographically secure salts.

### Case-Insensitive Matching, Whitespace Normalization & Aliases
To prevent accidental 401 rejections from mobile keyboards, input autofills, and demo quick-login buttons:
- **Username Resolution**: Evaluated using case-insensitive SQL matching with leading and trailing whitespace trimming: `WHERE LOWER(TRIM(username)) = LOWER(?)`.
- **Demo Quick-Login Aliases**: Maps common demo identifiers transparently (e.g., `merchant_realestate` -> `algiers_luxury_re`, `dar_al_nokhba` -> `setif_home_decor`, `auto_algerie` -> `batna_auto_showroom`) without requiring changes to existing database records.
- **Password Tolerant Verification**: Hashes and verifies passwords after stripping accidental whitespace while retaining constant-time comparison (`hmac.compare_digest`) against timing side-channel attacks.

### Token Extraction & Candidate Resolution Priority
The server inspects candidate authentication credentials using a deterministic 5-stage priority ladder (`_extract_candidate_tokens`), ensuring explicit per-request credentials override ambient browser cookies:
1. **Authorization Header**: `Authorization: Bearer <token_or_session>`
2. **Explicit Form Fields**: Multipart/form-data payload fields (`session_token`, `auth_token`, `token`)
3. **Custom Authentication Headers**: `X-Session-Token`, `X-Auth-Token`
4. **Query Parameters**: `?session_token=`, `?auth_token=`, `?token=`
5. **Ambient Session Cookies**: `Cookie: session_token=sess_*`

### Session Validation Endpoints
- **`GET /api/auth/session`**: Validates active session tokens provided via Bearer headers or ambient HTTP-only cookies, returning the user profile, session details, and quota allowance.
- **`GET /api/auth/me`**: Fetches user profile, active status, expiration dates, and generation history. Validates session tokens issued by either login endpoint as well as permanent merchant auth tokens. Returns `unlimited: true` for administrative roles (`pluto`, `admin`).

### Gated Video Processing Pipeline Integration
- Both `POST /api/jobs/create` (asynchronous generation) and `POST /api/upload-and-process` (direct synchronous generation) accept active session tokens across Bearer headers, form payloads, or ambient cookies.
- Verified users are dynamically checked for quota availability (`check_quota`) and account lifecycle status (`valid_from`, `expires_at`, `status`).
- Successful post-production jobs are automatically recorded in SaaS generation audit history (`video_generations`).

---

## 11. Dynamic Video Pipeline, Vision Models & Atomic Job Delivery

### Gemini Vision Model Hierarchy & Resiliency
To ensure video keyframes are genuinely analyzed rather than prematurely falling back to generic scripts, the multimodal vision engine (`web/vision_analyzer.py`) implements a resilient model failover architecture:
1. **Active High-Performance Vision Models**:
   - `gemini-3.8-flash`: Primary high-speed multimodal vision analyzer.
   - `gemini-2.5-flash`: Secondary robust multimodal fallback.
   - `gemini-3.1-pro-preview`: Advanced analytical vision fallback.
   - *Retired models (`gemini-1.5-flash`, `gemini-2.0-flash`, `gemini-2.5-pro`) that previously returned HTTP 404 have been deprecated and removed.*
2. **Extended Timeout & Retry Support**:
   - Read timeout increased to **45 seconds** (`GEMINI_VISION_READ_TIMEOUT=45.0`) to comfortably accommodate dense keyframe image payloads.
   - Transient network errors and timeouts automatically trigger a retry before falling back to the next model in the hierarchy.
   - HTTP 404 responses immediately trigger fast failover to the next active candidate model.
   - If all API candidates fail, the system activates the smart architectural heuristic fallback (`_get_smart_fallback`).

### Dynamic Job Video Output & Premature Completion Guard
To eliminate stale cached video loads and playback failures on mobile browsers:
1. **Premature Completion Guard (`/api/status/{job_id}`)**:
   - The status endpoint strictly verifies that the output cut file (`outputs/mobile_cuts/cut_{job_id}.mp4`) is completely written, non-empty, and closed on disk.
   - If a job is nearing completion but the file is not yet finalized, the endpoint holds status at `processing` (progress: 98%), preventing clients from loading unrendered or partial files.
   - Reports `status: 'completed'` and `progress: 100` **only** when the final cut and all FFmpeg video annotations have successfully finished rendering and flushed to disk.
2. **Dynamic URL Exposure**:
   - Every completed job response dynamically exposes:
     - `"video_url"`: `/outputs/mobile_cuts/cut_{job_id}.mp4`
     - `"output_video_url"`: `/outputs/mobile_cuts/cut_{job_id}.mp4`
     - `"output_video"`: `/outputs/mobile_cuts/cut_{job_id}.mp4`
     - `"file_size_bytes"`: Real-time byte count of the rendered MP4 file.
3. **Atomic Legacy Mirroring**:
   - Upon completion, the rendered video cut is atomically copied to `outputs/final_cut.mp4` via a temporary file (`outputs/final_cut_{job_id}.mp4.tmp`) using atomic filesystem replacement (`replace()`). This guarantees that legacy consumers always receive a complete, valid cut without race conditions.

### Video Cut Endpoint Streaming (`/outputs/mobile_cuts/{filename}`)
The server provides a dedicated endpoint for serving rendered cuts:
- **Route**: `GET /outputs/mobile_cuts/{filename}`
- **MIME Type**: `video/mp4`
- **Byte-Range Support**: Full HTTP 206 Partial Content streaming support with `Range` and `Content-Range` headers, allowing seamless seek and playback across desktop and mobile browsers.

---

## 12. Prompt Intent Disentanglement & Persistent Video Overlays Architecture

### Prompt Intent & Directive Disentanglement
When non-technical merchants or mobile users submit natural language instructions in the creative prompt box (e.g. requesting specific voiceover styles, Algerian Darja dialect, and persistent contact numbers at the bottom of the video), the platform automatically disentangles meta-instructions from narration text:

1. **Directive & Meta-Prompt Detection (`is_meta_prompt`, `extract_directives`)**:
   - Detects user command verbs (`أريد`, `اجعل`, `اكتب`, `ضع`, `دير`, `تكلم`) and directive phrases (`أسفل الفيديو`, `طول ما الفيديو شغال`, `تعليق صوتي`, `بالدارجة`, `به الرقم التالي`).
   - Standardizes and extracts Algerian mobile phone numbers (`05...`, `06...`, `07...`, and international prefixes `+213` / `00213`) into canonical 10-digit formats (`0XXXXXXXXX`).
   - Automatically detects persistent lower-third banner requests and assigns appropriate overlay labels.

2. **Strict Voiceover Isolation Mandate**:
   - **User instructions are NEVER read aloud by Gemini Speech TTS!**
   - If a meta-prompt is submitted in place of a literal script, the system switches to auto-mode, moves the directives into thematic steering instructions, and prompts Gemini Multimodal Vision / LLM:
     > *"The user provided instructions: {user_prompt}. Do NOT speak these instructions literally. Instead, compose an authentic, vivid marketing voiceover script in Algerian Darja tailored to the actual video frames. Additionally, extract any visual overlay directives (such as persistent bottom text, phone numbers, contact info)."*
   - Only the organically composed Algerian Darja narration describing the property is passed to the neural TTS synthesizer.
   - Smart fallback profile generators (`_get_smart_fallback`) similarly guard against echoing meta-prompts into narration text.
   - Script sanitization (`sanitize_script_against_meta_prompts`) strips any LLM artifacts or labeling prefixes (e.g. `السيناريو:`, `التعليق الصوتي:`).

### Persistent Bottom Text & Phone Number Overlays
When persistent text or a phone number is detected or provided:
1. **FFmpeg Filtergraph Styling**:
   - Styled via `_build_drawtext_filter` using `style="persistent_bottom"`:
     - **Positioning**: Centered horizontally (`x=(w-text_w)/2`), aligned at the lower edge (`y=h-text_h-40`).
     - **High-Contrast Box**: Semi-transparent black background box (`box=1:boxcolor=black@0.6:boxborderw=8`) ensuring clear readability against bright floors or sunlit windows.
     - **Typography**: Crisp white lettering (`fontcolor=white`) at `fontsize=28`.
     - **Full Duration Persistence**: Active across the entire video duration from `0.00s` to `total_duration` (`enable='between(t,0.00,total_duration)'` or full stream duration).

2. **Status Telemetry & API Contract**:
   - The synthesized script, persistent bottom text, and phone number are exposed in all job telemetry states and responses:
     - `data["script"]`: Composed voiceover narration script.
     - `data["bottom_text"]`: Applied persistent bottom text overlay.
     - `data["phone_number"]`: Extracted contact phone number.
   - Accessible via `POST /api/jobs/create`, `POST /api/upload-and-process`, and `GET /api/status/{job_id}`.

---

## 13. Autonomous AI Video Montage, Shot Trimming & MCP Server Architecture

The platform provides adaptive video editing, shot trimming, and multi-segment assembly driven directly by natural language user prompts or autonomous Multimodal Vision decision-making.

### 1. Natural Language Montage Directives
The directive parser in [`pipeline_bridge.py`](file:///home/pluto/projects/lok/web/pipeline_bridge.py) safely extracts editing instructions across Arabic, English, and French:
- **Interval Trimming**: e.g., *"قص الفيديو من الثانية 2 إلى 8"* or *"trim from 0:02 to 0:15"* -> extracts `trim_start=2.0`, `trim_end=8.0`.
- **Head Trimming**: e.g., *"قص أول 3 ثواني من الفيديو"* or *"cut the first 4s"* -> extracts `trim_start=3.0`.
- **Tail Trimming**: e.g., *"احذف آخر 5 ثواني"* or *"cut the last 5s"* -> extracts `trim_end_offset=5.0`.
- **Target Duration & Highlights**: e.g., *"اجعل مدة الفيديو 15 ثانية ومونتاج ذكي"* -> extracts `target_duration=15.0`, `smart_montage=True`.

### 2. Video Editing Engine (`video_editor.py`)
Implemented in [`video_editor.py`](file:///home/pluto/projects/lok/web/video_editor.py):
- **`trim_video_clip`**: Frame-accurate single segment cutting using FFmpeg `trim`/`atrim` and `setpts`/`asetpts` filtergraphs, maintaining audio-video sync.
- **`assemble_shot_segments`**: Multi-clip concatenation taking an array of `(start, end)` tuples and fusing them into a continuous stream.
- **`auto_smart_montage`**: Autonomous selection of diverse key moments (establishing, interior highlight, climax) to reach target durations without empty pauses.

### 3. Dedicated Fast Video Montage MCP Server (`video_montage_mcp.py`)
Exposes standardized Model Context Protocol tools via JSON-RPC stdio for autonomous AI agents:
- **`montage_cut_and_trim`**: Programmatic cutting and segment slicing.
- **`smart_ai_montage`**: Natural language prompt-directed editing.
- **`detect_video_scenes`**: Scene change detection and candidate cut timestamp calculation.
- Configured in [`mcp_config.json`](file:///home/pluto/projects/lok/mcp_config.json) under the `video-montage` service identifier.

---

## 14. Dynamic Audio Mixing, Prominent Safe Overlays & Adaptive Script Pacing

The platform features comprehensive dynamic audio mixing, prominent safe text overlay positioning, and duration-adaptive Algerian Darja marketing voiceovers.

### 1. Dynamic Audio Mixing & Music Directives (`parse_music_directives`)
Natural language audio instructions in user prompts are automatically parsed and translated into FFmpeg audio filtergraphs:
- **Mute Music Directive (`mute_music`)**:
  - Detects keywords: `بدون موسيقى`, `صوت فقط`, `كتم الموسيقى`, `بلا موسيقى`, `نحي الموسيقى`, `من غير موسيقى`, `mute music`, `no music`, `sans musique`.
  - When active, the FFmpeg filtergraph bypasses background music entirely, executing without `-i music` to render 100% pure voiceover audio.
- **Contextual Track Selection & Custom Volume**:
  - Matches track preferences using contextual keywords (e.g. `موسيقى بيانو`, `موسيقى قيثارة`, `موسيقى تأملية`) to prevent false positives with descriptive property adjectives (e.g. `شقة فاخرة`).
  - Supports custom volume specifications (`خفف الموسيقى`, `music volume 10%`, etc.).
- **Acoustic Ducking Calibration**:
  - Default ambient music volume lowered to `0.16` for optimal speech intelligibility.
  - Sidechain ducking parameters calibrated to `threshold=0.015` and `ratio=12.0` (`sidechaincompress=threshold=0.015:ratio=12.0:attack=15:release=350`), creating smooth, professional transitions under speech.

### 2. Prominent Large Safe Overlays & Player Control Clearance
To ensure high-visibility commercial branding and avoid mobile player timeline scrubbers:
- **Large Font Detection (`large_font`)**:
  - Triggered by phrases like `خط كبير`, `تكبير الخط`, `كتابة واضحة`, `large font`, `big text`.
  - Dynamically calculates font size: `font_size = max(48, min(64, int(target_h * 0.042)))`.
  - High-contrast background banner: `boxborderw=16`, `boxcolor=black@0.78` guaranteeing crisp legibility over bright floors, windows, and reflections.
- **Safe Margin Elevation**:
  - Persistent bottom text is elevated with a dynamic safety margin: `safe_margin = max(110, int(video_height * 0.085))` (`y=h-text_h-{safe_margin}`).
  - Prevents platform progress bars, playheads, and navigation bars from obscuring contact phone numbers and branding banners.

### 3. Property Feature Extraction & Dynamic Algerian Darja Pacing
Ensures narration remains engaging throughout the entire video duration without premature silence or raw digit recitation:
- **Feature Extraction (`extract_property_features`)**:
  - Detects unit configurations (`F1` through `F6`), sea views (`مطل على البحر`, `vue sur mer`, `واجهة بحرية`), and property types (`منزل`, `فيلا`, `شقة`, `دوبلكس`, `استوديو`).
- **Unclamped Word Count Scaling**:
  - Scales target word count continuously across duration: `target_words = max(18, min(160, int(speech_duration * 2.1)))`, removing previous 65-word limits.
- **3-Phase Narrative Arc (`_generate_dynamic_darja_script`)**:
  - **Phase 1 (Hook)**: Engaging opening mentioning the property type, unit configuration, and neighborhood prestige.
  - **Phase 2 (Walkthrough)**: Highlights sea views, spacious interiors, natural lighting, and refined finishes.
  - **Phase 3 (Call-to-Action)**: Prompts viewers to call via the persistent on-screen banner (`اتصلو بنا على الرقم الظاهر أسفل الشاشة`) without reciting raw numeric phone digits aloud.

---

## 15. Synchronized Captions, Shot-by-Shot Visual Grounding & Strict Prompt Adherence

The platform provides fine-grained shot-by-shot visual grounding, strict anti-hallucination verification, videographer live speech extraction, and timestamp-synchronized subtitle overlays.

### 1. Shot-by-Shot Visual Grounding & Anti-Hallucination Mandate
To ensure voiceover narrations match what is physically on-screen without fabricating unseen features:
- **Timestamp Anchoring (`extract_keyframe_records` & `build_shot_timeline`)**:
  - Normalizes keyframe metadata into structured records with precise `timestamp_sec` timestamps.
  - Constructs explicit chronological shot intervals: e.g. `Scene 1 [0.0s - 3.5s]`, `Scene 2 [3.5s - 7.0s]`, etc., covering the total video duration.
- **Strict Anti-Hallucination Mandate**:
  - The Gemini Vision prompt explicitly enforces:
    > *"Ground every sentence of your voiceover strictly in the exact room and visual scene shown at that timestamp. STRICT PROHIBITION AGAINST HALLUCINATIONS: You are strictly forbidden from mentioning any room, facility, or amenity (such as an extra salon, second bathroom, swimming pool, garden, balcony, garage) UNLESS it is physically, unmistakably visible in the keyframe for that specific time interval."*
  - Smart heuristic fallback similarly confines script generation to physically verified property features.
- **Videographer Live Speech Extraction (`analyze_source_audio_for_speech`)**:
  - Automatically probes source video audio tracks via `ffprobe` and extracts mono 16kHz audio slices.
  - Inspects volume energy with `volumedetect` to filter out silent audio, and utilizes Gemini API to transcribe authentic on-site remarks spoken by the person recording the footage.
  - Injects videographer observations into the vision prompt and fallback script generator to accurately identify spaces without picking up background ambient noise.

### 2. Synchronized Captions / Subtitles Pipeline
Generates dynamic on-screen subtitles that match the spoken narration rhythm word-for-word:
- **Phased Clause Segmentation (`generate_synchronized_subtitles`)**:
  - Splits spoken scripts by punctuation (`.`, `،`, `!`, `؟`) and natural phrasing boundaries into readable chunks (4 to 7 words per segment).
  - Calculates proportional duration (`seg_ratio = seg_words / total_words`) anchored to `[visual_lead_in, visual_lead_in + narration_duration]`, producing monotonic `start_sec` and `end_sec` timestamps.
- **Dual Overlay Harmony (Captions + Persistent Contact Badge)**:
  - Subtitles are rendered via FFmpeg drawtext with `style="subtitle"` (`fontcolor=white`, `boxcolor=black@0.72`, `enable='between(t, start, end)'`).
  - Elevated safe margin: Subtitles are positioned at `safe_margin = max(185, int(target_h * 0.145))` (`y=h-text_h-{safe_margin}`).
  - Meanwhile, persistent contact/phone banners remain anchored at lower margin `safe_margin = max(110, int(target_h * 0.085))` with `start_sec=0.0, end_sec=total_duration`.
  - Both visual layers coexist independently on screen without collision or clipping.

### 3. Strict Customer Prompt Adherence & Telemetry Contracts
Guarantees that all customer directives are executed faithfully:
- **Comprehensive Directive Extraction (`extract_directives`)**:
  - Captures phone numbers (`05...`, `06...`, `07...`), property units (`F1`..`F6`), sea views, property types (`منزل`, `فيلا`, `شقة`), music muting, and large font styling.
  - Preserves extracted specs in `summary["customer_specifications"]`.
- **Exposed Telemetry Fields**:
  - Completed job results and `/api/status/{job_id}` dynamically return:
    - `"subtitles"`: Array of timed subtitle segment objects (`start_sec`, `end_sec`, `text`).
    - `"subtitles_count"`: Total number of timed subtitle lines.
    - `"shot_timeline"`: Itemized list of chronological scene intervals.
    - `"videographer_speech"`: Extracted field speech transcribed from source video audio.
    - `"customer_specifications"`: Validated dictionary of customer-requested features.

---

## 16. Strict Explicit Opt-In Architecture, Multi-Tenant Job Sandboxing & Creative Variety Engine

Sprint 3 implements foundational architectural guardrails ensuring a minimalist clean default output, robust multi-tenant job isolation, and non-repetitive narrative synthesis.

### 1. Strict Explicit Opt-In Architecture (Default: Clean & Pure)
Secondary overlays, synchronized captions, and background music are strictly disabled by default to deliver maximum performance, clean visual aesthetic, and 100% pure voiceover intelligibility unless explicitly requested:
- **Synchronized Captions (`subtitles_requested`)**:
  - Default: **OFF**.
  - Activated ONLY when the customer prompt explicitly contains opt-in keywords (e.g. `أضف ترجمة`, `شريط ترجمة`, `ترجمة فورية`, `ترجمة متزامنة`, `كتابة متزامنة`, `مع ترجمة`, `subtitles`, `captions`) or passes `enable_subtitles=True`.
  - When disabled, `subtitles_list` is empty (`[]`) and zero subtitle drawtext filters are injected into the video rendering pipeline.
- **Persistent Lower-Third & Contact Banners**:
  - Default: **OFF**.
  - Rendered ONLY when a valid Algerian phone number (`05...`, `06...`, `07...`) or explicit custom promotional banner text is supplied.
  - Generic decorative banners and badges are suppressed in clean runs, eliminating visual clutter.
- **Background Music & Ducking (`mute_music`)**:
  - Default: **OFF** (`mute_music=True`).
  - Activated ONLY when the customer explicitly asks for background music, acoustic styling, or provides an explicit `music_track` argument.
  - Pure voiceover mode runs FFmpeg with only 2 inputs (video + speech narration), entirely omitting music files and audio mixing overhead.

### 2. Multi-Tenant Job Sandboxing (`outputs/jobs/<job_id>/sandbox/`)
To eliminate race conditions, file collisions, and cache pollution across concurrent renders:
- **Isolated Workspace**:
  - Every job allocates a dedicated isolated directory: `outputs/jobs/<job_id>/sandbox/`.
  - All temporary artifacts, extracted keyframe JPEGs (`sandbox/keyframes/`), audio probe WAV slices, neural narration speech files (`narration_<job_id>.wav`), and intermediate MP4 video cuts (`montaged_<job_id>.mp4`, `cut_<job_id>.mp4`) reside strictly within this sandbox.
- **Dual Mirroring & Backward Compatibility**:
  - Sandboxed video URL is exposed via `"sandboxed_video_url": f"/outputs/jobs/{job_id}/sandbox/cut_{job_id}.mp4"`.
  - Final rendered cuts, narration tracks, and execution summary JSONs are atomically mirrored to legacy locations (`outputs/mobile_cuts/cut_<job_id>.mp4` and `outputs/final_cut.mp4`), guaranteeing zero disruption to legacy consumers and static file routes.

### 3. Creative Variety Engine (Stochastic LLM Pacing & Narrative Diversification)
Addresses repetition when processing identical video footage by injecting generative variance across multiple layers:
- **Elevated Generative Temperature**:
  - Gemini Multimodal Vision API sampling configuration raised to `temperature=0.80`, `topP=0.95` (configurable via `GEMINI_VISION_TEMPERATURE`).
- **Dynamic Marketing Hooks & Angles**:
  - Injects varied commercial angles into the vision prompt:
    - *Architectural Elegance & Luxury Finishes*
    - *Family Sanctuary & Peaceful Living*
    - *Prime Investment & Strategic Opportunity*
    - *Modern Mediterranean Flow & Panoramic Horizons*
    - *Warm Welcoming Living & Contemporary Prestige*
- **Rich Algerian Darja Phrasing Pools (`_generate_dynamic_darja_script`)**:
  - Replaced rigid static strings with rich variation pools for opening hooks (`HOOK_TEMPLATES`), salon walkthroughs (`SALON_TEMPLATES`), bedroom quarters (`ROOMS_TEMPLATES`), kitchen & amenities (`KITCHEN_TEMPLATES`), and neighborhood CTAs (`CTA_TEMPLATES`).
  - Stochastically combines segments to produce fresh, authentic marketing rhythms across repeated runs while strictly maintaining physical accuracy and shot-by-shot visual grounding.

### 4. Verification Suite & Author Attribution
- **Comprehensive Test Suite**: Covered by [`test_optin_sandboxing_and_creative_variety.py`](file:///home/pluto/projects/lok/tests/test_optin_sandboxing_and_creative_variety.py) (19 passing unit & integration tests) testing:
  - Default-off behavior for subtitles, background music, and text badges (`TestStrictOptInArchitecture`).
  - Opt-in keyword parsing across bilingual tokens (`subtitles`, `captions`, `أضف ترجمة`, `شريط ترجمة`, `ترجمة فورية`, `ترجمة متزامنة`).
  - Job sandbox directory creation and artifact confinement in `outputs/jobs/<job_id>/sandbox/` (`TestMultiTenantJobSandboxing`).
  - Generative variety in Darija script synthesis and dynamic hook injection (`TestCreativeVarietyEngine`).
- **Zero Character U+0669 Guardrail**: Scanned across the entire codebase to guarantee complete compliance.
- **Author Identity**: `MouhammedBoure <mohamadbormoz2@gmail.com>`.

---

## 17. Pipeline Latency Optimization, Fast Telemetry & Real-Time Error Propagation

Sprint 4 resolves polling timeout exceptions and pipeline latency bottlenecks:

### 1. Granular Progress & Step Telemetry
- **Consistent Telemetry Keys**: In [`web/server.py`](file:///home/pluto/projects/lok/web/server.py) and [`web/pipeline_bridge.py`](file:///home/pluto/projects/lok/web/pipeline_bridge.py), every telemetry update emits both `progress` and `progress_percent` (float/int), as well as `step` and `current_step` (1: Probe/Montage, 2: Keyframes, 3: Vision & Voice, 4: Audio Mix & Ducking, 5: FFmpeg Render & Annotations).
- **Smooth Incremental Progression**: Progress advances continuously across milestones (15% -> 25% -> 30% -> 45% -> 60% -> 70% -> 85% -> 90% -> 95% -> 100%), eliminating perceived freezing.

### 2. Immediate Error Capture & Propagation
- **Zero Hanging Jobs**: Any unexpected exception during background rendering or analysis is captured immediately by `process_mobile_video` and `_execute_processing_job` / `execute_video_job`.
- **Actionable Failure State**: Job status transitions immediately to `"failed"` with:
  - `status`: `"failed"`
  - `step`: `0`, `current_step`: `0`
  - `progress`: `0`, `progress_percent`: `0`
  - `error`: Clear string message of the failure.
  - `error_details`: Structured payload containing `{"type": "ExceptionClass", "message": "..."}`.
- **No False 98% Stalling**: `/api/status/{job_id}` resolves candidate output cuts via `_find_finalized_cut_file` across sandbox (`outputs/jobs/<job_id>/sandbox/cut_<job_id>.mp4`), mirrors (`outputs/mobile_cuts/cut_<job_id>.mp4`), and result dictionaries, preventing jobs from being falsely held at 98%.

### 3. Latency & Performance Optimizations
- **FFmpeg Accelerated Encoding**: Switched video encoding preset from `medium` to `faster` with multi-core CPU thread pooling (`-threads 0`), delivering 2x to 3x faster final cut exports.
- **Vision Keyframe Payload Optimization**: Dense vision keyframes capped to 10 frames (configurable via `GEMINI_VISION_MAX_FRAMES`), reducing upload payload and cutting LLM round-trip latency.
- **Adaptive Timeouts & Rapid Fallback**: Network read timeout reduced to 25s with 1 retry, seamlessly falling back to `_get_smart_fallback` upon network latency.

### 4. Verification Suite & Author Attribution
- **Test Suite**: Covered by [`test_pipeline_latency_and_telemetry.py`](file:///home/pluto/projects/lok/tests/test_pipeline_latency_and_telemetry.py) (7 passing unit and integration tests) verifying:
  - `execute_video_job` alias and step/progress telemetry contracts.
  - Immediate error propagation on background pipeline exceptions.
  - Multi-path finalized cut file resolution.
  - Vision analyzer frame limits and timeout constraints.
- **Author Identity**: `MouhammedBoure <mohamadbormoz2@gmail.com>`.










