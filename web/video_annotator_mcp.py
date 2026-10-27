#!/usr/bin/env python3
"""
Video Annotator Fast MCP Server & CLI.
Exposes 'annotate_video_cut' MCP tool for rapid visual overlays, badges,
lower-third titles, and price stamps on video cuts.

Author: MohammedBoure
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from web.video_annotator import annotate_video

MCP_TOOL_DEFINITION = {
    "name": "annotate_video_cut",
    "description": "Fast hardware-accelerated video annotation tool to overlay titles, lower-third tags, prices, and marketing captions onto MP4 video files.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "input_video": {
                "type": "string",
                "description": "Absolute or relative path to the source MP4 video"
            },
            "output_video": {
                "type": "string",
                "description": "Target destination path for the annotated video output"
            },
            "annotations": {
                "type": "array",
                "description": "List of annotation dictionaries with text, timestamps, position, and style",
                "items": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Text caption to display"},
                        "start_sec": {"type": "number", "description": "Timestamp in seconds when text appears"},
                        "end_sec": {"type": "number", "description": "Timestamp in seconds when text disappears"},
                        "position": {
                            "type": "string",
                            "enum": ["lower_third", "top_banner", "bottom_banner", "center"],
                            "default": "lower_third"
                        },
                        "style": {
                            "type": "string",
                            "enum": ["luxury_gold", "emerald_badge", "modern_white", "price_tag"],
                            "default": "luxury_gold"
                        },
                        "font_size": {"type": "integer", "default": 36}
                    },
                    "required": ["text"]
                }
            }
        },
        "required": ["input_video", "output_video", "annotations"]
    }
}


def handle_mcp_call(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Execute MCP tool request and return standardized result."""
    if tool_name != "annotate_video_cut":
        return {"error": f"Unknown tool: {tool_name}"}

    input_video = arguments.get("input_video")
    output_video = arguments.get("output_video")
    annotations = arguments.get("annotations", [])

    if not input_video or not output_video:
        return {"error": "Both input_video and output_video are required"}

    try:
        res = annotate_video(input_video, output_video, annotations)
        return res
    except Exception as exc:
        return {"error": str(exc)}


def process_mcp_message(req: Dict[str, Any]) -> Dict[str, Any]:
    """Process a single MCP JSON-RPC message and return the JSON-RPC response."""
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
                "serverInfo": {"name": "video-annotator-mcp", "version": "1.0.0"}
            }
        }
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {"tools": [MCP_TOOL_DEFINITION]}
        }
    elif method == "tools/call":
        tool_name = params.get("name")
        args = params.get("arguments", {})
        call_res = handle_mcp_call(tool_name, args)
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "content": [{"type": "text", "text": json.dumps(call_res, ensure_ascii=False)}],
                "isError": "error" in call_res
            }
        }
    else:
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"}
        }


def run_stdio_mcp_server() -> None:
    """Run lightweight JSON-RPC MCP server over stdin/stdout."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue

        resp = process_mcp_message(req)
        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()


def main() -> None:
    parser = argparse.ArgumentParser(description="Video Annotator MCP Server & CLI Tool")
    parser.add_argument("--mcp", action="store_true", help="Run as stdio MCP server")
    parser.add_argument("--input", "-i", type=str, help="Input video file path")
    parser.add_argument("--output", "-o", type=str, help="Output video file path")
    parser.add_argument("--text", "-t", type=str, help="Single annotation text")
    parser.add_argument("--start", type=float, default=0.0, help="Start time in seconds")
    parser.add_argument("--end", type=float, default=4.0, help="End time in seconds")
    parser.add_argument("--style", default="luxury_gold", help="Visual style")
    parser.add_argument("--position", default="lower_third", help="Position on screen")
    args = parser.parse_args()

    if args.mcp:
        run_stdio_mcp_server()
        return

    if not args.input or not args.output:
        parser.print_help()
        sys.exit(1)

    ann = []
    if args.text:
        ann.append({
            "text": args.text,
            "start_sec": args.start,
            "end_sec": args.end,
            "style": args.style,
            "position": args.position
        })

    result = annotate_video(args.input, args.output, ann)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
