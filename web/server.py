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
    get_presets_list,
    process_mobile_video,
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
        )
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
        voice = voice.strip()

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
    PROGRESS_STORE[job_id] = {
        "job_id": job_id,
        "status": "processing",
        "step": 1,
        "progress_percent": 10,
        "message": "تم استلام الفيديو من هاتفك بنجاح. جاري فحص وتحليل الملف...",
        "agent_logs": [f"تم رفع الفيديو '{original_filename}' وحفظه على الخادم."],
        "auto_mode": auto_mode,
        "emotional_tone": emotional_tone,
        "inferred_script": None,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    # Launch background thread
    t = threading.Thread(
        target=_execute_processing_job,
        args=(job_id, saved_video_path, script, preset, voice, duck_level, music_track, auto_mode, emotional_tone),
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
        voice = voice.strip()

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
        )
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


# ---------------------------------------------------------------------------
# Application Initialization & Static Mounts
# ---------------------------------------------------------------------------

routes = [
    Route("/api/health", health_check, methods=["GET"]),
    Route("/api/presets", get_presets, methods=["GET"]),
    Route("/api/music-tracks", get_music_tracks, methods=["GET"]),
    Route("/api/principles", get_principles_endpoint, methods=["GET"]),
    Route("/api/principles", save_principles_endpoint, methods=["POST"]),
    Route("/api/principles/reset", reset_principles_endpoint, methods=["POST"]),
    Route("/api/video/annotate", annotate_video_endpoint, methods=["POST"]),
    Route("/api/upload-and-process", upload_and_process, methods=["POST"]),
    Route("/api/jobs/create", create_job_async, methods=["POST"]),
    Route("/api/status/{job_id}", get_job_status, methods=["GET"]),
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
