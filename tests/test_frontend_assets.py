"""
Unit & Integration Tests for Mobile Web Front-End Assets (tests/test_frontend_assets.py)
Author: MohammedBoure
Role: Mobile Front-End & Real Estate UI/UX Lead (agy51)
Branch: frontend/agy51-one-click-ux-and-session-persistence
"""

import re
from pathlib import Path
import pytest
from starlette.testclient import TestClient
from web.server import app

STATIC_DIR = Path(__file__).resolve().parent.parent / "web" / "static"


def test_frontend_files_exist():
    """Verify that all core front-end deliverables exist in web/static/."""
    expected_files = ["index.html", "style.css", "app.js", "README.md"]
    for fname in expected_files:
        fpath = STATIC_DIR / fname
        assert fpath.is_file(), f"Missing required front-end file: {fname}"
        assert fpath.stat().st_size > 100, f"File {fname} appears empty or too small"


def test_index_html_dom_elements():
    """Verify index.html contains all critical mobile camera & UI components."""
    html_content = (STATIC_DIR / "index.html").read_text(encoding="utf-8")

    # Document properties
    assert 'lang="ar"' in html_content
    assert 'dir="rtl"' in html_content
    assert "استوديو عقارات الجزائر" in html_content

    # Mobile Camera Recording elements
    assert 'id="cameraInput"' in html_content
    assert 'capture="environment"' in html_content
    assert 'id="btnNativeCamera"' in html_content
    assert 'id="btnToggleViewfinder"' in html_content
    assert 'id="viewfinderVideo"' in html_content
    assert 'id="btnRecordToggle"' in html_content
    assert 'id="btnFlipCamera"' in html_content
    assert 'id="galleryInput"' in html_content
    assert 'id="dropZone"' in html_content
    assert 'id="previewPlayer"' in html_content

    # Real Estate Presets & Script (inside optional accordion)
    assert 'id="advancedAccordion"' in html_content
    assert 'id="accordionSummary"' in html_content
    assert 'id="presetsSelectorGrid"' in html_content
    assert 'id="scriptText"' in html_content
    assert 'id="wordCount"' in html_content
    assert 'id="charCount"' in html_content
    assert 'id="speechEstDuration"' in html_content

    # Audio Controls
    assert 'id="voiceSelect"' in html_content
    assert 'id="musicSelect"' in html_content
    assert 'id="duckSlider"' in html_content

    # Prominent Voice Selection (Main Screen)
    assert 'id="voiceSelectionCard"' in html_content
    assert 'id="mainVoiceCardsGrid"' in html_content
    assert 'name="prominentVoice"' in html_content
    assert 'id="voiceCardStandardA"' in html_content
    assert 'id="voiceCardStandardB"' in html_content
    assert 'id="voiceCardStandardC"' in html_content
    assert 'id="voiceCardStandardD"' in html_content
    assert 'value="ar-XA-Standard-A"' in html_content
    assert 'value="ar-XA-Standard-B"' in html_content
    assert 'value="ar-XA-Standard-C"' in html_content
    assert 'value="ar-XA-Standard-D"' in html_content
    assert "صوت أنثوي دافئ وطبيعي" in html_content
    assert "صوت رجالي فخم وواثق" in html_content
    assert "صوت رجالي حيوي وعصري" in html_content
    assert "صوت أنثوي أنيق وهادئ" in html_content

    # 1-Click Production CTA & Stepper
    assert 'id="btnProduce"' in html_content
    assert "إنتاج الفيديو تلقائياً بالذكاء الاصطناعي بنقرة واحدة" in html_content
    assert 'id="stepperBox"' in html_content
    assert 'id="step1"' in html_content
    assert 'id="step2"' in html_content
    assert 'id="step3"' in html_content
    assert 'id="step4"' in html_content
    assert 'id="step5"' in html_content

    # Session Reset & Reconnection Buttons
    assert 'id="btnResetNewVideo"' in html_content
    assert 'id="btnStartNewProduction"' in html_content
    assert 'id="btnCancelSession"' in html_content

    # Emotional Tone Spotlight & Badges
    assert 'id="emotionalToneSpotlight"' in html_content
    assert 'id="emotionalToneVal"' in html_content

    # Video Player & Delivery
    assert 'id="finalVideoPlayer"' in html_content
    assert 'id="btnDownloadVideo"' in html_content
    assert 'id="btnShareVideo"' in html_content
    assert 'id="keyframesCarousel"' in html_content
    assert 'id="keyframeModal"' in html_content

    # Linguistic Video & Speech Description Prompts
    assert 'id="visualDescription"' in html_content
    assert 'name="visual_description"' in html_content
    assert "وصف ما تريده أن يظهر في الفيديو" in html_content
    assert 'id="speechDescription"' in html_content
    assert 'name="speech_description"' in html_content
    assert "وصف ما تريده أن يُقال في التعليق الصوتي" in html_content

    # Prompt History & Restoration UI
    assert 'id="promptHistorySelect"' in html_content
    assert 'id="promptHistoryChips"' in html_content
    assert 'id="btnSavePrompt"' in html_content
    assert 'id="btnRefreshPromptHistory"' in html_content
    assert 'id="btnClearPrompts"' in html_content
    assert 'id="submitBtn"' in html_content

    # Production Principles Modal
    assert 'id="principlesModal"' in html_content
    assert 'id="btnClosePrinciples"' in html_content
    assert 'id="btnSavePrinciples"' in html_content
    assert 'id="btnResetPrinciples"' in html_content


def test_app_js_dom_references():
    """Verify all document.getElementById calls in app.js match actual IDs in index.html."""
    html_content = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    js_content = (STATIC_DIR / "app.js").read_text(encoding="utf-8")

    # Extract all getElementById("...") IDs from app.js
    id_pattern = re.compile(r'getElementById\(["\']([^"\']+)["\']\)')
    referenced_ids = set(id_pattern.findall(js_content))

    for el_id in referenced_ids:
        assert f'id="{el_id}"' in html_content, f"ID '{el_id}' referenced in app.js not found in index.html"


def test_session_persistence_and_one_click_logic():
    """Verify app.js contains logic for localStorage session persistence and 1-click auto mode."""
    js_content = (STATIC_DIR / "app.js").read_text(encoding="utf-8")

    assert "ACTIVE_JOB_KEY = 'active_job_id'" in js_content
    assert "localStorage.setItem(ACTIVE_JOB_KEY" in js_content
    assert "localStorage.getItem(ACTIVE_JOB_KEY)" in js_content
    assert "localStorage.removeItem(ACTIVE_JOB_KEY)" in js_content
    assert "restoreSavedSession" in js_content
    assert "resetSessionAndNewVideo" in js_content
    assert "auto_mode" in js_content
    assert "emotionalTone" in js_content


def test_linguistic_prompts_and_sqlite_history_logic():
    """Verify app.js includes linguistic prompts, SQLite history fetch/restore, and FormData serialization."""
    js_content = (STATIC_DIR / "app.js").read_text(encoding="utf-8")

    assert "visual_description" in js_content
    assert "speech_description" in js_content
    assert "/api/prompts/history" in js_content
    assert "/api/prompts" in js_content
    assert "fetchPromptHistory" in js_content
    assert "renderPromptHistory" in js_content
    assert "restorePrompt" in js_content
    assert "saveCurrentPrompt" in js_content
    assert "formData.append(\"visual_description\"" in js_content
    assert "formData.append(\"speech_description\"" in js_content


def test_principles_modal_mobile_responsive_css():
    """Verify style.css implements mobile responsive touch scrolling & high-contrast glassmorphism."""
    css_content = (STATIC_DIR / "style.css").read_text(encoding="utf-8")

    assert "-webkit-overflow-scrolling: touch" in css_content
    assert "max-height: 88vh" in css_content or "max-height: 90vh" in css_content
    assert ".modal-principles-card" in css_content
    assert ".principles-modal-body" in css_content
    assert "@media (max-width: 480px)" in css_content
    assert ".linguistic-prompts-sub-section" in css_content
    assert ".prompt-history-card" in css_content


def test_voice_selector_and_decluttering():
    """Verify prominent voice selection and localStorage persistence in app.js and CSS."""
    js_content = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    css_content = (STATIC_DIR / "style.css").read_text(encoding="utf-8")

    # LocalStorage persistence & voice setup
    assert "preferred_voice" in js_content
    assert "PREF_VOICE_KEY" in js_content
    assert "setupVoiceSelector" in js_content
    assert "applyVoiceSelectionToUI" in js_content
    assert 'formData.append("voice"' in js_content

    # CSS styles for voice selection & decluttered containers
    assert ".voice-selector-card" in css_content
    assert ".voice-cards-grid" in css_content
    assert ".voice-card" in css_content
    assert ".voice-card.active" in css_content
    assert ".production-cta-container" in css_content
    assert ".terminal-collapsible" in css_content


def test_character_mapping_compliance():
    """Verify that the Arabic numeral character U+0669 does not appear in source files."""
    for fname in ["index.html", "style.css", "app.js", "README.md"]:
        content = (STATIC_DIR / fname).read_text(encoding="utf-8")
        assert "\u0669" not in content, f"Forbidden Arabic character U+0669 found in {fname}"


def test_static_routes_http_serving():
    """Verify Starlette serves HTML, CSS, JS, and API endpoints correctly."""
    client = TestClient(app)

    # 1. Index root
    r_index = client.get("/")
    assert r_index.status_code == 200
    assert "text/html" in r_index.headers["content-type"]
    assert "استوديو عقارات الجزائر" in r_index.text
    assert "إنتاج الفيديو تلقائياً بالذكاء الاصطناعي بنقرة واحدة" in r_index.text

    # 2. Static CSS
    r_css = client.get("/static/style.css")
    assert r_css.status_code == 200
    assert "--emerald-500" in r_css.text
    assert ".btn-produce-1click" in r_css.text

    # 3. Static JS
    r_js = client.get("/static/app.js")
    assert r_js.status_code == 200
    assert "restoreSavedSession" in r_js.text

    # 4. Presets API
    r_presets = client.get("/api/presets")
    assert r_presets.status_code == 200
    presets = r_presets.json()
    assert len(presets) == 4
