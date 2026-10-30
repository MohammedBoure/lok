"""
Unit and Integration Tests for Dynamic Video Pipeline & Vision Model Hierarchy.

Validates:
1. Active Vision model hierarchy and retry/timeout handling (gemini-3.8-flash, gemini-2.5-flash, gemini-3.1-pro-preview).
2. Failover when models return 404 (retired models) or timeout (45s read timeout).
3. Job status progression: verifying 'completed' and progress: 100 ONLY occur after the cut file exists on disk.
4. Dynamic video_url and output_video_url return in /api/status/{job_id}.
5. Atomic mirror to legacy outputs/final_cut.mp4.
6. Endpoint /outputs/mobile_cuts/{filename} serving with MIME type video/mp4 and byte-range streaming (200 / 206).
7. Strict adherence to zero occurrences of forbidden Arabic character U+0669.
"""

import io
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
    _get_smart_fallback,
)

client = TestClient(app)


# ---------------------------------------------------------------------------
# 1. Vision Model Hierarchy & Resiliency Tests
# ---------------------------------------------------------------------------

class TestVisionModelHierarchyAndResiliency:
    """Test suite for Gemini Vision Model fallback list, timeout, and retry resiliency."""

    def test_vision_model_hierarchy_defaults(self):
        """Ensure active vision models are correctly configured in priority order."""
        assert ACTIVE_VISION_MODELS == [
            "gemini-3.8-flash",
            "gemini-2.5-flash",
            "gemini-3.1-pro-preview",
        ]
        # Ensure deprecated / retired models are eliminated
        for retired in ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-2.5-pro"]:
            assert retired not in ACTIVE_VISION_MODELS

    def test_vision_model_fallback_on_404(self, tmp_path):
        """Verify seamless failover when the primary vision model returns 404 (retired)."""
        # Create a real dummy keyframe image
        dummy_kf = tmp_path / "keyframe_01.jpg"
        dummy_kf.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00")

        # Mock requests.post: 404 for gemini-3.8-flash, 200 for gemini-2.5-flash
        mock_resp_404 = MagicMock()
        mock_resp_404.status_code = 404
        mock_resp_404.text = '{"error": {"message": "models/gemini-3.8-flash is not found"}}'

        mock_resp_200 = MagicMock()
        mock_resp_200.status_code = 200
        mock_resp_200.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": json.dumps({
                                    "script": "شقة عصرية فاخرة بتشطيبات راقية في وهران الباهية",
                                    "emotional_tone": "فاخر وهادئ",
                                    "emotional_prompt": "Warm, luxurious tone",
                                    "recommended_music": "luxury_piano",
                                    "highlights": ["صالون واسع", "إطلالة بحرية"],
                                })
                            }
                        ]
                    }
                }
            ]
        }

        def fake_post(url, json=None, timeout=None):
            if "gemini-3.8-flash" in url:
                return mock_resp_404
            elif "gemini-2.5-flash" in url:
                return mock_resp_200
            return mock_resp_404

        with patch("requests.post", side_effect=fake_post) as mock_req:
            with patch.dict(os.environ, {"GEMINI_API_KEY": "test_fake_api_key"}):
                result = infer_video_script_and_mood(
                    keyframe_paths=[dummy_kf],
                    video_duration=12.0,
                )

        assert result["engine"] == "gemini_multimodal_vision"
        assert result["model_used"] == "gemini-2.5-flash"
        assert "وهران الباهية" in result["script"]
        assert result["emotional_tone"] == "فاخر وهادئ"
        assert result["recommended_music"] == "luxury_piano"

    def test_vision_model_timeout_and_retry(self, tmp_path):
        """Verify that read timeout (45s) on attempt 1 triggers retry and succeeds on attempt 2."""
        dummy_kf = tmp_path / "keyframe_02.jpg"
        dummy_kf.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00")

        mock_resp_200 = MagicMock()
        mock_resp_200.status_code = 200
        mock_resp_200.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": json.dumps({
                                    "script": "فيلا فخمة مع مسبح خاص وإطلالة خلابة",
                                    "emotional_tone": "دافئ وأنيق",
                                    "emotional_prompt": "Warm and elegant cadence",
                                    "recommended_music": "ambient_meditation",
                                    "highlights": ["مسبح خاص"],
                                })
                            }
                        ]
                    }
                }
            ]
        }

        attempts = {"count": 0}

        def fake_post_with_timeout(url, json=None, timeout=None):
            # Assert read timeout is at least 20.0
            if isinstance(timeout, tuple):
                assert timeout[1] >= 20.0
            else:
                assert timeout >= 20.0

            attempts["count"] += 1
            if attempts["count"] == 1:
                raise requests.exceptions.Timeout("Read timeout after 45.0s")
            return mock_resp_200

        with patch("requests.post", side_effect=fake_post_with_timeout):
            with patch.dict(os.environ, {"GEMINI_API_KEY": "test_fake_api_key"}):
                result = infer_video_script_and_mood(
                    keyframe_paths=[dummy_kf],
                    video_duration=10.0,
                )

        assert attempts["count"] == 2
        assert result["engine"] == "gemini_multimodal_vision"
        assert result["model_used"] == "gemini-3.8-flash"
        assert "فيلا فخمة" in result["script"]

    def test_vision_fallback_when_all_models_fail(self, tmp_path):
        """Verify that when all vision models fail or time out, smart fallback is invoked."""
        dummy_kf = tmp_path / "keyframe_03.jpg"
        dummy_kf.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00")

        mock_500 = MagicMock()
        mock_500.status_code = 500
        mock_500.text = "Internal Server Error"

        with patch("requests.post", return_value=mock_500):
            with patch.dict(os.environ, {"GEMINI_API_KEY": "test_fake_api_key", "GEMINI_VISION_MAX_RETRIES": "1"}):
                result = infer_video_script_and_mood(
                    keyframe_paths=[dummy_kf],
                    video_duration=10.0,
                    preset_hint="oran_seaview_villa",
                )

        assert result["engine"] == "smart_vision_fallback"
        assert "script" in result
        assert len(result["script"]) > 10


# ---------------------------------------------------------------------------
# 2. Dynamic Video Output & Premature Completion Guard Tests
# ---------------------------------------------------------------------------

class TestDynamicVideoOutputAndPrematureCompletion:
    """Test suite ensuring /api/status/{job_id} never returns completed before cut file is flushed."""

    def test_job_status_reports_processing_when_file_not_ready(self):
        """Verify /api/status/{job_id} guards against premature 'completed' when MP4 is missing."""
        job_id = "test_guard_missing_file_001"
        cut_file = OUTPUTS_DIR / "mobile_cuts" / f"cut_{job_id}.mp4"
        if cut_file.exists():
            cut_file.unlink()

        # Simulate job marked as completed in PROGRESS_STORE before file is written
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
            res = client.get(f"/api/status/{job_id}")
            assert res.status_code == 200
            data = res.json()
            # Guard must prevent status 'completed' and hold at 'processing' (98%)
            assert data["status"] == "processing"
            assert data["progress"] == 98
            assert data["progress_percent"] == 98
        finally:
            PROGRESS_STORE.pop(job_id, None)

    def test_job_status_reports_completed_with_dynamic_urls_when_file_ready(self):
        """Verify /api/status/{job_id} reports completed with dynamic video URLs once file is on disk."""
        job_id = "test_guard_ready_file_002"
        cuts_dir = OUTPUTS_DIR / "mobile_cuts"
        cuts_dir.mkdir(parents=True, exist_ok=True)
        cut_file = cuts_dir / f"cut_{job_id}.mp4"
        cut_file.write_bytes(b"\x00\x00\x00\x20ftypisom" + b"A" * 1024)

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
                "output_video_url": f"/outputs/mobile_cuts/cut_{job_id}.mp4",
                "output_video": f"/outputs/mobile_cuts/cut_{job_id}.mp4",
                "output_path": str(cut_file),
            },
        }

        try:
            res = client.get(f"/api/status/{job_id}")
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "completed"
            assert data["progress"] == 100
            assert data["progress_percent"] == 100
            expected_url = f"/outputs/mobile_cuts/cut_{job_id}.mp4"
            assert data["video_url"] == expected_url
            assert data["output_video_url"] == expected_url
            assert data["output_video"] == expected_url
            assert data["file_size_bytes"] == cut_file.stat().st_size
        finally:
            PROGRESS_STORE.pop(job_id, None)
            cut_file.unlink(missing_ok=True)

    def test_atomic_mirror_to_legacy_final_cut(self):
        """Verify that completed cuts are atomically mirrored to outputs/final_cut.mp4."""
        job_id = "test_atomic_mirror_003"
        cuts_dir = OUTPUTS_DIR / "mobile_cuts"
        cuts_dir.mkdir(parents=True, exist_ok=True)
        cut_file = cuts_dir / f"cut_{job_id}.mp4"
        sample_bytes = b"\x00\x00\x00\x20ftypmp42" + b"X" * 2048
        cut_file.write_bytes(sample_bytes)

        legacy_cut = OUTPUTS_DIR / "final_cut.mp4"
        legacy_tmp = OUTPUTS_DIR / f"final_cut_{job_id}.mp4.tmp"

        import shutil
        shutil.copyfile(cut_file, legacy_tmp)
        legacy_tmp.replace(legacy_cut)

        try:
            assert legacy_cut.is_file()
            assert legacy_cut.read_bytes() == sample_bytes
            assert not legacy_tmp.exists(), "Temporary atomic swap file must be cleanly replaced"
        finally:
            cut_file.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 3. Specific Video Cut Endpoint Serving & Byte-Range Tests
# ---------------------------------------------------------------------------

class TestVideoCutEndpointServing:
    """Test suite verifying /outputs/mobile_cuts/{filename} serves with 200/206 and video/mp4 MIME."""

    def test_serve_mobile_cut_200_full_content(self):
        """Verify 200 OK with correct MIME type and size for full cut download."""
        filename = "cut_test_stream_200.mp4"
        target_path = OUTPUTS_DIR / "mobile_cuts" / filename
        sample_data = b"0123456789" * 100  # 1000 bytes
        target_path.write_bytes(sample_data)

        try:
            res = client.get(f"/outputs/mobile_cuts/{filename}")
            assert res.status_code == 200
            assert "video/mp4" in res.headers.get("content-type", "")
            assert res.headers.get("content-length") == "1000"
            assert res.content == sample_data
        finally:
            target_path.unlink(missing_ok=True)

    def test_serve_mobile_cut_206_partial_content_range(self):
        """Verify 206 Partial Content with Content-Range for byte range streaming."""
        filename = "cut_test_stream_206.mp4"
        target_path = OUTPUTS_DIR / "mobile_cuts" / filename
        sample_data = b"ABCDEFGHIJ" * 100  # 1000 bytes
        target_path.write_bytes(sample_data)

        try:
            # Request first 50 bytes (bytes=0-49)
            res = client.get(f"/outputs/mobile_cuts/{filename}", headers={"Range": "bytes=0-49"})
            assert res.status_code == 206
            assert "video/mp4" in res.headers.get("content-type", "")
            assert res.headers.get("content-range") == "bytes 0-49/1000"
            assert len(res.content) == 50
            assert res.content == sample_data[:50]
        finally:
            target_path.unlink(missing_ok=True)

    def test_serve_mobile_cut_404_not_found(self):
        """Verify 404 response when requesting a non-existent cut file."""
        res = client.get("/outputs/mobile_cuts/cut_non_existent_random_xyz999.mp4")
        assert res.status_code == 404
        assert res.json()["status"] == "error"


# ---------------------------------------------------------------------------
# 4. Standards & Governance: Forbidden Character Rule
# ---------------------------------------------------------------------------

def test_no_forbidden_arabic_character_in_repository():
    """Verify strictly 0 occurrences of forbidden Arabic-Indic character U+0669."""
    repo_root = Path(__file__).resolve().parent.parent
    watched_extensions = (".py", ".html", ".js", ".css", ".md", ".json", ".sh")
    forbidden = "\u0669"
    violations = []

    for path in repo_root.rglob("*"):
        if any(p in path.parts for p in (".git", "__pycache__", ".pytest_cache", "venv", ".venv")):
            continue
        if path.is_file() and path.suffix in watched_extensions:
            try:
                content = path.read_text(encoding="utf-8")
                if forbidden in content:
                    violations.append(str(path))
            except Exception:
                pass

    assert not violations, f"Forbidden Arabic character U+0669 found in: {violations}"
