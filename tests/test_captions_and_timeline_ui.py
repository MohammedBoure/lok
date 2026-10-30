"""
Frontend UI/UX Test Suite for Synchronized Captions Pill and Shot Timeline Inspection
File: tests/test_captions_and_timeline_ui.py
Author: MohammedBoure <datasupabase@gmail.com>
Role: Frontend UI/UX Auditor (agy51)
Branch: frontend/agy51-caption-sync-and-shot-timeline-ui
"""

from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = REPO_ROOT / "web" / "static"


class TestCaptionsAndTimelineUI:
    """Verifies that lok studio presents synchronized captions indicators and shot-by-shot timeline breakdown."""

    def test_captions_pill_dom_structure(self):
        """Verify presence of resultCaptionsPill and its child elements in index.html."""
        html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
        assert 'id="resultCaptionsPill"' in html
        assert 'id="resultCaptionsIcon"' in html
        assert 'id="resultCaptionsText"' in html
        assert 'id="resultCaptionsBadge"' in html
        assert "ترجمة الكلام المتزامنة:" in html

    def test_timeline_section_dom_structure(self):
        """Verify presence of shotsTimelineSection, badge, and timeline list in index.html."""
        html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
        assert 'id="shotsTimelineSection"' in html
        assert 'id="timelineBadge"' in html
        assert 'id="shotsTimelineList"' in html
        assert "التسلسل الزمني للمشاهد واللقطات" in html
        assert "Shot-by-Shot Timeline" in html

    def test_prompt_guidance_for_captions_and_shot_grounding(self):
        """Verify that promptTextarea and promptInputHint instruct users on caption sync and scene grounding."""
        html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
        # Check caption sync guidance
        assert "ترجمة الكلام المتزامنة" in html
        assert "كلمة بكلمة" in html
        # Check scene grounding guidance
        assert "فهم وتطابق المشاهد" in html or "فهم المشاهد واللقطات" in html

    def test_app_js_captions_pill_logic(self):
        """Verify app.js populates caption status text and badge dynamically."""
        js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
        assert "resultCaptionsPill" in js
        assert "resultCaptionsText" in js
        assert "resultCaptionsBadge" in js
        assert "ترجمة الكلام متزامنة" in js
        assert "captionsApplied" in js or "captions_applied" in js

    def test_app_js_timeline_rendering_logic(self):
        """Verify app.js includes timeline rendering with timestamp formatting."""
        js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
        assert "renderShotTimeline" in js
        assert "formatTimestampRange" in js
        assert "shot-timeline-item" in js
        assert "shot-timestamp" in js
        assert "shotsTimelineSection" in js
        assert "shotsTimelineList" in js

    def test_css_styles_for_captions_pill_and_timeline(self):
        """Verify CSS tokens and styling rules for captions pill and timeline section."""
        css = (STATIC_DIR / "style.css").read_text(encoding="utf-8")
        assert ".result-captions-pill" in css
        assert ".captions-badge" in css
        assert ".shots-timeline-section" in css
        assert ".timeline-header" in css
        assert ".shots-timeline-list" in css
        assert ".shot-timeline-item" in css
        assert ".shot-timestamp" in css

    def test_zero_forbidden_character_u0669(self):
        """Verify that no forbidden character U+0669 exists in this test file or deliverables."""
        forbidden = "\u0669"
        for f in [
            STATIC_DIR / "index.html",
            STATIC_DIR / "style.css",
            STATIC_DIR / "app.js",
            Path(__file__),
        ]:
            content = f.read_text(encoding="utf-8")
            assert forbidden not in content, f"Forbidden character found in {f.name}"
