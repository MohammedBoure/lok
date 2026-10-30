#!/usr/bin/env python3
"""
Mobile API Server (web/server.py)
Starlette & Uvicorn REST API for smartphone video recording & post-production.

Author: MouhammedBoure
Role: Backend Architecture & Processing Bridge (agy11)
Branch: backend/agy11-mobile-api-server
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import sys
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Load environment configuration (.env)
def _ensure_env_loaded():
    """Load GEMINI_API_KEY from .env if not currently present in os.environ."""
    if os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEYS"):
        return
    candidates = [
        REPO_ROOT / ".env",
        REPO_ROOT / "tts" / ".env",
        Path.cwd() / ".env",
    ]
    for env_path in candidates:
        if env_path.is_file():
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k, v = k.strip(), v.strip().strip("\"'")
                            if k not in os.environ:
                                os.environ[k] = v
            except OSError:
                pass

_ensure_env_loaded()

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from config.production_principles_manager import (
    load_principles,
    reset_principles,
    save_principles,
)
from web.pipeline_bridge import (
    ALGERIAN_REAL_ESTATE_PRESETS,
    MUSIC_LIBRARY,
    extract_algerian_phone,
    extract_directives,
    get_music_tracks_list,
    get_or_create_voice_sample,
    get_presets_list,
    get_voice_profiles_list,
    is_meta_prompt,
    parse_prompt_instructions,
    process_mobile_video,
    resolve_voice_profile,
    sanitize_and_validate_prompt,
)
from web.prompt_db import (
    delete_prompt,
    get_prompt_by_id,
    get_recent_prompts,
    save_prompt,
    update_prompt_script,
)
from web.auth_db import (
    authenticate_credentials,
    authenticate_token,
    authenticate_user,
    check_quota,
    create_session,
    create_user,
    delete_session,
    get_demo_accounts,
    get_platform_stats,
    get_session,
    get_user_activity_logs,
    get_user_by_id,
    get_user_by_username,
    get_user_history,
    hash_password,
    list_users,
    log_user_event,
    record_generation,
    update_user,
    verify_admin_login,
    verify_password,
)
from web.video_annotator import annotate_video

logger = logging.getLogger("mobile_api_server")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s")

# Ensure required storage directories exist
UPLOADS_DIR = REPO_ROOT / "inputs" / "mobile_uploads"
OUTPUTS_DIR = REPO_ROOT / "outputs"
STATIC_DIR = REPO_ROOT / "web" / "static"

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# In-memory registry for jobs and real-time status telemetry
JOBS_STORE: Dict[str, Dict[str, Any]] = {}
PROGRESS_STORE: Dict[str, Dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# API Route Handlers
# ---------------------------------------------------------------------------

async def health_check(request: Request) -> JSONResponse:
    """GET /api/health - Service health and telemetry."""
    return JSONResponse({
        "status": "ok",
        "service": "mobile-video-processing-api",
        "agent": "agy11",
        "role": "Backend Architecture & Processing Bridge",
        "has_gemini_api_key": bool(os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEYS")),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


async def get_presets(request: Request) -> JSONResponse:
    """GET /api/presets - Returns catalog of Algerian real estate presets."""
    return JSONResponse(get_presets_list())


async def get_music_tracks(request: Request) -> JSONResponse:
    """GET /api/music-tracks - Returns catalog of available open-source background music."""
    return JSONResponse(get_music_tracks_list())


def _extract_candidate_tokens(request: Request, form: Optional[Any] = None) -> List[str]:
    """
    Extract and normalize all potential session or auth tokens from request:
    Authorization header, form fields, custom headers, query parameters, and cookies.
    Explicit request tokens take precedence over ambient cookies.
    """
    raw_tokens: List[Any] = []

    # 1. Authorization header (Bearer <token>)
    auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
    if auth_header:
        raw_tokens.append(auth_header)

    # 2. Form fields (explicitly submitted with request)
    if form:
        for f in ("session_token", "auth_token", "token"):
            val = form.get(f)
            if val:
                raw_tokens.append(val)

    # 3. Custom headers
    for h in ("X-Session-Token", "x-session-token", "X-Auth-Token", "x-auth-token"):
        val = request.headers.get(h)
        if val:
            raw_tokens.append(val)

    # 4. Query parameters
    for q in ("session_token", "auth_token", "token"):
        val = request.query_params.get(q)
        if val:
            raw_tokens.append(val)

    # 5. Ambient Cookies
    for c in ("session_token", "auth_token", "token"):
        val = request.cookies.get(c)
        if val:
            raw_tokens.append(val)

    candidates: List[str] = []
    for item in raw_tokens:
        if not isinstance(item, str):
            continue
        cleaned = item.strip()
        if cleaned.lower().startswith("bearer "):
            cleaned = cleaned[7:].strip()
        if (
            cleaned
            and cleaned.lower() not in ("none", "null", "undefined", '""', "''")
            and cleaned not in candidates
        ):
            candidates.append(cleaned)

    return candidates


def _get_authenticated_user_and_session(
    request: Request,
    form: Optional[Any] = None,
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """
    Authenticate user and session by testing extracted candidate tokens.
    Returns:
        (user_dict, session_dict) if authenticated, else (None, None).
    """
    candidates = _extract_candidate_tokens(request, form)

    for token in candidates:
        # 1. Check if token is an active session
        sess = get_session(token)
        if sess and sess.get("user"):
            return (sess["user"], sess)

        # 2. Check if token is a permanent merchant/admin auth token
        user = authenticate_token(token)
        if user:
            return (user, None)

    return (None, None)


def _get_authenticated_user_from_form_or_header(
    request: Request,
    form: Optional[Any] = None,
) -> Optional[Dict[str, Any]]:
    """Convenience alias returning only the authenticated user dictionary (or None)."""
    user, _ = _get_authenticated_user_and_session(request, form)
    return user


def _execute_processing_job(
    job_id: str,
    saved_video_path: Path,
    script: Optional[str],
    preset: Optional[str],
    voice: str,
    duck_level: float,
    music_track: Optional[str],
    auto_mode: bool = False,
    emotional_tone: Optional[str] = None,
    visual_description: Optional[str] = None,
    speech_description: Optional[str] = None,
    prompt_id: Optional[int] = None,
    visual_lead_in: float = 1.2,
    user_id: Optional[int] = None,
    fixed_text: Optional[str] = None,
    text_position: Optional[str] = "lower_third",
    text_style: Optional[str] = "modern_white",
    video_orientation: Optional[str] = None,
    bottom_text: Optional[str] = None,
    phone_number: Optional[str] = None,
    enable_subtitles: Optional[bool] = None,
    enable_music: Optional[bool] = None,
):
    """Worker function executed synchronously or in a background thread."""
    def _on_progress(event: Dict[str, Any]):
        curr = PROGRESS_STORE.get(job_id, {})
        agent_logs = curr.get("agent_logs", [])
        if event.get("log") and event["log"] not in agent_logs:
            agent_logs.append(event["log"])

        pct = event.get("percent") if event.get("percent") is not None else event.get("progress_percent", 15)
        step = event.get("step", 1)

        evt_status = event.get("status")
        if evt_status in ("failed", "error"):
            status_val = "failed"
        elif evt_status in ("completed", "done") or (isinstance(pct, (int, float)) and pct >= 100):
            status_val = "completed"
        else:
            status_val = "processing"

        payload = {
            "job_id": job_id,
            "status": status_val,
            "step": step,
            "current_step": step,
            "progress": pct,
            "progress_percent": pct,
            "message": event.get("message", "جاري المعالجة..."),
            "agent_logs": agent_logs,
            "auto_mode": auto_mode,
            "emotional_tone": event.get("emotional_tone") or curr.get("emotional_tone") or emotional_tone,
            "inferred_script": event.get("inferred_script") or curr.get("inferred_script"),
            "voice": voice,
            "visual_lead_in": visual_lead_in,
            "user_id": user_id,
            "fixed_text": fixed_text,
            "bottom_text": event.get("bottom_text") or curr.get("bottom_text") or bottom_text,
            "phone_number": event.get("phone_number") or curr.get("phone_number") or phone_number,
            "script": event.get("script") or curr.get("script") or script,
            "error": event.get("error") or curr.get("error"),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if event.get("error_details"):
            payload["error_details"] = event["error_details"]
        if event.get("video_url"):
            payload["video_url"] = event["video_url"]
        if event.get("sandboxed_video_url"):
            payload["sandboxed_video_url"] = event["sandboxed_video_url"]

        PROGRESS_STORE[job_id] = payload
        if status_val == "failed":
            JOBS_STORE[job_id] = dict(payload)

    try:
        summary = process_mobile_video(
            video_path=saved_video_path,
            script=script,
            preset_id=preset,
            voice=voice,
            duck_level=duck_level,
            music_track=music_track,
            output_dir=OUTPUTS_DIR / "mobile_cuts",
            progress_callback=_on_progress,
            auto_mode=auto_mode,
            emotional_tone=emotional_tone,
            visual_description=visual_description,
            speech_description=speech_description,
            visual_lead_in=visual_lead_in,
            fixed_text=fixed_text,
            text_position=text_position,
            text_style=text_style,
            video_orientation=video_orientation,
            bottom_text=bottom_text,
            phone_number=phone_number,
            enable_subtitles=enable_subtitles,
            enable_music=enable_music,
        )

        # Record video generation in SaaS audit history
        if user_id:
            try:
                record_generation(
                    user_id=user_id,
                    job_id=job_id,
                    video_url=summary.get("video_url"),
                    title=preset or fixed_text or f"فيديو {saved_video_path.stem}",
                )
            except Exception as re:
                logger.warning("Failed to record video generation in auth_db: %s", re)

        # Auto-update or save prompt descriptions in SQLite prompt_db
        if prompt_id is not None:
            update_prompt_script(
                prompt_id=prompt_id,
                inferred_script=summary.get("inferred_script") or summary.get("script", ""),
            )
            summary["prompt_id"] = prompt_id
        elif visual_description or speech_description:
            try:
                new_pid = save_prompt(
                    visual_description=visual_description or "",
                    speech_description=speech_description or "",
                    inferred_script=summary.get("inferred_script") or summary.get("script"),
                    title=preset or saved_video_path.stem,
                    metadata={"job_id": job_id, "video": saved_video_path.name, "voice": voice, "visual_lead_in": visual_lead_in},
                )
                summary["prompt_id"] = new_pid
            except Exception as pe:
                logger.warning("Failed to auto-save prompt in background job: %s", pe)

        # Verify output cut file if present on disk
        cut_file = None
        for cand in [summary.get("output_path"), summary.get("video_path"), OUTPUTS_DIR / "mobile_cuts" / f"cut_{job_id}.mp4"]:
            if cand and Path(cand).is_file():
                cut_file = Path(cand)
                break

        video_web_url = summary.get("video_url") or f"/outputs/mobile_cuts/cut_{job_id}.mp4"
        summary["video_url"] = video_web_url
        summary["output_video_url"] = video_web_url
        summary["output_video"] = video_web_url
        summary["progress"] = 100
        summary["progress_percent"] = 100
        summary.setdefault("status", "completed")

        if cut_file:
            summary["file_size_bytes"] = cut_file.stat().st_size
            # Atomically update legacy outputs/final_cut.mp4 for backward compatibility
            try:
                legacy_final = OUTPUTS_DIR / "final_cut.mp4"
                legacy_tmp = OUTPUTS_DIR / f"final_cut_{job_id}.mp4.tmp"
                shutil.copyfile(cut_file, legacy_tmp)
                legacy_tmp.replace(legacy_final)
                logger.info("Job %s: Atomically mirrored to legacy %s", job_id, legacy_final)
            except Exception as l_err:
                logger.warning("Job %s: Failed to mirror to legacy final_cut.mp4: %s", job_id, l_err)

        JOBS_STORE[job_id] = summary
        PROGRESS_STORE[job_id] = {
            "job_id": job_id,
            "status": "completed",
            "step": 5,
            "current_step": 5,
            "progress": 100,
            "progress_percent": 100,
            "video_url": video_web_url,
            "output_video_url": video_web_url,
            "output_video": video_web_url,
            "file_size_bytes": cut_file.stat().st_size if cut_file else summary.get("file_size_bytes", 0),
            "message": "اكتمل إنتاج الفيديو التسويقي بنجاح! جاهز للمعاينة والتحميل.",
            "agent_logs": PROGRESS_STORE.get(job_id, {}).get("agent_logs", []) + ["اكتملت جميع مراحل المعالجة بنجاح."],
            "auto_mode": summary.get("auto_mode", auto_mode),
            "emotional_tone": summary.get("emotional_tone"),
            "inferred_script": summary.get("inferred_script"),
            "voice": voice,
            "visual_lead_in": visual_lead_in,
            "analyzed_frames_count": summary.get("analyzed_frames_count"),
            "user_id": user_id,
            "fixed_text": fixed_text,
            "bottom_text": summary.get("bottom_text", bottom_text),
            "phone_number": summary.get("phone_number", phone_number),
            "script": summary.get("script", script),
            "montage_applied": summary.get("montage_applied", False),
            "montage_details": summary.get("montage_details"),
            "result": summary,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.exception("Error processing job %s: %s", job_id, exc)
        failed_payload = {
            "job_id": job_id,
            "status": "failed",
            "step": 0,
            "current_step": 0,
            "progress": 0,
            "progress_percent": 0,
            "message": f"حدث خطأ أثناء المعالجة: {exc}",
            "error": str(exc),
            "error_details": {
                "type": type(exc).__name__,
                "message": str(exc),
            },
            "agent_logs": PROGRESS_STORE.get(job_id, {}).get("agent_logs", []) + [f"خطأ في المعالجة: {exc}"],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        PROGRESS_STORE[job_id] = failed_payload
        JOBS_STORE[job_id] = failed_payload


# Public alias for downstream modules and tests
execute_video_job = _execute_processing_job


async def create_job_async(request: Request) -> JSONResponse:
    """
    POST /api/jobs/create
    Asynchronous ingestion endpoint: accepts multipart video upload,
    returns job_id immediately with HTTP 202, and runs processing in background.
    Supports auto_mode (Gemini Multimodal Vision script & mood inference).
    """
    try:
        form = await request.form()
    except Exception as exc:
        return JSONResponse({"error": f"Invalid multipart form data: {exc}"}, status_code=400)

    # SaaS Multi-tenant Authentication & Quota Enforcement
    user = _get_authenticated_user_from_form_or_header(request, form)
    if not user:
        return JSONResponse(
            {
                "status": "error",
                "error": "unauthorized",
                "message": "غير مصرح به. يتطلب إنتاج الفيديو تسجيل دخول نشط أو رمز مصادقة صالح.",
            },
            status_code=401,
        )

    allowed, reason, quota_details = check_quota(user["id"])
    if not allowed:
        return JSONResponse(
            {
                "status": "error",
                "error": reason,
                "message": reason,
                "quota_exceeded": True,
                "quota_details": quota_details,
            },
            status_code=403,
        )

    video_field = form.get("video")
    if not video_field or not hasattr(video_field, "filename") or not video_field.filename:
        return JSONResponse({"error": "Missing required 'video' file field."}, status_code=400)

    script = form.get("script")
    if isinstance(script, str):
        script = script.strip() or None
    else:
        script = None

    preset = form.get("preset") or form.get("preset_id")
    if isinstance(preset, str):
        preset = preset.strip() or None
    else:
        preset = None

    voice = form.get("voice") or "ar-XA-Standard-A"
    if isinstance(voice, str):
        voice = resolve_voice_profile(voice.strip())[0]

    visual_lead_in_raw = form.get("visual_lead_in") or 1.2
    try:
        visual_lead_in = float(visual_lead_in_raw)
        visual_lead_in = max(0.0, min(5.0, visual_lead_in))
    except (ValueError, TypeError):
        visual_lead_in = 1.2

    music_track = form.get("music") or form.get("music_track")
    if isinstance(music_track, str):
        music_track = music_track.strip() or None
    else:
        music_track = None

    duck_level_raw = form.get("duck_level") or 0.25
    try:
        duck_level = float(duck_level_raw)
    except (ValueError, TypeError):
        duck_level = 0.25

    auto_mode_raw = form.get("auto_mode")
    auto_mode = str(auto_mode_raw).lower() in ("true", "1", "yes", "on") if auto_mode_raw is not None else False

    emotional_tone = form.get("emotional_tone") or form.get("mood")
    if isinstance(emotional_tone, str):
        emotional_tone = emotional_tone.strip() or None
    else:
        emotional_tone = None

    visual_description = form.get("visual_description")
    if isinstance(visual_description, str):
        visual_description = visual_description.strip() or None
    else:
        visual_description = None

    speech_description = form.get("speech_description")
    if isinstance(speech_description, str):
        speech_description = speech_description.strip() or None
    else:
        speech_description = None

    # Fixed text overlay and layout options
    fixed_text = form.get("fixed_text")
    if isinstance(fixed_text, str):
        fixed_text = fixed_text.strip() or None
    else:
        fixed_text = None

    bottom_text = form.get("bottom_text")
    if isinstance(bottom_text, str):
        bottom_text = bottom_text.strip() or None
    else:
        bottom_text = None

    phone_number = form.get("phone_number")
    if isinstance(phone_number, str):
        phone_number = phone_number.strip() or None
    else:
        phone_number = None

    enable_subtitles_raw = form.get("enable_subtitles") or form.get("subtitles")
    enable_subtitles = None
    if enable_subtitles_raw is not None:
        if isinstance(enable_subtitles_raw, str):
            enable_subtitles = enable_subtitles_raw.lower() in ("true", "1", "yes", "on")
        else:
            enable_subtitles = bool(enable_subtitles_raw)

    enable_music_raw = form.get("enable_music") or form.get("music_enabled")
    enable_music = None
    if enable_music_raw is not None:
        if isinstance(enable_music_raw, str):
            enable_music = enable_music_raw.lower() in ("true", "1", "yes", "on")
        else:
            enable_music = bool(enable_music_raw)

    # Prompt Security Guardrails
    raw_prompt = form.get("prompt")
    try:
        if isinstance(raw_prompt, str) and raw_prompt.strip():
            sanitize_and_validate_prompt(raw_prompt)
        if script:
            script = sanitize_and_validate_prompt(script)
        if speech_description:
            speech_description = sanitize_and_validate_prompt(speech_description)
        if visual_description:
            visual_description = sanitize_and_validate_prompt(visual_description)
        if fixed_text:
            fixed_text = sanitize_and_validate_prompt(fixed_text)
        if bottom_text:
            bottom_text = sanitize_and_validate_prompt(bottom_text)
    except ValueError as sec_err:
        return JSONResponse(
            {
                "status": "error",
                "error": "security_violation",
                "message": str(sec_err),
            },
            status_code=400,
        )

    # Prompt intent & directive disentanglement
    incoming_prompt_sources = [s for s in [raw_prompt, script, speech_description, fixed_text, bottom_text] if s and str(s).strip()]
    merged_prompt_text = "\n".join(incoming_prompt_sources)
    if merged_prompt_text:
        dirs = extract_directives(merged_prompt_text)
        if not phone_number and dirs.get("phone_number"):
            phone_number = dirs["phone_number"]
        if not bottom_text and dirs.get("bottom_text"):
            bottom_text = dirs["bottom_text"]
        if dirs.get("is_meta_prompt"):
            auto_mode = True
            if script and is_meta_prompt(script):
                speech_description = (f"{speech_description or ''}\n{script}").strip()
                script = None

    text_position = form.get("text_position")
    if isinstance(text_position, str):
        text_position = text_position.strip() or "lower_third"
    else:
        text_position = "lower_third"

    text_style = form.get("text_style")
    if isinstance(text_style, str):
        text_style = text_style.strip() or "modern_white"
    else:
        text_style = "modern_white"

    video_orientation = form.get("video_orientation") or form.get("orientation")
    if isinstance(video_orientation, str):
        video_orientation = video_orientation.strip() or None
    else:
        video_orientation = None

    # Save uploaded file
    original_filename = Path(video_field.filename).name
    clean_suffix = Path(original_filename).suffix.lower() or ".mp4"
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    unique_name = f"upload_{timestamp_str}_{uuid.uuid4().hex[:6]}{clean_suffix}"
    saved_video_path = UPLOADS_DIR / unique_name

    try:
        with open(saved_video_path, "wb") as f_out:
            shutil.copyfileobj(video_field.file, f_out)
    except Exception as exc:
        return JSONResponse({"error": f"Failed to save file: {exc}"}, status_code=500)

    job_id = f"{timestamp_str}_{uuid.uuid4().hex[:6]}"

    # Auto-save prompt description to SQLite prompt_db immediately
    prompt_id: Optional[int] = None
    if visual_description or speech_description:
        try:
            prompt_id = save_prompt(
                visual_description=visual_description or "",
                speech_description=speech_description or "",
                inferred_script=None,
                title=preset or Path(original_filename).stem,
                metadata={"job_id": job_id, "video": original_filename, "voice": voice, "visual_lead_in": visual_lead_in},
            )
        except Exception as pe:
            logger.warning("Failed to auto-save prompt in create_job_async: %s", pe)

    PROGRESS_STORE[job_id] = {
        "job_id": job_id,
        "status": "processing",
        "step": 1,
        "progress_percent": 10,
        "message": "تم استلام الفيديو من هاتفك بنجاح. جاري فحص وتحليل الملف...",
        "agent_logs": [f"تم رفع الفيديو '{original_filename}' وحفظه على الخادم."],
        "auto_mode": auto_mode,
        "emotional_tone": emotional_tone,
        "visual_description": visual_description,
        "speech_description": speech_description,
        "prompt_id": prompt_id,
        "voice": voice,
        "visual_lead_in": visual_lead_in,
        "user_id": user["id"],
        "fixed_text": fixed_text,
        "bottom_text": bottom_text,
        "phone_number": phone_number,
        "script": script,
        "inferred_script": None,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    # Launch background thread
    t = threading.Thread(
        target=_execute_processing_job,
        args=(
            job_id,
            saved_video_path,
            script,
            preset,
            voice,
            duck_level,
            music_track,
            auto_mode,
            emotional_tone,
            visual_description,
            speech_description,
            prompt_id,
            visual_lead_in,
            user["id"],
            fixed_text,
            text_position,
            text_style,
            video_orientation,
            bottom_text,
            phone_number,
            enable_subtitles,
            enable_music,
        ),
        daemon=True,
    )
    t.start()

    return JSONResponse(
        {
            "job_id": job_id,
            "status": "processing",
            "message": "بدأ وكيل الذكاء الاصطناعي معالجة الفيديو بنجاح.",
            "status_url": f"/api/status/{job_id}",
            "auto_mode": auto_mode,
            "emotional_tone": emotional_tone,
            "prompt_id": prompt_id,
            "voice": voice,
            "visual_lead_in_seconds": visual_lead_in,
            "bottom_text": bottom_text,
            "phone_number": phone_number,
            "user": {
                "id": user["id"],
                "username": user["username"],
                "business_name": user["business_name"],
                "business_category": user["business_category"],
            },
            "quotas": quota_details,
            "fixed_text": fixed_text,
            "video_orientation": video_orientation,
        },
        status_code=202,
    )


async def upload_and_process(request: Request) -> JSONResponse:
    """
    POST /api/upload-and-process
    Synchronous processing endpoint for direct client calls and automated tests.
    Supports auto_mode (Gemini Multimodal Vision script & mood inference).
    """
    try:
        form = await request.form()
    except Exception as exc:
        return JSONResponse({"error": f"Invalid multipart form data: {exc}"}, status_code=400)

    # SaaS Multi-tenant Authentication & Quota Enforcement
    user = _get_authenticated_user_from_form_or_header(request, form)
    if not user:
        return JSONResponse(
            {
                "status": "error",
                "error": "unauthorized",
                "message": "غير مصرح به. يتطلب إنتاج الفيديو تسجيل دخول نشط أو رمز مصادقة صالح.",
            },
            status_code=401,
        )

    allowed, reason, quota_details = check_quota(user["id"])
    if not allowed:
        return JSONResponse(
            {
                "status": "error",
                "error": reason,
                "message": reason,
                "quota_exceeded": True,
                "quota_details": quota_details,
            },
            status_code=403,
        )

    video_field = form.get("video")
    if not video_field or not hasattr(video_field, "filename") or not video_field.filename:
        return JSONResponse({"error": "Missing required 'video' file field in multipart form."}, status_code=400)

    script = form.get("script")
    if isinstance(script, str):
        script = script.strip() or None
    else:
        script = None

    preset = form.get("preset") or form.get("preset_id")
    if isinstance(preset, str):
        preset = preset.strip() or None
    else:
        preset = None

    voice = form.get("voice") or "ar-XA-Standard-A"
    if isinstance(voice, str):
        voice = resolve_voice_profile(voice.strip())[0]

    visual_lead_in_raw = form.get("visual_lead_in") or 1.2
    try:
        visual_lead_in = float(visual_lead_in_raw)
        visual_lead_in = max(0.0, min(5.0, visual_lead_in))
    except (ValueError, TypeError):
        visual_lead_in = 1.2

    music_track = form.get("music") or form.get("music_track")
    if isinstance(music_track, str):
        music_track = music_track.strip() or None
    else:
        music_track = None

    duck_level_raw = form.get("duck_level") or 0.25
    try:
        duck_level = float(duck_level_raw)
    except (ValueError, TypeError):
        duck_level = 0.25

    auto_mode_raw = form.get("auto_mode")
    auto_mode = str(auto_mode_raw).lower() in ("true", "1", "yes", "on") if auto_mode_raw is not None else False

    emotional_tone = form.get("emotional_tone") or form.get("mood")
    if isinstance(emotional_tone, str):
        emotional_tone = emotional_tone.strip() or None
    else:
        emotional_tone = None

    visual_description = form.get("visual_description")
    if isinstance(visual_description, str):
        visual_description = visual_description.strip() or None
    else:
        visual_description = None

    speech_description = form.get("speech_description")
    if isinstance(speech_description, str):
        speech_description = speech_description.strip() or None
    else:
        speech_description = None

    # Fixed text overlay and layout options
    fixed_text = form.get("fixed_text")
    if isinstance(fixed_text, str):
        fixed_text = fixed_text.strip() or None
    else:
        fixed_text = None

    bottom_text = form.get("bottom_text")
    if isinstance(bottom_text, str):
        bottom_text = bottom_text.strip() or None
    else:
        bottom_text = None

    phone_number = form.get("phone_number")
    if isinstance(phone_number, str):
        phone_number = phone_number.strip() or None
    else:
        phone_number = None

    enable_subtitles_raw = form.get("enable_subtitles") or form.get("subtitles")
    enable_subtitles = None
    if enable_subtitles_raw is not None:
        if isinstance(enable_subtitles_raw, str):
            enable_subtitles = enable_subtitles_raw.lower() in ("true", "1", "yes", "on")
        else:
            enable_subtitles = bool(enable_subtitles_raw)

    enable_music_raw = form.get("enable_music") or form.get("music_enabled")
    enable_music = None
    if enable_music_raw is not None:
        if isinstance(enable_music_raw, str):
            enable_music = enable_music_raw.lower() in ("true", "1", "yes", "on")
        else:
            enable_music = bool(enable_music_raw)

    # Prompt Security Guardrails
    raw_prompt = form.get("prompt")
    try:
        if isinstance(raw_prompt, str) and raw_prompt.strip():
            sanitize_and_validate_prompt(raw_prompt)
        if script:
            script = sanitize_and_validate_prompt(script)
        if speech_description:
            speech_description = sanitize_and_validate_prompt(speech_description)
        if visual_description:
            visual_description = sanitize_and_validate_prompt(visual_description)
        if fixed_text:
            fixed_text = sanitize_and_validate_prompt(fixed_text)
        if bottom_text:
            bottom_text = sanitize_and_validate_prompt(bottom_text)
    except ValueError as sec_err:
        return JSONResponse(
            {
                "status": "error",
                "error": "security_violation",
                "message": str(sec_err),
            },
            status_code=400,
        )

    # Prompt intent & directive disentanglement
    incoming_prompt_sources = [s for s in [raw_prompt, script, speech_description, fixed_text, bottom_text] if s and str(s).strip()]
    merged_prompt_text = "\n".join(incoming_prompt_sources)
    if merged_prompt_text:
        dirs = extract_directives(merged_prompt_text)
        if not phone_number and dirs.get("phone_number"):
            phone_number = dirs["phone_number"]
        if not bottom_text and dirs.get("bottom_text"):
            bottom_text = dirs["bottom_text"]
        if dirs.get("is_meta_prompt"):
            auto_mode = True
            if script and is_meta_prompt(script):
                speech_description = (f"{speech_description or ''}\n{script}").strip()
                script = None

    text_position = form.get("text_position")
    if isinstance(text_position, str):
        text_position = text_position.strip() or "lower_third"
    else:
        text_position = "lower_third"

    text_style = form.get("text_style")
    if isinstance(text_style, str):
        text_style = text_style.strip() or "modern_white"
    else:
        text_style = "modern_white"

    video_orientation = form.get("video_orientation") or form.get("orientation")
    if isinstance(video_orientation, str):
        video_orientation = video_orientation.strip() or None
    else:
        video_orientation = None

    original_filename = Path(video_field.filename).name
    clean_suffix = Path(original_filename).suffix.lower() or ".mp4"
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    unique_name = f"upload_{timestamp_str}_{uuid.uuid4().hex[:6]}{clean_suffix}"
    saved_video_path = UPLOADS_DIR / unique_name

    try:
        with open(saved_video_path, "wb") as f_out:
            shutil.copyfileobj(video_field.file, f_out)
    except Exception as exc:
        return JSONResponse({"error": f"Failed to save uploaded file: {exc}"}, status_code=500)

    job_id = f"{timestamp_str}_{uuid.uuid4().hex[:6]}"
    PROGRESS_STORE[job_id] = {
        "job_id": job_id,
        "status": "processing",
        "step": 1,
        "current_step": 1,
        "progress": 15,
        "progress_percent": 15,
        "message": "جاري بدء معالجة الفيديو...",
        "agent_logs": [f"تم رفع الفيديو '{original_filename}'."],
        "auto_mode": auto_mode,
        "emotional_tone": emotional_tone,
        "user_id": user["id"],
        "fixed_text": fixed_text,
        "inferred_script": None,
    }

    def _on_progress(event: Dict[str, Any]):
        curr = PROGRESS_STORE.get(job_id, {})
        logs = curr.get("agent_logs", [])
        if event.get("log") and event["log"] not in logs:
            logs.append(event["log"])

        pct = event.get("percent") if event.get("percent") is not None else event.get("progress_percent", 15)
        step = event.get("step", 1)

        evt_status = event.get("status")
        if evt_status in ("failed", "error"):
            status_val = "failed"
        elif evt_status in ("completed", "done") or (isinstance(pct, (int, float)) and pct >= 100):
            status_val = "completed"
        else:
            status_val = "processing"

        payload = {
            "job_id": job_id,
            "status": status_val,
            "step": step,
            "current_step": step,
            "progress": pct,
            "progress_percent": pct,
            "message": event.get("message", "جاري المعالجة..."),
            "agent_logs": logs,
            "auto_mode": auto_mode,
            "emotional_tone": event.get("emotional_tone") or curr.get("emotional_tone") or emotional_tone,
            "inferred_script": event.get("inferred_script") or curr.get("inferred_script"),
            "user_id": user["id"],
            "fixed_text": fixed_text,
            "bottom_text": event.get("bottom_text") or curr.get("bottom_text") or bottom_text,
            "phone_number": event.get("phone_number") or curr.get("phone_number") or phone_number,
            "script": event.get("script") or curr.get("script") or script,
            "error": event.get("error") or curr.get("error"),
        }
        if event.get("error_details"):
            payload["error_details"] = event["error_details"]
        if event.get("video_url"):
            payload["video_url"] = event["video_url"]
        if event.get("sandboxed_video_url"):
            payload["sandboxed_video_url"] = event["sandboxed_video_url"]

        PROGRESS_STORE[job_id] = payload
        if status_val == "failed":
            JOBS_STORE[job_id] = dict(payload)

    try:
        summary = process_mobile_video(
            video_path=saved_video_path,
            script=script,
            preset_id=preset,
            voice=voice,
            duck_level=duck_level,
            music_track=music_track,
            output_dir=OUTPUTS_DIR / "mobile_cuts",
            progress_callback=_on_progress,
            auto_mode=auto_mode,
            emotional_tone=emotional_tone,
            visual_description=visual_description,
            speech_description=speech_description,
            visual_lead_in=visual_lead_in,
            fixed_text=fixed_text,
            text_position=text_position,
            text_style=text_style,
            video_orientation=video_orientation,
            bottom_text=bottom_text,
            phone_number=phone_number,
            enable_subtitles=enable_subtitles,
            enable_music=enable_music,
        )

        # Record video generation in SaaS audit history
        try:
            record_generation(
                user_id=user["id"],
                job_id=summary.get("job_id", job_id),
                video_url=summary.get("video_url"),
                title=preset or fixed_text or Path(original_filename).stem,
            )
        except Exception as re:
            logger.warning("Failed to record generation in upload_and_process: %s", re)

        _, _, updated_quotas = check_quota(user["id"])
        summary["user"] = {
            "id": user["id"],
            "username": user["username"],
            "business_name": user["business_name"],
            "business_category": user["business_category"],
        }
        summary["quotas"] = updated_quotas

        # Auto-save prompt descriptions in SQLite prompt_db
        if visual_description or speech_description:
            try:
                prompt_id = save_prompt(
                    visual_description=visual_description or "",
                    speech_description=speech_description or "",
                    inferred_script=summary.get("inferred_script") or summary.get("script"),
                    title=preset or Path(original_filename).stem,
                    metadata={"job_id": summary.get("job_id"), "video": original_filename, "voice": voice, "visual_lead_in": visual_lead_in},
                )
                summary["prompt_id"] = prompt_id
            except Exception as pe:
                logger.warning("Failed to auto-save prompt in upload_and_process: %s", pe)

        assigned_job_id = summary.get("job_id", job_id)
        summary["job_id"] = assigned_job_id

        # Verify output cut file if present on disk
        cut_file = None
        for cand in [summary.get("output_path"), summary.get("video_path"), OUTPUTS_DIR / "mobile_cuts" / f"cut_{assigned_job_id}.mp4"]:
            if cand and Path(cand).is_file():
                cut_file = Path(cand)
                break

        video_web_url = summary.get("video_url") or f"/outputs/mobile_cuts/cut_{assigned_job_id}.mp4"
        summary["video_url"] = video_web_url
        summary["output_video_url"] = video_web_url
        summary["output_video"] = video_web_url
        summary["progress"] = 100
        summary["progress_percent"] = 100
        summary.setdefault("status", "completed")

        if cut_file:
            summary["file_size_bytes"] = cut_file.stat().st_size
            # Atomically update legacy outputs/final_cut.mp4 for backward compatibility
            try:
                legacy_final = OUTPUTS_DIR / "final_cut.mp4"
                legacy_tmp = OUTPUTS_DIR / f"final_cut_{assigned_job_id}.mp4.tmp"
                shutil.copyfile(cut_file, legacy_tmp)
                legacy_tmp.replace(legacy_final)
                logger.info("Job %s: Atomically mirrored upload cut to legacy %s", assigned_job_id, legacy_final)
            except Exception as l_err:
                logger.warning("Job %s: Failed to mirror upload cut to legacy final_cut.mp4: %s", assigned_job_id, l_err)

        JOBS_STORE[assigned_job_id] = summary
        PROGRESS_STORE[assigned_job_id] = {
            "job_id": assigned_job_id,
            "status": "completed",
            "step": 5,
            "current_step": 5,
            "progress": 100,
            "progress_percent": 100,
            "video_url": video_web_url,
            "output_video_url": video_web_url,
            "output_video": video_web_url,
            "file_size_bytes": cut_file.stat().st_size if cut_file else summary.get("file_size_bytes", 0),
            "message": "اكتمل الإنتاج بنجاح!",
            "auto_mode": summary.get("auto_mode", auto_mode),
            "emotional_tone": summary.get("emotional_tone"),
            "inferred_script": summary.get("inferred_script"),
            "user_id": user["id"],
            "bottom_text": summary.get("bottom_text", bottom_text),
            "phone_number": summary.get("phone_number", phone_number),
            "script": summary.get("script", script),
            "montage_applied": summary.get("montage_applied", False),
            "montage_details": summary.get("montage_details"),
            "result": summary,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        return JSONResponse(summary, status_code=200)

    except Exception as exc:
        logger.exception("Error during video processing: %s", exc)
        failed_payload = {
            "job_id": job_id,
            "status": "failed",
            "step": 0,
            "current_step": 0,
            "progress": 0,
            "progress_percent": 0,
            "message": f"حدث خطأ أثناء المعالجة: {exc}",
            "error": str(exc),
            "error_details": {
                "type": type(exc).__name__,
                "message": str(exc),
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        PROGRESS_STORE[job_id] = failed_payload
        JOBS_STORE[job_id] = failed_payload
        return JSONResponse(failed_payload, status_code=500)


def _find_finalized_cut_file(job_id: str, data: Optional[Dict[str, Any]] = None) -> Tuple[Optional[Path], str]:
    """
    Check candidate paths on disk to verify if the output video cut is finalized and non-empty.
    Returns (Path or None, web_url).
    """
    data = data or {}
    candidates = []

    # Check explicit paths from payload / result
    for key in ("output_path", "absolute_output_path", "video_path"):
        val = data.get(key)
        if val:
            candidates.append(Path(val))
    if isinstance(data.get("result"), dict):
        for key in ("output_path", "absolute_output_path", "video_path"):
            val = data["result"].get(key)
            if val:
                candidates.append(Path(val))

    # Check sandboxed job directory
    candidates.append(OUTPUTS_DIR / "jobs" / job_id / "sandbox" / f"cut_{job_id}.mp4")
    # Check mobile_cuts directory
    candidates.append(OUTPUTS_DIR / "mobile_cuts" / f"cut_{job_id}.mp4")
    if job_id in ("final_cut", "default"):
        candidates.append(OUTPUTS_DIR / "final_cut.mp4")

    for cand in candidates:
        try:
            if cand.is_file() and cand.stat().st_size > 0:
                if f"jobs/{job_id}/sandbox" in str(cand):
                    url = f"/outputs/jobs/{job_id}/sandbox/cut_{job_id}.mp4"
                elif "mobile_cuts" in str(cand):
                    url = f"/outputs/mobile_cuts/{cand.name}"
                else:
                    url = data.get("video_url") or f"/outputs/mobile_cuts/cut_{job_id}.mp4"
                return (cand, url)
        except OSError:
            pass

    default_url = data.get("video_url") or f"/outputs/mobile_cuts/cut_{job_id}.mp4"
    return (None, default_url)


async def get_job_status(request: Request) -> JSONResponse:
    """GET /api/status/{job_id} - Retrieve live telemetry, status and execution summary for a job."""
    job_id = request.path_params.get("job_id", "")
    if not job_id:
        return JSONResponse({"error": "Missing job_id parameter."}, status_code=400)

    # 1. Check in-flight progress telemetry
    if job_id in PROGRESS_STORE:
        p_data = PROGRESS_STORE[job_id]

        # Immediate error propagation
        if p_data.get("status") in ("failed", "error"):
            err_msg = p_data.get("error") or p_data.get("message") or "فشلت معالجة الفيديو."
            return JSONResponse({
                "job_id": job_id,
                "status": "failed",
                "step": 0,
                "current_step": 0,
                "progress": 0,
                "progress_percent": 0,
                "message": p_data.get("message", "حدث خطأ أثناء المعالجة."),
                "error": err_msg,
                "error_details": p_data.get("error_details") or {"message": err_msg},
                "agent_logs": p_data.get("agent_logs", []),
                "updated_at": p_data.get("updated_at"),
            })

        if p_data.get("status") in ("completed", "done"):
            cut_file, video_web_url = _find_finalized_cut_file(job_id, p_data)
            res_dict = dict(p_data.get("result") or p_data)
            res_dict.setdefault("emotional_tone", p_data.get("emotional_tone"))
            res_dict.setdefault("inferred_script", p_data.get("inferred_script"))
            res_dict.setdefault("script", p_data.get("script") or p_data.get("inferred_script"))
            res_dict.setdefault("bottom_text", p_data.get("bottom_text"))
            res_dict.setdefault("phone_number", p_data.get("phone_number"))
            res_dict.setdefault("auto_mode", p_data.get("auto_mode", False))
            res_dict.setdefault("subtitles", p_data.get("subtitles") or [])
            res_dict.setdefault("shot_timeline", p_data.get("shot_timeline") or [])
            res_dict.setdefault("videographer_speech", p_data.get("videographer_speech"))
            res_dict.setdefault("customer_specifications", p_data.get("customer_specifications") or {})
            res_dict["job_id"] = job_id
            res_dict["status"] = "completed"
            res_dict["step"] = 5
            res_dict["current_step"] = 5
            res_dict["progress"] = 100
            res_dict["progress_percent"] = 100
            res_dict["video_url"] = video_web_url
            res_dict["output_video_url"] = video_web_url
            res_dict["output_video"] = video_web_url
            if cut_file:
                res_dict["file_size_bytes"] = cut_file.stat().st_size
            return JSONResponse(res_dict)

        # In-flight processing state
        resp = dict(p_data)
        step = resp.get("step") or resp.get("current_step") or 1
        resp["step"] = step
        resp["current_step"] = step
        pct = resp.get("progress_percent") if resp.get("progress_percent") is not None else resp.get("progress", 15)
        resp["progress"] = pct
        resp["progress_percent"] = pct
        return JSONResponse(resp)

    # 2. Check in-memory completed store
    if job_id in JOBS_STORE:
        j_data = JOBS_STORE[job_id]
        if j_data.get("status") in ("failed", "error"):
            err_msg = j_data.get("error") or j_data.get("message") or "فشلت معالجة الفيديو."
            return JSONResponse({
                "job_id": job_id,
                "status": "failed",
                "step": 0,
                "current_step": 0,
                "progress": 0,
                "progress_percent": 0,
                "message": j_data.get("message", "حدث خطأ أثناء المعالجة."),
                "error": err_msg,
                "error_details": j_data.get("error_details") or {"message": err_msg},
                "agent_logs": j_data.get("agent_logs", []),
                "updated_at": j_data.get("updated_at"),
            })

        cut_file, video_web_url = _find_finalized_cut_file(job_id, j_data)
        res = dict(j_data)
        res["job_id"] = job_id
        res["status"] = "completed"
        res["step"] = 5
        res["current_step"] = 5
        res["progress"] = 100
        res["progress_percent"] = 100
        res["video_url"] = video_web_url
        res["output_video_url"] = video_web_url
        res["output_video"] = video_web_url
        if cut_file:
            res["file_size_bytes"] = cut_file.stat().st_size
        return JSONResponse(res)

    # 3. Check disk for summary_<job_id>.json in sandbox or mobile_cuts
    summary_candidates = [
        OUTPUTS_DIR / "jobs" / job_id / "sandbox" / f"summary_{job_id}.json",
        OUTPUTS_DIR / "mobile_cuts" / f"summary_{job_id}.json",
    ]
    for summary_file in summary_candidates:
        if summary_file.is_file():
            try:
                with open(summary_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                cut_file, video_web_url = _find_finalized_cut_file(job_id, data)
                data["job_id"] = job_id
                data["video_url"] = video_web_url
                data["output_video_url"] = video_web_url
                data["output_video"] = video_web_url
                data["status"] = "completed"
                data["step"] = 5
                data["current_step"] = 5
                data["progress"] = 100
                data["progress_percent"] = 100
                if cut_file:
                    data["file_size_bytes"] = cut_file.stat().st_size
                JOBS_STORE[job_id] = data
                return JSONResponse(data)
            except Exception as exc:
                logger.warning("Failed to read summary file %s: %s", summary_file, exc)

    return JSONResponse(
        {
            "job_id": job_id,
            "status": "not_found",
            "error": f"Job '{job_id}' not found.",
            "message": f"لم يتم العثور على المهمة '{job_id}'.",
        },
        status_code=404,
    )


async def get_mobile_cut_endpoint(request: Request) -> Response:
    """
    GET /outputs/mobile_cuts/{filename}
    Serve rendered job video cut with MIME type video/mp4, Accept-Ranges,
    and full HTTP 206 Partial Content range streaming support.
    """
    filename = request.path_params.get("filename", "")
    safe_name = Path(filename).name
    cut_path = OUTPUTS_DIR / "mobile_cuts" / safe_name
    if not cut_path.is_file():
        return JSONResponse(
            {"status": "error", "error": "file_not_found", "message": f"Video cut '{safe_name}' not found."},
            status_code=404,
        )
    return FileResponse(
        str(cut_path),
        media_type="video/mp4",
        filename=safe_name,
    )


async def index_page(request: Request) -> Response:
    """GET / - Serve mobile web application index."""
    html_file = STATIC_DIR / "index.html"
    if html_file.is_file():
        return FileResponse(str(html_file), media_type="text/html")
    return JSONResponse({
        "service": "Mobile Video API",
        "message": "Welcome. The static frontend will be served here.",
    })


async def admin_page(request: Request) -> Response:
    """GET /admin - Serve dedicated Bootstrap admin portal."""
    admin_file = STATIC_DIR / "admin.html"
    if admin_file.is_file():
        return FileResponse(str(admin_file), media_type="text/html")
    return JSONResponse({
        "status": "not_found",
        "message": "Admin portal template not found.",
    }, status_code=404)


async def style_css_endpoint(request: Request) -> Response:
    """GET /style.css - Root alias for CSS stylesheet."""
    css_file = STATIC_DIR / "style.css"
    if css_file.is_file():
        return FileResponse(str(css_file), media_type="text/css")
    return Response(content="/* style.css */", media_type="text/css")


async def app_js_endpoint(request: Request) -> Response:
    """GET /app.js - Root alias for JavaScript application bundle."""
    js_file = STATIC_DIR / "app.js"
    if js_file.is_file():
        return FileResponse(str(js_file), media_type="application/javascript")
    return Response(content="// app.js", media_type="application/javascript")


async def favicon_endpoint(request: Request) -> Response:
    """GET /favicon.ico - Returns clean SVG or empty icon to prevent 404."""
    fav_file = STATIC_DIR / "favicon.ico"
    if fav_file.is_file():
        return FileResponse(str(fav_file), media_type="image/x-icon")
    svg_icon = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text y=".9em" font-size="90">🎬</text></svg>'
    return Response(content=svg_icon, media_type="image/svg+xml")
async def get_principles_endpoint(request: Request) -> JSONResponse:
    """GET /api/principles - Retrieve currently active production & voice principles."""
    return JSONResponse(load_principles())


async def save_principles_endpoint(request: Request) -> JSONResponse:
    """POST /api/principles - Save updated user/AI production principles."""
    try:
        body = await request.json()
        saved = save_principles(body)
        return JSONResponse({
            "status": "ok",
            "message": "تم حفظ معايير الإنتاج وتحديثها بنجاح",
            "principles": saved
        })
    except Exception as exc:
        logger.warning("Failed to save principles: %s", exc)
        return JSONResponse({"status": "error", "error": str(exc)}, status_code=400)


async def reset_principles_endpoint(request: Request) -> JSONResponse:
    """POST /api/principles/reset - Reset principles to factory defaults."""
    res = reset_principles()
    return JSONResponse({
        "status": "ok",
        "message": "تمت استعادة معايير الإنتاج الافتراضية بنجاح",
        "principles": res
    })


async def annotate_video_endpoint(request: Request) -> JSONResponse:
    """POST /api/video/annotate - Apply visual annotations and badges onto a video cut."""
    try:
        body = await request.json()
        input_video = body.get("input_video")
        output_video = body.get("output_video")
        annotations = body.get("annotations", [])
        if not input_video or not output_video:
            return JSONResponse({"error": "Missing input_video or output_video parameter."}, status_code=400)
        res = annotate_video(input_video, output_video, annotations)
        return JSONResponse(res)
    except FileNotFoundError as fnf:
        logger.warning("Annotate video target not found: %s", fnf)
        return JSONResponse({"status": "error", "error": str(fnf)}, status_code=404)
    except Exception as exc:
        logger.exception("Failed to annotate video: %s", exc)
        return JSONResponse({"status": "error", "error": str(exc)}, status_code=500)


async def get_prompts_history_endpoint(request: Request) -> JSONResponse:
    """GET /api/prompts/history - Retrieve recent prompt descriptions history."""
    try:
        limit_param = request.query_params.get("limit", "50")
        limit = int(limit_param)
    except (ValueError, TypeError):
        limit = 50
    prompts = get_recent_prompts(limit=limit)
    return JSONResponse({
        "status": "ok",
        "prompts": prompts,
    })


async def create_prompt_endpoint(request: Request) -> JSONResponse:
    """
    POST /api/prompts - Save prompt descriptions and title to SQLite.
    Accepts JSON: {"visual_description": "...", "speech_description": "...", "title": "..."}
    """
    try:
        body = await request.json()
    except Exception as exc:
        return JSONResponse({"status": "error", "error": f"Invalid JSON body: {exc}"}, status_code=400)

    visual_description = body.get("visual_description", "")
    speech_description = body.get("speech_description", "")
    title = body.get("title")
    inferred_script = body.get("inferred_script")
    metadata = body.get("metadata")

    prompt_id = save_prompt(
        visual_description=visual_description,
        speech_description=speech_description,
        inferred_script=inferred_script,
        title=title,
        metadata=metadata,
    )
    prompt_record = get_prompt_by_id(prompt_id)
    return JSONResponse({
        "status": "ok",
        "id": prompt_id,
        "prompt": prompt_record,
    }, status_code=200)


async def delete_prompt_endpoint(request: Request) -> JSONResponse:
    """DELETE /api/prompts/{prompt_id} - Delete prompt record from SQLite."""
    prompt_id_raw = request.path_params.get("prompt_id")
    try:
        prompt_id = int(prompt_id_raw)
    except (ValueError, TypeError):
        return JSONResponse({"status": "error", "error": "Invalid prompt_id"}, status_code=400)

    deleted = delete_prompt(prompt_id)
    if not deleted:
        return JSONResponse({
            "status": "error",
            "message": f"Prompt with ID {prompt_id} not found.",
            "deleted": False,
        }, status_code=404)

    return JSONResponse({
        "status": "ok",
        "message": f"Prompt {prompt_id} deleted successfully.",
        "deleted": True,
    })


async def get_voices_endpoint(request: Request) -> JSONResponse:
    """GET /api/voices - Returns catalog of supported real estate voice profiles."""
    return JSONResponse({
        "status": "ok",
        "voices": get_voice_profiles_list(),
    })


async def voice_sample_endpoint(request: Request) -> Response:
    """GET /api/voices/{voice_id}/sample - Stream audio preview sample for voice audition."""
    voice_id = request.path_params.get("voice_id", "ar-XA-Standard-A")
    try:
        sample_path = get_or_create_voice_sample(voice_id)
        if sample_path.is_file() and sample_path.stat().st_size > 0:
            return FileResponse(
                str(sample_path),
                media_type="audio/wav",
                filename=f"{voice_id}_sample.wav",
            )
        return JSONResponse({"status": "error", "message": f"Could not generate sample for {voice_id}"}, status_code=500)
    except Exception as exc:
        logger.exception("Voice sample generation error: %s", exc)
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=500)


async def login_endpoint(request: Request) -> JSONResponse:
    """
    POST /api/auth/login
    Accepts JSON or form data: {"username": "...", "password": "..."} or {"token": "..."}.
    Validates credentials, creates authenticated session, sets cookie, and returns token + quotas.
    Recognizes master admin 'pluto' (password 'plutosw4') as well as commercial merchant accounts.
    """
    username = None
    password = None
    token = None
    try:
        body = await request.json()
        username = body.get("username") or body.get("user") or body.get("login")
        password = body.get("password") or body.get("pass")
        token = body.get("token") or body.get("auth_token") or body.get("session_token")
    except Exception:
        try:
            form = await request.form()
            username = form.get("username") or form.get("user") or form.get("login")
            password = form.get("password") or form.get("pass")
            token = form.get("token") or form.get("auth_token") or form.get("session_token")
        except Exception:
            pass

    if isinstance(username, str):
        username = username.strip()
    if isinstance(password, str):
        password = password.strip()
    if isinstance(token, str):
        token = token.strip()
        if token.lower().startswith("bearer "):
            token = token[7:].strip()

    user = None
    if token and not username and not password:
        user = authenticate_token(token)
    elif username:
        user = authenticate_user(username, password)
    elif password and not username:
        user = authenticate_token(password)

    if not user:
        return JSONResponse(
            {
                "status": "error",
                "message": "اسم المستخدم أو كلمة المرور غير صحيحة.",
            },
            status_code=401,
        )

    if not user.get("is_active", True) or user.get("status") in ("suspended", "inactive"):
        return JSONResponse(
            {
                "status": "error",
                "message": "الحساب معطل حالياً من قِبل إدارة المنصة.",
            },
            status_code=403,
        )

    # Create authenticated session
    session = create_session(user["id"])
    allowed, reason, quota_details = check_quota(user["id"])

    response = JSONResponse(
        {
            "status": "ok",
            "message": "تم تسجيل الدخول بنجاح.",
            "session_token": session["session_token"],
            "token": session["session_token"],
            "auth_token": user.get("auth_token"),
            "expires_at": session["expires_at"],
            "user": user,
            "session": session,
            "quota": quota_details,
            "quotas": quota_details,
        }
    )
    response.set_cookie(
        key="session_token",
        value=session["session_token"],
        httponly=True,
        samesite="lax",
        max_age=7 * 86400,
        path="/",
    )
    return response


async def logout_endpoint(request: Request) -> JSONResponse:
    """POST /api/auth/logout - Invalidate active session and clear session cookie."""
    token = None
    try:
        body = await request.json()
        token = body.get("session_token") or body.get("token") or body.get("auth_token")
    except Exception:
        try:
            form = await request.form()
            token = form.get("session_token") or form.get("token") or form.get("auth_token")
        except Exception:
            pass

    if not token:
        user, session = _get_authenticated_user_and_session(request)
        if session:
            token = session["session_token"]
        elif user:
            token = user.get("auth_token")

    if token:
        delete_session(token)

    response = JSONResponse({"status": "ok", "message": "تم تسجيل الخروج بنجاح."})
    response.delete_cookie("session_token", path="/")
    return response


async def auth_session_endpoint(request: Request) -> JSONResponse:
    """GET /api/auth/session - Verify active session and return user profile + quotas."""
    user, session = _get_authenticated_user_and_session(request)
    if not user:
        return JSONResponse(
            {
                "status": "error",
                "authenticated": False,
                "message": "غير مصرح به. يرجى تسجيل الدخول أولاً.",
            },
            status_code=401,
        )

    allowed, reason, quota_details = check_quota(user["id"])
    return JSONResponse(
        {
            "status": "ok",
            "authenticated": True,
            "user": user,
            "session": session,
            "quota": quota_details,
            "quotas": quota_details,
        }
    )


async def auth_me_endpoint(request: Request) -> JSONResponse:
    """GET /api/auth/me - Retrieve current merchant profile, session, and quota details."""
    auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
    explicit_token = (
        request.query_params.get("token")
        or request.query_params.get("auth_token")
        or request.query_params.get("session_token")
        or request.headers.get("X-Session-Token")
        or request.headers.get("x-session-token")
        or request.headers.get("X-Auth-Token")
        or request.headers.get("x-auth-token")
    )

    if not auth_header and not explicit_token:
        return JSONResponse(
            {
                "status": "error",
                "authenticated": False,
                "message": "غير مصرح، يرجى تقديم رمز المصادقة (Bearer token)",
            },
            status_code=401,
        )

    user, session = _get_authenticated_user_and_session(request)
    if not user:
        return JSONResponse(
            {
                "status": "error",
                "authenticated": False,
                "message": "رمز المصادقة غير صالح أو منتهي",
            },
            status_code=401,
        )

    allowed, reason, quota_details = check_quota(user["id"])
    history = get_user_history(user["id"], limit=20)
    return JSONResponse(
        {
            "status": "ok",
            "authenticated": True,
            "user": user,
            "session": session,
            "quota": quota_details,
            "quotas": quota_details,
            "history": history,
        }
    )


async def demo_accounts_endpoint(request: Request) -> JSONResponse:
    """GET /api/auth/demo-accounts - Returns list of pre-seeded accounts for 1-tap switching."""
    return JSONResponse({
        "status": "ok",
        "accounts": get_demo_accounts(),
    })


async def admin_login_endpoint(request: Request) -> JSONResponse:
    """
    POST /api/admin/login
    Admin authentication portal: validates username 'pluto' and password 'plutosw4'
    (or any active admin credentials), creates an active session token, sets cookie, and records login audit log.
    """
    username = None
    password = None
    try:
        body = await request.json()
        username = body.get("username") or body.get("user") or body.get("login")
        password = body.get("password") or body.get("pass")
    except Exception:
        try:
            form = await request.form()
            username = form.get("username") or form.get("user") or form.get("login")
            password = form.get("password") or form.get("pass")
        except Exception:
            pass

    if isinstance(username, str):
        username = username.strip()
    if isinstance(password, str):
        password = password.strip()

    if not username or not password:
        return JSONResponse({
            "status": "error",
            "error": "Missing username or password",
            "message": "يرجى إدخال اسم المستخدم وكلمة المرور",
        }, status_code=400)

    user = verify_admin_login(username=username, password_or_token=password)
    if not user:
        return JSONResponse({
            "status": "error",
            "error": "invalid_credentials",
            "message": "بيانات تسجيل الدخول غير صحيحة أو ليس لديك صلاحية مدير النظام",
        }, status_code=401)

    # Check status
    if user.get("status") in ("suspended", "inactive") or not user.get("is_active"):
        return JSONResponse({
            "status": "error",
            "error": "account_suspended",
            "message": "تم تعطيل حساب المدير",
        }, status_code=403)

    session = create_session(user_id=user["id"])
    log_user_event(user["id"], "admin_login", {"username": username, "role": user.get("role")})
    allowed, reason, quota_details = check_quota(user["id"])

    response = JSONResponse({
        "status": "ok",
        "message": "تم تسجيل دخول المسؤول بنجاح",
        "session_token": session["session_token"],
        "token": session["session_token"],
        "auth_token": user.get("auth_token"),
        "expires_at": session["expires_at"],
        "user": user,
        "session": session,
        "quota": quota_details,
        "quotas": quota_details,
    })
    response.set_cookie(
        key="session_token",
        value=session["session_token"],
        httponly=True,
        samesite="lax",
        max_age=7 * 86400,
        path="/",
    )
    return response


async def admin_list_accounts_endpoint(request: Request) -> JSONResponse:
    """
    GET /api/admin/accounts & GET /api/admin/users
    Returns all accounts with usage and quota statistics, status, and validity dates.
    """
    users = list_users()
    return JSONResponse({
        "status": "ok",
        "accounts": users,
        "users": users,
    })


async def admin_create_account_endpoint(request: Request) -> JSONResponse:
    """
    POST /api/admin/accounts & POST /api/admin/users
    Admin creates new commercial merchant or admin account with custom dates, quotas, and password.
    """
    try:
        body = await request.json()
    except Exception as exc:
        return JSONResponse({"status": "error", "error": f"Invalid JSON body: {exc}"}, status_code=400)

    username = body.get("username")
    business_name = body.get("business_name")
    if not username or not business_name:
        return JSONResponse({"status": "error", "error": "Missing required 'username' or 'business_name'"}, status_code=400)

    try:
        new_account = create_user(
            username=str(username).strip(),
            business_name=str(business_name).strip(),
            business_category=body.get("business_category", "ecommerce"),
            role=body.get("role", "merchant"),
            password=body.get("password"),
            valid_from=body.get("valid_from"),
            expires_at=body.get("expires_at"),
            daily_quota=int(body.get("daily_quota", 5)),
            weekly_quota=int(body.get("weekly_quota", 25)),
            auth_token=body.get("auth_token"),
            is_active=1 if body.get("is_active", True) else 0,
            status=body.get("status", "active"),
        )
        return JSONResponse({
            "status": "ok",
            "message": "تم إنشاء الحساب بنجاح",
            "account": new_account,
            "user": new_account,
        }, status_code=201)
    except Exception as exc:
        return JSONResponse({"status": "error", "error": str(exc)}, status_code=400)


async def admin_update_account_endpoint(request: Request) -> JSONResponse:
    """
    PATCH /api/admin/accounts/{user_id} & PATCH /api/admin/users/{user_id}
    Admin updates user password, status, valid_from, expires_at, daily/weekly quotas.
    """
    user_id_raw = request.path_params.get("user_id")
    try:
        user_id = int(user_id_raw)
    except (ValueError, TypeError):
        return JSONResponse({"status": "error", "error": "Invalid user_id parameter"}, status_code=400)

    try:
        body = await request.json()
    except Exception as exc:
        return JSONResponse({"status": "error", "error": f"Invalid JSON body: {exc}"}, status_code=400)

    updated = update_user(user_id, **body)
    if not updated:
        return JSONResponse({"status": "error", "message": f"Account {user_id} not found or no updates provided"}, status_code=404)

    user = get_user_by_id(user_id)
    return JSONResponse({
        "status": "ok",
        "message": "تم تحديث بيانات الحساب بنجاح",
        "account": user,
        "user": user,
    })


async def admin_account_logs_endpoint(request: Request) -> JSONResponse:
    """
    GET /api/admin/accounts/{user_id}/logs
    Return activity audit log events recorded for a specific user account.
    """
    user_id_raw = request.path_params.get("user_id")
    try:
        user_id = int(user_id_raw)
    except (ValueError, TypeError):
        return JSONResponse({"status": "error", "error": "Invalid user_id parameter"}, status_code=400)

    limit_param = request.query_params.get("limit", "50")
    try:
        limit = max(1, min(200, int(limit_param)))
    except (ValueError, TypeError):
        limit = 50

    logs = get_user_activity_logs(user_id=user_id, limit=limit)
    return JSONResponse({
        "status": "ok",
        "user_id": user_id,
        "count": len(logs),
        "logs": logs,
    })


async def admin_stats_endpoint(request: Request) -> JSONResponse:
    """GET /api/admin/stats - Macro platform statistics overview."""
    return JSONResponse({
        "status": "ok",
        "stats": get_platform_stats(),
    })


# ---------------------------------------------------------------------------
# Application Initialization & Static Mounts
# ---------------------------------------------------------------------------

routes = [
    Route("/api/health", health_check, methods=["GET"]),
    Route("/api/presets", get_presets, methods=["GET"]),
    Route("/api/voices", get_voices_endpoint, methods=["GET"]),
    Route("/api/voices/{voice_id}/sample", voice_sample_endpoint, methods=["GET"]),
    Route("/api/music-tracks", get_music_tracks, methods=["GET"]),
    Route("/api/principles", get_principles_endpoint, methods=["GET"]),
    Route("/api/principles", save_principles_endpoint, methods=["POST"]),
    Route("/api/principles/reset", reset_principles_endpoint, methods=["POST"]),
    Route("/api/video/annotate", annotate_video_endpoint, methods=["POST"]),
    Route("/api/prompts/history", get_prompts_history_endpoint, methods=["GET"]),
    Route("/api/prompts", create_prompt_endpoint, methods=["POST"]),
    Route("/api/prompts/{prompt_id:int}", delete_prompt_endpoint, methods=["DELETE"]),
    Route("/api/prompts/{prompt_id}", delete_prompt_endpoint, methods=["DELETE"]),
    Route("/api/auth/login", login_endpoint, methods=["POST"]),
    Route("/api/auth/logout", logout_endpoint, methods=["POST"]),
    Route("/api/auth/session", auth_session_endpoint, methods=["GET"]),
    Route("/api/auth/me", auth_me_endpoint, methods=["GET"]),
    Route("/api/auth/demo-accounts", demo_accounts_endpoint, methods=["GET"]),
    Route("/api/admin/login", admin_login_endpoint, methods=["POST"]),
    Route("/api/admin/accounts", admin_list_accounts_endpoint, methods=["GET"]),
    Route("/api/admin/accounts", admin_create_account_endpoint, methods=["POST"]),
    Route("/api/admin/accounts/{user_id:int}", admin_update_account_endpoint, methods=["PATCH"]),
    Route("/api/admin/accounts/{user_id}", admin_update_account_endpoint, methods=["PATCH"]),
    Route("/api/admin/accounts/{user_id:int}/logs", admin_account_logs_endpoint, methods=["GET"]),
    Route("/api/admin/accounts/{user_id}/logs", admin_account_logs_endpoint, methods=["GET"]),
    Route("/api/admin/users", admin_list_accounts_endpoint, methods=["GET"]),
    Route("/api/admin/users", admin_create_account_endpoint, methods=["POST"]),
    Route("/api/admin/users/{user_id:int}", admin_update_account_endpoint, methods=["PATCH"]),
    Route("/api/admin/users/{user_id}", admin_update_account_endpoint, methods=["PATCH"]),
    Route("/api/admin/users/{user_id:int}/logs", admin_account_logs_endpoint, methods=["GET"]),
    Route("/api/admin/users/{user_id}/logs", admin_account_logs_endpoint, methods=["GET"]),
    Route("/api/admin/stats", admin_stats_endpoint, methods=["GET"]),
    Route("/api/upload-and-process", upload_and_process, methods=["POST"]),
    Route("/api/jobs/create", create_job_async, methods=["POST"]),
    Route("/api/status/{job_id}", get_job_status, methods=["GET"]),
    Route("/admin", admin_page, methods=["GET"]),
    Route("/style.css", style_css_endpoint, methods=["GET"]),
    Route("/app.js", app_js_endpoint, methods=["GET"]),
    Route("/favicon.ico", favicon_endpoint, methods=["GET"]),
    Route("/outputs/mobile_cuts/{filename}", get_mobile_cut_endpoint, methods=["GET"]),
    Route("/", index_page, methods=["GET"]),
    Mount("/outputs", StaticFiles(directory=str(OUTPUTS_DIR)), name="outputs"),
    Mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static"),
]

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
]

app = Starlette(
    debug=True,
    routes=routes,
    middleware=middleware,
)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
