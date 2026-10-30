#!/usr/bin/env python3
"""
Test Suite for SQLite Prompt Descriptions Persistence & Linguistic Agent Integration
(tests/test_prompt_descriptions_and_agent.py)

Author: MouhammedBoure
Role: Backend Architecture & Systems Engineer (agy11)
Branch: backend/agy11-sqlite-prompt-descriptions-and-agent
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
import tempfile
from pathlib import Path
from typing import Generator

import pytest
from starlette.testclient import TestClient

from web import prompt_db
from web.pipeline_bridge import process_mobile_video
from web.server import app
from web.vision_analyzer import _get_smart_fallback, infer_video_script_and_mood

client = TestClient(app)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_db(tmp_path: Path) -> Path:
    """Fixture providing an isolated SQLite database path."""
    db_file = tmp_path / "prompts_test.db"
    return db_file


@pytest.fixture(scope="session")
def sample_test_video(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Generate a lightweight 2.0s MP4 test video for API ingestion tests."""
    tmp_dir = tmp_path_factory.mktemp("prompt_test_videos")
    video_path = tmp_dir / "quick_sample.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=duration=2:size=320x240:rate=15",
        "-c:v", "libx264", "-preset", "ultrafast",
        "-t", "2.0",
        str(video_path),
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return video_path


# ---------------------------------------------------------------------------
# Unit Tests: SQLite Prompt DB Layer
# ---------------------------------------------------------------------------

def test_prompt_db_preseed(temp_db: Path):
    """Test that SQLite DB initializes with 2-3 realistic Algerian real estate prompts."""
    prompts = prompt_db.get_recent_prompts(limit=10, db_path=temp_db)
    assert len(prompts) == 3, f"Expected 3 pre-seeded items, found {len(prompts)}"

    titles = [p["title"] for p in prompts]
    assert any("وهران" in t or "فيلا" in t for t in titles)
    assert any("سيدي يحيى" in t or "بنتهاوس" in t for t in titles)
    assert any("قسنطينة" in t or "تجاري" in t for t in titles)

    for p in prompts:
        assert p["visual_description"]
        assert p["speech_description"]
        assert p["inferred_script"]
        meta = json.loads(p["metadata"])
        assert isinstance(meta, dict)


def test_save_and_fetch_prompt(temp_db: Path):
    """Test inserting a new prompt and fetching it by ID."""
    row_id = prompt_db.save_prompt(
        visual_description="صالون عصري فسيح مطل على البحر",
        speech_description="التركيز على الراحة والإطلالة البانورامية الهادئة",
        inferred_script="شوفو معايا هاد الصالون الرائع بإطلالة ولا أروع على البحر.",
        title="شقة مطلة على البحر",
        metadata={"property_type": "apartment", "city": "Algiers"},
        db_path=temp_db,
    )
    assert row_id > 3

    fetched = prompt_db.get_prompt_by_id(row_id, db_path=temp_db)
    assert fetched is not None
    assert fetched["id"] == row_id
    assert fetched["title"] == "شقة مطلة على البحر"
    assert fetched["visual_description"] == "صالون عصري فسيح مطل على البحر"
    assert fetched["speech_description"] == "التركيز على الراحة والإطلالة البانورامية الهادئة"
    assert fetched["inferred_script"] == "شوفو معايا هاد الصالون الرائع بإطلالة ولا أروع على البحر."
    assert "apartment" in fetched["metadata"]


def test_delete_prompt(temp_db: Path):
    """Test deleting prompt record by ID."""
    row_id = prompt_db.save_prompt(
        visual_description="حديقة واسعة",
        speech_description="التركيز على المساحات الخضراء",
        title="فيلا بحديقة",
        db_path=temp_db,
    )
    assert prompt_db.get_prompt_by_id(row_id, db_path=temp_db) is not None

    deleted = prompt_db.delete_prompt(row_id, db_path=temp_db)
    assert deleted is True
    assert prompt_db.get_prompt_by_id(row_id, db_path=temp_db) is None

    # Deleting non-existent row should return False
    assert prompt_db.delete_prompt(99999, db_path=temp_db) is False


def test_update_prompt_script(temp_db: Path):
    """Test updating inferred_script for an existing prompt."""
    row_id = prompt_db.save_prompt(
        visual_description="مطبخ إيطالي فاخر",
        speech_description="التركيز على الفخامة والتجهيزات الحديثة",
        title="مطبخ عصري",
        db_path=temp_db,
    )
    initial = prompt_db.get_prompt_by_id(row_id, db_path=temp_db)
    assert initial["inferred_script"] is None

    updated = prompt_db.update_prompt_script(
        prompt_id=row_id,
        inferred_script="مطبخ مجهز بالكامل بأحدث الأجهزة الإيطالية العصرية.",
        db_path=temp_db,
    )
    assert updated is True

    after = prompt_db.get_prompt_by_id(row_id, db_path=temp_db)
    assert after["inferred_script"] == "مطبخ مجهز بالكامل بأحدث الأجهزة الإيطالية العصرية."


# ---------------------------------------------------------------------------
# API Tests: REST Endpoints
# ---------------------------------------------------------------------------

def test_api_prompts_history():
    """Test GET /api/prompts/history endpoint."""
    resp = client.get("/api/prompts/history")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert isinstance(data["prompts"], list)
    assert len(data["prompts"]) >= 3


def test_api_prompts_post_and_delete():
    """Test POST /api/prompts and DELETE /api/prompts/{id} REST endpoints."""
    payload = {
        "title": "فيلا شاطئية",
        "visual_description": "مسبح إنفينيتي وواجهة بحرية ساحرة",
        "speech_description": "تسليط الضوء على هدوء الشاطئ والفخامة الصيفية",
        "inferred_script": "عش تجربة الفخامة الصيفية أمام البحر مباشرة.",
        "metadata": {"test": True},
    }
    post_res = client.post("/api/prompts", json=payload)
    assert post_res.status_code == 200
    post_data = post_res.json()
    assert post_data["status"] == "ok"
    prompt_id = post_data["id"]
    assert prompt_id > 0
    assert post_data["prompt"]["title"] == "فيلا شاطئية"

    # Verify presence in history
    hist_res = client.get("/api/prompts/history?limit=10")
    assert hist_res.status_code == 200
    prompts_list = hist_res.json()["prompts"]
    assert any(p["id"] == prompt_id for p in prompts_list)

    # Delete prompt
    del_res = client.delete(f"/api/prompts/{prompt_id}")
    assert del_res.status_code == 200
    del_data = del_res.json()
    assert del_data["status"] == "ok"
    assert del_data["deleted"] is True

    # Deleting again returns 404
    del_404 = client.delete(f"/api/prompts/{prompt_id}")
    assert del_404.status_code == 404
    assert del_404.json()["deleted"] is False


def test_api_jobs_create_with_descriptions(sample_test_video: Path):
    """Test POST /api/jobs/create accepts visual & speech descriptions and auto-saves to prompt_db."""
    with open(sample_test_video, "rb") as f_vid:
        resp = client.post(
            "/api/jobs/create",
            files={"video": ("test_clip.mp4", f_vid, "video/mp4")},
            data={
                "visual_description": "شرفة واسعة بإطلالة جبلية",
                "speech_description": "التركيز على الهواء النقي والهدوء",
                "auto_mode": "true",
            },
        )
    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "processing"
    assert "job_id" in data
    assert data.get("prompt_id") is not None

    # Check that prompt_id exists in prompt_db
    p = prompt_db.get_prompt_by_id(data["prompt_id"])
    assert p is not None
    assert p["visual_description"] == "شرفة واسعة بإطلالة جبلية"
    assert p["speech_description"] == "التركيز على الهواء النقي والهدوء"


# ---------------------------------------------------------------------------
# Unit Tests: Linguistic Intent Guidance in Vision Analyzer
# ---------------------------------------------------------------------------

def test_smart_fallback_linguistic_speech_intent():
    """Test that vision analyzer fallback transforms speech_description intent into Darja script."""
    fallback = _get_smart_fallback(
        duration=8.0,
        preset_hint=None,
        speech_description="التركيز على الفخامة والسكينة وقرب المرافق التجارية",
        visual_description="شقة فاخرة، صالون ملكي رخامي، مطبخ عصري مجهز",
    )
    assert fallback["script"]
    # Intent should be woven naturally into the script
    assert "الفخامة" in fallback["script"] or "المرافق" in fallback["script"]
    # Visual description should steer highlights
    assert len(fallback["highlights"]) >= 1
    assert any("صالون" in h or "مطبخ" in h or "شقة" in h for h in fallback["highlights"])


def test_smart_fallback_visual_intent_badges():
    """Test that visual_description phrases are extracted as lower-third badges in fallback mode."""
    fallback = _get_smart_fallback(
        duration=10.0,
        preset_hint="oran_seaview_villa",
        visual_description="مسبح خاص واسع، إطلالة بحرية بانورامية، صالون تركي رخامي",
    )
    assert len(fallback["highlights"]) >= 2
    badges_str = " ".join(fallback["highlights"])
    assert "مسبح" in badges_str or "إطلالة" in badges_str or "صالون" in badges_str
