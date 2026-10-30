"""
Frontend UI/UX Test Suite for Music Status Pill, Prominent Overlays, and Prompt Guidance
File: tests/test_music_and_overlay_ui.py
Author: MohammedBoure <datasupabase@gmail.com>
Role: Frontend UI/UX Auditor (agy51)
Branch: frontend/agy51-music-pills-and-overlay-ux
"""

from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = REPO_ROOT / "web" / "static"


class TestMusicPillAndOverlayUI:
    """Verifies that lok studio presents music mixing pills, prominent overlays, and prompt guidance."""

    def test_music_pill_dom_structure(self):
        """Verify presence of resultMusicPill and its sub-elements in index.html."""
        html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
        assert 'id="resultMusicPill"' in html
        assert 'id="resultMusicIcon"' in html
        assert 'id="resultMusicText"' in html
        assert 'id="resultMusicBadge"' in html
        assert "الموسيقى والمكساج:" in html

    def test_overlay_pill_and_badges_dom_structure(self):
        """Verify presence of resultOverlayPill, large font badge, and property specs badge in index.html."""
        html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
        assert 'id="resultOverlayPill"' in html
        assert 'id="resultOverlayText"' in html
        assert 'id="bottomTextBadge"' in html
        assert 'id="overlayFontBadge"' in html
        assert 'id="propertySpecsBadge"' in html
        assert "الشريط السفلي:" in html

    def test_prompt_guidance_for_music_and_font_controls(self):
        """Verify that promptTextarea and promptInputHint instruct users on music and font controls."""
        html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
        # Check music controls guidance in placeholder or hint
        assert "بدون موسيقى" in html
        assert "كتم الموسيقى" in html
        assert "صوت نقي 100%" in html
        # Check font size guidance
        assert "بخط كبير وواضح" in html or "بخط عريض وبارز" in html
        # Check property features guidance
        assert "F5" in html
        assert "مطل على البحر" in html

    def test_app_js_music_feedback_logic(self):
        """Verify app.js formats muted music and active music tracks properly."""
        js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
        # Check muted message
        assert "صوت نقي 100% (تم كتم وإلغاء موسيقى الخلفية بالكامل)" in js
        # Check muted class toggle and icon
        assert 'classList.add("muted")' in js
        assert "isMusicMuted" in js
        # Check active track and volume percentage formatting
        assert "مستوى الصوت:" in js
        assert "volPercent" in js or "volume" in js
        assert "resultMusicPill" in js
        assert "resultMusicText" in js

    def test_app_js_large_font_and_property_specs_logic(self):
        """Verify app.js populates large font badge and property specs badge dynamically."""
        js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
        assert "overlayFontBadge" in js
        assert "propertySpecsBadge" in js
        assert "large_font_applied" in js or "largeFontApplied" in js
        assert "property_features" in js or "propFeatures" in js
        assert "بخط كبير وواضح" in js

    def test_css_styles_for_music_pill_and_badges(self):
        """Verify CSS tokens and styling rules for music pill and badges."""
        css = (STATIC_DIR / "style.css").read_text(encoding="utf-8")
        assert ".result-music-pill" in css
        assert ".result-music-pill.muted" in css
        assert ".overlay-font-badge" in css
        assert ".property-specs-badge" in css
        assert ".music-badge" in css
        assert ".result-pills-row" in css

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
