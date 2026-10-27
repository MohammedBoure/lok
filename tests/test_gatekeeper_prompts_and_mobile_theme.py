#!/usr/bin/env python3
"""
Comprehensive Integration Test Suite for SQLite Prompt Descriptions & Mobile Principles Theme
(tests/test_gatekeeper_prompts_and_mobile_theme.py)

Gatekeeper: agy100
Author: MohammedBoure
Branch: test/agy100-prompts-sqlite-and-mobile-theme-gatekeeper
Scope: SQLite CRUD operations, REST API endpoints, Multimodal linguistic intent conversion,
       automatic prompt recording during video job processing, and mobile frontend assets.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Generator

import pytest
from starlette.testclient import TestClient

from web import prompt_db
from web.pipeline_bridge import ALGERIAN_REAL_ESTATE_PRESETS, process_mobile_video
from web.server import app
from web.vision_analyzer import _get_smart_fallback, infer_video_script_and_mood

REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = REPO_ROOT / "web" / "static"

client = TestClient(app)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def isolated_db(tmp_path: Path) -> Path:
    """Provide an isolated SQLite database file path."""
    return tmp_path / "gatekeeper_prompts.db"


@pytest.fixture(scope="session")
def dummy_video(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Generate a lightweight 1.5s MP4 video fixture for API processing."""
    tmp_dir = tmp_path_factory.mktemp("gatekeeper_videos")
    video_file = tmp_dir / "gatekeeper_sample.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=duration=1.5:size=320x240:rate=15",
        "-c:v", "libx264", "-preset", "ultrafast",
        str(video_file),
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return video_file


# ---------------------------------------------------------------------------
# 1. SQLite CRUD Operations in web/prompt_db.py
# ---------------------------------------------------------------------------

def test_sqlite_auto_seed(isolated_db: Path):
    """Verify that an uninitialized SQLite DB auto-seeds default Algerian real estate prompts."""
    # Ensure file does not exist initially
    assert not isolated_db.exists()

    # Calling get_recent_prompts triggers init_db and auto-seeding
    prompts = prompt_db.get_recent_prompts(limit=10, db_path=isolated_db)
    assert len(prompts) >= 3, f"Expected at least 3 auto-seeded prompts, found {len(prompts)}"

    # Validate essential fields in preseeded items
    for p in prompts:
        assert p["id"] > 0
        assert p["title"]
        assert p["visual_description"]
        assert p["speech_description"]
        assert p["inferred_script"]
        assert p["created_at"]
        meta = json.loads(p["metadata"]) if p["metadata"] else {}
        assert isinstance(meta, dict)


def test_sqlite_save_and_get_prompt(isolated_db: Path):
    """Verify save_prompt inserts record and get_prompt_by_id retrieves accurate fields."""
    v_desc = "صالون فسيح بإطلالة بحرية مفتوحة ومطبخ أمريكي رخامي"
    s_desc = "التركيز على الفخامة والهدوء والتشطيبات العصرية الفائقة"
    script = "شوفو معايا هاد الصالون الرائع بإطلالة ساحرة ومطبخ عصري مجهز بالكامل."
    title = "شقة ديلوكس وهران"
    metadata = {"property_type": "apartment", "city": "وهران", "featured": True}

    prompt_id = prompt_db.save_prompt(
        visual_description=v_desc,
        speech_description=s_desc,
        inferred_script=script,
        title=title,
        metadata=metadata,
        db_path=isolated_db,
    )
    assert isinstance(prompt_id, int)
    assert prompt_id > 0

    record = prompt_db.get_prompt_by_id(prompt_id, db_path=isolated_db)
    assert record is not None
    assert record["id"] == prompt_id
    assert record["title"] == title
    assert record["visual_description"] == v_desc
    assert record["speech_description"] == s_desc
    assert record["inferred_script"] == script

    parsed_meta = json.loads(record["metadata"])
    assert parsed_meta["city"] == "وهران"
    assert parsed_meta["featured"] is True


def test_sqlite_get_recent_prompts_ordering(isolated_db: Path):
    """Verify get_recent_prompts returns records in descending order of ID respecting limits."""
    # Seed base
    prompt_db.init_db(isolated_db)

    # Insert two distinct records
    id1 = prompt_db.save_prompt(
        visual_description="غرفة معيشة مضيئة",
        speech_description="الراحة والسكينة",
        title="عقار أ",
        db_path=isolated_db,
    )
    id2 = prompt_db.save_prompt(
        visual_description="تراس بانورامي خارجي",
        speech_description="الإطلالة الحصرية",
        title="عقار ب",
        db_path=isolated_db,
    )

    recents = prompt_db.get_recent_prompts(limit=2, db_path=isolated_db)
    assert len(recents) == 2
    assert recents[0]["id"] == id2
    assert recents[1]["id"] == id1


def test_sqlite_update_prompt_script(isolated_db: Path):
    """Verify update_prompt_script modifies inferred_script properly."""
    pid = prompt_db.save_prompt(
        visual_description="حديقة خاصة ومسبح",
        speech_description="الرفاهية العائلية",
        title="فيلا خاصة",
        db_path=isolated_db,
    )

    # Initial inferred_script is None
    record = prompt_db.get_prompt_by_id(pid, db_path=isolated_db)
    assert record["inferred_script"] is None

    # Update script
    updated = prompt_db.update_prompt_script(
        prompt_id=pid,
        inferred_script="فيلا خاصة مميزة بمسبح وحديقة خضراء عائلية هادئة.",
        db_path=isolated_db,
    )
    assert updated is True

    record_after = prompt_db.get_prompt_by_id(pid, db_path=isolated_db)
    assert record_after["inferred_script"] == "فيلا خاصة مميزة بمسبح وحديقة خضراء عائلية هادئة."

    # Update non-existent record
    assert prompt_db.update_prompt_script(999999, "نص وهمي", db_path=isolated_db) is False


def test_sqlite_delete_prompt(isolated_db: Path):
    """Verify delete_prompt removes the row and handles non-existent IDs."""
    pid = prompt_db.save_prompt(
        visual_description="مكتب تجاري واسع",
        speech_description="الموقع الاستثماري",
        title="مكتب بالعاصمة",
        db_path=isolated_db,
    )
    assert prompt_db.get_prompt_by_id(pid, db_path=isolated_db) is not None

    # Delete
    del_ok = prompt_db.delete_prompt(pid, db_path=isolated_db)
    assert del_ok is True
    assert prompt_db.get_prompt_by_id(pid, db_path=isolated_db) is None

    # Delete again
    del_again = prompt_db.delete_prompt(pid, db_path=isolated_db)
    assert del_again is False


# ---------------------------------------------------------------------------
# 2. REST API Endpoints Verification
# ---------------------------------------------------------------------------

def test_api_prompts_history_endpoint():
    """Verify GET /api/prompts/history returns 200 and a list of prompts."""
    res = client.get("/api/prompts/history")
    assert res.status_code == 200
    data = res.json()
    assert data.get("status") == "ok"
    assert "prompts" in data
    assert isinstance(data["prompts"], list)
    assert len(data["prompts"]) >= 3

    first = data["prompts"][0]
    assert "id" in first
    assert "title" in first
    assert "visual_description" in first
    assert "speech_description" in first


def test_api_prompts_crud_lifecycle():
    """Verify POST /api/prompts creates prompt and DELETE /api/prompts/{id} deletes it."""
    payload = {
        "title": "شقة دوبلكس حيدرة",
        "visual_description": "صالون كبير بتشطيبات عصرية وإضاءة ليد مخفية",
        "speech_description": "تسليط الضوء على هدوء الحي الدبلوماسي وجودة السكن",
        "inferred_script": "مرحباً بكم في حيدرة، دوبلكس عصري فخم يوفر أرقى مستويات الراحة.",
        "metadata": {"zone": "Hydra", "level": 2},
    }

    # 1. POST
    post_res = client.post("/api/prompts", json=payload)
    assert post_res.status_code == 200
    post_json = post_res.json()
    assert post_json.get("status") == "ok"
    created_id = post_json.get("id")
    assert isinstance(created_id, int) and created_id > 0
    assert post_json["prompt"]["title"] == "شقة دوبلكس حيدرة"

    # 2. Check presence in history
    hist_res = client.get("/api/prompts/history?limit=10")
    assert hist_res.status_code == 200
    prompts = hist_res.json()["prompts"]
    matching = [p for p in prompts if p["id"] == created_id]
    assert len(matching) == 1
    assert matching[0]["speech_description"] == payload["speech_description"]

    # 3. DELETE
    del_res = client.delete(f"/api/prompts/{created_id}")
    assert del_res.status_code == 200
    del_json = del_res.json()
    assert del_json.get("status") == "ok"
    assert del_json.get("deleted") is True

    # 4. DELETE again -> 404
    del_res_repeat = client.delete(f"/api/prompts/{created_id}")
    assert del_res_repeat.status_code == 404
    assert del_res_repeat.json().get("deleted") is False


# ---------------------------------------------------------------------------
# 3. Linguistic Speech & Visual Intent Descriptions in Vision Analyzer & Pipeline
# ---------------------------------------------------------------------------

def test_linguistic_speech_intent_conversion_to_narrative():
    """Verify that speech_description intent is converted into a full narrative script."""
    speech_intent = "التركيز على الفخامة والسكينة وقرب المرافق التجارية"
    visual_intent = "شقة فاخرة، صالون ملكي رخامي، مطبخ عصري مجهز"

    result = _get_smart_fallback(
        duration=12.0,
        preset_hint=None,
        speech_description=speech_intent,
        visual_description=visual_intent,
    )

    script = result.get("script", "")
    assert len(script) > 20
    # The speech intent must be woven naturally into the generated narrative
    assert "الفخامة" in script or "المرافق" in script or "السكينة" in script

    # Visual description must guide highlights / lower-third badges
    highlights = result.get("highlights", [])
    assert len(highlights) >= 1
    combined_badges = " ".join(highlights)
    assert any(term in combined_badges for term in ["صالون", "مطبخ", "شقة"])


def test_visual_intent_badges_extraction():
    """Verify that visual_description phrases are extracted as badge highlights."""
    visual_desc = "مسبح إنفينيتي خاص، إطلالة بحرية بانورامية، صالون إيطالي رخامي"
    result = _get_smart_fallback(
        duration=10.0,
        preset_hint="oran_seaview_villa",
        speech_description=None,
        visual_description=visual_desc,
    )
    badges = result.get("highlights", [])
    assert len(badges) >= 2
    badges_str = " ".join(badges)
    assert "مسبح" in badges_str or "إطلالة" in badges_str or "صالون" in badges_str


def test_automatic_prompt_recording_upon_video_job(dummy_video: Path):
    """Verify that submitting a video job automatically records prompt history in SQLite."""
    v_desc = "شرفة فسيحة بإطلالة خضراء على الحديقة"
    s_desc = "التشديد على نقاء الهواء والهدوء التام"

    with open(dummy_video, "rb") as vid_file:
        res = client.post(
            "/api/jobs/create",
            files={"video": ("gatekeeper_test.mp4", vid_file, "video/mp4")},
            data={
                "visual_description": v_desc,
                "speech_description": s_desc,
                "auto_mode": "true",
            },
        )

    assert res.status_code == 202
    job_info = res.json()
    assert job_info.get("status") == "processing"
    assert "job_id" in job_info
    prompt_id = job_info.get("prompt_id")
    assert prompt_id is not None
    assert isinstance(prompt_id, int) and prompt_id > 0

    # Retrieve from SQLite prompt_db to verify persistence
    saved_prompt = prompt_db.get_prompt_by_id(prompt_id)
    assert saved_prompt is not None
    assert saved_prompt["visual_description"] == v_desc
    assert saved_prompt["speech_description"] == s_desc
    assert saved_prompt["id"] == prompt_id


# ---------------------------------------------------------------------------
# 4. Frontend Mobile Assets & Theme Verification
# ---------------------------------------------------------------------------

def test_frontend_html_mobile_modal_and_prompt_elements():
    """Check web/static/index.html contains mobile modal structure, prompt textareas, dropdown/chips, and save button."""
    index_html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")

    # Mobile Principles Modal Structure
    assert 'id="principlesModal"' in index_html
    assert 'class="modal-card modal-principles-card"' in index_html
    assert 'class="modal-body principles-modal-body"' in index_html
    assert 'id="btnClosePrinciples"' in index_html
    assert 'id="btnSavePrinciples"' in index_html
    assert 'id="btnResetPrinciples"' in index_html

    # Linguistic Video & Speech Description Textareas
    assert 'id="visualDescription"' in index_html
    assert 'name="visual_description"' in index_html
    assert 'id="speechDescription"' in index_html
    assert 'name="speech_description"' in index_html

    # Prompt History Restoration Dropdown, Chips, and Save/Clear Buttons
    assert 'id="promptHistorySelect"' in index_html
    assert 'id="promptHistoryChips"' in index_html
    assert 'id="btnRefreshPromptHistory"' in index_html
    assert 'id="btnSavePrompt"' in index_html
    assert 'id="btnClearPrompts"' in index_html

    # Primary Action Buttons
    assert 'id="btnProduce"' in index_html
    assert 'id="submitBtn"' in index_html


def test_frontend_css_responsive_rules_and_modal_sizing():
    """Check web/static/style.css has responsive rules (max-width: 768px, 480px), touch scrolling, and modal sizing."""
    style_css = (STATIC_DIR / "style.css").read_text(encoding="utf-8")

    # Responsive Media Query Breakpoints
    assert "@media (max-width: 768px)" in style_css
    assert "@media (max-width: 480px)" in style_css

    # Touch scrolling
    assert "-webkit-overflow-scrolling: touch" in style_css

    # Modal Viewport Sizing
    assert ".modal-principles-card" in style_css
    assert "max-height: 88vh" in style_css or "max-height: 89vh" in style_css or "max-height: 90vh" in style_css
    assert ".principles-modal-body" in style_css


def test_frontend_app_js_prompts_history_and_formdata_bindings():
    """Check web/static/app.js handles prompt loading, restoration, saving, and FormData population."""
    app_js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")

    # Prompt loading & rendering
    assert "fetchPromptHistory" in app_js
    assert "renderPromptHistory" in app_js

    # Prompt restoration & saving
    assert "restorePrompt" in app_js
    assert "saveCurrentPrompt" in app_js
    assert "promptHistorySelect" in app_js
    assert "btnSavePrompt" in app_js

    # FormData population
    assert 'formData.append("visual_description"' in app_js
    assert 'formData.append("speech_description"' in app_js

    # Handlers for both #submitBtn and #btnProduce
    assert "btnProduce" in app_js
    assert "submitBtn" in app_js
    assert 'dom.btnProduce.addEventListener("click", handleProduceProduction)' in app_js
    assert 'dom.submitBtn.addEventListener("click", handleProduceProduction)' in app_js


def test_no_forbidden_arabic_character_compliance():
    """Ensure character mapping rule: Arabic numeral ٩ (U+0669) does not appear in test suite or deliverables."""
    for fname in ["index.html", "style.css", "app.js"]:
        content = (STATIC_DIR / fname).read_text(encoding="utf-8")
        assert "\u0669" not in content, f"Forbidden Arabic numeral U+0669 detected in {fname}"
