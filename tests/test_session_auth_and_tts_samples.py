#!/usr/bin/env python3
"""
Comprehensive Test Suite for Session-Based Authentication, Default Admin Credentials,
Gated Service Execution, and Real TTS Voice Sample Generation
(tests/test_session_auth_and_tts_samples.py).

Author: MohammedBoure <datasupabase@gmail.com>
Role: Backend Architecture & Systems Specialist (agy11)
Branch: backend/agy11-session-auth-tts-voice-samples
"""

from __future__ import annotations

import io
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

client = TestClient(app)


@pytest.fixture
def fresh_client():
    """Return a fresh TestClient instance without lingering cookies."""
    c = TestClient(app)
    c.cookies.clear()
    return c


# ---------------------------------------------------------------------------
# 1. Password Hashing & Verification Tests
# ---------------------------------------------------------------------------

class TestPasswordHashingAndVerification:
    """Tests for PBKDF2-HMAC-SHA256 password hashing and verification."""

    def test_hash_password_format_and_uniqueness(self):
        """Verify hash format contains pbkdf2_sha256 identifier, iterations, salt, and digest."""
        pwd = "SecretPassword123!"
        h1 = auth_db.hash_password(pwd)
        h2 = auth_db.hash_password(pwd)

        assert h1.startswith("pbkdf2_sha256$")
        parts1 = h1.split("$")
        assert len(parts1) == 4
        assert int(parts1[1]) >= 100_000
        # Salt uniqueness guarantees different hashes for identical passwords
        assert h1 != h2

    def test_verify_password_correct_and_incorrect(self):
        """Verify password verification matches correct password and rejects invalid ones."""
        pwd = "TestCorrectPassword@2026"
        hashed = auth_db.hash_password(pwd)

        assert auth_db.verify_password(pwd, hashed) is True
        assert auth_db.verify_password("WrongPassword!", hashed) is False
        assert auth_db.verify_password("", hashed) is False
        assert auth_db.verify_password(pwd, "") is False
        assert auth_db.verify_password(pwd, None) is False

    def test_empty_password_hash_raises_value_error(self):
        """Verify empty password raises ValueError."""
        with pytest.raises(ValueError):
            auth_db.hash_password("")


# ---------------------------------------------------------------------------
# 2. Pre-seeded Admin & Merchant Credentials Tests
# ---------------------------------------------------------------------------

class TestPreseededCredentials:
    """Verifies default admin and merchant credentials in the database."""

    def test_default_admin_login_credentials(self):
        """Verify default admin credentials (username: 'admin', password: 'admin123')."""
        admin = auth_db.authenticate_credentials("admin", "admin123")
        assert admin is not None
        assert admin["username"] == "admin"
        assert admin["role"] == "admin"
        assert admin["is_active"] is True

        # Incorrect password must be rejected
        assert auth_db.authenticate_credentials("admin", "wrong_admin_pass") is None

    def test_preseeded_merchants_default_password(self):
        """Verify all 10 preseeded commercial merchants authenticate with default password 'merchant123'."""
        merchants = [acc["username"] for acc in auth_db.PRESEEDED_ACCOUNTS if acc["role"] == "merchant"]
        assert len(merchants) == 10

        for username in merchants:
            user = auth_db.authenticate_credentials(username, "merchant123")
            assert user is not None, f"Merchant '{username}' failed authentication with 'merchant123'"
            assert user["username"] == username
            assert user["role"] == "merchant"
            assert user["is_active"] is True

            # Negative check
            assert auth_db.authenticate_credentials(username, "invalid_pwd") is None


# ---------------------------------------------------------------------------
# 3. Session Management Lifecycle (auth_db)
# ---------------------------------------------------------------------------

class TestSessionLifecycleDB:
    """Verifies session creation, retrieval, validation, and invalidation."""

    def test_create_and_get_session(self):
        """Verify creating a session returns token and retrieval returns user profile."""
        admin = auth_db.get_user_by_username("admin")
        assert admin is not None

        sess = auth_db.create_session(admin["id"], duration_seconds=3600)
        assert sess is not None
        token = sess["session_token"]
        assert token.startswith("sess_")
        assert sess["user_id"] == admin["id"]

        # Retrieve session
        retrieved = auth_db.get_session(token)
        assert retrieved is not None
        assert retrieved["session_token"] == token
        assert retrieved["user"]["username"] == "admin"

    def test_delete_session(self):
        """Verify deleting session invalidates subsequent lookups."""
        user = auth_db.get_user_by_username("algiers_luxury_re")
        assert user is not None

        sess = auth_db.create_session(user["id"])
        token = sess["session_token"]

        assert auth_db.get_session(token) is not None
        ok = auth_db.delete_session(token)
        assert ok is True
        assert auth_db.get_session(token) is None

    def test_expired_session_auto_cleaned(self):
        """Verify expired session returns None upon retrieval."""
        user = auth_db.get_user_by_username("oran_seafood_bistro")
        assert user is not None

        # Create session expired in the past (-10 seconds)
        sess = auth_db.create_session(user["id"], duration_seconds=-10)
        token = sess["session_token"]

        assert auth_db.get_session(token) is None


# ---------------------------------------------------------------------------
# 4. REST API Authentication Endpoints
# ---------------------------------------------------------------------------

class TestRestApiAuthEndpoints:
    """Verifies POST /api/auth/login, POST /api/auth/logout, GET /api/auth/session, and GET /api/auth/me."""

    def test_login_success_with_admin_password(self, fresh_client: TestClient):
        """Verify POST /api/auth/login with 'admin' / 'admin123' returns 200, session_token, and quota."""
        r = fresh_client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert "session_token" in body
        assert body["user"]["username"] == "admin"
        assert body["user"]["role"] == "admin"
        assert "quota" in body
        assert "session_token" in r.cookies

    def test_login_success_with_merchant_password(self, fresh_client: TestClient):
        """Verify POST /api/auth/login with merchant credentials returns 200, token, and quotas."""
        r = fresh_client.post("/api/auth/login", json={"username": "oran_seafood_bistro", "password": "merchant123"})
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert body["user"]["username"] == "oran_seafood_bistro"
        assert body["quota"]["daily_quota"] == 8

    def test_login_invalid_password_returns_401(self, fresh_client: TestClient):
        """Verify POST /api/auth/login with wrong password returns 401 Unauthorized with Arabic message."""
        r = fresh_client.post("/api/auth/login", json={"username": "admin", "password": "wrong_password"})
        assert r.status_code == 401
        body = r.json()
        assert body["status"] == "error"
        assert "اسم المستخدم أو كلمة المرور غير صحيحة" in body["message"]

    def test_auth_session_and_me_endpoints(self, fresh_client: TestClient):
        """Verify GET /api/auth/session and GET /api/auth/me require authentication."""
        # Unauthenticated calls must return 401
        r_unauth = fresh_client.get("/api/auth/session")
        assert r_unauth.status_code == 401
        assert "غير مصرح" in r_unauth.json()["message"]

        r_me_unauth = fresh_client.get("/api/auth/me")
        assert r_me_unauth.status_code == 401

        # Login and obtain session token
        r_login = fresh_client.post("/api/auth/login", json={"username": "annaba_elegance_couture", "password": "merchant123"})
        sess_token = r_login.json()["session_token"]

        # Authenticated via Bearer header
        headers = {"Authorization": f"Bearer {sess_token}"}
        c2 = TestClient(app)
        r_sess = c2.get("/api/auth/session", headers=headers)
        assert r_sess.status_code == 200
        assert r_sess.json()["user"]["username"] == "annaba_elegance_couture"

        r_me = c2.get("/api/auth/me", headers=headers)
        assert r_me.status_code == 200
        assert r_me.json()["user"]["username"] == "annaba_elegance_couture"

        # Authenticated via Cookie
        c3 = TestClient(app)
        c3.cookies.set("session_token", sess_token)
        r_cookie = c3.get("/api/auth/session")
        assert r_cookie.status_code == 200
        assert r_cookie.json()["user"]["username"] == "annaba_elegance_couture"

    def test_logout_endpoint(self, fresh_client: TestClient):
        """Verify POST /api/auth/logout terminates the session."""
        r_login = fresh_client.post("/api/auth/login", json={"username": "constantine_smart_tech", "password": "merchant123"})
        sess_token = r_login.json()["session_token"]

        headers = {"Authorization": f"Bearer {sess_token}"}
        r_check = fresh_client.get("/api/auth/session", headers=headers)
        assert r_check.status_code == 200

        # Perform logout
        r_logout = fresh_client.post("/api/auth/logout", headers=headers)
        assert r_logout.status_code == 200
        assert "تم تسجيل الخروج بنجاح" in r_logout.json()["message"]

        # Session should now be rejected
        c_after = TestClient(app)
        r_after = c_after.get("/api/auth/session", headers=headers)
        assert r_after.status_code == 401


# ---------------------------------------------------------------------------
# 5. Gated Service Execution Tests
# ---------------------------------------------------------------------------

class TestGatedServiceExecution:
    """Verifies that video generation endpoints are strictly gated by authentication."""

    def test_unauthenticated_jobs_create_rejected_with_401(self, fresh_client: TestClient):
        """Verify POST /api/jobs/create without session or auth token returns 401 Unauthorized."""
        dummy_video = io.BytesIO(b"fake_video_bytes")
        r = fresh_client.post(
            "/api/jobs/create",
            data={"script": "إعلان عقاري مميز"},
            files={"video": ("clip.mp4", dummy_video, "video/mp4")},
        )
        assert r.status_code == 401
        body = r.json()
        assert body["status"] == "error"
        assert "غير مصرح به" in body["message"]

    def test_unauthenticated_upload_and_process_rejected_with_401(self, fresh_client: TestClient):
        """Verify POST /api/upload-and-process without session or auth token returns 401 Unauthorized."""
        dummy_video = io.BytesIO(b"fake_video_bytes")
        r = fresh_client.post(
            "/api/upload-and-process",
            data={"script": "إعلان عقاري مميز"},
            files={"video": ("clip.mp4", dummy_video, "video/mp4")},
        )
        assert r.status_code == 401
        body = r.json()
        assert body["status"] == "error"
        assert "غير مصرح به" in body["message"]

    def test_authenticated_session_jobs_create_accepted(self, fresh_client: TestClient):
        """Verify POST /api/jobs/create with active session token succeeds and returns 202."""
        r_login = fresh_client.post("/api/auth/login", json={"username": "batna_auto_showroom", "password": "merchant123"})
        sess_token = r_login.json()["session_token"]

        dummy_video = io.BytesIO(b"fake_video_bytes")
        with patch("web.server._execute_processing_job") as mock_exec:
            r = fresh_client.post(
                "/api/jobs/create",
                headers={"Authorization": f"Bearer {sess_token}"},
                data={"script": "معرض سيارات باتنة"},
                files={"video": ("auto.mp4", dummy_video, "video/mp4")},
            )
            assert r.status_code == 202
            body = r.json()
            assert body["status"] == "processing"
            assert "job_id" in body

    def test_permanent_auth_token_jobs_create_accepted(self, fresh_client: TestClient):
        """Verify POST /api/jobs/create with merchant auth_token succeeds and returns 202."""
        user = auth_db.get_user_by_username("bejaia_coast_tours")
        assert user is not None
        auth_token = user["auth_token"]

        dummy_video = io.BytesIO(b"fake_video_bytes")
        with patch("web.server._execute_processing_job") as mock_exec:
            r = fresh_client.post(
                "/api/jobs/create",
                data={"auth_token": auth_token, "script": "جولات بجاية البحرية"},
                files={"video": ("tour.mp4", dummy_video, "video/mp4")},
            )
            assert r.status_code == 202
            body = r.json()
            assert body["status"] == "processing"


# ---------------------------------------------------------------------------
# 6. Real TTS Voice Reference Audio Tests
# ---------------------------------------------------------------------------

class TestTtsVoiceReferenceSamples:
    """Verifies that high-fidelity reference audio clips exist and stream for all personas."""

    @pytest.mark.parametrize("voice_id", ["ar-XA-Standard-A", "ar-XA-Standard-B", "ar-XA-Standard-C", "ar-XA-Standard-D"])
    def test_voice_sample_file_exists_and_valid_wav(self, voice_id: str):
        """Verify each standard voice reference sample WAV exists, has valid header and > 1.0s duration."""
        sample_path = get_or_create_voice_sample(voice_id)
        assert sample_path.is_file(), f"Voice sample file missing for {voice_id}"
        assert sample_path.stat().st_size > 50_000, f"Sample file too small ({sample_path.stat().st_size} bytes)"

        with wave.open(str(sample_path), "rb") as wf:
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()
            n_frames = wf.getnframes()
            duration = n_frames / float(framerate)

            assert n_channels in (1, 2)
            assert sampwidth in (2, 4)
            assert framerate in (24000, 48000, 44100, 22050)
            assert duration >= 2.0, f"Duration {duration:.2f}s is less than 2.0s"

    @pytest.mark.parametrize("voice_id", ["ar-XA-Standard-A", "ar-XA-Standard-B", "ar-XA-Standard-C", "ar-XA-Standard-D"])
    def test_api_voice_sample_preview_streaming(self, voice_id: str):
        """Verify GET /api/voices/{voice_id}/sample streams audio/wav preview with accurate bytes."""
        r = client.get(f"/api/voices/{voice_id}/sample")
        assert r.status_code == 200
        assert r.headers["content-type"] == "audio/wav"
        assert len(r.content) > 50_000
        # First 4 bytes must be 'RIFF' (WAV magic bytes)
        assert r.content[:4] == b"RIFF"


# ---------------------------------------------------------------------------
# 7. Character Mapping Compliance (User Rule 5)
# ---------------------------------------------------------------------------

class TestCharacterMappingCompliance:
    """Verify absence of forbidden character U+0669 in all promotional texts and responses."""

    def test_no_forbidden_arabic_character_in_voice_scripts(self):
        """Verify VOICE_SAMPLE_SCRIPTS contains no occurrence of U+0669."""
        for vid, meta in VOICE_SAMPLE_SCRIPTS.items():
            text = meta.get("text", "")
            tone = meta.get("tone", "")
            style = meta.get("style_prompt", "")
            assert "\u0669" not in text, f"Found U+0669 in text of {vid}"
            assert "\u0669" not in tone, f"Found U+0669 in tone of {vid}"
            assert "\u0669" not in style, f"Found U+0669 in style of {vid}"
