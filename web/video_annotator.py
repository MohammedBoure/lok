#!/usr/bin/env python3
"""
Video Annotator & Visual Overlay Engine.
Applies lower-third banners, price tags, and architectural highlight captions
onto video cuts using fast hardware-accelerated FFmpeg filtergraphs.

Author: MouhammedBoure
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

# Cross-platform fallback font paths (Windows + Linux + macOS) supporting Arabic & Latin scripts
FONT_CANDIDATES = [
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/tahomabd.ttf",
    "C:/Windows/Fonts/tahoma.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
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


def wrap_annotation_text(text: str, max_chars_per_line: int = 38) -> str:
    """
    Wrap long text onto multiple balanced lines so it never overflows horizontal video bounds.
    Preserves short phrases on a single line.
    """
    raw = str(text or "").strip()
    if not raw or len(raw) <= max_chars_per_line or "\n" in raw:
        return raw

    words = raw.split()
    if len(words) <= 1:
        return raw

    lines: List[str] = []
    current_words: List[str] = []
    current_len = 0

    for w in words:
        w_len = len(w)
        if current_words and (current_len + 1 + w_len > max_chars_per_line):
            lines.append(" ".join(current_words))
            current_words = [w]
            current_len = w_len
        else:
            current_words.append(w)
            current_len = current_len + (1 if current_len > 0 else 0) + w_len

    if current_words:
        lines.append(" ".join(current_words))

    return "\n".join(lines[:3])


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


def _escape_ffmpeg_fontfile_path(font_path: str) -> str:
    """Escape Windows drive colons and backslashes in fontfile path for FFmpeg filter syntax."""
    norm = font_path.replace("\\", "/")
    return norm.replace(":", "\\:")


def _build_drawtext_filter(
    annotation: Dict[str, Any],
    font_file: Optional[str] = None,
    video_width: int = 1080,
    video_height: int = 1920
) -> str:
    """Build a single FFmpeg drawtext filter string for an annotation."""
    raw_text = annotation.get("text", "").strip()
    max_line_chars = 34 if video_width <= 1080 else 46
    wrapped_text = wrap_annotation_text(raw_text, max_chars_per_line=max_line_chars) if annotation.get("wrap", True) else raw_text
    escaped_text = escape_ffmpeg_drawtext(wrapped_text)
    start_sec = max(0.0, float(annotation.get("start_sec", 0.0)))
    raw_end = annotation.get("end_sec")
    end_sec = max(start_sec + 0.5, float(raw_end)) if raw_end is not None else None
    position = str(annotation.get("position", "lower_third")).lower()
    style = str(annotation.get("style", "luxury_gold")).lower()
    font_size = int(annotation.get("font_size", 36))
    boxborderw = int(annotation.get("boxborderw", 12))
    is_persistent = bool(annotation.get("persistent") or annotation.get("is_persistent") or style == "persistent_bottom")
    is_large = bool(annotation.get("large_font"))

    # Color themes and positioning
    if position in ("subtitle", "captions") or style in ("subtitle", "caption", "synchronized_caption"):
        font_color = "white"
        box_color = annotation.get("box_color", "black@0.72")
        boxborderw = int(annotation.get("boxborderw", 10))
        if is_large:
            default_fs = max(40, min(54, int(video_height * 0.035)))
        elif "font_size" in annotation:
            default_fs = int(annotation["font_size"])
        else:
            default_fs = max(30, min(42, int(video_height * 0.026)))
        font_size = default_fs
        coord_x = "(w-text_w)/2"
        # Subtitles sit cleanly elevated above the persistent bottom badge
        safe_margin = int(annotation.get("safe_margin", max(185, int(video_height * 0.145))))
        coord_y = f"h-text_h-{safe_margin}"
    elif position in ("bottom_banner", "persistent_bottom", "bottom") or style in ("persistent_bottom", "bottom_box", "phone_overlay"):
        font_color = "white"
        box_color = annotation.get("box_color", "black@0.78")
        boxborderw = int(annotation.get("boxborderw", 16 if is_large else 14))
        if is_large:
            default_fs = max(48, min(64, int(video_height * 0.042)))
        elif "font_size" in annotation:
            default_fs = int(annotation["font_size"])
        else:
            default_fs = max(38, min(50, int(video_height * 0.034)))
        font_size = default_fs
        coord_x = "(w-text_w)/2"
        # Safe margin to keep text clearly elevated above player controls, timeline, and mobile UI bars
        safe_margin = int(annotation.get("safe_margin", max(110, int(video_height * 0.085))))
        coord_y = f"h-text_h-{safe_margin}"
    elif style == "emerald_badge":
        font_color = "0xECFDF5"
        box_color = "0x064E3B@0.88"
        boxborderw = int(annotation.get("boxborderw", 14))
        coord_x = "(w-text_w)/2"
        coord_y = "h*0.72"
    elif style == "price_tag":
        font_color = "0xFEF3C7"
        box_color = "0x1E1B4B@0.90"
        boxborderw = int(annotation.get("boxborderw", 14))
        coord_x = "(w-text_w)/2"
        coord_y = "h*0.72"
    elif style == "modern_white":
        font_color = "0xFFFFFF"
        box_color = "0x0F172A@0.84"
        boxborderw = int(annotation.get("boxborderw", 14))
        coord_x = "(w-text_w)/2"
        coord_y = "h*0.75"
    elif style == "commercial_red":
        font_color = "0xFFFFFF"
        box_color = "0xB91C1C@0.90"
        boxborderw = int(annotation.get("boxborderw", 14))
        coord_x = "(w-text_w)/2"
        coord_y = "h*0.75"
    elif style == "highlight_badge":
        font_color = "0xF8FAFC"
        box_color = "0x09090B@0.82"
        boxborderw = int(annotation.get("boxborderw", 12))
        font_size = int(annotation.get("font_size", max(30, min(42, int(video_height * 0.025)))))
        coord_x = "(w-text_w)/2"
        coord_y = "max(68,h*0.07)"
    else:  # luxury_gold
        font_color = "0xFBBF24"
        box_color = "0x18181B@0.86"
        boxborderw = int(annotation.get("boxborderw", 14))
        coord_x = "(w-text_w)/2"
        coord_y = "h*0.75"

    # Explicit position override if not handled in theme
    if position == "top_banner":
        coord_x = "(w-text_w)/2"
        coord_y = "max(64,h*0.065)"
    elif position == "badge":
        coord_x = "(w-text_w)/2"
        coord_y = "max(68,h*0.07)"
    elif position == "center":
        coord_x = "(w-text_w)/2"
        coord_y = "(h-text_h)/2"

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
        escaped_font = _escape_ffmpeg_fontfile_path(font_file)
        filter_parts.append(f"fontfile='{escaped_font}'")

    return "drawtext=" + ":".join(filter_parts)


def annotate_video(
    input_video_path: str | Path | None = None,
    output_video_path: str | Path | None = None,
    annotations: Optional[List[Dict[str, Any]]] = None,
    video_width: Optional[int] = None,
    video_height: Optional[int] = None,
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

    vw = int(video_width or kwargs.get("width") or 0)
    vh = int(video_height or kwargs.get("height") or 0)
    if vw <= 0 or vh <= 0:
        try:
            probe_cmd = [
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height",
                "-of", "csv=s=x:p=0",
                str(input_path),
            ]
            res = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
            parts = res.stdout.strip().split("x")
            if len(parts) == 2:
                vw = int(parts[0])
                vh = int(parts[1])
        except Exception:
            vw = 1080
            vh = 1920

    font_file = find_system_font()
    filter_chain = ",".join(
        _build_drawtext_filter(a, font_file=font_file, video_width=vw, video_height=vh)
        for a in valid_annotations
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-vf", filter_chain,
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "23",
        "-threads", "0",
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
