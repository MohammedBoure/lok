#!/usr/bin/env python3
"""
Mobile API Server (web/server.py)
Starlette & Uvicorn REST API for smartphone video recording & post-production.

Author: MohammedBoure
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
    get_music_tracks_list,
    get_or_create_voice_sample,
    get_presets_list,
    get_voice_profiles_list,
    process_mobile_video,
    resolve_voice_profile,
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
    check_quota,
    create_session,
    create_user,
    delete_session,
    get_demo_accounts,
    get_platform_stats,
    get_session,
    get_user_by_id,
    get_user_by_username,
    get_user_history,
    hash_password,
    list_users,
    record_generation,
    update_user,
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


def _get_authenticated_user_and_session(
    request: Request,
    form: Optional[Any] = None,
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """
    Authenticate user and session from Form data (session_token / auth_token / token),
    Authorization header (Bearer <token_or_session>), custom headers (X-Session-Token, X-Auth-Token),
    cookies (session_token), or query parameters.
    Returns:
        (user_dict, session_dict) if authenticated, else (None, None).
    """
    token = None
    if form:
        token = form.get("session_token") or form.get("auth_token") or form.get("token")

    if not token:
        auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
        if auth_header and "bearer " in auth_header.lower():
            token = auth_header.split(None, 1)[1].strip() if len(auth_header.split(None, 1)) > 1 else None
        elif auth_header:
            token = auth_header.strip()

    if not token:
        token = (
            request.headers.get("X-Session-Token")
            or request.headers.get("x-session-token")
            or request.headers.get("X-Auth-Token")
            or request.headers.get("x-auth-token")
        )

    if not token:
        token = request.cookies.get("session_token")

    if not token:
        token = (
            request.query_params.get("session_token")
            or request.query_params.get("token")
            or request.query_params.get("auth_token")
        )

    if not token or not str(token).strip():
        return (None, None)

    clean_token = str(token).strip()

    # 1. Check if token is an active session
    sess = get_session(clean_token)
    if sess and sess.get("user"):
        return (sess["user"], sess)

    # 2. Check if token is a permanent merchant/admin auth token
    user = authenticate_token(clean_token)
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
):
    """Worker function executed synchronously or in a background thread."""
    def _on_progress(event: Dict[str, Any]):
        curr = PROGRESS_STORE.get(job_id, {})
        agent_logs = curr.get("agent_logs", [])
        if event.get("log") and event["log"] not in agent_logs:
            agent_logs.append(event["log"])
        PROGRESS_STORE[job_id] = {
            "job_id": job_id,
            "status": "processing",
            "step": event.get("step", 1),
            "progress_percent": event.get("progress_percent", 15),
            "message": event.get("message", "جاري المعالجة..."),
            "agent_logs": agent_logs,
            "auto_mode": auto_mode,
            "emotional_tone": event.get("emotional_tone") or curr.get("emotional_tone") or emotional_tone,
            "inferred_script": event.get("inferred_script") or curr.get("inferred_script"),
            "voice": voice,
            "visual_lead_in": visual_lead_in,
            "user_id": user_id,
            "fixed_text": fixed_text,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

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

        JOBS_STORE[job_id] = summary
        PROGRESS_STORE[job_id] = {
            "job_id": job_id,
            "status": "completed",
            "step": 5,
            "progress_percent": 100,
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
            "result": summary,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.exception("Error processing job %s: %s", job_id, exc)
        PROGRESS_STORE[job_id] = {
            "job_id": job_id,
            "status": "failed",
            "step": 0,
            "progress_percent": 0,
            "message": f"حدث خطأ أثناء المعالجة: {exc}",
            "error": str(exc),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }


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
        PROGRESS_STORE[job_id] = {
            "job_id": job_id,
            "status": "processing",
            "step": event.get("step", 1),
            "progress_percent": event.get("progress_percent", 15),
            "message": event.get("message", "جاري المعالجة..."),
            "agent_logs": logs,
            "auto_mode": auto_mode,
            "emotional_tone": event.get("emotional_tone") or curr.get("emotional_tone") or emotional_tone,
            "inferred_script": event.get("inferred_script") or curr.get("inferred_script"),
            "user_id": user["id"],
            "fixed_text": fixed_text,
        }

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

        JOBS_STORE[summary["job_id"]] = summary
        PROGRESS_STORE[summary["job_id"]] = {
            "job_id": summary["job_id"],
            "status": "completed",
            "step": 5,
            "progress_percent": 100,
            "message": "اكتمل الإنتاج بنجاح!",
            "auto_mode": summary.get("auto_mode", auto_mode),
            "emotional_tone": summary.get("emotional_tone"),
            "inferred_script": summary.get("inferred_script"),
            "user_id": user["id"],
            "result": summary,
        }
        return JSONResponse(summary, status_code=200)

    except Exception as exc:
        logger.exception("Error during video processing: %s", exc)
        return JSONResponse(
            {
                "status": "failed",
                "error": str(exc),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            status_code=500,
        )


async def get_job_status(request: Request) -> JSONResponse:
    """GET /api/status/{job_id} - Retrieve live telemetry, status and execution summary for a job."""
    job_id = request.path_params.get("job_id", "")
    if not job_id:
        return JSONResponse({"error": "Missing job_id parameter."}, status_code=400)

    # 1. Check in-flight progress telemetry
    if job_id in PROGRESS_STORE:
        p_data = PROGRESS_STORE[job_id]
        if p_data.get("status") == "completed" and "result" in p_data:
            res_dict = dict(p_data["result"])
            res_dict.setdefault("emotional_tone", p_data.get("emotional_tone"))
            res_dict.setdefault("inferred_script", p_data.get("inferred_script"))
            res_dict.setdefault("auto_mode", p_data.get("auto_mode", False))
            return JSONResponse(res_dict)
        return JSONResponse(p_data)

    # 2. Check in-memory completed store
    if job_id in JOBS_STORE:
        return JSONResponse(JOBS_STORE[job_id])

    # 3. Check disk for summary_<job_id>.json
    summary_file = OUTPUTS_DIR / "mobile_cuts" / f"summary_{job_id}.json"
    if summary_file.is_file():
        try:
            with open(summary_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            JOBS_STORE[job_id] = data
            return JSONResponse(data)
        except Exception as exc:
            logger.warning("Failed to read summary file %s: %s", summary_file, exc)

    return JSONResponse(
        {"error": f"Job '{job_id}' not found.", "status": "not_found"},
        status_code=404,
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
    """
    username = None
    password = None
    token = None
    try:
        body = await request.json()
        username = body.get("username")
        password = body.get("password")
        token = body.get("token") or body.get("auth_token") or body.get("session_token")
    except Exception:
        try:
            form = await request.form()
            username = form.get("username")
            password = form.get("password")
            token = form.get("token") or form.get("auth_token") or form.get("session_token")
        except Exception:
            pass

    user = None
    if token and not username and not password:
        user = authenticate_token(token)
    elif username:
        user = authenticate_credentials(username, password)
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

    if not user.get("is_active", True):
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
            "auth_token": user["auth_token"],
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
    token = request.query_params.get("token") or request.query_params.get("auth_token")

    if not auth_header and not token:
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


async def admin_list_users_endpoint(request: Request) -> JSONResponse:
    """GET /api/admin/users - Returns all merchant accounts with usage and quota statistics."""
    return JSONResponse({
        "status": "ok",
        "users": list_users(),
    })


async def admin_create_user_endpoint(request: Request) -> JSONResponse:
    """POST /api/admin/users - Admin creates new commercial merchant account."""
    try:
        body = await request.json()
    except Exception as exc:
        return JSONResponse({"status": "error", "error": f"Invalid JSON body: {exc}"}, status_code=400)

    username = body.get("username")
    business_name = body.get("business_name")
    if not username or not business_name:
        return JSONResponse({"status": "error", "error": "Missing required 'username' or 'business_name'"}, status_code=400)

    try:
        new_user = create_user(
            username=username,
            business_name=business_name,
            business_category=body.get("business_category", "ecommerce"),
            role=body.get("role", "merchant"),
            expires_at=body.get("expires_at"),
            daily_quota=int(body.get("daily_quota", 5)),
            weekly_quota=int(body.get("weekly_quota", 25)),
            auth_token=body.get("auth_token"),
            is_active=1 if body.get("is_active", True) else 0,
        )
        return JSONResponse({
            "status": "ok",
            "message": "تم إنشاء حساب التاجر بنجاح",
            "user": new_user,
        }, status_code=201)
    except Exception as exc:
        return JSONResponse({"status": "error", "error": str(exc)}, status_code=400)


async def admin_update_user_endpoint(request: Request) -> JSONResponse:
    """PATCH /api/admin/users/{user_id} - Admin updates user account status, quotas, or expiry."""
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
        return JSONResponse({"status": "error", "message": f"User {user_id} not found or no updates provided"}, status_code=404)

    user = get_user_by_id(user_id)
    return JSONResponse({
        "status": "ok",
        "message": "تم تحديث بيانات الحساب بنجاح",
        "user": user,
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
    Route("/api/admin/users", admin_list_users_endpoint, methods=["GET"]),
    Route("/api/admin/users", admin_create_user_endpoint, methods=["POST"]),
    Route("/api/admin/users/{user_id:int}", admin_update_user_endpoint, methods=["PATCH"]),
    Route("/api/admin/users/{user_id}", admin_update_user_endpoint, methods=["PATCH"]),
    Route("/api/admin/stats", admin_stats_endpoint, methods=["GET"]),
    Route("/api/upload-and-process", upload_and_process, methods=["POST"]),
    Route("/api/jobs/create", create_job_async, methods=["POST"]),
    Route("/api/status/{job_id}", get_job_status, methods=["GET"]),
    Route("/", index_page, methods=["GET"]),
    Route("/admin", admin_page, methods=["GET"]),
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
