"""
Tests for Video Annotations & Fast MCP Tool (tests/test_video_annotation_mcp.py)

Author: MouhammedBoure <mohamadbormoz2@gmail.com>
Role: Testing, Verification & Gatekeepers (agy101)
Branch: test/agy101-video-annotation-mcp-verification
"""

import json
from pathlib import Path
import pytest
from starlette.testclient import TestClient

from web.video_annotator import escape_ffmpeg_drawtext, annotate_video
from web.video_annotator_mcp import handle_mcp_call, process_mcp_message, MCP_TOOL_DEFINITION
from web.server import app


def test_escape_ffmpeg_drawtext():
    """Test escaping special characters for FFmpeg drawtext filter syntax."""
    raw = "سعر: 25,000 دج / 100% 'فاخر' [مميز]"
    escaped = escape_ffmpeg_drawtext(raw)
    assert "\\:" in escaped
    assert "\\'" in escaped
    assert "\\%" in escaped


def test_mcp_tool_definition():
    """Test MCP tool specification compliance with JSON-RPC schemas."""
    assert MCP_TOOL_DEFINITION["name"] == "annotate_video_cut"
    schema = MCP_TOOL_DEFINITION["inputSchema"]
    assert "input_video" in schema["properties"]
    assert "output_video" in schema["properties"]
    assert "annotations" in schema["properties"]


def test_handle_mcp_call_tools_list():
    """Test MCP server returns tool definitions upon tools/list request."""
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {},
    }
    response = process_mcp_message(request)
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 1
    assert "tools" in response["result"]
    tool_names = [t["name"] for t in response["result"]["tools"]]
    assert "annotate_video_cut" in tool_names


def test_handle_mcp_call_missing_input_file():
    """Test MCP tool returns informative error when input video does not exist."""
    request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "annotate_video_cut",
            "arguments": {
                "input_video": "non_existent_video_path.mp4",
                "output_video": "output.mp4",
                "annotations": [{"text": "عقار فاخر"}],
            },
        },
    }
    response = process_mcp_message(request)
    assert response["result"]["isError"] is True
    content = response["result"]["content"][0]["text"]
    assert "not found" in content.lower()


def test_api_video_annotate_validation_error():
    """Test REST endpoint /api/video/annotate validates payload and missing files."""
    client = TestClient(app)
    # Missing input_video
    resp = client.post("/api/video/annotate", json={"annotations": []})
    assert resp.status_code == 400

    # Non-existent input file
    resp = client.post("/api/video/annotate", json={
        "input_video": "does_not_exist.mp4",
        "output_video": "out.mp4",
        "annotations": [{"text": "مرحباً"}],
    })
    assert resp.status_code == 404
