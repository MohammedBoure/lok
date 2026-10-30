"""
Unit and Integration Tests for Job ID Consistency and 404 Prevention.
File: tests/test_job_id_consistency_and_delivery.py

Author: MouhammedBoure <mohamadbormoz2@gmail.com>
"""

from __future__ import annotations

import io
import json
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from starlette.testclient import TestClient

from web.server import (
    OUTPUTS_DIR,
    PROGRESS_STORE,
    JOBS_STORE,
    app,
    _find_finalized_cut_file,
    _execute_processing_job,
)
from web.pipeline_bridge import process_mobile_video

REPO_ROOT = Path(__file__).resolve().parent.parent
client = TestClient(app)


class TestJobIdConsistency:
    """Verifies that the job_id generated at request ingestion is consistently preserved across the pipeline."""

    def test_process_mobile_video_respects_explicit_job_id(self, tmp_path):
        """process_mobile_video must accept and preserve an explicit job_id rather than regenerating a new one."""
        custom_job_id = "20261030_test_custom_job_99a8b7"
        
        # Create minimal valid video file mock
        dummy_video = tmp_path / "input.mp4"
        dummy_video.write_bytes(b"\x00\x00\x00\x20ftypisom" + b"\x00" * 1024)

        # Mock downstream heavy components
        with patch("frame_extractor.get_video_metadata") as mock_meta, \
             patch("frame_extractor.extract_keyframes") as mock_extract, \
             patch("web.vision_analyzer.infer_video_script_and_mood") as mock_vision, \
             patch("web.pipeline_bridge.synthesize_narration") as mock_speech, \
             patch("subprocess.run") as mock_subproc:

            mock_meta.return_value = {
                "duration": 10.0,
                "width": 1080,
                "height": 1920,
                "aspect_ratio": "9:16",
                "fps": 30.0,
                "has_audio": True,
            }
            mock_extract.return_value = {"frames": [], "count": 0}
            mock_vision.return_value = {
                "script": "شقة فاخرة للبيع",
                "emotional_tone": "فاخر وهادئ",
                "recommended_music": "luxury_piano",
            }
            mock_speech.return_value = {
                "duration": 5.0,
                "synthesizer": "mock",
                "audio_path": tmp_path / "mock_narration.wav",
            }

            def fake_subproc(cmd, **kwargs):
                # If command produces cut file in sandbox, write dummy bytes
                for arg in cmd:
                    if str(arg).endswith(".mp4") and "sandbox" in str(arg):
                        p = Path(arg)
                        p.parent.mkdir(parents=True, exist_ok=True)
                        p.write_bytes(b"\x00\x00\x00\x20ftypisom" + b"X" * 1024)
                return MagicMock(returncode=0)

            mock_subproc.side_effect = fake_subproc

            summary = process_mobile_video(
                video_path=dummy_video,
                script="شقة فاخرة للبيع في موقع مميز",
                output_dir=tmp_path / "mobile_cuts",
                job_id=custom_job_id,
            )

            assert summary["job_id"] == custom_job_id
            assert custom_job_id in summary["video_url"]
            assert summary["video_url"] == f"/outputs/mobile_cuts/cut_{custom_job_id}.mp4"
            assert custom_job_id in summary["sandbox_dir"]

    def test_get_mobile_cut_endpoint_resolves_from_sandbox_if_missing_in_mobile_cuts(self, tmp_path):
        """If cut is in the sandbox directory, get_mobile_cut_endpoint discovers and serves it."""
        job_id = "test_sandbox_discovery_001"
        sandbox_dir = OUTPUTS_DIR / "jobs" / job_id / "sandbox"
        sandbox_dir.mkdir(parents=True, exist_ok=True)
        sandbox_cut = sandbox_dir / f"cut_{job_id}.mp4"
        sample_bytes = b"\x00\x00\x00\x20ftypisom" + b"Z" * 2048
        sandbox_cut.write_bytes(sample_bytes)

        mobile_cut = OUTPUTS_DIR / "mobile_cuts" / f"cut_{job_id}.mp4"
        if mobile_cut.exists():
            mobile_cut.unlink()

        try:
            resp = client.get(f"/outputs/mobile_cuts/cut_{job_id}.mp4")
            assert resp.status_code == 200
            assert resp.headers.get("content-type") == "video/mp4"
            assert len(resp.content) == len(sample_bytes)
            # Verify it was mirrored to mobile_cuts for future fast hits
            assert mobile_cut.is_file()
        finally:
            mobile_cut.unlink(missing_ok=True)
            shutil.rmtree(OUTPUTS_DIR / "jobs" / job_id, ignore_errors=True)

    def test_non_existent_cut_file_returns_404(self):
        """A truly non-existent cut must return 404 Not Found."""
        resp = client.get("/outputs/mobile_cuts/cut_totally_non_existent_xyz123.mp4")
        assert resp.status_code == 404
        assert resp.json()["status"] == "error"

    def test_status_endpoint_returns_matching_job_id_and_url(self):
        """Status endpoint ensures video_url strictly matches job_id and file existence."""
        job_id = "test_status_matching_job_007"
        cut_file = OUTPUTS_DIR / "mobile_cuts" / f"cut_{job_id}.mp4"
        cut_file.write_bytes(b"\x00\x00\x00\x20ftypisom" + b"A" * 1024)

        PROGRESS_STORE[job_id] = {
            "job_id": job_id,
            "status": "completed",
            "step": 5,
            "progress": 100,
            "progress_percent": 100,
            "video_url": f"/outputs/mobile_cuts/cut_{job_id}.mp4",
        }

        try:
            resp = client.get(f"/api/status/{job_id}")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "completed"
            assert data["job_id"] == job_id
            assert data["video_url"] == f"/outputs/mobile_cuts/cut_{job_id}.mp4"
            assert data["file_size_bytes"] == cut_file.stat().st_size
        finally:
            PROGRESS_STORE.pop(job_id, None)
            cut_file.unlink(missing_ok=True)


def test_zero_forbidden_character_u0669():
    """Verify zero occurrences of forbidden character U+0669 in this test file."""
    content = Path(__file__).read_text(encoding="utf-8")
    assert "\u0669" not in content
