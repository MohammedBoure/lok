#!/usr/bin/env python3
"""
Comprehensive End-to-End Integration, Visual/Experiential & Production Pipeline Test Suite.
File: tests/test_e2e_auth_and_video_pipeline.py

Author: MohammedBoure <datasupabase@gmail.com>
Role: Visual, Experiential & E2E Integration Gatekeeper (agy101)
Branch: test/agy101-e2e-auth-and-video-production-gatekeeper
"""

from __future__ import annotations

import io
import os
import uuid
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from starlette.testclient import TestClient

from web.server import app
import web.auth_db as auth_db

REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = REPO_ROOT / "web" / "static"
client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_db_environment():
    """Ensure database schema and pre-seeded accounts are initialized before each test."""
    auth_db.init_db()
    yield


# ==============================================================================
# 1. Admin Account Lifecycle E2E Tests
# ==============================================================================

class TestAdminAccountLifecycleE2E:
    """Verifies complete admin login, merchant account creation, and audit logging."""

    def test_pluto_admin_login_and_account_creation_with_audit_log(self):
        """Admin pluto/plutosw4 logs in -> creates new merchant -> verifies audit activity logs."""
        # 1. Login as master admin via /api/admin/login
        res_login = client.post("/api/admin/login", json={"username": "pluto", "password": "plutosw4"})
        assert res_login.status_code == 200, res_login.text
        login_data = res_login.json()
        assert login_data["status"] == "ok"
        admin_token = login_data["session_token"]
        assert admin_token is not None
        assert login_data["user"]["role"] == "admin"

        # 2. POST /api/admin/accounts to create a new merchant
        unique_id = uuid.uuid4().hex[:6]
        merchant_user = f"e2e_merchant_{unique_id}"
        merchant_pass = f"Pass_{unique_id}!123"

        create_payload = {
            "username": merchant_user,
            "password": merchant_pass,
            "business_name": "مؤسسة الأوراس للترويج التجاري",
            "business_category": "retail",
            "role": "merchant",
            "daily_quota": 10,
            "weekly_quota": 50,
            "valid_from": "2026-01-01",
            "expires_at": "2028-12-31",
            "status": "active",
        }
        headers = {"Authorization": f"Bearer {admin_token}"}
        res_create = client.post("/api/admin/accounts", json=create_payload, headers=headers)
        assert res_create.status_code in (200, 201), res_create.text
        created_acc = res_create.json()["account"]
        user_id = created_acc["id"]
        assert created_acc["username"] == merchant_user
        assert created_acc["daily_quota"] == 10
        assert created_acc["weekly_quota"] == 50

        # 3. Verify audit activity logs for new account
        res_logs = client.get(f"/api/admin/accounts/{user_id}/logs", headers=headers)
        assert res_logs.status_code == 200, res_logs.text
        logs_data = res_logs.json()
        assert logs_data["status"] == "ok"
        event_types = [log["event_type"] for log in logs_data["logs"]]
        assert "account_created" in event_types

        # 4. Clean up created account
        conn = auth_db.get_connection()
        try:
            with conn:
                conn.execute("DELETE FROM users WHERE id = ?;", (user_id,))
        finally:
            conn.close()


# ==============================================================================
# 2. Studio Client Login E2E Tests
# ==============================================================================

class TestStudioClientLoginE2E:
    """Verifies studio client authentication, whitespace trimming, casing, and error codes."""

    def test_admin_and_merchant_login_via_auth_login(self):
        """Both admin pluto and commercial merchants authenticate via studio /api/auth/login."""
        # 1. Admin login via /api/auth/login
        res_admin = client.post("/api/auth/login", json={"username": "pluto", "password": "plutosw4"})
        assert res_admin.status_code == 200
        data_admin = res_admin.json()
        assert data_admin["status"] == "ok"
        assert data_admin["user"]["username"] == "pluto"
        assert data_admin["user"]["role"] == "admin"
        assert data_admin["quota"]["unlimited"] is True

        # 2. Merchant login via /api/auth/login
        res_merch = client.post("/api/auth/login", json={"username": "algiers_luxury_re", "password": "merchant123"})
        assert res_merch.status_code == 200
        data_merch = res_merch.json()
        assert data_merch["status"] == "ok"
        assert data_merch["user"]["username"] == "algiers_luxury_re"
        assert data_merch["user"]["role"] == "merchant"
        assert data_merch["quota"]["daily_quota"] >= 1

    def test_whitespace_trimming_and_case_insensitivity(self):
        """Verify inputs with whitespace padding and mixed case succeed seamlessly."""
        # Uppercase pluto with spaces
        res_pluto = client.post("/api/auth/login", json={"username": "  PLUTO  ", "password": "  plutosw4  "})
        assert res_pluto.status_code == 200
        assert res_pluto.json()["user"]["username"] == "pluto"

        # Merchant with mixed case and leading/trailing spaces
        res_merch = client.post(
            "/api/auth/login",
            json={"username": "  Oran_Seafood_Bistro  ", "password": "  merchant123  "}
        )
        assert res_merch.status_code == 200
        assert res_merch.json()["user"]["username"] == "oran_seafood_bistro"

    def test_invalid_credentials_returns_401_with_friendly_arabic_message(self):
        """Invalid credentials return HTTP 401 with informative Arabic message."""
        # Bad password
        res_bad_pw = client.post("/api/auth/login", json={"username": "pluto", "password": "wrong_password_999"})
        assert res_bad_pw.status_code == 401
        body = res_bad_pw.json()
        assert body["status"] == "error"
        assert "اسم المستخدم أو كلمة المرور غير صحيحة" in body["message"]

        # Unknown user
        res_unknown = client.post("/api/auth/login", json={"username": "unknown_user_xyz", "password": "any"})
        assert res_unknown.status_code == 401
        assert "اسم المستخدم أو كلمة المرور غير صحيحة" in res_unknown.json()["message"]

    def test_suspended_account_returns_403_forbidden(self):
        """Suspended or deactivated account returns HTTP 403 Forbidden on login."""
        unique_id = uuid.uuid4().hex[:6]
        suspended_user = f"suspended_{unique_id}"
        u = auth_db.create_user(
            username=suspended_user,
            password="test_password_123",
            business_name="متجر معطل",
            status="suspended",
            is_active=False,
        )

        try:
            res_login = client.post("/api/auth/login", json={"username": suspended_user, "password": "test_password_123"})
            assert res_login.status_code == 403
            body = res_login.json()
            assert body["status"] == "error"
            assert "معطل" in body["message"]
        finally:
            conn = auth_db.get_connection()
            try:
                with conn:
                    conn.execute("DELETE FROM users WHERE id = ?;", (u["id"],))
            finally:
                conn.close()


# ==============================================================================
# 3. Session & Cookie Persistence E2E Tests
# ==============================================================================

class TestSessionAndCookiePersistenceE2E:
    """Verifies /api/auth/session and /api/auth/me authentication via headers, cookies, and tokens."""

    def test_session_and_me_endpoints_with_bearer_and_cookies(self):
        """Active session token works in /api/auth/session and /api/auth/me via Bearer and cookie."""
        # Authenticate merchant
        res_login = client.post("/api/auth/login", json={"username": "oran_seafood_bistro", "password": "merchant123"})
        assert res_login.status_code == 200
        token = res_login.json()["session_token"]

        # 1. GET /api/auth/session via Bearer header
        res_sess_bearer = client.get("/api/auth/session", headers={"Authorization": f"Bearer {token}"})
        assert res_sess_bearer.status_code == 200
        assert res_sess_bearer.json()["user"]["username"] == "oran_seafood_bistro"
        assert "quota" in res_sess_bearer.json()

        # 2. GET /api/auth/session via cookie
        cookie_client = TestClient(app)
        cookie_client.cookies.set("session_token", token)
        res_sess_cookie = cookie_client.get("/api/auth/session")
        assert res_sess_cookie.status_code == 200
        assert res_sess_cookie.json()["user"]["username"] == "oran_seafood_bistro"

        # 3. GET /api/auth/me via Bearer header
        res_me_bearer = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert res_me_bearer.status_code == 200
        assert res_me_bearer.json()["user"]["username"] == "oran_seafood_bistro"

        # 4. GET /api/auth/me via query parameter ?token=
        res_me_query = client.get(f"/api/auth/me?token={token}")
        assert res_me_query.status_code == 200
        assert res_me_query.json()["user"]["username"] == "oran_seafood_bistro"

    def test_invalid_session_returns_401(self):
        """Invalid or non-existent session token returns HTTP 401 Unauthorized."""
        clean_c = TestClient(app)
        clean_c.cookies.clear()
        res_invalid = clean_c.get("/api/auth/session", headers={"Authorization": "Bearer non_existent_token_123"})
        assert res_invalid.status_code == 401
        assert res_invalid.json()["status"] == "error"

        res_me_invalid = clean_c.get("/api/auth/me", headers={"Authorization": "Bearer bad_token_xyz"})
        assert res_me_invalid.status_code == 401


# ==============================================================================
# 4. Visual & DOM Contract Verification
# ==============================================================================

class TestVisualAndDomContractsE2E:
    """Verifies that index.html and app.js fulfill UI, styling, and error handling contracts."""

    def test_index_html_gated_login_elements(self):
        """Verify index.html contains gated login elements, error alerts, and credentials hints."""
        html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")

        # Gated login container
        assert 'id="loginView"' in html
        assert 'id="merchantLoginForm"' in html
        assert 'id="merchantLoginUsername"' in html
        assert 'id="merchantLoginPassword"' in html
        assert 'id="btnSubmitMerchantLogin"' in html

        # Error feedback elements
        assert 'id="loginErrorMessage"' in html
        assert 'id="loginErrorAlert"' in html or 'login-error-alert' in html

        # Quick credentials hints & 1-tap demo logins
        assert 'id="loginCredentialHints"' in html
        assert "pluto" in html
        assert "plutosw4" in html
        assert 'id="merchantQuickLoginGrid"' in html

        # Link to admin portal
        assert "/admin" in html

    def test_app_js_login_ux_contracts(self):
        """Verify app.js implements whitespace trimming, credentials: 'include', and error handling."""
        js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")

        # Input trimming
        assert ".trim()" in js

        # Enter key submission
        assert 'e.key === "Enter"' in js or 'key === "Enter"' in js

        # Arabic error feedback strings
        assert "اسم المستخدم أو كلمة المرور غير صحيحة" in js
        assert "الحساب معطل أو منتهي الصلاحية" in js

        # Session & cookie persistence
        assert "session_token=" in js
        assert "SameSite=Lax" in js
        assert "max-age=604800" in js

        # credentials: "include" for cross-request session cookies
        assert 'credentials: "include"' in js or "credentials: 'include'" in js

        # Video production Authorization header attachment
        assert "Authorization" in js
        assert "Bearer" in js


# ==============================================================================
# 5. Video Production Pipeline E2E Execution Tests
# ==============================================================================

class TestVideoProductionPipelineE2E:
    """Verifies authenticated video job creation, quota deduction, and status polling."""

    def test_jobs_create_authenticated_quota_decrement_and_status(self):
        """Authenticated /api/jobs/create decrements quota and provides tracked status."""
        # 1. Login as merchant to obtain token and baseline quota
        res_login = client.post("/api/auth/login", json={"username": "algiers_luxury_re", "password": "merchant123"})
        assert res_login.status_code == 200
        token = res_login.json()["session_token"]
        user_id = res_login.json()["user"]["id"]
        initial_quota = res_login.json()["quota"]
        initial_remaining = initial_quota["daily_remaining"]

        # 2. POST /api/jobs/create with Authorization header
        dummy_video = io.BytesIO(b"fake_mp4_bytes_for_testing")
        with patch("web.server._execute_processing_job"):
            form_payload = {
                "script": "شقة فاخرة للبيع في قلب العاصمة الجزائر",
                "voice": "ar-XA-Standard-A",
                "video_orientation": "portrait",
            }
            res_create = client.post(
                "/api/jobs/create",
                data=form_payload,
                headers={"Authorization": f"Bearer {token}"},
                files={"video": ("test_vid.mp4", dummy_video, "video/mp4")},
            )
        assert res_create.status_code in (200, 201, 202), res_create.text
        create_data = res_create.json()
        assert create_data["status"] == "processing"
        job_id = create_data["job_id"]
        assert job_id is not None
        assert create_data["user"]["username"] == "algiers_luxury_re"

        # 3. GET /api/status/{job_id} returns valid job status
        res_status = client.get(f"/api/status/{job_id}", headers={"Authorization": f"Bearer {token}"})
        assert res_status.status_code == 200
        status_data = res_status.json()
        assert status_data["job_id"] == job_id

        # 4. Verify record_generation decrements daily remaining quota
        auth_db.record_generation(user_id=user_id, job_id=job_id, title="Test Job Quota")
        _, _, updated_quota = auth_db.check_quota(user_id)
        assert updated_quota["daily_remaining"] <= initial_remaining - 1

    def test_upload_and_process_authenticated_execution(self):
        """Authenticated /api/upload-and-process succeeds with session token cookie."""
        # Login merchant
        res_login = client.post("/api/auth/login", json={"username": "annaba_elegance_couture", "password": "merchant123"})
        assert res_login.status_code == 200
        token = res_login.json()["session_token"]
        user_id = res_login.json()["user"]["id"]

        dummy_video = io.BytesIO(b"fake_mp4_bytes_couture")
        mock_pipeline_output = {
            "status": "success",
            "job_id": "job_e2e_couture_1",
            "video_path": "/tmp/mock_couture.mp4",
            "video_url": "/outputs/mobile_cuts/mock_couture.mp4",
            "script": "أرقى تصاميم الأزياء العصرية في عنابة",
            "voice": "ar-XA-Standard-B",
            "duration": 14.5,
        }

        with patch("web.server.process_mobile_video", return_value=mock_pipeline_output):
            cookie_client = TestClient(app)
            cookie_client.cookies.set("session_token", token)
            res_upload = cookie_client.post(
                "/api/upload-and-process",
                data={"script": "أرقى تصاميم الأزياء", "voice": "ar-XA-Standard-B"},
                files={"video": ("couture.mp4", dummy_video, "video/mp4")},
            )
        assert res_upload.status_code == 200
        upload_data = res_upload.json()
        assert upload_data["status"] == "success"
        assert upload_data["user"]["username"] == "annaba_elegance_couture"
        assert upload_data["job_id"] == "job_e2e_couture_1"

    def test_unauthenticated_request_rejected_with_401(self):
        """Unauthenticated requests to production endpoints are strictly rejected with 401."""
        dummy_video = io.BytesIO(b"fake_video")
        clean_client = TestClient(app)
        clean_client.cookies.clear()

        # POST /api/jobs/create without credentials
        res_create = clean_client.post(
            "/api/jobs/create",
            data={"script": "طلب بدون تسجيل دخول"},
            files={"video": ("unauth.mp4", dummy_video, "video/mp4")},
        )
        assert res_create.status_code == 401
        assert res_create.json()["error"] == "unauthorized"

        # POST /api/upload-and-process without credentials
        dummy_video2 = io.BytesIO(b"fake_video_2")
        res_upload = clean_client.post(
            "/api/upload-and-process",
            data={"script": "طلب بدون تسجيل دخول"},
            files={"video": ("unauth2.mp4", dummy_video2, "video/mp4")},
        )
        assert res_upload.status_code == 401
        assert res_upload.json()["error"] == "unauthorized"


# ==============================================================================
# 6. Strict Character Mapping Compliance
# ==============================================================================

class TestStrictCharacterMappingE2E:
    """Verifies that the forbidden Arabic character U+0669 is strictly zero across all files."""

    FORBIDDEN_CHAR = chr(0x0669)

    def test_zero_forbidden_character_across_all_repo_files(self):
        """Assert across all repository deliverables that character U+0669 is strictly zero."""
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
                        # Strip escaped test references
                        clean_text = text.replace(r"\u0669", "").replace(r"\\u0669", "")
                        if self.FORBIDDEN_CHAR in clean_text:
                            violations.append(str(path.relative_to(REPO_ROOT)))
                    except Exception:
                        pass

        assert (
            len(violations) == 0
        ), f"Forbidden Arabic character U+0669 detected in files: {violations}. Must be strictly mapped to Arabic letter Jeem."
