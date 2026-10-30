#!/usr/bin/env python3
"""
Autonomous Video Montage & Editorial Decision MCP Server & CLI (web/video_montage_mcp.py)
Exposes tools for AI video editing, trimming, shot slicing, and prompt-directed montage.

Author: MouhammedBoure
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure repository root is in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from web.video_editor import (
    probe_video_stream,
    trim_video_clip,
    assemble_shot_segments,
    auto_smart_montage,
    calculate_smart_montage_segments,
)
from frame_extractor import detect_scene_cut_timestamps

logger = logging.getLogger("video_montage_mcp")


MCP_TOOLS_DEFINITIONS = [
    {
        "name": "montage_cut_and_trim",
        "description": "High-performance frame-accurate video trimming, slicing, and multi-segment shot assembly.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "input_video": {"type": "string", "description": "Path to the input video file"},
                "output_video": {"type": "string", "description": "Target path for the exported montage cut"},
                "start_sec": {"type": "number", "description": "Start timestamp in seconds", "default": 0.0},
                "end_sec": {"type": "number", "description": "End timestamp in seconds"},
                "target_duration": {"type": "number", "description": "Target total duration in seconds"},
                "segments": {
                    "type": "array",
                    "description": "List of [start_sec, end_sec] shot segments for multi-clip assembly",
                    "items": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 2,
                        "maxItems": 2
                    }
                },
                "target_width": {"type": "integer", "description": "Target video width (e.g. 1080 or 1920)"},
                "target_height": {"type": "integer", "description": "Target video height (e.g. 1920 or 1080)"}
            },
            "required": ["input_video", "output_video"]
        }
    },
    {
        "name": "smart_ai_montage",
        "description": "Intelligently edits video cuts based on natural language instructions (e.g. 'قص أول 3 ثواني واحتفظ بـ 15 ثانية') or AI scene selection.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "input_video": {"type": "string", "description": "Path to input video file"},
                "output_video": {"type": "string", "description": "Target output path"},
                "prompt": {"type": "string", "description": "Natural language editing directives in Arabic, French, or English"},
                "target_duration": {"type": "number", "description": "Target clip duration in seconds", "default": 15.0},
                "target_width": {"type": "integer", "description": "Target output width"},
                "target_height": {"type": "integer", "description": "Target output height"}
            },
            "required": ["input_video", "output_video"]
        }
    },
    {
        "name": "detect_video_scenes",
        "description": "Detects visual scene transitions and recommends editorial cut points across a video.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "input_video": {"type": "string", "description": "Path to input video"},
                "threshold": {"type": "number", "description": "Scene detection sensitivity threshold", "default": 0.25}
            },
            "required": ["input_video"]
        }
    }
]


def handle_mcp_call(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Execute MCP tool request and return standardized result."""
    if tool_name == "montage_cut_and_trim":
        in_path = arguments.get("input_video")
        out_path = arguments.get("output_video")
        if not in_path or not out_path:
            return {"error": "Both input_video and output_video are required"}

        segments = arguments.get("segments")
        if segments:
            seg_tuples = [(float(s[0]), float(s[1])) for s in segments if len(s) == 2]
            return assemble_shot_segments(
                input_path=in_path,
                output_path=out_path,
                segments=seg_tuples,
                target_w=arguments.get("target_width"),
                target_h=arguments.get("target_height"),
            )
        else:
            return trim_video_clip(
                input_path=in_path,
                output_path=out_path,
                start_sec=float(arguments.get("start_sec", 0.0)),
                end_sec=arguments.get("end_sec"),
                target_duration=arguments.get("target_duration"),
                target_w=arguments.get("target_width"),
                target_h=arguments.get("target_height"),
            )

    elif tool_name == "smart_ai_montage":
        in_path = arguments.get("input_video")
        out_path = arguments.get("output_video")
        prompt = arguments.get("prompt", "")
        target_dur = float(arguments.get("target_duration", 15.0))

        if not in_path or not out_path:
            return {"error": "Both input_video and output_video are required"}

        from web.pipeline_bridge import extract_directives
        dirs = extract_directives(prompt)
        m_plan = dirs.get("montage_plan", {})

        if m_plan.get("trim_start") is not None or m_plan.get("trim_end") is not None:
            return trim_video_clip(
                input_path=in_path,
                output_path=out_path,
                start_sec=float(m_plan.get("trim_start") or 0.0),
                end_sec=m_plan.get("trim_end"),
                target_duration=m_plan.get("target_duration") or target_dur,
                target_w=arguments.get("target_width"),
                target_h=arguments.get("target_height"),
            )
        else:
            eff_dur = m_plan.get("target_duration") or target_dur
            return auto_smart_montage(
                input_path=in_path,
                output_path=out_path,
                target_duration=eff_dur,
                target_w=arguments.get("target_width"),
                target_h=arguments.get("target_height"),
            )

    elif tool_name == "detect_video_scenes":
        in_path = arguments.get("input_video")
        if not in_path:
            return {"error": "input_video is required"}
        threshold = float(arguments.get("threshold", 0.25))

        meta = probe_video_stream(in_path)
        cuts = detect_scene_cut_timestamps(in_path, threshold=threshold)
        return {
            "status": "success",
            "video": in_path,
            "duration": meta["duration"],
            "scene_cuts_count": len(cuts),
            "cut_timestamps": cuts,
        }

    return {"error": f"Unknown tool: {tool_name}"}


def process_mcp_message(req: Dict[str, Any]) -> Dict[str, Any]:
    """Process JSON-RPC message."""
    msg_id = req.get("id")
    method = req.get("method")
    params = req.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "video-montage-server", "version": "1.0.0"}
            }
        }

    if method == "notifications/initialized":
        return {}

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {"tools": MCP_TOOLS_DEFINITIONS}
        }

    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments", {})
        result = handle_mcp_call(name, arguments)
        is_err = "error" in result
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
                "isError": is_err
            }
        }

    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"}
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Video Montage MCP Server & CLI")
    parser.add_argument("--mcp", action="store_true", help="Run in MCP JSON-RPC stdio server mode")
    parser.add_argument("--json-call", type=str, help="Execute direct JSON-RPC call string")
    args = parser.parse_args()

    if args.json_call:
        req = json.loads(args.json_call)
        resp = process_mcp_message(req)
        print(json.dumps(resp, indent=2, ensure_ascii=False))
        return

    if args.mcp or not sys.stdin.isatty():
        for line in sys.stdin:
            line_str = line.strip()
            if not line_str:
                continue
            try:
                req = json.loads(line_str)
                resp = process_mcp_message(req)
                if resp:
                    sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
                    sys.stdout.flush()
            except Exception as exc:
                err_resp = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": f"Parse error: {exc}"}
                }
                sys.stdout.write(json.dumps(err_resp) + "\n")
                sys.stdout.flush()
        return

    parser.print_help()


if __name__ == "__main__":
    main()
