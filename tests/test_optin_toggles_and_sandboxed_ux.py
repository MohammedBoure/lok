"""
Frontend UI/UX Test Suite for Opt-In Feature Toggles and Sandboxed Asset UX
File: tests/test_optin_toggles_and_sandboxed_ux.py
Author: MohammedBoure <datasupabase@gmail.com>
Role: Frontend UI/UX Auditor (agy51)
Branch: frontend/agy51-optin-toggles-and-sandboxed-ux
"""

from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = REPO_ROOT / "web" / "static"


class TestOptInTogglesAndSandboxedUX:
    """Verifies that lok studio implements clean opt-in toggles, default-off feature gating, and sandboxed asset isolation."""

    def test_optin_quick_bar_dom_structure(self):
        """Verify presence of opt-in quick bar and 1-tap toggles in index.html."""
        html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
        assert 'id="optInQuickBar"' in html
        assert 'id="btnToggleCaptionsOptIn"' in html
        assert 'id="statusCaptionsOptIn"' in html
        assert 'id="btnToggleMusicOptIn"' in html
        assert 'id="statusMusicOptIn"' in html
        assert 'id="btnToggleTimelineOptIn"' in html
        assert 'id="statusTimelineOptIn"' in html
        assert "ميزات اختيارية (Opt-In):" in html

    def test_settings_modal_optin_switches_dom_structure(self):
        """Verify presence of opt-in switches section in settings modal."""
        html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
        assert 'id="sectionOptInPreferences"' in html
        assert 'id="settingToggleCaptions"' in html
        assert 'id="settingToggleMusic"' in html
        assert 'id="settingToggleTimeline"' in html
        assert "تفضيلات الميزات الإضافية (Opt-In Features)" in html
        assert "الوضع الافتراضي معطل لضمان السرعة والصوت النقي" in html

    def test_prompt_guidance_for_optin_architecture(self):
        """Verify that promptTextarea and promptInputHint explain the opt-in default-off architecture."""
        html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
        assert "التعطيل الافتراضي" in html or "الاختيار المسبق" in html or "Opt-In" in html
        assert "معطلة افتراضياً" in html
        assert "صوت نقي 100%" in html
        assert "بدون موسيقى" in html

    def test_app_js_optin_state_and_sync_logic(self):
        """Verify app.js includes opt-in state management, persistence, and UI synchronization."""
        js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
        assert "optIn:" in js
        assert "setupOptInToggles" in js
        assert "setOptInFeature" in js
        assert "syncOptInUI" in js
        assert "loadOptInSettings" in js
        assert "lok_optin_settings" in js
        assert "btnToggleCaptionsOptIn" in js
        assert "btnToggleMusicOptIn" in js
        assert "btnToggleTimelineOptIn" in js

    def test_app_js_optin_result_gating_logic(self):
        """Verify captions pill and timeline section remain strictly hidden when not opted in."""
        js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
        # Captions gating
        assert "dom.resultCaptionsPill.style.display = \"none\"" in js
        assert "captionsRequestedOrApplied" in js or "captionsApplied" in js
        # Timeline gating
        assert "isTimelineOptedIn" in js
        assert "dom.shotsTimelineSection.style.display = \"none\"" in js

    def test_sandboxed_video_url_binding_and_isolation(self):
        """Verify app.js binds to sandboxed job directories and cache-busts with job context."""
        js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
        assert "/outputs/jobs/" in js
        assert "data.job_id" in js or "jobId" in js
        assert "dataset.sandboxed" in js or "dataset.jobId" in js
        assert "buildDynamicVideoUrl" in js

    def test_css_styles_for_optin_components(self):
        """Verify CSS tokens and styling rules for opt-in bars, toggles, and switches."""
        css = (STATIC_DIR / "style.css").read_text(encoding="utf-8")
        assert ".optin-toggles-bar" in css
        assert ".btn-optin-toggle" in css
        assert ".btn-optin-toggle.active" in css
        assert ".optin-switches-list" in css
        assert ".optin-switch-item" in css
        assert ".lok-switch" in css
        assert ".lok-slider" in css

    def test_zero_forbidden_character_u0669(self):
        """Verify that no forbidden character U+0669 exists in deliverables."""
        forbidden = "\u0669"
        for f in [
            STATIC_DIR / "index.html",
            STATIC_DIR / "style.css",
            STATIC_DIR / "app.js",
            Path(__file__),
        ]:
            content = f.read_text(encoding="utf-8")
            assert forbidden not in content, f"Forbidden character found in {f.name}"
