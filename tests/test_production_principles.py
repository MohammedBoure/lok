"""
Tests for Production Principles & Dynamic Governance (tests/test_production_principles.py)

Author: MouhammedBoure <mohamadbormoz2@gmail.com>
Role: Testing, Verification & Gatekeepers (agy101)
Branch: test/agy101-production-principles-verification
"""

import json
from pathlib import Path
import pytest
from starlette.testclient import TestClient

from config.production_principles_manager import (
    load_principles,
    save_principles,
    reset_principles,
    build_vision_prompt_principles,
    build_tts_style_principles,
    DEFAULT_PRINCIPLES,
)
from web.server import app


@pytest.fixture(autouse=True)
def ensure_default_principles_clean():
    """Ensure principles are restored to default before and after each test."""
    reset_principles()
    yield
    reset_principles()


def test_load_principles_defaults():
    """Test loading principles returns valid structure with expected top-level keys."""
    principles = load_principles()
    assert "master_directive" in principles
    assert "voice_principles" in principles
    assert "narrative_principles" in principles
    assert "visual_principles" in principles
    assert "annotation_principles" in principles
    assert principles["voice_principles"]["active_tone_bias"] == "فاخر وهادئ"


def test_save_principles_updates_memory_and_file():
    """Test saving customized principles modifies the stored configuration."""
    custom = load_principles()
    custom["voice_principles"]["active_tone_bias"] = "متحمس وحيوي"
    custom["visual_principles"]["smart_ducking_volume"] = 0.10

    saved = save_principles(custom)
    assert saved["voice_principles"]["active_tone_bias"] == "متحمس وحيوي"
    assert saved["visual_principles"]["smart_ducking_volume"] == 0.10

    reloaded = load_principles()
    assert reloaded["voice_principles"]["active_tone_bias"] == "متحمس وحيوي"
    assert reloaded["visual_principles"]["smart_ducking_volume"] == 0.10


def test_reset_principles_restores_defaults():
    """Test resetting principles reverts all modifications back to default."""
    custom = load_principles()
    custom["voice_principles"]["active_tone_bias"] = "عصري وجريء"
    save_principles(custom)

    reset_result = reset_principles()
    assert reset_result["voice_principles"]["active_tone_bias"] == "فاخر وهادئ"

    reloaded = load_principles()
    assert reloaded["voice_principles"]["active_tone_bias"] == "فاخر وهادئ"


def test_build_vision_prompt_principles_output():
    """Test vision prompt principles builder produces formatted Arabic markdown instructions."""
    text = build_vision_prompt_principles()
    assert "معايير ومبادئ الصياغة والتسويق العقاري المعتمدة" in text
    assert "قواعد الوصف" in text
    assert "إرشادات نبرة الصوت" in text


def test_build_tts_style_principles_output():
    """Test TTS style prompt incorporates active principles."""
    prompt = build_tts_style_principles(emotional_tone="فاخر وهادئ")
    assert "فاخر وهادئ" in prompt
    assert "تحدث بنبرة عربية فصيحة" in prompt
    assert "الإيقاع" in prompt


def test_master_directive_custom_free_form_instructions():
    """Test user's arbitrary free-form instructions are prioritized in Vision and TTS prompts."""
    custom = load_principles()
    user_instruction = "إستخدم اللهجة الجزائرية و الصوت يجب أن يكون وصفيا مع المشهد كأن الشخص الدي يصور هو من يتكلم"
    custom["master_directive"]["custom_instructions"] = user_instruction
    save_principles(custom)

    vision_prompt = build_vision_prompt_principles()
    assert user_instruction in vision_prompt
    assert "توجيه المستخدم المخصص" in vision_prompt
    assert "الشخص الذي يصور" in vision_prompt
    assert "اللهجة الجزائرية" in vision_prompt

    tts_prompt = build_tts_style_principles(emotional_tone="متحمس وحيوي")
    assert user_instruction in tts_prompt
    assert "جزائرية دارجة" in tts_prompt
    assert "الشخص الذي يتجول ويصور" in tts_prompt


def test_api_get_principles():
    """Test GET /api/principles endpoint returns 200 and valid JSON."""
    client = TestClient(app)
    response = client.get("/api/principles")
    assert response.status_code == 200
    data = response.json()
    assert "master_directive" in data
    assert "voice_principles" in data
    assert "narrative_principles" in data
    assert "visual_principles" in data
    assert "annotation_principles" in data


def test_api_post_principles():
    """Test POST /api/principles endpoint saves user modifications."""
    client = TestClient(app)
    payload = load_principles()
    payload["voice_principles"]["active_tone_bias"] = "عصري وجريء"
    payload["master_directive"]["custom_instructions"] = "دارجة جزائرية حية وعفوية"

    response = client.post("/api/principles", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["principles"]["voice_principles"]["active_tone_bias"] == "عصري وجريء"
    assert data["principles"]["master_directive"]["custom_instructions"] == "دارجة جزائرية حية وعفوية"


def test_api_reset_principles():
    """Test POST /api/principles/reset endpoint restores default principles."""
    client = TestClient(app)
    payload = load_principles()
    payload["voice_principles"]["active_tone_bias"] = "متحمس وحيوي"
    client.post("/api/principles", json=payload)

    reset_resp = client.post("/api/principles/reset")
    assert reset_resp.status_code == 200
    data = reset_resp.json()
    assert data["principles"]["voice_principles"]["active_tone_bias"] == "فاخر وهادئ"
