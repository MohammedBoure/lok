#!/usr/bin/env python3
"""
Comprehensive Integration Test Suite for Session Authentication, Gated Services,
Decluttered Studio UI, and Real TTS Voice Reference Samples.
File: tests/test_gatekeeper_session_auth_and_tts.py

Quality Gatekeeper: agy100
Author: MohammedBoure <datasupabase@gmail.com>
Branch: test/agy100-session-auth-and-tts-gatekeeper
Scope:
  1. UI Decluttering & Multi-Sector Linguistic Guidance.
  2. Session Authentication & Default Admin / Merchant Credentials.
  3. Gated Service Security: Gating /api/upload-and-process and /api/jobs/create with HTTP 401.
  4. Real TTS Voice Reference Samples Generation & HTTP Streaming.
  5. Strict Character Mapping Compliance across the repository.
"""

from __future__ import annotations

import io
import re
import wave
from pathlib import Path
from unittest.mock import patch

import pytest
from starlette.testclient import TestClient

from web import auth_db
from web.pipeline_bridge import (
    SUPPORTED_VOICE_PROFILES,
    VOICE_SAMPLE_SCRIPTS,
    get_or_create_voice_sample,
)
from web.server import app

REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = REPO_ROOT / "web" / "static"

client = TestClient(app)


@pytest.fixture
def clean_client():
    """Return a clean TestClient instance with cleared cookies."""
    c = TestClient(app)
    c.cookies.clear()
    return c


# ---------------------------------------------------------------------------
# 1. UI Decluttering & Multi-Sector Linguistic Guidance
# ---------------------------------------------------------------------------

class TestUiDeclutteringAndLinguisticGuidance:
    """Verifies that legacy script/presets are hidden and multi-sector guidance is prominent."""

    def test_legacy_controls_hidden_or_removed(self):
        """Confirm #presetSection and #customScriptContainer are hidden in the DOM."""
        html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")

        # 1. Preset section must be hidden
        preset_match = re.search(r'<div[^>]*id="presetSection"[^>]*>', html)
        assert preset_match is not None, "Container #presetSection not found in index.html"
        preset_tag = preset_match.group(0)
        assert ("display: none" in preset_tag or "legacy-hidden-controls" in preset_tag), (
            "#presetSection is not hidden from the visible DOM"
        )

        # 2. Custom verbatim script container must be hidden
        script_match = re.search(r'<div[^>]*id="customScriptContainer"[^>]*>', html)
        assert script_match is not None, "Container #customScriptContainer not found in index.html"
        script_tag = script_match.group(0)
        assert ("display: none" in script_tag or "legacy-hidden-controls" in script_tag), (
            "#customScriptContainer is not hidden from the visible DOM"
        )

    def test_multi_sector_linguistic_guidance_present(self):
        """Verify presence of visual scene intent and speech intent inputs with sector chips."""
        html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")

        # Visual Scene Intent Input
        assert 'id="visualDescription"' in html
        assert 'name="visual_description"' in html
        assert "وصف المشهد المرئي المطلوب" in html

        # Speech Intent & Tone Input
        assert 'id="speechDescription"' in html
        assert 'name="speech_description"' in html
        assert "وصف النبرة وفحوى ما سيقال" in html

        # Recommendation Chips across sectors
        assert 'id="merchantTemplateChips"' in html
        assert 'id="chipRealEstate"' in html
        assert 'id="chipRestaurant"' in html
        assert 'id="chipFashion"' in html
        assert 'id="chipTech"' in html
        assert 'id="chipAuto"' in html


# ---------------------------------------------------------------------------
# 2. Session Authentication & Credentials
# ---------------------------------------------------------------------------

class TestSessionAuthentication:
    """Verifies default admin credentials, merchant authentication, and session lifecycle."""

    def test_default_admin_credentials_login(self, clean_client: TestClient):
        """Verify Admin credentials ('admin', 'admin123') authenticate with role 'admin' and token."""
        res = clean_client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "ok"
        assert "session_token" in body
        assert body["session_token"].startswith("sess_")
        assert body["user"]["username"] == "admin"
        assert body["user"]["role"] == "admin"
        assert "quota" in body

        # Verify session validity via GET /api/auth/session
        sess_token = body["session_token"]
        res_sess = clean_client.get(
            "/api/auth/session",
            headers={"Authorization": f"Bearer {sess_token}"},
        )
        assert res_sess.status_code == 200
        assert res_sess.json()["user"]["username"] == "admin"

    def test_merchant_credentials_and_invalid_login(self, clean_client: TestClient):
        """Verify merchant login succeeds with 'merchant123' and rejects invalid passwords."""
        # Valid merchant login
        res = clean_client.post(
            "/api/auth/login",
            json={"username": "algiers_luxury_re", "password": "merchant123"},
        )
        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "ok"
        assert body["user"]["username"] == "algiers_luxury_re"
        assert body["user"]["role"] == "merchant"

        # Invalid password rejection
        res_bad = clean_client.post(
            "/api/auth/login",
            json={"username": "algiers_luxury_re", "password": "wrong_password_999"},
        )
        assert res_bad.status_code == 401
        assert "اسم المستخدم أو كلمة المرور غير صحيحة" in res_bad.json()["message"]

    def test_session_logout_lifecycle(self, clean_client: TestClient):
        """Verify POST /api/auth/logout terminates the session immediately."""
        res = clean_client.post(
            "/api/auth/login",
            json={"username": "oran_seafood_bistro", "password": "merchant123"},
        )
        sess_token = res.json()["session_token"]
        headers = {"Authorization": f"Bearer {sess_token}"}

        # Logout
        res_logout = clean_client.post("/api/auth/logout", headers=headers)
        assert res_logout.status_code == 200
        assert "تم تسجيل الخروج بنجاح" in res_logout.json()["message"]

        # Verification that session is now dead
        res_after = clean_client.get("/api/auth/session", headers=headers)
        assert res_after.status_code == 401


# ---------------------------------------------------------------------------
# 3. Gated Service Security
# ---------------------------------------------------------------------------

class TestGatedServiceSecurity:
    """Verifies that production endpoints strictly require authentication and reject unauthenticated calls."""

    def test_unauthenticated_requests_strictly_rejected_with_401(self, clean_client: TestClient):
        """Confirm /api/upload-and-process and /api/jobs/create return 401 without auth."""
        dummy_video = io.BytesIO(b"fake_video_bytes")

        # 1. POST /api/jobs/create
        res_jobs = clean_client.post(
            "/api/jobs/create",
            data={"visual_description": "مشهد صالون", "speech_description": "نبرة هادئة"},
            files={"video": ("sample.mp4", dummy_video, "video/mp4")},
        )
        assert res_jobs.status_code == 401
        assert "غير مصرح به" in res_jobs.json()["message"]

        # 2. POST /api/upload-and-process
        dummy_video.seek(0)
        res_upload = clean_client.post(
            "/api/upload-and-process",
            data={"visual_description": "مشهد صالون", "speech_description": "نبرة هادئة"},
            files={"video": ("sample.mp4", dummy_video, "video/mp4")},
        )
        assert res_upload.status_code == 401
        assert "غير مصرح به" in res_upload.json()["message"]

    def test_authenticated_requests_accepted(self, clean_client: TestClient):
        """Confirm video generation requests pass with valid session or auth token."""
        # Login merchant
        res_login = clean_client.post(
            "/api/auth/login",
            json={"username": "constantine_smart_tech", "password": "merchant123"},
        )
        sess_token = res_login.json()["session_token"]

        dummy_video = io.BytesIO(b"fake_video_bytes")
        with patch("web.server._execute_processing_job"):
            res = clean_client.post(
                "/api/jobs/create",
                headers={"Authorization": f"Bearer {sess_token}"},
                data={"visual_description": "أجهزة ذكية", "speech_description": "نبرة تقنية حماسية"},
                files={"video": ("tech.mp4", dummy_video, "video/mp4")},
            )
            assert res.status_code == 202
            assert res.json()["status"] == "processing"


# ---------------------------------------------------------------------------
# 4. Real TTS Voice Reference Samples
# ---------------------------------------------------------------------------

class TestTtsVoiceReferenceAudio:
    """Verifies that high-fidelity reference audio exists and streams for all 4 standard voices."""

    @pytest.mark.parametrize(
        "voice_id",
        ["ar-XA-Standard-A", "ar-XA-Standard-B", "ar-XA-Standard-C", "ar-XA-Standard-D"],
    )
    def test_voice_sample_files_and_wav_specs(self, voice_id: str):
        """Verify each standard voice reference sample WAV exists, is > 50KB, and duration >= 2.0s."""
        sample_path = get_or_create_voice_sample(voice_id)
        assert sample_path.is_file(), f"Sample file not found for voice {voice_id}"
        assert sample_path.stat().st_size > 50_000, f"Sample file too small for voice {voice_id}"

        with wave.open(str(sample_path), "rb") as wf:
            channels = wf.getnchannels()
            framerate = wf.getframerate()
            frames = wf.getnframes()
            duration = frames / float(framerate)

            assert channels in (1, 2)
            assert framerate in (24000, 48000, 44100, 22050)
            assert duration >= 2.0, f"Sample duration {duration:.2f}s is less than 2.0 seconds"

    @pytest.mark.parametrize(
        "voice_id",
        ["ar-XA-Standard-A", "ar-XA-Standard-B", "ar-XA-Standard-C", "ar-XA-Standard-D"],
    )
    def test_get_voice_sample_streaming_endpoint(self, voice_id: str):
        """Verify GET /api/voices/{voice_id}/sample streams valid WAV audio."""
        res = client.get(f"/api/voices/{voice_id}/sample")
        assert res.status_code == 200
        assert res.headers["content-type"] == "audio/wav"
        assert len(res.content) > 50_000
        assert res.content[:4] == b"RIFF"


# ---------------------------------------------------------------------------
# 5. Strict Character Mapping Compliance (User Rule 5)
# ---------------------------------------------------------------------------

class TestStrictCharacterMappingCompliance:
    """Verifies absence of forbidden Arabic numeral character across all repository deliverables."""

    @pytest.mark.parametrize(
        "rel_path",
        [
            "web/auth_db.py",
            "web/server.py",
            "web/pipeline_bridge.py",
            "web/static/index.html",
            "web/static/style.css",
            "web/static/app.js",
            "tests/test_gatekeeper_session_auth_and_tts.py",
            "tests/test_session_auth_and_tts_samples.py",
            "tests/test_clean_studio_and_session_ui.py",
            "tests/README.md",
            "web/README.md",
            "web/static/README.md",
        ],
    )
    def test_no_forbidden_arabic_character(self, rel_path: str):
        """Ensure U+0669 is strictly absent from all target files (must use Arabic letter 'ج')."""
        target = REPO_ROOT / rel_path
        if target.is_file():
            content = target.read_text(encoding="utf-8")
            assert "\u0669" not in content, f"Forbidden Arabic numeral U+0669 found in {rel_path}"
