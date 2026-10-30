#!/usr/bin/env python3
"""
Test Suite: AI Video Montage & Smart Editorial Assembly (tests/test_ai_video_montage.py)
Validates prompt intent parsing for video trimming and cutting, FFmpeg assembly,
the dedicated Fast Video Montage MCP server, and pipeline integration.

Author: MouhammedBoure
"""

import json
from pathlib import Path
import pytest
import shutil
import subprocess

from web.pipeline_bridge import extract_directives, parse_montage_directives, process_mobile_video
from web.video_editor import (
    probe_video_stream,
    trim_video_clip,
    assemble_shot_segments,
    calculate_smart_montage_segments,
    auto_smart_montage,
)
from web.video_montage_mcp import process_mcp_message

REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_VIDEO = REPO_ROOT / "inputs" / "source_fox_cub.mp4"


# ---------------------------------------------------------------------------
# 1. Prompt Directive Extraction Tests
# ---------------------------------------------------------------------------

def test_montage_directive_interval_arabic():
    """Verify parsing of Arabic interval trimming prompts."""
    text1 = "قص الفيديو من الثانية 2 إلى 8 واكتب في الأسفل 0558815453"
    dirs1 = extract_directives(text1)
    plan1 = dirs1["montage_plan"]
    assert plan1["requested"] is True
    assert plan1["mode"] == "interval"
    assert plan1["trim_start"] == 2.0
    assert plan1["trim_end"] == 8.0
    assert dirs1["phone_number"] == "0558815453"
    assert dirs1["is_meta_prompt"] is True

    text2 = "اقتطع المشهد من 0:03 الى 0:12 مع تعليق بالدارجة"
    dirs2 = extract_directives(text2)
    plan2 = dirs2["montage_plan"]
    assert plan2["requested"] is True
    assert plan2["trim_start"] == 3.0
    assert plan2["trim_end"] == 12.0
    assert dirs2["darja_requested"] is True


def test_montage_directive_trim_start():
    """Verify parsing of trim start directives."""
    text1 = "قص أول 3 ثواني من الفيديو"
    plan1 = parse_montage_directives(text1)
    assert plan1["requested"] is True
    assert plan1["mode"] == "trim_start"
    assert plan1["trim_start"] == 3.0

    text2 = "احذف بداية 5 ثواني"
    plan2 = parse_montage_directives(text2)
    assert plan2["requested"] is True
    assert plan2["trim_start"] == 5.0


def test_montage_directive_trim_end():
    """Verify parsing of trim end / tail directives."""
    text1 = "قص آخر 4 ثواني من المقطع"
    plan1 = parse_montage_directives(text1)
    assert plan1["requested"] is True
    assert plan1["mode"] == "trim_end"
    assert plan1["trim_end_offset"] == 4.0

    text2 = "احذف آخر 6 ثوانٍ"
    plan2 = parse_montage_directives(text2)
    assert plan2["requested"] is True
    assert plan2["trim_end_offset"] == 6.0


def test_montage_directive_target_duration():
    """Verify parsing of explicit target duration."""
    text1 = "اجعل مدة الفيديو 15 ثانية"
    plan1 = parse_montage_directives(text1)
    assert plan1["requested"] is True
    assert plan1["mode"] == "target_duration"
    assert plan1["target_duration"] == 15.0

    text2 = "احتفظ بـ 12 ثانية فقط"
    plan2 = parse_montage_directives(text2)
    assert plan2["requested"] is True
    assert plan2["target_duration"] == 12.0


def test_montage_directive_smart_montage():
    """Verify parsing of smart highlight montage requests."""
    text1 = "أريد مونتاج ذكي لأفضل المشاهد"
    plan1 = parse_montage_directives(text1)
    assert plan1["requested"] is True
    assert plan1["smart_montage"] is True

    text2 = "قص اللقطات واحتفظ بأجمل اللقطات"
    plan2 = parse_montage_directives(text2)
    assert plan2["requested"] is True
    assert plan2["smart_montage"] is True


def test_montage_directive_multilingual():
    """Verify English and French trimming commands."""
    text_en = "trim from 0:02 to 0:08 and keep 6 seconds"
    plan_en = parse_montage_directives(text_en)
    assert plan_en["requested"] is True
    assert plan_en["trim_start"] == 2.0
    assert plan_en["trim_end"] == 8.0

    text_fr = "couper entre 2 et 7 secondes"
    plan_fr = parse_montage_directives(text_fr)
    assert plan_fr["requested"] is True
    assert plan_fr["trim_start"] == 2.0
    assert plan_fr["trim_end"] == 7.0


# ---------------------------------------------------------------------------
# 2. Video Editor Engine Primitives Tests
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_output_dir(tmp_path):
    d = tmp_path / "montage_test_outputs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def test_video_editor_probe(tmp_output_dir):
    """Verify probing video stream properties."""
    meta = probe_video_stream(SAMPLE_VIDEO)
    assert meta["duration"] > 0.0
    assert meta["width"] == 1280
    assert meta["height"] == 720
    assert meta["codec"] == "h264"
    assert meta["has_audio"] is True


def test_video_editor_trim_clip(tmp_output_dir):
    """Verify trimming a video segment."""
    out_file = tmp_output_dir / "trimmed_fox.mp4"
    res = trim_video_clip(
        input_path=SAMPLE_VIDEO,
        output_path=out_file,
        start_sec=1.5,
        end_sec=5.5,
    )
    assert res["status"] == "success"
    assert out_file.is_file()
    assert out_file.stat().st_size > 1000
    meta = probe_video_stream(out_file)
    assert 3.8 <= meta["duration"] <= 4.2


def test_video_editor_assemble_segments(tmp_output_dir):
    """Verify multi-segment shot assembly."""
    out_file = tmp_output_dir / "assembled_fox.mp4"
    res = assemble_shot_segments(
        input_path=SAMPLE_VIDEO,
        output_path=out_file,
        segments=[(0.5, 2.5), (4.0, 6.0)],
    )
    assert res["status"] == "success"
    assert res["segment_count"] == 2
    assert out_file.is_file()
    meta = probe_video_stream(out_file)
    assert 3.8 <= meta["duration"] <= 4.2


def test_video_editor_calculate_smart_montage_segments():
    """Verify smart segment calculation logic."""
    segments = calculate_smart_montage_segments(
        total_duration=40.0,
        target_duration=12.0,
    )
    assert len(segments) >= 2
    total_calc = sum(en - st for st, en in segments)
    assert 10.0 <= total_calc <= 14.0


# ---------------------------------------------------------------------------
# 3. Video Montage MCP Server Tests
# ---------------------------------------------------------------------------

def test_video_montage_mcp_tools_list():
    """Verify MCP tools/list returns all 3 video montage tools."""
    req = {
        "jsonrpc": "2.0",
        "id": 101,
        "method": "tools/list",
        "params": {}
    }
    resp = process_mcp_message(req)
    assert resp["id"] == 101
    tools = resp["result"]["tools"]
    tool_names = [t["name"] for t in tools]
    assert "montage_cut_and_trim" in tool_names
    assert "smart_ai_montage" in tool_names
    assert "detect_video_scenes" in tool_names


def test_video_montage_mcp_call_trim(tmp_output_dir):
    """Verify MCP tools/call for montage_cut_and_trim."""
    out_file = tmp_output_dir / "mcp_trimmed.mp4"
    req = {
        "jsonrpc": "2.0",
        "id": 102,
        "method": "tools/call",
        "params": {
            "name": "montage_cut_and_trim",
            "arguments": {
                "input_video": str(SAMPLE_VIDEO),
                "output_video": str(out_file),
                "start_sec": 2.0,
                "end_sec": 5.0,
            }
        }
    }
    resp = process_mcp_message(req)
    assert resp["id"] == 102
    assert resp["result"]["isError"] is False
    content_text = resp["result"]["content"][0]["text"]
    result_data = json.loads(content_text)
    assert result_data["status"] == "success"
    assert out_file.is_file()


def test_video_montage_mcp_detect_scenes():
    """Verify MCP tools/call for detect_video_scenes."""
    req = {
        "jsonrpc": "2.0",
        "id": 103,
        "method": "tools/call",
        "params": {
            "name": "detect_video_scenes",
            "arguments": {
                "input_video": str(SAMPLE_VIDEO),
                "threshold": 0.25,
            }
        }
    }
    resp = process_mcp_message(req)
    assert resp["id"] == 103
    content_text = resp["result"]["content"][0]["text"]
    result_data = json.loads(content_text)
    assert result_data["status"] == "success"
    assert "cut_timestamps" in result_data


# ---------------------------------------------------------------------------
# 4. End-to-End Pipeline Integration Test
# ---------------------------------------------------------------------------

def test_pipeline_bridge_with_montage(tmp_output_dir):
    """Verify that process_mobile_video executes prompt-driven montage cleanly."""
    res = process_mobile_video(
        video_path=SAMPLE_VIDEO,
        speech_description="قص من 1.0 إلى 6.0 ثانية واكتب أسفل الفيديو 0661234567",
        voice="ar-XA-Standard-A",
        output_dir=tmp_output_dir,
    )
    assert res["status"] == "completed"
    assert res["montage_applied"] is True
    assert res["montage_details"]["mode"] == "interval_trim"
    assert res["montage_details"]["start_sec"] == 1.0
    assert res["montage_details"]["end_sec"] == 6.0
    assert res["bottom_text"] == "0661234567"
    assert Path(res["output_path"]).is_file()


# ---------------------------------------------------------------------------
# 5. Invariant Test: Zero U+0669 Occurrences
# ---------------------------------------------------------------------------

def test_zero_forbidden_indic_digits():
    """Verify zero occurrences of Arabic-Indic digit 9 (U+0669) across all files."""
    forbidden = "\u0669"
    target_files = [
        REPO_ROOT / "web" / "pipeline_bridge.py",
        REPO_ROOT / "web" / "video_editor.py",
        REPO_ROOT / "web" / "video_montage_mcp.py",
        REPO_ROOT / "web" / "vision_analyzer.py",
        REPO_ROOT / "web" / "server.py",
        REPO_ROOT / "web" / "static" / "app.js",
        REPO_ROOT / "web" / "static" / "index.html",
        REPO_ROOT / "web" / "static" / "style.css",
        Path(__file__),
    ]

    for p in target_files:
        if p.is_file():
            content = p.read_text(encoding="utf-8")
            count = content.count(forbidden)
            assert count == 0, f"Found {count} occurrences of forbidden U+0669 in {p}"
