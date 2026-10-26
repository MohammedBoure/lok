#!/usr/bin/env python3
"""
Mobile API Server (web/server.py)
Starlette & Uvicorn REST API for smartphone video recording & post-production.

Author: MohammedBoure
Role: Backend Architecture & Processing Bridge (agy11)
Branch: backend/agy11-mobile-api-server
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from web.pipeline_bridge import (
    ALGERIAN_REAL_ESTATE_PRESETS,
    get_presets_list,
    process_mobile_video,
)

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

# In-memory registry for jobs
JOBS_STORE: Dict[str, Dict[str, Any]] = {}


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
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


async def get_presets(request: Request) -> JSONResponse:
    """GET /api/presets - Returns catalog of Algerian real estate presets."""
    return JSONResponse(get_presets_list())


async def upload_and_process(request: Request) -> JSONResponse:
    """
    POST /api/upload-and-process
    Receives multipart form data:
      - 'video': Video file (required)
      - 'script': Optional narration script
      - 'preset' / 'preset_id': Optional preset identifier
      - 'voice': Optional voice identifier (default 'ar-XA-Standard-A')
      - 'duck_level': Optional ducking multiplier (default 0.25)
    """
    try:
        form = await request.form()
    except Exception as exc:
        logger.error("Failed to parse multipart form data: %s", exc)
        return JSONResponse({"error": f"Invalid multipart form data: {exc}"}, status_code=400)

    video_field = form.get("video")
    if not video_field or not hasattr(video_field, "filename") or not video_field.filename:
        return JSONResponse(
            {"error": "Missing required 'video' file field in multipart form."},
            status_code=400,
        )

    # Extract optional fields
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

    duck_level_raw = form.get("duck_level") or 0.25
    try:
        duck_level = float(duck_level_raw)
    except (ValueError, TypeError):
        duck_level = 0.25

    # Save uploaded video stream to inputs/mobile_uploads
    original_filename = Path(video_field.filename).name
    clean_suffix = Path(original_filename).suffix.lower() or ".mp4"
    unique_name = f"upload_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}{clean_suffix}"
    saved_video_path = UPLOADS_DIR / unique_name

    logger.info("Saving incoming mobile upload to %s...", saved_video_path)
    try:
        with open(saved_video_path, "wb") as f_out:
            shutil.copyfileobj(video_field.file, f_out)
    except Exception as exc:
        logger.error("Failed to save uploaded file: %s", exc)
        return JSONResponse({"error": f"Failed to save uploaded file: {exc}"}, status_code=500)

    # Run processing pipeline
    logger.info("Starting processing for uploaded video: %s (preset=%s, script=%s)", saved_video_path, preset, bool(script))
    try:
        summary = process_mobile_video(
            video_path=saved_video_path,
            script=script,
            preset_id=preset,
            voice=voice,
            duck_level=duck_level,
            output_dir=OUTPUTS_DIR / "mobile_cuts",
        )
        job_id = summary["job_id"]
        JOBS_STORE[job_id] = summary
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
    """GET /api/status/{job_id} - Retrieve status and execution summary for a job."""
    job_id = request.path_params.get("job_id", "")
    if not job_id:
        return JSONResponse({"error": "Missing job_id parameter."}, status_code=400)

    # 1. Check in-memory store
    if job_id in JOBS_STORE:
        return JSONResponse(JOBS_STORE[job_id])

    # 2. Check disk for summary_<job_id>.json
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
        "api_endpoints": {
            "health": "/api/health",
            "presets": "/api/presets",
            "upload_and_process": "/api/upload-and-process",
            "job_status": "/api/status/{job_id}",
        },
    })


# ---------------------------------------------------------------------------
# Application Factory
# ---------------------------------------------------------------------------

def create_app() -> Starlette:
    """Construct Starlette application instance with routes and CORS middleware."""
    routes = [
        Route("/", endpoint=index_page, methods=["GET"]),
        Route("/api/health", endpoint=health_check, methods=["GET"]),
        Route("/api/presets", endpoint=get_presets, methods=["GET"]),
        Route("/api/upload-and-process", endpoint=upload_and_process, methods=["POST"]),
        Route("/api/status/{job_id}", endpoint=get_job_status, methods=["GET"]),
        Mount("/outputs", app=StaticFiles(directory=str(OUTPUTS_DIR)), name="outputs"),
        Mount("/static", app=StaticFiles(directory=str(STATIC_DIR)), name="static"),
    ]

    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
            allow_credentials=True,
        )
    ]

    return Starlette(routes=routes, middleware=middleware)


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web.server:app", host="0.0.0.0", port=8000, reload=True)
