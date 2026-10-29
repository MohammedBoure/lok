#!/usr/bin/env python3
"""
Video Annotator & Visual Overlay Engine.
Applies lower-third banners, price tags, and architectural highlight captions
onto video cuts using fast hardware-accelerated FFmpeg filtergraphs.

Author: MohammedBoure
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

# Standard fallback font paths on Linux
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
]


def find_system_font() -> Optional[str]:
    """Find an available system TrueType font for FFmpeg drawtext."""
    for font_path in FONT_CANDIDATES:
        if os.path.isfile(font_path):
            return font_path
    return None


def escape_ffmpeg_drawtext(text: str) -> str:
    """
    Escape text for FFmpeg drawtext filter syntax.
    Escapes colons, backslashes, single quotes, and percent signs.
    """
    escaped = text.replace("\\", "\\\\")
    escaped = escaped.replace("'", "'\\''")
    escaped = escaped.replace(":", "\\:")
    escaped = escaped.replace("%", "\\%")
    return escaped


def _build_drawtext_filter(
    annotation: Dict[str, Any],
    font_file: Optional[str] = None,
    video_width: int = 1080,
    video_height: int = 1920
) -> str:
    """Build a single FFmpeg drawtext filter string for an annotation."""
    text = annotation.get("text", "").strip()
    escaped_text = escape_ffmpeg_drawtext(text)
    start_sec = max(0.0, float(annotation.get("start_sec", 0.0)))
    raw_end = annotation.get("end_sec")
    end_sec = max(start_sec + 0.5, float(raw_end)) if raw_end is not None else None
    position = str(annotation.get("position", "lower_third")).lower()
    style = str(annotation.get("style", "luxury_gold")).lower()
    font_size = int(annotation.get("font_size", 36))
    boxborderw = int(annotation.get("boxborderw", 12))
    is_persistent = bool(annotation.get("persistent") or annotation.get("is_persistent") or style == "persistent_bottom")

    # Color themes
    if style in ("persistent_bottom", "bottom_box", "phone_overlay"):
        font_color = "white"
        box_color = "black@0.6"
        boxborderw = int(annotation.get("boxborderw", 8))
        font_size = int(annotation.get("font_size", 28))
    elif style == "emerald_badge":
        font_color = "0x10B981"
        box_color = "0x064E3B@0.85"
    elif style == "price_tag":
        font_color = "0xF59E0B"
        box_color = "0x1E1B4B@0.88"
    elif style == "modern_white":
        font_color = "0xFFFFFF"
        box_color = "0x0F172A@0.80"
    elif style == "commercial_red":
        font_color = "0xFFFFFF"
        box_color = "0xDC2626@0.90"
    else:  # luxury_gold
        font_color = "0xFBBF24"
        box_color = "0x18181B@0.85"

    # Positioning coordinates
    if position in ("bottom_banner", "persistent_bottom", "bottom") or style in ("persistent_bottom", "bottom_box", "phone_overlay"):
        coord_x = "(w-text_w)/2"
        coord_y = "h-text_h-40"
    elif position == "top_banner":
        coord_x = "(w-text_w)/2"
        coord_y = "60"
    elif position == "badge":
        coord_x = "40"
        coord_y = "50"
    elif position == "center":
        coord_x = "(w-text_w)/2"
        coord_y = "(h-text_h)/2"
    else:  # lower_third (default)
        coord_x = "(w-text_w)/2"
        coord_y = "h*0.75"

    filter_parts = [
        f"text='{escaped_text}'",
        f"fontsize={font_size}",
        f"fontcolor={font_color}",
        f"box=1",
        f"boxcolor={box_color}",
        f"boxborderw={boxborderw}",
        f"x={coord_x}",
        f"y={coord_y}",
    ]

    if end_sec is not None:
        filter_parts.append(f"enable='between(t,{start_sec:.2f},{end_sec:.2f})'")
    elif start_sec > 0:
        filter_parts.append(f"enable='gte(t,{start_sec:.2f})'")

    if font_file:
        filter_parts.append(f"fontfile='{font_file}'")

    return "drawtext=" + ":".join(filter_parts)


def annotate_video(
    input_video_path: str | Path | None = None,
    output_video_path: str | Path | None = None,
    annotations: Optional[List[Dict[str, Any]]] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Apply text annotations onto a video via FFmpeg drawtext filters.
    If no annotations are supplied, copies input to output.
    """
    src_path = input_video_path or kwargs.get("input_video")
    dst_path = output_video_path or kwargs.get("output_video")
    if not src_path or not dst_path:
        raise ValueError("Both input_video and output_video must be specified.")

    input_path = Path(src_path).resolve()
    output_path = Path(dst_path).resolve()

    if not input_path.is_file():
        raise FileNotFoundError(f"Input video not found: {input_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    valid_annotations = [a for a in annotations if isinstance(a, dict) and a.get("text", "").strip()]
    if not valid_annotations:
        shutil.copy2(input_path, output_path)
        return {
            "status": "ok",
            "annotations_applied": 0,
            "output_video": str(output_path),
            "message": "No annotations provided; stream copied directly."
        }

    font_file = find_system_font()
    filter_chain = ",".join(
        _build_drawtext_filter(a, font_file=font_file) for a in valid_annotations
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-vf", filter_chain,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "22",
        "-c:a", "copy",
        "-movflags", "+faststart",
        str(output_path)
    ]

    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return {
            "status": "ok",
            "annotations_applied": len(valid_annotations),
            "output_video": str(output_path),
            "filtergraph": filter_chain
        }
    except subprocess.CalledProcessError as exc:
        # Fallback to direct copy if drawtext fails (e.g. font missing or filter issue)
        shutil.copy2(input_path, output_path)
        return {
            "status": "warning",
            "annotations_applied": 0,
            "output_video": str(output_path),
            "error": exc.stderr,
            "message": "FFmpeg filter failed; fell back to original video without annotations."
        }
