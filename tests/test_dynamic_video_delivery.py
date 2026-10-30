#!/usr/bin/env python3
"""
Integration and Gatekeeper Test Suite for Dynamic Video Delivery & Vision Model Resilience.
File: tests/test_dynamic_video_delivery.py

Author: MouhammedBoure <mohamadbormoz2@gmail.com>
Role: Quality Gatekeeper (agy100)
Branch: test/agy100-dynamic-video-delivery-gatekeeper
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests
from starlette.testclient import TestClient

from web.server import app, OUTPUTS_DIR, PROGRESS_STORE, JOBS_STORE
from web.vision_analyzer import (
    ACTIVE_VISION_MODELS,
    infer_video_script_and_mood,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = REPO_ROOT / "web" / "static"
client = TestClient(app)


# ==============================================================================
# 1. Vision Model Hierarchy & Resilience Gatekeeper Tests
# ==============================================================================

class TestVisionModelHierarchyGatekeeper:
    """Verifies that Gemini Vision models use active models and graceful fallback on 404/timeout."""

    def test_vision_model_hierarchy_order_and_exclusions(self):
        """Verify ACTIVE_VISION_MODELS priority list and exclusion of retired models."""
        expected_models = [
            "gemini-3.8-flash",
            "gemini-2.5-flash",
            "gemini-3.1-pro-preview",
        ]
        assert ACTIVE_VISION_MODELS == expected_models

        # Ensure deprecated 404 models are completely removed
        deprecated = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-2.5-pro"]
        for model in deprecated:
            assert model not in ACTIVE_VISION_MODELS

    def test_vision_model_fallback_on_404_resilience(self, tmp_path):
        """Verify that when primary model returns 404, fallback model (gemini-2.5-flash) succeeds."""
        dummy_kf = tmp_path / "keyframe_gatekeeper.jpg"
        dummy_kf.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00")

        mock_404 = MagicMock()
        mock_404.status_code = 404
        mock_404.text = '{"error": {"message": "models/gemini-3.8-flash is not found"}}'

        mock_200 = MagicMock()
        mock_200.status_code = 200
        mock_200.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": json.dumps({
                                    "script": "شقة راقية عصرية في العاصمة بإطلالة رائعة",
                                    "emotional_tone": "فاخر وهادئ",
                                    "emotional_prompt": "Smooth luxury voiceover",
                                    "recommended_music": "luxury_piano",
                                    "highlights": ["شرفة واسعة", "مطبخ مجهز"],
                                })
                            }
                        ]
                    }
                }
            ]
        }

        def mock_post_route(url, json=None, timeout=None):
            if "gemini-3.8-flash" in url:
                return mock_404
            elif "gemini-2.5-flash" in url:
                return mock_200
            return mock_404

        with patch("requests.post", side_effect=mock_post_route):
            with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_test_key"}):
                result = infer_video_script_and_mood(
                    keyframe_paths=[dummy_kf],
                    video_duration=14.0,
                )

        assert result["engine"] == "gemini_multimodal_vision"
        assert result["model_used"] == "gemini-2.5-flash"
        assert "شقة راقية" in result["script"]
        assert result["recommended_music"] == "luxury_piano"


# ==============================================================================
# 2. Dynamic Video Status & Premature Completion Guard Tests
# ==============================================================================

class TestDynamicJobStatusAndPrematureGuard:
    """Verifies /api/status/{job_id} returns dynamic cut URLs and holds completion until file exists."""

    def test_status_endpoint_guards_against_premature_completion(self):
        """Status endpoint must return processing (98%) if MP4 cut file is missing or zero bytes."""
        job_id = "job_premature_guard_test_01"
        cut_file = OUTPUTS_DIR / "mobile_cuts" / f"cut_{job_id}.mp4"
        if cut_file.exists():
            cut_file.unlink()

        PROGRESS_STORE[job_id] = {
            "job_id": job_id,
            "status": "completed",
            "step": 5,
            "progress_percent": 100,
            "message": "اكتمل الإنتاج بنجاح!",
            "result": {
                "job_id": job_id,
                "status": "completed",
                "output_path": str(cut_file),
            },
        }

        try:
            resp = client.get(f"/api/status/{job_id}")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "processing"
            assert data["progress"] == 98
            assert data["progress_percent"] == 98
        finally:
            PROGRESS_STORE.pop(job_id, None)

    def test_status_endpoint_returns_dynamic_cut_url_when_file_ready(self):
        """Status endpoint returns status='completed' and dynamic video URLs once MP4 is on disk."""
        job_id = "job_ready_cut_test_02"
        cuts_dir = OUTPUTS_DIR / "mobile_cuts"
        cuts_dir.mkdir(parents=True, exist_ok=True)
        cut_file = cuts_dir / f"cut_{job_id}.mp4"
        cut_file.write_bytes(b"\x00\x00\x00\x20ftypisom" + b"X" * 1024)

        PROGRESS_STORE[job_id] = {
            "job_id": job_id,
            "status": "completed",
            "step": 5,
            "progress_percent": 100,
            "message": "اكتمل الإنتاج بنجاح!",
            "result": {
                "job_id": job_id,
                "status": "completed",
                "video_url": f"/outputs/mobile_cuts/cut_{job_id}.mp4",
                "output_path": str(cut_file),
            },
        }

        try:
            resp = client.get(f"/api/status/{job_id}")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "completed"
            assert data["progress"] == 100
            expected_video_url = f"/outputs/mobile_cuts/cut_{job_id}.mp4"
            assert data["video_url"] == expected_video_url
            assert data["output_video_url"] == expected_video_url
            assert data["file_size_bytes"] == cut_file.stat().st_size
        finally:
            PROGRESS_STORE.pop(job_id, None)
            cut_file.unlink(missing_ok=True)

    def test_status_endpoint_returns_json_summary_when_loaded_from_disk(self):
        """Status endpoint reads disk summary and returns completed with dynamic video URL."""
        job_id = "job_disk_summary_test_03"
        cuts_dir = OUTPUTS_DIR / "mobile_cuts"
        cuts_dir.mkdir(parents=True, exist_ok=True)
        cut_file = cuts_dir / f"cut_{job_id}.mp4"
        cut_file.write_bytes(b"\x00\x00\x00\x20ftypmp42" + b"Y" * 2048)

        summary_file = cuts_dir / f"summary_{job_id}.json"
        summary_payload = {
            "job_id": job_id,
            "status": "completed",
            "video_url": f"/outputs/mobile_cuts/cut_{job_id}.mp4",
            "script": "إعلان عقاري مميز",
            "voice": "ar-XA-Standard-A",
        }
        summary_file.write_text(json.dumps(summary_payload), encoding="utf-8")

        try:
            resp = client.get(f"/api/status/{job_id}")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "completed"
            assert data["video_url"] == f"/outputs/mobile_cuts/cut_{job_id}.mp4"
            assert data["output_video_url"] == f"/outputs/mobile_cuts/cut_{job_id}.mp4"
        finally:
            cut_file.unlink(missing_ok=True)
            summary_file.unlink(missing_ok=True)
            JOBS_STORE.pop(job_id, None)


# ==============================================================================
# 3. Frontend Dynamic Video & Stepper Contracts Tests
# ==============================================================================

class TestFrontendDynamicVideoAndStepperContracts:
    """Verifies app.js dynamically updates video src with cache busting and drives stepper."""

    def test_frontend_app_js_dynamic_video_src_and_cache_busting(self):
        """app.js must dynamically resolve video_url, apply ?v= cache-busting, and load element."""
        js_content = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
        html_content = (STATIC_DIR / "index.html").read_text(encoding="utf-8")

        # Dynamic URL resolution function
        assert "buildDynamicVideoUrl" in js_content
        assert "data.video_url" in js_content
        assert "data.output_video_url" in js_content or "output_video" in js_content

        # Cache-busting parameter
        assert "v=" in js_content or "Date.now()" in js_content

        # Player assignment and loading
        assert "dom.resultVideo.src = dynamicVideoSrc" in js_content
        assert "dom.resultVideo.load()" in js_content

        # Download & share button link updates
        assert "dom.btnDownloadVideo.href = dynamicVideoSrc" in js_content
        assert 'id="btnDownloadVideo"' in html_content
        assert 'id="btnShareVideo"' in html_content

    def test_frontend_stepper_elements_and_logic(self):
        """HTML and app.js must have stepper stages: frames, analyze, voice, render, annotations."""
        html_content = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
        js_content = (STATIC_DIR / "app.js").read_text(encoding="utf-8")

        # Stepper stage chips in DOM
        assert 'id="stepFrames"' in html_content
        assert 'id="stepAnalyze"' in html_content
        assert 'id="stepVoice"' in html_content
        assert 'id="stepRender"' in html_content
        assert 'id="stepAnnotations"' in html_content

        # Stepper driver logic in app.js
        assert "updateStepperStatus" in js_content
        assert "resolveStepFromTelemetry" in js_content
        assert 'status === "completed"' in js_content


# ==============================================================================
# 4. Mobile Cut Video Serving, MIME Type & HTTP Range Tests
# ==============================================================================

class TestMobileCutServingMimeAndRange:
    """Verifies that /outputs/mobile_cuts/{filename} serves MP4 with 200/206 Range streaming."""

    def test_mobile_cut_served_with_video_mp4_mime(self):
        """GET /outputs/mobile_cuts/{filename} serves 200 with video/mp4 MIME type."""
        filename = "cut_gatekeeper_stream_200.mp4"
        file_path = OUTPUTS_DIR / "mobile_cuts" / filename
        data = b"\x00\x00\x00\x20ftypisom" + b"Z" * 1200
        file_path.write_bytes(data)

        try:
            resp = client.get(f"/outputs/mobile_cuts/{filename}")
            assert resp.status_code == 200
            assert "video/mp4" in resp.headers.get("content-type", "")
            assert resp.headers.get("content-length") == str(len(data))
            assert resp.content == data
        finally:
            file_path.unlink(missing_ok=True)

    def test_mobile_cut_supports_http_range_requests(self):
        """GET /outputs/mobile_cuts/{filename} with Range header returns 206 Partial Content."""
        filename = "cut_gatekeeper_range_206.mp4"
        file_path = OUTPUTS_DIR / "mobile_cuts" / filename
        data = b"0123456789" * 100  # 1000 bytes
        file_path.write_bytes(data)

        try:
            resp = client.get(f"/outputs/mobile_cuts/{filename}", headers={"Range": "bytes=100-199"})
            assert resp.status_code == 206
            assert "video/mp4" in resp.headers.get("content-type", "")
            assert resp.headers.get("content-range") == "bytes 100-199/1000"
            assert len(resp.content) == 100
            assert resp.content == data[100:200]
        finally:
            file_path.unlink(missing_ok=True)

    def test_mobile_cut_non_existent_returns_404(self):
        """GET /outputs/mobile_cuts/{filename} for non-existent file returns 404."""
        resp = client.get("/outputs/mobile_cuts/cut_non_existent_xyz_404.mp4")
        assert resp.status_code == 404


# ==============================================================================
# 5. Strict Character Mapping Compliance
# ==============================================================================

class TestStrictCharacterMappingGatekeeper:
    """Verifies that the forbidden character U+0669 is strictly zero across all files."""

    FORBIDDEN_CHAR = chr(0x0669)

    def test_zero_forbidden_character_across_repo(self):
        """Assert zero occurrences of U+0669 in all repository deliverables."""
        allowed_extensions = (".py", ".html", ".css", ".js", ".json", ".md")
        skip_dirs = {".git", "__pycache__", ".pytest_cache", ".gemini", "node_modules"}

        violations = []
        for root, dirs, files in os.walk(REPO_ROOT):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for f in files:
                if any(f.endswith(ext) for ext in allowed_extensions):
                    path = Path(root) / f
                    try:
                        text = path.read_text(encoding="utf-8")
                        clean_text = text.replace(r"\u0669", "").replace(r"\\u0669", "")
                        if self.FORBIDDEN_CHAR in clean_text:
                            violations.append(str(path.relative_to(REPO_ROOT)))
                    except Exception:
                        pass

        assert not violations, f"Forbidden character U+0669 found in: {violations}"
