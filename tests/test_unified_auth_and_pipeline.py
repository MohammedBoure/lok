"""
Tests for unified authentication, session validation, and pipeline execution.
Validates:
1. Master admin 'pluto' authentication via both /api/admin/login and /api/auth/login.
2. Case-insensitive and whitespace-padded username / password handling.
3. New accounts created via admin portal authenticate seamlessly via /api/auth/login.
4. Session tokens from either login endpoint validate properly in /api/auth/session and /api/auth/me.
5. Video creation endpoints (/api/jobs/create and /api/upload-and-process) accept active session tokens.
6. Zero occurrences of forbidden character U+0669.
"""

import io
import pytest
from unittest.mock import patch, MagicMock
from starlette.testclient import TestClient

from web.server import app
from web.auth_db import (
    authenticate_user,
    verify_admin_login,
    create_user,
    get_user_by_username,
    check_quota,
    init_db,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Ensure clean test environment before each test."""
    init_db()
    yield


def test_pluto_admin_login_and_auth_login():
    """Test master admin pluto can authenticate via both /api/admin/login and /api/auth/login."""
    # 1. /api/admin/login with exact credentials
    res_admin = client.post("/api/admin/login", json={"username": "pluto", "password": "plutosw4"})
    assert res_admin.status_code == 200, res_admin.text
    admin_data = res_admin.json()
    assert admin_data["status"] == "ok"
    assert admin_data["user"]["username"] == "pluto"
    assert admin_data["user"]["role"] == "admin"
    assert admin_data["quota"]["unlimited"] is True
    admin_sess_token = admin_data["session_token"]

    # 2. /api/auth/login with exact credentials
    res_auth = client.post("/api/auth/login", json={"username": "pluto", "password": "plutosw4"})
    assert res_auth.status_code == 200, res_auth.text
    auth_data = res_auth.json()
    assert auth_data["status"] == "ok"
    assert auth_data["user"]["username"] == "pluto"
    assert auth_data["user"]["role"] == "admin"
    assert auth_data["quota"]["unlimited"] is True
    auth_sess_token = auth_data["session_token"]

    assert admin_sess_token != auth_sess_token


def test_case_insensitive_and_whitespace_login():
    """Verify whitespace trimming and case-insensitive matching for username and password."""
    # Mixed casing and leading/trailing whitespace
    res = client.post("/api/auth/login", json={"username": "  Pluto  ", "password": " plutosw4 "})
    assert res.status_code == 200
    assert res.json()["user"]["username"] == "pluto"

    res_admin = client.post("/api/admin/login", json={"username": " PLUTO ", "password": "  plutosw4  "})
    assert res_admin.status_code == 200
    assert res_admin.json()["user"]["username"] == "pluto"

    # Merchant mixed case and whitespace
    res_merchant = client.post(
        "/api/auth/login",
        json={"username": "  Algiers_Luxury_RE  ", "password": "  merchant123  "}
    )
    assert res_merchant.status_code == 200
    assert res_merchant.json()["user"]["username"] == "algiers_luxury_re"


def test_created_account_can_login_via_auth_login():
    """Ensure accounts created via admin portal authenticate smoothly via /api/auth/login."""
    import uuid
    uniq = uuid.uuid4().hex[:6]
    username = f"sahara_crafts_{uniq}"

    # Create account via admin endpoint
    admin_login = client.post("/api/admin/login", json={"username": "pluto", "password": "plutosw4"})
    token = admin_login.json()["session_token"]

    new_user_payload = {
        "username": username,
        "password": "SecurePassword2026!",
        "business_name": "حرف وصناعات الواحات الصحراوية",
        "business_category": "handcrafts",
        "daily_quota": 8,
        "weekly_quota": 40,
        "valid_from": "2026-01-01",
        "expires_at": "2026-12-31",
        "is_active": True,
    }
    create_res = client.post(
        "/api/admin/accounts",
        json=new_user_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_res.status_code == 201
    created_user = create_res.json()["account"]
    assert created_user["username"] == username

    # Now authenticate that account via /api/auth/login
    login_res = client.post(
        "/api/auth/login",
        json={"username": f"  {username.upper()}  ", "password": "SecurePassword2026!"},
    )
    assert login_res.status_code == 200, login_res.text
    data = login_res.json()
    assert data["status"] == "ok"
    assert data["user"]["username"] == username
    assert data["quota"]["daily_quota"] == 8
    assert data["quota"]["weekly_quota"] == 40


def test_session_tokens_seamlessly_validate_in_session_and_me():
    """Verify session tokens from both endpoints validate in /api/auth/session and /api/auth/me."""
    # 1. Admin login session token
    r_admin = client.post("/api/admin/login", json={"username": "pluto", "password": "plutosw4"})
    admin_token = r_admin.json()["session_token"]

    # Test in /api/auth/session via Bearer header
    r_sess_admin = client.get("/api/auth/session", headers={"Authorization": f"Bearer {admin_token}"})
    assert r_sess_admin.status_code == 200
    assert r_sess_admin.json()["user"]["username"] == "pluto"
    assert r_sess_admin.json()["quota"]["unlimited"] is True

    # Test in /api/auth/me via Bearer header
    r_me_admin = client.get("/api/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
    assert r_me_admin.status_code == 200
    assert r_me_admin.json()["user"]["username"] == "pluto"
    assert r_me_admin.json()["quota"]["unlimited"] is True

    # 2. Merchant login session token
    r_merchant = client.post("/api/auth/login", json={"username": "oran_seafood_bistro", "password": "merchant123"})
    merchant_token = r_merchant.json()["session_token"]

    # Test in /api/auth/session via cookie
    c_cookie = TestClient(app)
    c_cookie.cookies.set("session_token", merchant_token)
    r_sess_cookie = c_cookie.get("/api/auth/session")
    assert r_sess_cookie.status_code == 200
    assert r_sess_cookie.json()["user"]["username"] == "oran_seafood_bistro"

    # Test in /api/auth/me via query param
    r_me_param = client.get(f"/api/auth/me?token={merchant_token}")
    assert r_me_param.status_code == 200
    assert r_me_param.json()["user"]["username"] == "oran_seafood_bistro"


def test_video_jobs_accept_active_session_token():
    """Ensure /api/jobs/create and /api/upload-and-process accept session token without 401/403."""
    # Obtain merchant session token
    r_login = client.post("/api/auth/login", json={"username": "constantine_smart_tech", "password": "merchant123"})
    assert r_login.status_code == 200
    sess_token = r_login.json()["session_token"]

    dummy_video = io.BytesIO(b"fake_video_mp4_content")

    # 1. /api/jobs/create with session token in Authorization Bearer
    with patch("web.server._execute_processing_job") as mock_exec:
        form_data = {
            "script": "أحدث الهواتف الذكية والأجهزة التقنية في قسنطينة مع ضمان رسمي",
            "voice": "ar-XA-Standard-A",
            "video_orientation": "portrait",
        }
        res_create = client.post(
            "/api/jobs/create",
            data=form_data,
            headers={"Authorization": f"Bearer {sess_token}"},
            files={"video": ("tech.mp4", dummy_video, "video/mp4")},
        )
        assert res_create.status_code == 202
        data = res_create.json()
        assert data["status"] == "processing"
        assert data["user"]["username"] == "constantine_smart_tech"

    # 2. /api/upload-and-process with session token in cookie
    dummy_video2 = io.BytesIO(b"fake_video_mp4_content_2")
    with patch("web.server.process_mobile_video") as mock_pipeline:
        mock_pipeline.return_value = {
            "status": "success",
            "job_id": "job_test_123",
            "video_path": "/tmp/out.mp4",
            "video_url": "/outputs/mobile_cuts/out.mp4",
            "script": "نص إعلاني رائع",
            "voice": "ar-XA-Standard-B",
            "duration": 15.0,
        }
        c = TestClient(app)
        c.cookies.set("session_token", sess_token)
        res_upload = c.post(
            "/api/upload-and-process",
            data={"voice": "ar-XA-Standard-B", "script": "إعلان متميز ومخصص للزوار"},
            files={"video": ("tech2.mp4", dummy_video2, "video/mp4")},
        )
        assert res_upload.status_code == 200
        assert res_upload.json()["status"] == "success"
        assert res_upload.json()["user"]["username"] == "constantine_smart_tech"


def test_character_mapping_rule_compliance():
    """Verify zero occurrences of Arabic character U+0669 in all repository python files."""
    import pathlib
    repo_root = pathlib.Path(__file__).parent.parent
    py_files = list(repo_root.glob("web/**/*.py")) + list(repo_root.glob("tests/**/*.py"))

    for py_file in py_files:
        content = py_file.read_text(encoding="utf-8")
        # Ensure that character U+0669 is never present
        assert "\u0669" not in content, f"Forbidden Arabic character U+0669 found in {py_file}"
