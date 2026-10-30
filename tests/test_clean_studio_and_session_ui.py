"""
Unit and Integration Tests for Decluttered Studio UI and Session Login Gateway
File: tests/test_clean_studio_and_session_ui.py
Author: MouhammedBoure
Role: Frontend & Interface Auditor (agy51)
Branch: frontend/agy51-clean-studio-session-login-ui
"""

import re
from pathlib import Path
import pytest
from starlette.testclient import TestClient
from web.server import app

STATIC_DIR = Path(__file__).resolve().parent.parent / "web" / "static"


def test_studio_decluttering_legacy_controls_hidden():
    """Verify that Algerian real estate presets and verbatim script are decluttered from Studio UI."""
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")

    # Preset section and script container must be hidden
    assert 'id="presetSection"' in html
    assert 'id="customScriptContainer"' in html
    assert 'class="legacy-hidden-controls"' in html or 'display: none' in html

    # Verify that presetSection is wrapped in display: none !important
    preset_block_match = re.search(r'<div[^>]*id="presetSection"[^>]*>', html)
    assert preset_block_match is not None, "presetSection container not found in index.html"
    preset_tag = preset_block_match.group(0)
    assert 'display: none !important;' in preset_tag or 'legacy-hidden-controls' in preset_tag


def test_linguistic_guidance_inputs_and_merchant_chips_highlighted():
    """Verify visual scene guidance, speech intent guidance, and commercial sector chips."""
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")

    # Control 1: Visual Scene Guidance
    assert 'id="visualDescription"' in html
    assert "وصف المشهد المرئي المطلوب" in html
    assert "توجيه مرئي ذكي" in html

    # Control 2: Speech Intent & Tone Guidance
    assert 'id="speechDescription"' in html
    assert "وصف النبرة وفحوى ما سيقال" in html
    assert "توجيه نبرة وليس نصاً حرفياً" in html

    # Commercial recommendation chips
    assert 'id="chipRealEstate"' in html
    assert 'id="chipRestaurant"' in html
    assert 'id="chipFashion"' in html
    assert 'id="chipTech"' in html
    assert 'id="chipAuto"' in html
    assert "عقارات" in html
    assert "مطاعم" in html
    assert "أزياء" in html
    assert "تقنية" in html
    assert "سيارات" in html


def test_session_login_gateway_modal_and_default_credentials():
    """Verify Session Login Modal structure, role toggle tabs, and default admin credentials hint."""
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")

    # Session Login Modal
    assert 'id="sessionLoginModal"' in html
    assert 'id="sessionLoginTitle"' in html
    assert 'id="btnCloseLoginModal"' in html

    # Role Toggle Tabs
    assert 'id="loginRoleTabs"' in html
    assert 'id="tabLoginAdmin"' in html
    assert 'id="tabLoginMerchant"' in html

    # Admin Login Section & Default Credentials Note
    assert 'id="loginAdminSection"' in html
    assert 'id="adminHelperNote"' in html
    assert "اسم المستخدم: admin | كلمة المرور الافتراضية: admin123" in html
    assert 'id="adminLoginForm"' in html
    assert 'id="adminLoginUsername"' in html
    assert 'id="adminLoginPassword"' in html
    assert 'id="btnSubmitAdminLogin"' in html

    # Merchant Login Section & Quick 1-Tap Grid
    assert 'id="loginMerchantSection"' in html
    assert 'id="merchantQuickLoginGrid"' in html
    assert 'id="merchantLoginForm"' in html
    assert 'id="merchantLoginUsername"' in html
    assert 'id="merchantLoginPassword"' in html
    assert 'id="btnSubmitMerchantLogin"' in html

    # Header Auth Action Buttons
    assert 'id="btnLogout"' in html
    assert 'id="btnOpenLoginModal"' in html


def test_app_js_session_auth_and_gated_production_logic():
    """Verify session auth lifecycle, token handling, and gated production check in app.js."""
    js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")

    # Session Token constant and state
    assert "SESSION_TOKEN_KEY" in js
    assert "saas_session_token" in js
    assert "isAuthenticated" in js
    assert "sessionToken" in js

    # Auth functions
    assert "setupSessionAuth" in js
    assert "openLoginModal" in js
    assert "closeLoginModal" in js
    assert "handleAdminLogin" in js
    assert "handleMerchantLogin" in js
    assert "handleQuickMerchantLogin" in js
    assert "handleLogout" in js
    assert "checkExistingSession" in js
    assert "updateAuthUI" in js

    # Gated production check
    assert "if (!state.isAuthenticated || !state.currentUser)" in js
    assert "openLoginModal" in js

    # Bearer authorization header attachment
    assert "Authorization" in js
    assert "Bearer" in js


def test_voice_audition_player_elements_and_logic():
    """Verify 4 voice audition buttons, sample API endpoints, and audition engine in app.js."""
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")

    # HTML audition buttons
    assert 'id="btnSampleStandardA"' in html
    assert 'id="btnSampleStandardB"' in html
    assert 'id="btnSampleStandardC"' in html
    assert 'id="btnSampleStandardD"' in html

    # Audition JS logic
    assert "playVoiceAudition" in js
    assert "stopVoiceAudition" in js
    assert "/api/voices/" in js
    assert "/sample" in js
    assert "currentPlayingVoice" in js


def test_css_login_and_soundwave_styles():
    """Verify style.css includes classes for session login gateway and audio wave animations."""
    css = (STATIC_DIR / "style.css").read_text(encoding="utf-8")

    assert ".modal-login-card" in css
    assert ".login-role-tabs" in css
    assert ".btn-role-tab" in css
    assert ".login-helper-note" in css
    assert ".merchant-quick-grid" in css
    assert ".btn-merchant-quick" in css
    assert ".btn-auth-header" in css
    assert ".btn-voice-preview.playing" in css
    assert ".highlight-guidance" in css


def test_character_mapping_strict_compliance():
    """Verify that forbidden character U+0669 does not appear in any static deliverable."""
    deliverables = ["index.html", "style.css", "app.js", "README.md"]
    for filename in deliverables:
        content = (STATIC_DIR / filename).read_text(encoding="utf-8")
        assert "\u0669" not in content, f"Forbidden Arabic character U+0669 found in {filename}"


def test_http_serving_of_clean_studio_and_login_modal():
    """Verify Starlette server successfully renders the updated UI with login modal."""
    client = TestClient(app)
    res = client.get("/")
    assert res.status_code == 200
    html = res.text

    assert "sessionLoginModal" in html
    assert "adminHelperNote" in html
    assert "visualDescription" in html
    assert "speechDescription" in html
    assert "chipRealEstate" in html
    assert "btnSampleStandardA" in html
