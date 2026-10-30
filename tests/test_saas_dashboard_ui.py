"""
Unit & Integration Tests for SaaS Dashboard, Merchant Studio, and Multi-Tenant Personas
File: tests/test_saas_dashboard_ui.py
Author: MouhammedBoure
Role: Frontend SaaS Lead & UI Auditor (agy51)
Branch: frontend/agy51-saas-dashboard-and-merchant-studio
"""

import json
import re
from pathlib import Path
import pytest
from starlette.testclient import TestClient
from web.server import app

STATIC_DIR = Path(__file__).resolve().parent.parent / "web" / "static"


def test_saas_branding_and_navigation():
    """Verify top header branding, active merchant/admin badge, and 3-tab navigation."""
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")

    # Platform Branding
    assert "منصة إنتاج الفيديو الذكي للتجار والشركات" in html
    assert "استوديو عقارات الجزائر ومتاجر الأعمال" in html

    # Active Persona Badge & 1-Tap Account Switcher
    assert 'id="saasHeaderControls"' in html
    assert 'id="activePersonaBadge"' in html
    assert 'id="personaRoleIcon"' in html
    assert 'id="personaBusinessName"' in html
    assert 'id="personaCategoryBadge"' in html
    assert 'id="accountSwitcherWrap"' in html
    assert 'id="accountSwitcherSelect"' in html

    # 3 Tabs
    assert 'id="saasTabsNav"' in html
    assert 'id="tabBtnStudio"' in html
    assert 'id="tabBtnMerchant"' in html
    assert 'id="tabBtnAdmin"' in html
    assert "استوديو الإنتاج" in html
    assert "لوحة التاجر" in html
    assert "لوحة الأدمن" in html

    # Tab Content Containers
    assert 'id="tabContentStudio"' in html
    assert 'id="tabContentMerchant"' in html
    assert 'id="tabContentAdmin"' in html


def test_saas_preseeded_merchant_personas():
    """Verify that app.js defines 10 pre-seeded merchant personas + 1 Admin with quotas and tokens."""
    js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")

    # Check constant definition
    assert "PRESEEDED_ACCOUNTS" in js
    assert "CURRENT_USER_KEY" in js
    assert "USER_VIDEOS_KEY" in js

    # Check key merchants from diverse sectors
    expected_usernames = [
        "dar_al_nokhba",
        "auto_algerie",
        "anaqat_el_awras",
        "techno_phone",
        "el_kasbah_resto",
        "zumurrud_jewelry",
        "abeer_parfums",
        "golden_furniture",
        "atlas_tours",
        "force_fitness",
        "admin",
    ]

    for uname in expected_usernames:
        assert uname in js, f"Expected merchant/admin '{uname}' not found in app.js PRESEEDED_ACCOUNTS"

    # Business categories
    assert "عقارات فاخرة" in js
    assert "معرض سيارات" in js
    assert "أزياء وقفطان راقي" in js
    assert "إلكترونيات وهواتف" in js
    assert "مطعم ومأكولات أصيلة" in js
    assert "مجوهرات وذهب" in js
    assert "عطور وتجميل" in js
    assert "أثاث وديكور راقي" in js
    assert "سياحة وأسفار" in js
    assert "نادي رياضي ورشاقة" in js


def test_merchant_studio_quota_and_appearance_controls():
    """Verify Quota Warning, Visual Orientation, Fixed Text, and Live Voice Audition in Studio."""
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")

    # 1. Quota Warning Banner
    assert 'id="quotaWarningBanner"' in html
    assert 'id="quotaStatusIcon"' in html
    assert 'id="quotaTitleText"' in html
    assert 'id="quotaDetailsLine"' in html
    assert 'id="quotaDailyRemaining"' in html
    assert 'id="quotaDailyTotal"' in html
    assert 'id="quotaWeeklyRemaining"' in html
    assert 'id="quotaWeeklyTotal"' in html
    assert 'id="quotaExpiryText"' in html
    assert 'id="quotaMiniBarFill"' in html

    # 2. Visual Orientation Selector
    assert 'id="visualOrientationGroup"' in html
    assert 'id="orientationSelectorGrid"' in html
    assert 'name="video_orientation"' in html
    assert 'value="portrait"' in html
    assert 'value="landscape"' in html
    assert 'value="square"' in html
    assert "9:16 عمودي للهاتف" in html
    assert "16:9 شاشة عريضة" in html
    assert "1:1 مربع" in html

    # 3. Fixed Text & Screen Appearance
    assert 'id="fixedTextSettingsCard"' in html
    assert 'id="fixedTextInput"' in html
    assert 'name="fixed_text"' in html
    assert 'id="textPositionSelect"' in html
    assert 'name="text_position"' in html
    assert 'value="lower_third"' in html
    assert 'value="top_banner"' in html
    assert 'value="badge"' in html
    assert 'id="textStyleSelect"' in html
    assert 'name="text_style"' in html
    assert 'value="modern_white"' in html
    assert 'value="luxury_gold"' in html
    assert 'value="commercial_red"' in html

    # 4. Voice Persona Cards with Live Audio Audition Buttons
    assert 'id="btnSampleStandardA"' in html
    assert 'id="btnSampleStandardB"' in html
    assert 'id="btnSampleStandardC"' in html
    assert 'id="btnSampleStandardD"' in html
    assert "استمع للصوت" in html

    # 5. Quick Merchant Template Chips
    assert 'id="merchantTemplateChips"' in html
    assert 'id="chipRealEstate"' in html
    assert 'id="chipAuto"' in html
    assert 'id="chipFashion"' in html
    assert 'id="chipTech"' in html
    assert 'id="chipRestaurant"' in html

    # 6. 1-Click Production Action
    assert 'id="btnProduce"' in html
    assert "✨ إنشاء الفيديو التسويقي بنقرة واحدة" in html


def test_merchant_dashboard_elements():
    """Verify Merchant Dashboard profile, quota meters, and video library in index.html."""
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")

    # Profile & Status
    assert 'id="merchantProfileCard"' in html
    assert 'id="merchantDashAvatarIcon"' in html
    assert 'id="merchantDashBusinessName"' in html
    assert 'id="merchantDashUsername"' in html
    assert 'id="merchantDashCategory"' in html
    assert 'id="merchantDashExpiry"' in html
    assert 'id="merchantDashStatus"' in html

    # Quota Progress Bars
    assert 'id="merchantQuotaMetersGrid"' in html
    assert 'id="merchantDailyProgressFill"' in html
    assert 'id="merchantDailyProgressText"' in html
    assert 'id="merchantWeeklyProgressFill"' in html
    assert 'id="merchantWeeklyProgressText"' in html

    # Video Library Grid & Counter
    assert 'id="merchantLibraryCard"' in html
    assert 'id="merchantVideoGrid"' in html
    assert 'id="merchantVideoCountBadge"' in html
    assert 'id="btnGoToStudioFromDash"' in html


def test_admin_dashboard_and_user_management():
    """Verify Admin Dashboard stats, merchant table, and modal inputs in index.html."""
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")

    # Platform Stats Cards
    assert 'id="adminStatsCard"' in html
    assert 'id="statTotalMerchants"' in html
    assert 'id="statVideosToday"' in html
    assert 'id="statActiveSubs"' in html
    assert 'id="statTotalVideos"' in html

    # Users Table & Create Action
    assert 'id="adminUsersCard"' in html
    assert 'id="btnOpenCreateMerchantModal"' in html
    assert 'id="adminUsersTable"' in html
    assert 'id="adminUsersTableBody"' in html

    # Create Merchant Modal & Form Controls
    assert 'id="createMerchantModal"' in html
    assert 'id="createMerchantForm"' in html
    assert 'id="newMerchantUsername"' in html
    assert 'id="newMerchantBusinessName"' in html
    assert 'id="newMerchantCategory"' in html
    assert 'id="newMerchantExpiry"' in html
    assert 'id="newMerchantDailyQuota"' in html
    assert 'id="newMerchantWeeklyQuota"' in html
    assert 'id="btnSaveNewMerchant"' in html
    assert 'id="btnCloseCreateMerchantModal"' in html
    assert 'id="btnCancelCreateMerchant"' in html

    # Edit Quotas Modal
    assert 'id="editQuotaModal"' in html
    assert 'id="editQuotaForm"' in html
    assert 'id="editQuotaUserId"' in html
    assert 'id="editQuotaDaily"' in html
    assert 'id="editQuotaWeekly"' in html
    assert 'id="btnSaveEditQuota"' in html
    assert 'id="btnCloseEditQuotaModal"' in html


def test_audio_audition_player_logic():
    """Verify live voice audition audio engine with HTML5 audio and Web Audio fallback."""
    js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")

    assert "setupVoiceAudition" in js
    assert "playVoiceAudition" in js
    assert "stopVoiceAudition" in js
    assert "playWebAudioHarmonicPreview" in js
    assert "/api/voices/" in js
    assert "/sample" in js
    assert "AudioContext" in js


def test_app_js_quota_enforcement_and_formdata_bindings():
    """Verify that handleProduceProduction validates quotas and serializes fixed text & orientation."""
    js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")

    # Quota validation logic
    assert "dailyRemaining" in js
    assert "weeklyRemaining" in js
    assert "isSuspended" in js
    assert "isExpired" in js

    # FormData bindings
    assert 'formData.append("video_orientation"' in js
    assert 'formData.append("fixed_text"' in js
    assert 'formData.append("text_position"' in js
    assert 'formData.append("text_style"' in js
    assert 'formData.append("voice"' in js
    assert "recordSuccessfulGeneration" in js
    assert "USER_VIDEOS_KEY" in js


def test_css_saas_rules_and_responsiveness():
    """Verify style.css implements SaaS headers, tabs, quota meters, and tables."""
    css = (STATIC_DIR / "style.css").read_text(encoding="utf-8")

    assert ".saas-header-controls" in css
    assert ".active-persona-badge" in css
    assert ".account-switcher-select" in css
    assert ".saas-tabs-nav" in css
    assert ".saas-tab-btn" in css
    assert ".saas-tab-btn.active" in css
    assert ".quota-warning-banner" in css
    assert ".orientation-selector-grid" in css
    assert ".orientation-card" in css
    assert ".orientation-card.active" in css
    assert ".btn-voice-preview" in css
    assert ".btn-voice-preview.playing" in css
    assert ".merchant-profile-card" in css
    assert ".merchant-video-grid" in css
    assert ".admin-stats-grid" in css
    assert ".saas-data-table" in css
    assert ".modal-admin-card" in css


def test_saas_character_mapping_compliance():
    """Verify that the Arabic character U+0669 does not appear in any SaaS source files."""
    for fname in ["index.html", "style.css", "app.js", "README.md"]:
        content = (STATIC_DIR / fname).read_text(encoding="utf-8")
        assert "\u0669" not in content, f"Forbidden Arabic character U+0669 found in {fname}"


def test_saas_dashboard_http_serving():
    """Verify Starlette serves the index page containing all SaaS elements."""
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text

    assert "منصة إنتاج الفيديو الذكي للتجار والشركات" in html
    assert "saasHeaderControls" in html
    assert "tabBtnStudio" in html
    assert "tabBtnMerchant" in html
    assert "tabBtnAdmin" in html
    assert "quotaWarningBanner" in html
    assert "fixedTextInput" in html
    assert "btnSampleStandardA" in html
    assert "adminUsersTable" in html
