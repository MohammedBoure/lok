#!/usr/bin/env python3
"""
Gatekeeper Multi-Tenant SaaS Platform Integration Test Suite
(tests/test_gatekeeper_saas_platform.py).

Quality Gatekeeper: agy100
Author: MohammedBoure <datasupabase@gmail.com>
Branch: test/agy100-saas-platform-gatekeeper
Scope:
  1. Multi-Tenant Account Lifecycle & Admin Provisioning (auth_db + REST API).
  2. Strict Daily & Weekly Quota Enforcement (HTTP 403 Rejection).
  3. Subscription Expiration & Account Deactivation Enforcement.
  4. 10 Pre-Seeded Commercial Merchant Personas across 10 distinct sectors + 1 Master Admin.
  5. Live Voice Audition Preview endpoint (GET /api/voices/{voice_id}/sample).
  6. Commercial Video Options (fixed_text, text_position, text_style, video_orientation).
  7. Frontend SaaS UI Contracts (3-tab layout, account switcher, quota meters, audio player).
  8. Strict Typography & Character Mapping Compliance (prohibiting Arabic numeral U+0669).
"""

from __future__ import annotations

import io
import json
import os
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from starlette.testclient import TestClient

from web import auth_db
from web.pipeline_bridge import (
    SUPPORTED_VOICE_PROFILES,
    get_or_create_voice_sample,
    process_mobile_video,
    resolve_voice_profile,
)
from web.server import PROGRESS_STORE, app

REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = REPO_ROOT / "web" / "static"

client = TestClient(app)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def isolated_saas_db(tmp_path: Path):
    """Provide an isolated SQLite database path initialized with seeds."""
    db_file = tmp_path / "gatekeeper_saas.db"
    auth_db.init_db(db_file)
    return db_file


# ---------------------------------------------------------------------------
# 1. Admin User Creation, Expiration & Quotas (REST API & auth_db)
# ---------------------------------------------------------------------------

class TestAdminUserCreationAndQuotas:
    """Verifies creation and modification of merchant accounts with custom quotas and expiry."""

    def test_auth_db_create_and_update_merchant(self, isolated_saas_db: Path):
        """Verify auth_db.create_user and auth_db.update_user with custom expiration and quotas."""
        uname = f"tlemcen_ceramics_{uuid.uuid4().hex[:6]}"
        user = auth_db.create_user(
            username=uname,
            business_name="فخار وخزف تلمسان التقليدي",
            business_category="handcrafts",
            role="merchant",
            expires_at="2029-12-31",
            daily_quota=14,
            weekly_quota=70,
            db_path=isolated_saas_db,
        )

        assert user["id"] > 0
        assert user["username"] == uname
        assert user["expires_at"] == "2029-12-31"
        assert user["daily_quota"] == 14
        assert user["weekly_quota"] == 70
        assert user["role"] == "merchant"
        assert user["is_active"] == 1

        # Update merchant quotas and expiration
        ok = auth_db.update_user(
            user["id"],
            db_path=isolated_saas_db,
            daily_quota=20,
            weekly_quota=100,
            expires_at="2030-06-30",
        )
        assert ok is True

        refetched = auth_db.get_user_by_id(user["id"], isolated_saas_db)
        assert refetched is not None
        assert refetched["daily_quota"] == 20
        assert refetched["weekly_quota"] == 100
        assert refetched["expires_at"] == "2030-06-30"

    def test_rest_api_admin_user_provisioning_and_patch(self):
        """Verify POST /api/admin/users and PATCH /api/admin/users/{id} endpoints."""
        uname = f"oran_patisserie_{uuid.uuid4().hex[:6]}"
        payload = {
            "username": uname,
            "business_name": "حلويات الباهية وهران",
            "business_category": "restaurant",
            "daily_quota": 12,
            "weekly_quota": 60,
            "expires_at": "2028-12-31",
        }

        # 1. POST create user
        res_create = client.post("/api/admin/users", json=payload)
        assert res_create.status_code == 201
        data_create = res_create.json()
        assert data_create["status"] == "ok"
        created_user = data_create["user"]
        assert created_user["username"] == uname
        assert created_user["daily_quota"] == 12
        assert created_user["weekly_quota"] == 60
        assert created_user["expires_at"] == "2028-12-31"
        user_id = created_user["id"]

        # 2. PATCH update user
        res_patch = client.patch(
            f"/api/admin/users/{user_id}",
            json={
                "daily_quota": 18,
                "weekly_quota": 90,
                "expires_at": "2029-01-01",
            },
        )
        assert res_patch.status_code == 200
        patched_user = res_patch.json()["user"]
        assert patched_user["daily_quota"] == 18
        assert patched_user["weekly_quota"] == 90
        assert patched_user["expires_at"] == "2029-01-01"


# ---------------------------------------------------------------------------
# 2. Strict Quota Enforcement (Daily & Weekly HTTP 403 Rejection)
# ---------------------------------------------------------------------------

class TestQuotaEnforcement:
    """Verifies that requests are strictly rejected with HTTP 403 when quotas are exhausted."""

    def test_daily_quota_exhaustion_rejects_with_403(self):
        """Verify video creation is rejected with HTTP 403 when daily quota is exhausted."""
        uname = f"daily_limit_user_{uuid.uuid4().hex[:6]}"
        user = auth_db.create_user(
            username=uname,
            business_name="متجر اختبار الحصة اليومية",
            daily_quota=2,
            weekly_quota=20,
        )
        token = user["auth_token"]

        # Consume daily quota (2 generations)
        auth_db.record_generation(user["id"], f"j1_{uuid.uuid4().hex[:4]}", title="Video 1")
        auth_db.record_generation(user["id"], f"j2_{uuid.uuid4().hex[:4]}", title="Video 2")

        # Third generation attempt must fail with HTTP 403
        dummy_video = io.BytesIO(b"fake_video_bytes")
        res = client.post(
            "/api/jobs/create",
            data={"auth_token": token, "script": "إعلان تجاري تجريبي"},
            files={"video": ("test_clip.mp4", dummy_video, "video/mp4")},
        )
        assert res.status_code == 403
        body = res.json()
        assert body["quota_exceeded"] is True
        assert "استنفاد الحصة اليومية" in body["error"]
        assert body["quota_details"]["daily_remaining"] == 0

    def test_weekly_quota_exhaustion_rejects_with_403(self):
        """Verify video creation is rejected with HTTP 403 when weekly quota is exhausted."""
        uname = f"weekly_limit_user_{uuid.uuid4().hex[:6]}"
        user = auth_db.create_user(
            username=uname,
            business_name="متجر اختبار الحصة الأسبوعية",
            daily_quota=10,
            weekly_quota=2,
        )
        token = user["auth_token"]

        # Consume weekly quota (2 generations)
        auth_db.record_generation(user["id"], f"jw1_{uuid.uuid4().hex[:4]}", title="Video 1")
        auth_db.record_generation(user["id"], f"jw2_{uuid.uuid4().hex[:4]}", title="Video 2")

        dummy_video = io.BytesIO(b"fake_video_bytes")
        res = client.post(
            "/api/jobs/create",
            data={"auth_token": token, "script": "إعلان تجاري تجريبي"},
            files={"video": ("test_clip.mp4", dummy_video, "video/mp4")},
        )
        assert res.status_code == 403
        body = res.json()
        assert body["quota_exceeded"] is True
        assert "استنفاد الحصة الأسبوعية" in body["error"]
        assert body["quota_details"]["weekly_remaining"] == 0


# ---------------------------------------------------------------------------
# 3. Account Expiration & Deactivation Enforcement
# ---------------------------------------------------------------------------

class TestAccountExpirationAndDeactivation:
    """Verifies that expired subscriptions and deactivated accounts are rejected with HTTP 403."""

    def test_expired_account_rejected_with_403(self):
        """Verify that an expired merchant account cannot create video jobs."""
        uname = f"expired_user_{uuid.uuid4().hex[:6]}"
        user = auth_db.create_user(
            username=uname,
            business_name="متجر منتهي الاشتراك",
            expires_at="2020-01-01",  # Past date
            daily_quota=10,
            weekly_quota=50,
        )
        token = user["auth_token"]

        dummy_video = io.BytesIO(b"fake_video_bytes")
        res = client.post(
            "/api/jobs/create",
            data={"auth_token": token, "script": "إعلان تجاري"},
            files={"video": ("expired_test.mp4", dummy_video, "video/mp4")},
        )
        assert res.status_code == 403
        body = res.json()
        assert body["quota_exceeded"] is True
        assert "صلاحية" in body["error"]
        assert body["quota_details"]["is_expired"] is True

    def test_deactivated_account_rejected_with_403(self):
        """Verify that a suspended merchant account is rejected with HTTP 403."""
        uname = f"deactivated_user_{uuid.uuid4().hex[:6]}"
        user = auth_db.create_user(
            username=uname,
            business_name="متجر مجمد وموقوف",
            is_active=0,
            daily_quota=10,
            weekly_quota=50,
        )
        token = user["auth_token"]

        dummy_video = io.BytesIO(b"fake_video_bytes")
        res = client.post(
            "/api/jobs/create",
            data={"auth_token": token, "script": "إعلان تجاري"},
            files={"video": ("deactivated_test.mp4", dummy_video, "video/mp4")},
        )
        assert res.status_code == 403
        body = res.json()
        assert body["quota_exceeded"] is True
        assert "معطل" in body["error"]
        assert body["quota_details"]["is_active"] is False


# ---------------------------------------------------------------------------
# 4. Pre-Seeded Merchant Personas (10 Sectors + 1 Master Admin)
# ---------------------------------------------------------------------------

class TestPreseededMerchantPersonas:
    """Verifies 10 diverse commercial merchants and 1 Master Admin in database and API."""

    def test_catalog_sectors_and_master_admin(self, isolated_saas_db: Path):
        """Verify the 10 commercial sectors are represented in preseeded database accounts."""
        users = auth_db.list_users(isolated_saas_db)
        assert len(users) >= 11

        admin = next((u for u in users if u["role"] == "admin"), None)
        assert admin is not None
        assert admin["username"] == "admin"
        assert admin["auth_token"] == "token_admin_master"

        # Check all 10 expected commercial merchant sectors
        expected_sectors = {
            "real_estate": "algiers_luxury_re",
            "restaurant": "oran_seafood_bistro",
            "fashion": "annaba_elegance_couture",
            "tech": "constantine_smart_tech",
            "automotive": "batna_auto_showroom",
            "handcrafts": "ghardaia_oasis_carpets",
            "tourism": "bejaia_coast_tours",
            "ecommerce": "setif_home_decor",
            "clinic": "blida_wellness_clinic",
            "fitness": "algiers_pro_fitness",
        }

        user_by_uname = {u["username"]: u for u in users}
        for sector, expected_uname in expected_sectors.items():
            assert expected_uname in user_by_uname, f"Missing merchant for sector '{sector}': {expected_uname}"
            u = user_by_uname[expected_uname]
            assert u["business_category"] == sector
            assert u["role"] == "merchant"
            assert u["daily_quota"] > 0
            assert u["weekly_quota"] > 0

    def test_demo_accounts_endpoint(self):
        """Verify GET /api/auth/demo-accounts serves all pre-seeded accounts."""
        res = client.get("/api/auth/demo-accounts")
        assert res.status_code == 200
        data = res.json()
        assert "accounts" in data
        assert len(data["accounts"]) >= 11
        unames = [a["username"] for a in data["accounts"]]
        assert "admin" in unames
        assert "algiers_luxury_re" in unames
        assert "oran_seafood_bistro" in unames
        assert "batna_auto_showroom" in unames


# ---------------------------------------------------------------------------
# 5. Live Voice Audition Preview Endpoint
# ---------------------------------------------------------------------------

class TestLiveVoiceAuditionPreview:
    """Verifies GET /api/voices/{voice_id}/sample streams valid audio for all standard voices."""

    @pytest.mark.parametrize(
        "voice_id",
        ["ar-XA-Standard-A", "ar-XA-Standard-B", "ar-XA-Standard-C", "ar-XA-Standard-D"],
    )
    def test_voice_sample_audio_streaming(self, voice_id: str):
        """Verify streaming audio sample returns HTTP 200 and audio payload for each voice."""
        res = client.get(f"/api/voices/{voice_id}/sample")
        assert res.status_code == 200
        assert "audio/" in res.headers["content-type"]
        assert len(res.content) > 500  # Valid non-empty audio stream
        assert res.content[:4] == b"RIFF"  # Valid WAV file header

    def test_voice_sample_file_caching(self):
        """Verify that voice samples are cached in outputs/voice_samples directory."""
        sample_file = get_or_create_voice_sample("ar-XA-Standard-A")
        assert sample_file.is_file()
        assert sample_file.stat().st_size > 500


# ---------------------------------------------------------------------------
# 6. Commercial Video Options (Fixed Text, Position, Style, Orientation)
# ---------------------------------------------------------------------------

class TestCommercialVideoOptions:
    """Verifies fixed banner text, text positions, visual styles, and orientation handling."""

    def test_api_jobs_create_receives_commercial_options(self):
        """Verify POST /api/jobs/create validates and passes commercial parameters to background worker."""
        dummy_video = io.BytesIO(b"fake_video_stream")
        form_data = {
            "auth_token": "token_admin_master",
            "script": "سيارات فاخرة وضمان لمدة سنتين",
            "fixed_text": "اتصل بنا: 0770001122",
            "text_position": "top_banner",
            "text_style": "commercial_red",
            "video_orientation": "square",
        }

        with patch("web.server._execute_processing_job") as mock_exec:
            res = client.post(
                "/api/jobs/create",
                data=form_data,
                files={"video": ("auto_clip.mp4", dummy_video, "video/mp4")},
            )
            assert res.status_code == 202
            data = res.json()
            assert data["status"] == "processing"
            assert data["fixed_text"] == "اتصل بنا: 0770001122"
            assert data["video_orientation"] == "square"

            mock_exec.assert_called_once()
            call_args = mock_exec.call_args[0]
            # Verify passed commercial args: fixed_text, text_pos, text_style, video_orient
            assert call_args[14] == "اتصل بنا: 0770001122"
            assert call_args[15] == "top_banner"
            assert call_args[16] == "commercial_red"
            assert call_args[17] == "square"

    def test_process_mobile_video_orientation_and_styling(self, tmp_path: Path):
        """Verify process_mobile_video resolutions for portrait, landscape, and square orientations."""
        dummy_input = tmp_path / "orient_input.mp4"
        dummy_input.write_bytes(b"dummy_video_bytes")

        captured_commands = []

        def mock_subprocess_run(cmd, *args, **kwargs):
            captured_commands.append(cmd)
            proc = MagicMock()
            proc.returncode = 0
            proc.stdout = ""
            proc.stderr = ""
            if isinstance(cmd, list) and any(str(c).endswith(".mp4") for c in cmd):
                for c in cmd:
                    if str(c).endswith(".mp4"):
                        Path(c).write_bytes(b"dummy_rendered_video")
            return proc

        mock_meta = {"width": 1280, "height": 720, "total_duration": 8.0}
        mock_keyframes = {
            "frames": [{"frame_index": 0, "timestamp": 1.0, "file_path": str(tmp_path / "k0.jpg")}],
            "count": 1,
        }
        (tmp_path / "k0.jpg").write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01")
        mock_narration = {"audio_path": str(tmp_path / "narr.wav"), "duration": 5.0, "synthesizer": "gemini_tts"}

        with patch("web.pipeline_bridge.frame_extractor.get_video_metadata", return_value=mock_meta), \
             patch("web.pipeline_bridge.frame_extractor.extract_keyframes", return_value=mock_keyframes), \
             patch("web.pipeline_bridge.synthesize_narration", return_value=mock_narration), \
             patch("subprocess.run", side_effect=mock_subprocess_run):

            # 1. Square 1:1
            summary_sq = process_mobile_video(
                video_path=dummy_input,
                script="إعلان مربع",
                output_dir=tmp_path / "cuts_sq",
                video_orientation="square",
                fixed_text="تخفيضات كبرى",
                text_position="badge",
                text_style="luxury_gold",
            )
            assert summary_sq["orientation"] == "square"
            assert summary_sq["aspect_ratio"] == "1:1"
            assert summary_sq["fixed_text"] == "تخفيضات كبرى"
            assert summary_sq["text_position"] == "badge"
            assert summary_sq["text_style"] == "luxury_gold"

            # 2. Portrait 9:16 override
            summary_port = process_mobile_video(
                video_path=dummy_input,
                script="إعلان عمودي للهاتف",
                output_dir=tmp_path / "cuts_port",
                video_orientation="portrait",
            )
            assert summary_port["orientation"] == "portrait"
            assert summary_port["aspect_ratio"] == "9:16"


# ---------------------------------------------------------------------------
# 7. Frontend SaaS UI Contracts
# ---------------------------------------------------------------------------

class TestFrontendSaasUiContracts:
    """Verifies that index.html, style.css, and app.js implement all required SaaS elements."""

    def test_index_html_saas_tabs_and_controls(self):
        """Verify index.html contains SaaS navigation, switcher, quota banners, and modal forms."""
        html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")

        # 3 Tabs
        assert 'id="tabBtnStudio"' in html
        assert 'id="tabBtnMerchant"' in html
        assert 'id="tabBtnAdmin"' in html
        assert 'id="tabContentStudio"' in html
        assert 'id="tabContentMerchant"' in html
        assert 'id="tabContentAdmin"' in html

        # Quick Account Switcher & Badges
        assert 'id="accountSwitcherSelect"' in html
        assert 'id="activePersonaBadge"' in html
        assert 'id="personaBusinessName"' in html

        # Quota Warning Banner
        assert 'id="quotaWarningBanner"' in html
        assert 'id="quotaDailyRemaining"' in html
        assert 'id="quotaWeeklyRemaining"' in html

        # Live Audition Player Buttons
        assert 'id="btnSampleStandardA"' in html
        assert 'id="btnSampleStandardB"' in html
        assert 'id="btnSampleStandardC"' in html
        assert 'id="btnSampleStandardD"' in html

        # Commercial Options Inputs
        assert 'name="video_orientation"' in html
        assert 'name="fixed_text"' in html
        assert 'name="text_position"' in html
        assert 'name="text_style"' in html

        # Admin Dashboard Table & Modals
        assert 'id="adminUsersTable"' in html
        assert 'id="createMerchantModal"' in html
        assert 'id="editQuotaModal"' in html

    def test_app_js_saas_state_and_handlers(self):
        """Verify app.js includes SaaS persona switching, tab switching, and audition logic."""
        js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")

        assert "PRESEEDED_ACCOUNTS" in js
        assert "switchAccount" in js
        assert "switchTab" in js
        assert "playVoiceAudition" in js
        assert "stopVoiceAudition" in js
        assert 'formData.append("fixed_text"' in js
        assert 'formData.append("video_orientation"' in js

    def test_style_css_saas_classes(self):
        """Verify style.css includes styling rules for SaaS tabs, cards, tables, and audition buttons."""
        css = (STATIC_DIR / "style.css").read_text(encoding="utf-8")

        assert ".saas-tabs-nav" in css
        assert ".saas-tab-btn" in css
        assert ".active-persona-badge" in css
        assert ".quota-warning-banner" in css
        assert ".btn-voice-preview" in css
        assert ".saas-data-table" in css
        assert ".admin-stats-grid" in css


# ---------------------------------------------------------------------------
# 8. Strict Character Mapping Compliance (User Rule 5)
# ---------------------------------------------------------------------------

class TestStrictCharacterMapping:
    """Verifies that the forbidden Arabic character U+0669 does not appear in any project files."""

    @pytest.mark.parametrize(
        "file_rel_path",
        [
            "web/auth_db.py",
            "web/server.py",
            "web/pipeline_bridge.py",
            "web/video_annotator.py",
            "web/static/index.html",
            "web/static/style.css",
            "web/static/app.js",
            "tests/test_gatekeeper_saas_platform.py",
            "tests/test_saas_auth_and_quotas.py",
            "tests/test_saas_dashboard_ui.py",
            "tests/README.md",
            "web/README.md",
            "web/static/README.md",
        ],
    )
    def test_no_forbidden_arabic_character(self, file_rel_path: str):
        """Ensure character U+0669 is strictly absent from all code, templates, and documentation."""
        target_path = REPO_ROOT / file_rel_path
        if target_path.is_file():
            content = target_path.read_text(encoding="utf-8")
            assert "\u0669" not in content, f"Forbidden Arabic numeral U+0669 detected in {file_rel_path}"
