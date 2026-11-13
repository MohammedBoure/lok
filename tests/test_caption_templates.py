#!/usr/bin/env python3
"""
Tests for CapCut-style Animated Caption Templates & Smart Text Splitting Engine.
"""

from __future__ import annotations

from pathlib import Path
from starlette.testclient import TestClient

from web.caption_templates import (
    CAPTION_TEMPLATES,
    assign_timings,
    build_ass_document,
    heuristic_split,
    list_caption_templates,
    prepare_caption_track,
    smart_split_text,
)
from web.server import app


def test_all_seven_templates_registered():
    expected = {
        "karaoke_highlight",
        "pop_bounce",
        "typewriter",
        "fade_slide_up",
        "box_caption",
        "bold_outline",
        "single_word",
    }
    assert set(CAPTION_TEMPLATES.keys()) == expected
    catalog = list_caption_templates()
    assert len(catalog) == 7


def test_smart_heuristic_split_preserves_words_and_numbers():
    sample = "أفضل بيتزا في المدينة، توصيل سريع لباب الدار! اتصل الآن 0558815453 واستمتع بعرض خاص اليوم"
    chunks = heuristic_split(sample, max_words=4)
    assert len(chunks) >= 3
    reconstructed = " ".join(c["text"] for c in chunks)
    assert reconstructed.split() == sample.split()
    # Phone number must remain intact inside a single chunk
    assert any("0558815453" in c["text"] for c in chunks)


def test_assign_timings_and_ass_generation_for_all_templates(tmp_path: Path):
    sample = "أفضل عرض خاص اليوم، جودة عالية وتوصيل سريع لكل الولايات"
    split_res = smart_split_text(sample, template="karaoke_highlight", duration=10.0, use_ai=False)
    timed = assign_timings(split_res["chunks"], total_duration=10.0)
    assert len(timed) == len(split_res["chunks"])
    assert timed[0]["start_sec"] >= 0.0
    assert timed[-1]["end_sec"] <= 10.0

    for tpl in CAPTION_TEMPLATES:
        ass_doc = build_ass_document(timed, template=tpl, video_width=1080, video_height=1920)
        assert "[V4+ Styles]" in ass_doc
        assert "Dialogue:" in ass_doc
        # Verify Encoding=-1 for libass FriBidi RTL auto-direction
        assert ",-1\n" in ass_doc

    meta = prepare_caption_track(
        tmp_path / "captions.ass",
        total_duration=10.0,
        video_width=1080,
        video_height=1920,
        template="box_caption",
        custom_text=sample,
        use_ai=False,
    )
    assert meta is not None
    assert Path(meta["ass_path"]).is_file()
    assert meta["template"] == "box_caption"
    assert meta["chunks_count"] >= 2


def test_caption_templates_and_split_endpoints():
    client = TestClient(app)
    resp_tpl = client.get("/api/captions/templates")
    assert resp_tpl.status_code == 200
    data_tpl = resp_tpl.json()
    assert data_tpl["status"] == "ok"
    assert len(data_tpl["templates"]) == 7

    resp_split = client.post(
        "/api/captions/split",
        json={
            "text": "أفضل قهوة مختصة في الجزائر، مذاق أصيل وخدمة سريعة يومياً",
            "template": "pop_bounce",
            "duration": 12.0,
        },
    )
    assert resp_split.status_code == 200
    data_split = resp_split.json()
    assert data_split["status"] == "ok"
    assert data_split["template"] == "pop_bounce"
    assert len(data_split["chunks"]) >= 2

