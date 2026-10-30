"""
Comprehensive Tests for Pipeline Latency Optimization, Fast Telemetry, and Real-Time Error Propagation.
Author: MouhammedBoure <mohamadbormoz2@gmail.com>
Agent: agy11 (Backend Logic & Systems Engineer)
Branch: backend/agy11-pipeline-latency-and-status-telemetry
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from starlette.requests import Request
from starlette.responses import JSONResponse

from web.server import (
    JOBS_STORE,
    PROGRESS_STORE,
    _execute_processing_job,
    _find_finalized_cut_file,
    execute_video_job,
    get_job_status,
)
from web.vision_analyzer import infer_video_script_and_mood

REPO_ROOT = Path(__file__).resolve().parent.parent


def _build_mock_request(job_id: str) -> Request:
    """Helper to construct a mock Starlette Request for get_job_status."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": f"/api/status/{job_id}",
        "headers": [],
        "path_params": {"job_id": job_id},
    }
    return Request(scope)


class TestStatusTelemetryAndStepTracking:
    """Verify live status telemetry reporting progress, current_step, and step progression."""

    def test_execute_video_job_alias_exists(self):
        """execute_video_job must exist and reference the core worker function."""
        assert callable(execute_video_job)
        assert execute_video_job == _execute_processing_job

    @pytest.mark.asyncio
    async def test_get_job_status_returns_current_step_and_progress(self):
        """In-flight processing jobs must report step, current_step, progress, and progress_percent."""
        job_id = "test_telemetry_inflight_01"
        PROGRESS_STORE[job_id] = {
            "job_id": job_id,
            "status": "processing",
            "step": 3,
            "current_step": 3,
            "progress": 60,
            "progress_percent": 60,
            "message": "تحليل المشاهد المعمارية عبر Gemini Multimodal Vision...",
            "agent_logs": ["تم فحص الفيديو بنجاح."],
        }

        req = _build_mock_request(job_id)
        resp = await get_job_status(req)
        assert resp.status_code == 200
        data = json.loads(resp.body.decode("utf-8"))

        assert data["job_id"] == job_id
        assert data["status"] == "processing"
        assert data["step"] == 3
        assert data["current_step"] == 3
        assert data["progress"] == 60
        assert data["progress_percent"] == 60
        assert "Gemini" in data["message"]

    @pytest.mark.asyncio
    async def test_get_job_status_completed_with_sandboxed_file(self, tmp_path):
        """Completed jobs must resolve cut files in per-job sandbox and report 100% completion."""
        job_id = "test_completed_sandboxed_02"
        sandbox_cut = REPO_ROOT / "outputs" / "jobs" / job_id / "sandbox" / f"cut_{job_id}.mp4"
        sandbox_cut.parent.mkdir(parents=True, exist_ok=True)
        sandbox_cut.write_bytes(b"\x00" * 4096)

        try:
            PROGRESS_STORE[job_id] = {
                "job_id": job_id,
                "status": "completed",
                "step": 5,
                "current_step": 5,
                "progress": 100,
                "progress_percent": 100,
                "message": "اكتمل إنتاج الفيديو بنجاح!",
                "result": {
                    "job_id": job_id,
                    "sandboxed_video_url": f"/outputs/jobs/{job_id}/sandbox/cut_{job_id}.mp4",
                    "output_path": str(sandbox_cut),
                },
            }

            req = _build_mock_request(job_id)
            resp = await get_job_status(req)
            assert resp.status_code == 200
            data = json.loads(resp.body.decode("utf-8"))

            assert data["status"] == "completed"
            assert data["step"] == 5
            assert data["current_step"] == 5
            assert data["progress"] == 100
            assert data["progress_percent"] == 100
            assert f"cut_{job_id}.mp4" in data["video_url"]
            assert data["file_size_bytes"] == 4096
        finally:
            if sandbox_cut.is_file():
                sandbox_cut.unlink()
            if sandbox_cut.parent.is_dir():
                try:
                    sandbox_cut.parent.rmdir()
                except OSError:
                    pass


class TestRealTimeErrorPropagation:
    """Verify immediate failure propagation and actionable error details to eliminate hung states."""

    @pytest.mark.asyncio
    async def test_immediate_error_capture_on_pipeline_exception(self, tmp_path):
        """When an exception occurs during background execution, job status becomes failed immediately."""
        job_id = "test_error_capture_03"
        dummy_video = tmp_path / "broken_video.mp4"
        dummy_video.write_bytes(b"corrupt_bytes")

        PROGRESS_STORE[job_id] = {
            "job_id": job_id,
            "status": "processing",
            "step": 1,
            "current_step": 1,
            "progress": 15,
            "progress_percent": 15,
            "message": "جاري التحليل...",
        }

        with patch("web.server.process_mobile_video", side_effect=RuntimeError("FFmpeg encoding pipeline crashed")):
            execute_video_job(
                job_id=job_id,
                saved_video_path=dummy_video,
                script="test script",
                preset=None,
                voice="ar-XA-Standard-A",
                duck_level=0.25,
                music_track=None,
            )

        # Check PROGRESS_STORE updated immediately to failed
        assert job_id in PROGRESS_STORE
        p_data = PROGRESS_STORE[job_id]
        assert p_data["status"] == "failed"
        assert p_data["step"] == 0
        assert p_data["current_step"] == 0
        assert p_data["progress"] == 0
        assert p_data["progress_percent"] == 0
        assert "FFmpeg encoding pipeline crashed" in p_data["error"]
        assert p_data["error_details"]["type"] == "RuntimeError"

        # Check JOBS_STORE updated to failed as well
        assert job_id in JOBS_STORE
        assert JOBS_STORE[job_id]["status"] == "failed"

        # Check /api/status/{job_id} returns the failed status immediately
        req = _build_mock_request(job_id)
        resp = await get_job_status(req)
        assert resp.status_code == 200
        res_data = json.loads(resp.body.decode("utf-8"))
        assert res_data["status"] == "failed"
        assert "FFmpeg encoding pipeline crashed" in res_data["error"]
        assert res_data["error_details"]["type"] == "RuntimeError"

    @pytest.mark.asyncio
    async def test_get_job_status_failed_in_progress_store(self):
        """Directly querying a failed job in PROGRESS_STORE yields failed status with error details."""
        job_id = "test_failed_query_04"
        PROGRESS_STORE[job_id] = {
            "job_id": job_id,
            "status": "failed",
            "step": 0,
            "current_step": 0,
            "progress": 0,
            "progress_percent": 0,
            "message": "حدث خطأ أثناء المعالجة: File corrupted",
            "error": "File corrupted",
            "error_details": {"type": "ValueError", "message": "File corrupted"},
        }

        req = _build_mock_request(job_id)
        resp = await get_job_status(req)
        assert resp.status_code == 200
        data = json.loads(resp.body.decode("utf-8"))
        assert data["status"] == "failed"
        assert data["error"] == "File corrupted"
        assert data["current_step"] == 0
        assert data["progress"] == 0


class TestPipelineLatencyOptimization:
    """Verify performance optimizations: lightweight status resolution and vision latency constraints."""

    def test_find_finalized_cut_file_candidates(self, tmp_path):
        """_find_finalized_cut_file checks candidate paths swiftly and returns correct URL."""
        job_id = "test_latency_cut_05"

        # Non-existent file yields (None, default_url)
        path, url = _find_finalized_cut_file(job_id, {})
        assert path is None
        assert f"cut_{job_id}.mp4" in url

        # Existing explicit path is discovered
        dummy_cut = tmp_path / f"cut_{job_id}.mp4"
        dummy_cut.write_bytes(b"\x00" * 1024)

        path, url = _find_finalized_cut_file(job_id, {"output_path": str(dummy_cut)})
        assert path == dummy_cut
        assert path.is_file()

    def test_vision_analyzer_latency_frame_limit_and_timeouts(self, tmp_path):
        """Vision analyzer restricts frames to max limit (default 10) and enforces fast timeouts."""
        frames = []
        for i in range(18):
            f = tmp_path / f"frame_{i:02d}.jpg"
            f.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 50)
            frames.append(f)

        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": json.dumps({
                                    "script": "شوفو معايا هاد الشقة الفاخرة والعصرية.",
                                    "emotional_tone": "فاخر وهادئ",
                                    "emotional_prompt": "Warm luxury narration",
                                    "recommended_music": "luxury_piano",
                                    "highlights": ["صالون راقي"],
                                })
                            }
                        ]
                    }
                }
            ]
        }

        with patch("requests.post", return_value=fake_resp) as mock_post, \
             patch.dict("os.environ", {"GEMINI_API_KEY": "mock_api_key"}):
            infer_video_script_and_mood(
                keyframe_paths=frames,
                video_duration=25.0,
                speech_description="شقة فاخرة للبيع",
            )

            assert mock_post.called
            call_kwargs = mock_post.call_args.kwargs
            json_payload = call_kwargs.get("json", {})
            parts = json_payload.get("contents", [{}])[0].get("parts", [])

            # Inline image parts should be limited to 10 (not all 18) for low latency
            image_parts = [p for p in parts if "inlineData" in p]
            assert len(image_parts) <= 10, f"Expected <= 10 image parts, got {len(image_parts)}"

            # Timeout must be optimized (<= 25.0s read timeout)
            timeout_arg = call_kwargs.get("timeout")
            assert isinstance(timeout_arg, tuple)
            connect_to, read_to = timeout_arg
            assert connect_to <= 10.0
            assert read_to <= 30.0
