#!/usr/bin/env python3
"""
Integration & Unit Test Suite for SaaS Multi-Tenant Authentication,
Quota Limits, Admin Management, Voice Preview, and Video Generation Audit
(tests/test_saas_auth_and_quotas.py).

Author: MohammedBoure
Role: Backend Architecture & SaaS Systems Engineer (agy11)
Branch: backend/agy11-saas-auth-quotas-and-dashboard
"""

from __future__ import annotations

import io
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from starlette.testclient import TestClient

from web import auth_db
from web.pipeline_bridge import get_or_create_voice_sample, process_mobile_video
from web.server import PROGRESS_STORE, app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def isolated_db(tmp_path: Path):
    """Provide an isolated SQLite database path initialized with seeds."""
    test_db = tmp_path / "test_saas.db"
    auth_db.init_db(test_db)
    return test_db


# ---------------------------------------------------------------------------
# 1. Database Seeding & User Catalog Tests
# ---------------------------------------------------------------------------

def test_preseeded_accounts_catalog(isolated_db: Path):
    """Verify that admin and diverse commercial merchants are pre-seeded."""
    users = auth_db.list_users(isolated_db)
    assert len(users) in (11, 12)

    # Check master admin
    admin = next((u for u in users if u["username"] == "admin"), None)
    assert admin is not None
    assert admin["username"] == "admin"
    assert admin["auth_token"] == "token_admin_master"
    assert admin["daily_quota"] >= 1000

    # Check merchant accounts across categories
    merchants = [u for u in users if u["role"] == "merchant"]
    assert len(merchants) == 10

    categories = {m["business_category"] for m in merchants}
    expected_categories = {
        "real_estate",
        "restaurant",
        "fashion",
        "tech",
        "automotive",
        "handcrafts",
        "tourism",
        "ecommerce",
        "clinic",
        "fitness",
    }
    assert expected_categories.issubset(categories)


# ---------------------------------------------------------------------------
# 2. Authentication Methods Tests
# ---------------------------------------------------------------------------

def test_token_and_credentials_authentication(isolated_db: Path):
    """Verify authenticate_token and authenticate_credentials lookups."""
    # Authenticate via exact token
    user = auth_db.authenticate_token("token_oran_seafood_bistro", isolated_db)
    assert user is not None
    assert user["username"] == "oran_seafood_bistro"
    assert user["business_category"] == "restaurant"

    # Authenticate with 'Bearer ' prefix
    user_bearer = auth_db.authenticate_token("Bearer token_oran_seafood_bistro", isolated_db)
    assert user_bearer is not None
    assert user_bearer["id"] == user["id"]

    # Authenticate via username
    user_creds = auth_db.authenticate_credentials("annaba_elegance_couture", db_path=isolated_db)
    assert user_creds is not None
    assert user_creds["business_category"] == "fashion"

    # Invalid lookups
    assert auth_db.authenticate_token("invalid_token_xyz", isolated_db) is None
    assert auth_db.authenticate_token("", isolated_db) is None
    assert auth_db.authenticate_credentials("non_existent_merchant", db_path=isolated_db) is None


# ---------------------------------------------------------------------------
# 3. Quota Enforcement & Expiration Tests
# ---------------------------------------------------------------------------

def test_quota_limits_and_consumption(isolated_db: Path):
    """Verify daily and weekly quota limits enforcement and consumption tracking."""
    user = auth_db.get_user_by_username("batna_auto_showroom", isolated_db)
    assert user is not None
    user_id = user["id"]
    daily_limit = user["daily_quota"]  # 5

    # Initially has full quota
    allowed, reason, details = auth_db.check_quota(user_id, isolated_db)
    assert allowed is True
    assert details["daily_used"] == 0
    assert details["daily_remaining"] == daily_limit

    # Simulate generating videos up to daily quota
    for i in range(daily_limit):
        auth_db.record_generation(user_id, f"job_test_{i}", f"/cut_{i}.mp4", f"Title {i}", isolated_db)

    # Now daily quota should be exhausted
    allowed_after, reason_after, details_after = auth_db.check_quota(user_id, isolated_db)
    assert allowed_after is False
    assert "استنفاد الحصة اليومية" in reason_after
    assert details_after["daily_remaining"] == 0
    assert details_after["daily_used"] == daily_limit

    # Verify admin bypasses quota limit
    admin = auth_db.get_user_by_username("admin", isolated_db)
    admin_allowed, _, _ = auth_db.check_quota(admin["id"], isolated_db)
    assert admin_allowed is True


def test_account_deactivation_and_expiration(isolated_db: Path):
    """Verify that disabled accounts and expired subscriptions are strictly rejected."""
    # 1. Create disabled merchant
    disabled_user = auth_db.create_user(
        username="disabled_merchant",
        business_name="متجر معطل",
        business_category="ecommerce",
        is_active=0,
        db_path=isolated_db,
    )
    allowed, reason, details = auth_db.check_quota(disabled_user["id"], isolated_db)
    assert allowed is False
    assert "معطل" in reason
    assert details["is_active"] is False

    # 2. Create expired merchant
    expired_user = auth_db.create_user(
        username="expired_merchant",
        business_name="متجر منتهي الصلاحية",
        business_category="fashion",
        expires_at="2020-01-01",  # in the past
        db_path=isolated_db,
    )
    allowed_exp, reason_exp, details_exp = auth_db.check_quota(expired_user["id"], isolated_db)
    assert allowed_exp is False
    assert "صلاحية" in reason_exp
    assert details_exp["is_expired"] is True


# ---------------------------------------------------------------------------
# 4. Admin Management & CRUD Tests
# ---------------------------------------------------------------------------

def test_admin_crud_and_platform_stats(isolated_db: Path):
    """Verify admin user creation, update, listing, and platform stats aggregation."""
    # Create new merchant
    created = auth_db.create_user(
        username="sahara_solar_tech",
        business_name="طاقة الصحراء الشمسية",
        business_category="tech",
        daily_quota=12,
        weekly_quota=60,
        expires_at="2028-12-31",
        db_path=isolated_db,
    )
    assert created["id"] is not None
    assert created["daily_quota"] == 12

    # Update merchant
    updated = auth_db.update_user(
        created["id"],
        db_path=isolated_db,
        daily_quota=15,
        business_name="طاقة الصحراء الشمسية المتقدمة",
    )
    assert updated is True

    fetched = auth_db.get_user_by_id(created["id"], isolated_db)
    assert fetched["daily_quota"] == 15
    assert fetched["business_name"] == "طاقة الصحراء الشمسية المتقدمة"

    # Platform stats
    stats = auth_db.get_platform_stats(isolated_db)
    assert stats["total_users"] in (12, 13)
    assert stats["active_merchants"] == 11
    assert "tech" in stats["category_breakdown"]


# ---------------------------------------------------------------------------
# 5. REST API Authentication Endpoints Tests
# ---------------------------------------------------------------------------

def test_api_auth_login_endpoints():
    """Verify POST /api/auth/login, GET /api/auth/me, and GET /api/auth/demo-accounts."""
    # 1. Login with username
    res = client.post("/api/auth/login", json={"username": "algiers_luxury_re"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["user"]["username"] == "algiers_luxury_re"
    assert "token" in data
    token = data["token"]

    # 2. Login with token
    res_token = client.post("/api/auth/login", json={"token": token})
    assert res_token.status_code == 200
    assert res_token.json()["user"]["id"] == data["user"]["id"]

    # 3. Invalid login
    res_bad = client.post("/api/auth/login", json={"username": "unknown_ghost"})
    assert res_bad.status_code == 401

    # 4. GET /api/auth/me with Bearer token
    res_me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res_me.status_code == 200
    me_data = res_me.json()
    assert me_data["user"]["username"] == "algiers_luxury_re"
    assert "quotas" in me_data
    assert "history" in me_data

    # 5. GET /api/auth/me without token
    res_me_unauth = client.get("/api/auth/me")
    assert res_me_unauth.status_code == 401

    # 6. GET /api/auth/demo-accounts
    res_demo = client.get("/api/auth/demo-accounts")
    assert res_demo.status_code == 200
    demo_data = res_demo.json()
    assert "accounts" in demo_data
    assert len(demo_data["accounts"]) >= 10


# ---------------------------------------------------------------------------
# 6. REST API Admin Endpoints Tests
# ---------------------------------------------------------------------------

def test_api_admin_management_endpoints():
    """Verify GET /api/admin/users, POST /api/admin/users, PATCH, and GET /api/admin/stats."""
    # 1. List users
    res_list = client.get("/api/admin/users")
    assert res_list.status_code == 200
    users = res_list.json()["users"]
    assert len(users) >= 11

    # 2. Create user via admin API with unique username for idempotency
    import uuid
    uniq_user = f"tlemcen_decor_{uuid.uuid4().hex[:6]}"
    new_user_payload = {
        "username": uniq_user,
        "business_name": "ديكور تلمسان الأندلسي",
        "business_category": "ecommerce",
        "daily_quota": 7,
        "weekly_quota": 35,
        "expires_at": "2028-12-31",
    }
    res_create = client.post("/api/admin/users", json=new_user_payload)
    assert res_create.status_code == 201
    created_user = res_create.json()["user"]
    user_id = created_user["id"]
    assert created_user["username"] == uniq_user

    # 3. Update user via PATCH
    res_patch = client.patch(f"/api/admin/users/{user_id}", json={"daily_quota": 9, "is_active": False})
    assert res_patch.status_code == 200
    patched_user = res_patch.json()["user"]
    assert patched_user["daily_quota"] == 9
    assert patched_user["is_active"] is False

    # 4. Admin stats overview
    res_stats = client.get("/api/admin/stats")
    assert res_stats.status_code == 200
    stats = res_stats.json()["stats"]
    assert stats["total_users"] >= 12
    assert "category_breakdown" in stats


# ---------------------------------------------------------------------------
# 7. Voice Audition Sample Preview Endpoint Tests
# ---------------------------------------------------------------------------

def test_voice_sample_preview_endpoint(tmp_path: Path):
    """Verify GET /api/voices/{voice_id}/sample streams valid audio file."""
    # Test for standard female voice
    res_a = client.get("/api/voices/ar-XA-Standard-A/sample")
    assert res_a.status_code == 200
    assert "audio/" in res_a.headers["content-type"]
    assert len(res_a.content) > 1000

    # Test for standard male voice
    res_b = client.get("/api/voices/ar-XA-Standard-B/sample")
    assert res_b.status_code == 200
    assert "audio/" in res_b.headers["content-type"]
    assert len(res_b.content) > 1000


# ---------------------------------------------------------------------------
# 8. Video Generation Integration with SaaS Auth & Quota Enforcement
# ---------------------------------------------------------------------------

def test_video_generation_quota_rejection():
    """Verify that video generation is rejected with HTTP 403 when quota is exceeded."""
    import uuid
    uniq_username = f"quota_exhausted_{uuid.uuid4().hex[:6]}"
    user = auth_db.create_user(
        username=uniq_username,
        business_name="متجر تجربة استنفاد الحصة",
        business_category="handcrafts",
        daily_quota=1,
        weekly_quota=5,
    )
    user_id = user["id"]
    token = user["auth_token"]

    # Fill single daily quota
    auth_db.record_generation(user_id, f"exhaust_job_{uuid.uuid4().hex[:4]}", title="Exhausted Job")

    # Now attempt async video job creation with this merchant's token
    dummy_video = io.BytesIO(b"fake_video_data_for_quota_test")
    form_data = {
        "auth_token": token,
        "script": "زرابي تقليدية فاخرة من واحات غرداية",
        "fixed_text": "تخفيض 25% بمناسبة الربيع",
        "text_position": "lower_third",
        "text_style": "luxury_gold",
        "video_orientation": "portrait",
    }
    res = client.post(
        "/api/jobs/create",
        data=form_data,
        files={"video": ("carpet_promo.mp4", dummy_video, "video/mp4")},
    )
    assert res.status_code == 403
    err_data = res.json()
    assert err_data["quota_exceeded"] is True
    assert "استنفاد الحصة اليومية" in err_data["error"]


def test_video_generation_with_fixed_text_and_audit():
    """Verify async job accepts fixed text, orientation, and records audit upon completion."""
    user = auth_db.get_user_by_username("oran_seafood_bistro")
    assert user is not None
    token = user["auth_token"]

    dummy_video = io.BytesIO(b"fake_video_stream")
    form_data = {
        "auth_token": token,
        "script": "أشهى المأكولات البحرية الطازجة على شاطئ وهران",
        "fixed_text": "احجز طاولتك الآن: 0550123456",
        "text_position": "top_banner",
        "text_style": "commercial_red",
        "video_orientation": "square",
    }

    with patch("web.server._execute_processing_job") as mock_exec:
        res = client.post(
            "/api/jobs/create",
            data=form_data,
            files={"video": ("bistro_tour.mp4", dummy_video, "video/mp4")},
        )
        assert res.status_code == 202
        data = res.json()
        assert data["status"] == "processing"
        assert data["fixed_text"] == "احجز طاولتك الآن: 0550123456"
        assert data["video_orientation"] == "square"
        assert data["user"]["username"] == "oran_seafood_bistro"

        # Verify background thread was invoked with fixed text and user_id
        mock_exec.assert_called_once()
        args = mock_exec.call_args[0]
        # args: (job_id, saved_path, script, preset, voice, duck_level, music, auto_mode, tone, visual_desc, speech_desc, prompt_id, visual_lead_in, user_id, fixed_text, text_pos, text_style, video_orient)
        assert args[13] == user["id"]
        assert args[14] == "احجز طاولتك الآن: 0550123456"
        assert args[15] == "top_banner"
        assert args[16] == "commercial_red"
        assert args[17] == "square"
