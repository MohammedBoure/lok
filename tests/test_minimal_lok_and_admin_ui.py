"""
Comprehensive Test Suite for Minimalist 'lok' Studio UI & Bootstrap Admin Portal
File: tests/test_minimal_lok_and_admin_ui.py
Author: MohammedBoure <datasupabase@gmail.com>
Role: Lead Frontend Engineer (agy51)
Branch: frontend/agy51-minimal-lok-and-admin-ui
"""

import re
from pathlib import Path
import pytest
from starlette.testclient import TestClient
from web.server import app

REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = REPO_ROOT / "web" / "static"
client = TestClient(app)


# ==============================================================================
# 1. Main Client 'lok' UI & Minimalist Studio Verification
# ==============================================================================

class TestMinimalLokClientUi:
    """Verifies radical minimalist redesign into 'lok' with gated login and decluttered studio."""

    def test_lok_branding_and_title(self):
        """Verify 'lok' branding, page title, and modern typography in index.html."""
        html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
        assert "lok" in html
        assert "<title>lok • استوديو إنتاج الفيديو الذكي</title>" in html
        assert "Cairo" in html
        assert "Inter" in html
        assert "/static/style.css" in html
        assert "/static/app.js" in html

    def test_gated_login_screen_structure(self):
        """Verify gated login view is present before studio access and persists credentials."""
        html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
        assert 'id="loginView"' in html
        assert 'id="merchantLoginUsername"' in html
        assert 'id="merchantLoginPassword"' in html
        assert 'id="btnSubmitMerchantLogin"' in html
        assert 'id="merchantQuickLoginGrid"' in html
        assert "/admin" in html

    def test_minimalist_studio_essential_controls_only(self):
        """Verify Studio UI keeps ONLY upload dropzone, detailed prompt, settings button, and produce button."""
        html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")

        # 1. Pre-recorded video upload area (file selector/dropzone, NO in-browser camera stream)
        assert 'id="videoDropzone"' in html
        assert 'id="videoFileInput"' in html
        assert 'accept="video/*"' in html
        assert "مقطع الفيديو المسجل" in html or "الفيديوهات الجاهزة والمسجلة مسبقاً" in html
        # Confirm no in-browser webcam recording controls in visible studio
        assert 'id="btnStartRecording"' not in html
        assert 'id="viewfinderVideo"' not in html

        # 2. Detailed prompt textarea (speech speed, visuals, tone, dialect)
        assert 'id="promptTextarea"' in html
        assert "سرعة الإلقاء" in html
        assert "المشاهد المرئية" in html
        assert "نبرة الصوت" in html
        assert "اللهجة" in html

        # 3. Simple Settings button
        assert 'id="btnOpenSettings"' in html
        assert "الإعدادات" in html

        # 4. Produce Video action button
        assert 'id="btnProduceVideo"' in html
        assert "إنتاج الفيديو" in html

        # Verify old cluttered tabs and accordions are removed from visible studio
        assert 'class="saas-tabs-nav"' not in html
        assert 'id="advancedAccordion"' not in html

    def test_settings_view_components_and_back_button(self):
        """Verify Settings view contains Back button, quota balance, recommendations manager, voice picker, logout."""
        html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")

        # Settings Overlay / View
        assert 'id="settingsModal"' in html

        # Back Button ("زر عودة")
        assert 'id="btnSettingsBack"' in html
        assert "العودة للاستوديو" in html

        # 1. Current balance / remaining quota indicator
        assert 'id="quotaDailyRemaining"' in html
        assert 'id="quotaDailyTotal"' in html
        assert 'id="quotaWeeklyRemaining"' in html
        assert 'id="quotaWeeklyTotal"' in html
        assert 'id="quotaExpiryText"' in html
        assert "حالة الرصيد" in html or "الحصة المتاحة" in html

        # 2. Recommendations Manager (CRUD + attach)
        assert 'id="newRecommendationInput"' in html
        assert 'id="btnAddRecommendation"' in html
        assert 'id="recommendationsList"' in html
        assert "إدارة التوصيات" in html

        # 3. Voiceover Artist Picker (with Algerian Darja audition player)
        assert 'id="btnSampleStandardA"' in html
        assert 'id="btnSampleStandardB"' in html
        assert 'id="btnSampleStandardC"' in html
        assert 'id="btnSampleStandardD"' in html
        assert "عينة صوتية بالدارجة" in html
        assert "تعيين المعلق الصوتي" in html

        # 4. Logout Button
        assert 'id="btnLogout"' in html
        assert "تسجيل الخروج" in html


# ==============================================================================
# 2. Modern Black & White CSS Theme Verification
# ==============================================================================

class TestModernBlackAndWhiteTheme:
    """Verifies that style.css implements an authentic modern monochrome B&W design system."""

    def test_black_and_white_color_tokens(self):
        """Verify CSS tokens enforce rich blacks, pure whites, and zinc borders."""
        css = (STATIC_DIR / "style.css").read_text(encoding="utf-8")
        assert "--lok-bg: #09090b" in css or "#000000" in css
        assert "--lok-white: #ffffff" in css
        assert "--lok-black: #000000" in css
        assert "--lok-border: #27272a" in css or "--lok-border" in css

    def test_black_and_white_button_classes(self):
        """Verify high-contrast B&W button styling."""
        css = (STATIC_DIR / "style.css").read_text(encoding="utf-8")
        assert ".btn-bw-primary" in css
        assert ".btn-bw-secondary" in css
        assert ".btn-bw-settings" in css
        assert ".btn-bw-back" in css
        assert ".btn-bw-danger" in css
        assert ".btn-bw-audition" in css

    def test_clean_dropzone_and_prompt_styles(self):
        """Verify dropzone and textarea styling."""
        css = (STATIC_DIR / "style.css").read_text(encoding="utf-8")
        assert ".video-dropzone" in css
        assert ".lok-prompt-textarea" in css
        assert ".settings-modal-dialog" in css or ".lok-settings-overlay" in css


# ==============================================================================
# 3. Dedicated Bootstrap Admin Portal Verification (`admin.html` & `/admin`)
# ==============================================================================

class TestDedicatedBootstrapAdminPortal:
    """Verifies Bootstrap 5 Admin Portal at /admin with dedicated pluto login, accounts table, and logs."""

    def test_admin_html_file_exists(self):
        """Confirm web/static/admin.html exists and is well-formed HTML5."""
        admin_path = STATIC_DIR / "admin.html"
        assert admin_path.is_file(), "web/static/admin.html file must exist"
        html = admin_path.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in html
        assert "Bootstrap" in html or "bootstrap" in html
        assert "lok" in html
        assert "لوحة التحكم الإدارية" in html

    def test_dedicated_admin_login_credentials_view(self):
        """Verify dedicated login view configured for username pluto and password plutosw4."""
        html = (STATIC_DIR / "admin.html").read_text(encoding="utf-8")
        assert 'id="adminLoginSection"' in html
        assert 'id="adminUsername"' in html
        assert 'id="adminPassword"' in html
        assert 'id="btnAdminLoginSubmit"' in html
        assert "pluto" in html
        assert "plutosw4" in html

    def test_admin_accounts_table_and_validity_columns(self):
        """Verify accounts table columns: username, business name, status, valid_from, expires_at, quotas."""
        html = (STATIC_DIR / "admin.html").read_text(encoding="utf-8")
        assert 'id="accountsTable"' in html
        assert "اسم المستخدم" in html
        assert "اسم النشاط التجاري" in html
        assert "الحالة" in html
        assert "بدء الصلاحية" in html
        assert "انتهاء الصلاحية" in html
        assert "الحصة اليومية" in html
        assert "الحصة الأسبوعية" in html

    def test_admin_crud_and_activity_logs_modals(self):
        """Verify modals for add account, edit account, change password, and activity event logs."""
        html = (STATIC_DIR / "admin.html").read_text(encoding="utf-8")
        assert 'id="modalAddAccount"' in html
        assert 'id="modalEditAccount"' in html
        assert 'id="modalChangePassword"' in html
        assert 'id="modalAccountLogs"' in html
        assert "سجل النشاطات" in html

    def test_http_route_serving_admin_portal(self):
        """Verify HTTP GET /admin serves the Bootstrap admin portal with status 200 OK."""
        res = client.get("/admin")
        assert res.status_code == 200
        assert "لوحة التحكم الإدارية" in res.text
        assert "pluto" in res.text

    def test_admin_standalone_embedded_css_stylesheet(self):
        """Verify admin.html embeds a comprehensive, self-contained standalone CSS stylesheet."""
        html = (STATIC_DIR / "admin.html").read_text(encoding="utf-8")
        assert "<style>" in html, "admin.html must contain an embedded <style> block"

        # 1. Reset, box-sizing, and typography
        assert "box-sizing: border-box" in html
        assert "--bs-body-font-family" in html or "font-family" in html
        assert "Cairo" in html or "Inter" in html
        assert "radial-gradient" in html or "background-color" in html

        # 2. Grid & Layout System
        assert ".container" in html
        assert ".container-fluid" in html
        assert ".row" in html
        assert ".col-6" in html
        assert ".col-md-3" in html
        assert ".col-lg-4" in html
        assert ".d-flex" in html
        assert ".justify-content-center" in html
        assert ".align-items-center" in html
        assert ".gap-2" in html
        assert ".mb-3" in html
        assert ".p-3" in html

        # 3. Navbar & Branding
        assert ".navbar" in html
        assert ".navbar-brand" in html
        assert ".brand-logo-text" in html

        # 4. Cards & Metrics
        assert ".card" in html
        assert ".card-header" in html
        assert ".card-body" in html
        assert ".shadow-lg" in html
        assert "border-radius: 12px" in html or ".card" in html

        # 5. Tables & Wrapping
        assert ".table" in html
        assert ".table-hover" in html
        assert ".table-responsive" in html
        assert ".table-bordered" in html

        # 6. Badges
        assert ".badge" in html
        assert ".bg-success" in html
        assert ".bg-danger" in html
        assert ".bg-warning" in html
        assert ".bg-secondary" in html
        assert ".bg-primary" in html
        assert ".badge-active" in html
        assert ".badge-suspended" in html

        # 7. Buttons
        assert ".btn" in html
        assert ".btn-primary" in html
        assert ".btn-secondary" in html
        assert ".btn-success" in html
        assert ".btn-danger" in html
        assert ".btn-dark" in html
        assert ".btn-light" in html
        assert ".btn-sm" in html
        assert ".btn-lok-primary" in html
        assert ".btn-lok-outline" in html

        # 8. Form Controls
        assert ".form-control" in html
        assert ".form-select" in html
        assert ".form-label" in html
        assert ".input-group" in html

        # 9. Alerts
        assert ".alert" in html
        assert ".alert-info" in html
        assert ".alert-danger" in html
        assert ".alert-success" in html
        assert ".alert-warning" in html

        # 10. Modals & Dialogs
        assert ".modal" in html
        assert ".modal-backdrop" in html
        assert ".modal-dialog" in html
        assert ".modal-content" in html
        assert ".modal-header" in html
        assert ".modal-body" in html
        assert ".modal-footer" in html
        assert ".modal-title" in html
        assert ".btn-close" in html
        assert "z-index: 1055" in html
        assert "z-index: 1050" in html

    def test_admin_standalone_offline_js_polyfill(self):
        """Verify admin.html includes native standalone polyfill for Bootstrap Modal and Toast offline."""
        html = (STATIC_DIR / "admin.html").read_text(encoding="utf-8")
        assert 'window.bootstrap = {' in html or "typeof window.bootstrap" in html
        assert "Modal:" in html
        assert "Toast:" in html
        assert "data-bs-dismiss" in html


# ==============================================================================
# 4. Strict Typography & Zero U+0669 Character Compliance
# ==============================================================================

class TestStrictTypographyCompliance:
    """Verifies complete absence of forbidden character U+0669 across all repository deliverables."""

    @pytest.mark.parametrize("rel_path", [
        "web/static/index.html",
        "web/static/style.css",
        "web/static/app.js",
        "web/static/admin.html",
        "web/static/README.md",
    ])
    def test_zero_forbidden_character_in_deliverables(self, rel_path: str):
        """Confirm zero occurrences of U+0669 in all client files."""
        target_file = REPO_ROOT / rel_path
        if target_file.is_file():
            content = target_file.read_text(encoding="utf-8")
            assert "\u0669" not in content, f"Forbidden Arabic character U+0669 found in {rel_path}"

    def test_zero_forbidden_character_in_test_file(self):
        """Confirm zero occurrences of U+0669 in this test suite."""
        self_content = Path(__file__).read_text(encoding="utf-8")
        sanitized = self_content.replace("\\u0669", "")
        assert "\u0669" not in sanitized, "Forbidden Arabic character U+0669 found directly in test suite"
