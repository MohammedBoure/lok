"""
Frontend UI/UX Test Suite for Polling Resilience, Adaptive Timeouts, and Progress Telemetry
File: tests/test_polling_resilience_and_progress_ux.py
Author: MouhammedBoure <mohamadbormoz2@gmail.com>
Role: Frontend UI/UX Auditor (agy51)
Branch: frontend/agy51-polling-resilience-and-progress-telemetry
"""

from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = REPO_ROOT / "web" / "static"


class TestPollingResilienceAndProgressUX:
    """Verifies adaptive polling, progress synchronization, immediate completion, and retry UX."""

    def test_error_box_and_retry_button_dom_structure(self):
        """Verify presence of dedicated error alert container and retry action in index.html."""
        html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
        assert 'id="studioErrorBox"' in html
        assert 'id="studioErrorMessage"' in html
        assert 'id="btnRetryProduction"' in html
        assert "إعادة المحاولة" in html
        assert "تعذر إكمال إنتاج الفيديو" in html

    def test_stepper_dom_and_chips_structure(self):
        """Verify presence of stepper container, progress bar fill, and 5 step chips in index.html."""
        html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
        assert 'id="processingStepper"' in html
        assert 'id="stepperStatusText"' in html
        assert 'id="stepperFill"' in html
        assert 'id="stepFrames"' in html
        assert 'id="stepAnalyze"' in html
        assert 'id="stepVoice"' in html
        assert 'id="stepRender"' in html
        assert 'id="stepAnnotations"' in html

    def test_css_styles_for_error_box_and_retry_action(self):
        """Verify CSS styling tokens for studio error box and retry action button."""
        css = (STATIC_DIR / "style.css").read_text(encoding="utf-8")
        assert ".studio-error-box" in css
        assert ".error-box-header" in css
        assert ".error-title" in css
        assert ".error-message" in css
        assert ".error-actions" in css
        assert ".btn-retry-action" in css

    def test_app_js_adaptive_polling_and_extended_timeout(self):
        """Verify app.js implements extended polling ceiling (>=150 attempts) and adaptive delays."""
        js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
        # Extended polling ceiling
        assert "maxAttempts = 160" in js or "maxAttempts = 180" in js or "maxAttempts = 200" in js
        # Adaptive delay cadence
        assert "pollDelayMs" in js
        assert "consecutiveNetworkErrors" in js
        assert "maxNetworkErrors" in js
        # Actionable timeout error
        assert "استغرقت معالجة الفيديو وقتاً طويلاً. يرجى التحقق من لوحة التحكم أو إعادة المحاولة." in js

    def test_app_js_server_progress_telemetry_synchronization(self):
        """Verify app.js binds progress bar to server telemetry and avoids premature 100% pacing."""
        js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
        assert "d.progress_percent" in js
        assert "d.progress" in js
        assert "targetDisplayPercent" in js
        assert "currentDisplayPercent" in js
        # In-flight operations must not show 100% prematurely
        assert "serverPercent = Math.min(96" in js

    def test_app_js_immediate_completion_handling(self):
        """Verify app.js immediately transitions to completed video on status 'completed'."""
        js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
        assert 'd.status === "completed"' in js
        assert "isComplete" in js
        # Stepper is set to 100% immediately
        assert 'updateStepperStatus("اكتمل إنتاج الفيديو التسويقي بنجاح!", 100, "stepAnnotations")' in js

    def test_app_js_error_propagation_and_nondestructive_retry(self):
        """Verify app.js propagates actual backend failure messages and enables retry without re-upload."""
        js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
        assert 'd.status === "failed"' in js or 'd.status === "error"' in js
        assert "backendError" in js
        assert "dom.studioErrorBox.style.display = \"block\"" in js
        assert "dom.studioErrorMessage.textContent = errorMsg" in js
        assert "btnRetryProduction" in js
        # Retry event listener triggers production without reset
        assert "handleProduceProduction()" in js

    def test_zero_forbidden_character_u0669(self):
        """Verify that no forbidden character U+0669 exists in any deliverable."""
        forbidden = "\u0669"
        for f in [
            STATIC_DIR / "index.html",
            STATIC_DIR / "style.css",
            STATIC_DIR / "app.js",
            STATIC_DIR / "README.md",
            Path(__file__),
        ]:
            content = f.read_text(encoding="utf-8")
            assert forbidden not in content, f"Forbidden character found in {f.name}"
