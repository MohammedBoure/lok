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

OVERLAY_FONTS: List[Dict[str, Any]] = [
    {
        "id": "arial_bold",
        "name_ar": "أريال عريض (واضح وعصري)",
        "name_en": "Arial Bold",
        "sample_ar": "0558 81 54 53 • عرض خاص",
        "candidates": [
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ],
    },
    {
        "id": "tahoma_bold",
        "name_ar": "تاهوما (كلاسيكي للريلز)",
        "name_en": "Tahoma Bold",
        "sample_ar": "0558 81 54 53 • تاهوما",
        "candidates": [
            "C:/Windows/Fonts/tahomabd.ttf",
            "C:/Windows/Fonts/tahoma.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ],
    },
    {
        "id": "segoe_bold",
        "name_ar": "سيغوي ناعم (عصري وخفيف)",
        "name_en": "Segoe UI Bold",
        "sample_ar": "0558 81 54 53 • خط عصري",
        "candidates": [
            "C:/Windows/Fonts/segoeuib.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        ],
    },
    {
        "id": "sakkal_majalla",
        "name_ar": "صقل مجلة (أنيق للعقارات)",
        "name_en": "Sakkal Majalla",
        "sample_ar": "0558 81 54 53 • خط مجلة",
        "candidates": [
            "C:/Windows/Fonts/majallab.ttf",
            "C:/Windows/Fonts/majalla.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
        ],
    },
    {
        "id": "arabic_typesetting",
        "name_ar": "نسخ عربي كلاسيكي (فاخر)",
        "name_en": "Arabic Typesetting",
        "sample_ar": "0558 81 54 53 • خط كلاسيكي",
        "candidates": [
            "C:/Windows/Fonts/arabtype.ttf",
            "C:/Windows/Fonts/trado.ttf",
            "C:/Windows/Fonts/arial.ttf",
        ],
    },
    {
        "id": "simplified_arabic",
        "name_ar": "عربي مبسط (رسمي مرتب)",
        "name_en": "Simplified Arabic",
        "sample_ar": "0558 81 54 53 • عربي مبسط",
        "candidates": [
            "C:/Windows/Fonts/simpo.ttf",
            "C:/Windows/Fonts/trado.ttf",
            "C:/Windows/Fonts/arial.ttf",
        ],
    },
    {
        "id": "times_bold",
        "name_ar": "تايمز عريض (رقمي فخم)",
        "name_en": "Times Bold",
        "sample_ar": "0558 81 54 53 • تايمز",
        "candidates": [
            "C:/Windows/Fonts/timesbd.ttf",
            "C:/Windows/Fonts/times.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        ],
    },
]

OVERLAY_EFFECTS: List[Dict[str, Any]] = [
    {
        "id": "solid_dark",
        "name_ar": "شريط داكن أنيق",
        "name_en": "Dark Pill",
        "description_ar": "خلفية سوداء شفافة واضحة مع ظل خفيف",
        "animated": False,
    },
    {
        "id": "luxury_gold",
        "name_ar": "ذهبي فاخر",
        "name_en": "Luxury Gold",
        "description_ar": "خط ذهبي داخل صندوق داكن مع حدود بارزة",
        "animated": False,
    },
    {
        "id": "clean_outline",
        "name_ar": "نص حر بإطار أسود",
        "name_en": "Clean Outline",
        "description_ar": "نص شفاف بدون خلفية مع إطار أسود واضح",
        "animated": False,
    },
    {
        "id": "neon_glow",
        "name_ar": "توهج نيون سماوي",
        "name_en": "Neon Glow",
        "description_ar": "إضاءة سماوية محيطة للنصوص والأرقام",
        "animated": False,
    },
    {
        "id": "fade_in",
        "name_ar": "ظهور متدرج ناعم",
        "name_en": "Smooth Fade-In",
        "description_ar": "يدخل النص بنعومة في بداية الفيديو",
        "animated": True,
    },
    {
        "id": "pulse_glow",
        "name_ar": "نبض ولفت الانتباه",
        "name_en": "Soft Pulse",
        "description_ar": "توهج متكرر خفيف يلفت النظر لرقم الهاتف",
        "animated": True,
    },
    {
        "id": "slide_up",
        "name_ar": "انزلاق من الأسفل",
        "name_en": "Slide Up",
        "description_ar": "ينزلق النص للأعلى ويستقر في موضعه",
        "animated": True,
    },
    {
        "id": "urgent_red",
        "name_ar": "شارة عرض مميز",
        "name_en": "Promo Badge",
        "description_ar": "شارة حمراء واضحة للأسعار والعروض",
        "animated": False,
    },
]

OVERLAY_COLOR_PRESETS: Dict[str, str] = {
    "default": "",
    "white": "0xFFFFFF",
    "gold": "0xFBBF24",
    "cyan": "0x38BDF8",
    "emerald": "0x34D399",
    "rose": "0xFB7185",
}


def find_system_font() -> Optional[str]:
    """Find an available system TrueType font for FFmpeg drawtext."""
    for font_path in FONT_CANDIDATES:
        if os.path.isfile(font_path):
            return font_path
    return None


def resolve_overlay_font(font_id: Optional[str] = None) -> Dict[str, Any]:
    """Resolve an allowlisted overlay font entry to an existing local TrueType file path."""
    wanted = str(font_id or "").strip().lower()
    entry = next((f for f in OVERLAY_FONTS if f["id"] == wanted), OVERLAY_FONTS[0])
    resolved_file = next((p for p in entry["candidates"] if os.path.isfile(p)), None)
    if not resolved_file:
        resolved_file = find_system_font()
    return {
        "id": entry["id"],
        "name_ar": entry["name_ar"],
        "name_en": entry["name_en"],
        "sample_ar": entry["sample_ar"],
        "file": resolved_file,
    }


def get_overlay_fonts_list() -> List[Dict[str, Any]]:
    """Return available overlay fonts with API preview URLs (without exposing internal paths directly)."""
    items: List[Dict[str, Any]] = []
    for entry in OVERLAY_FONTS:
        resolved = resolve_overlay_font(entry["id"])
        items.append({
            "id": entry["id"],
            "name_ar": entry["name_ar"],
            "name_en": entry["name_en"],
            "sample_ar": entry["sample_ar"],
            "available": bool(resolved.get("file")),
            "font_url": f"/api/overlay-fonts/{entry['id']}/file",
        })
    return items


def get_overlay_effects_list() -> List[Dict[str, Any]]:
    """Return supported visual & animated overlay effects for the placement designer."""
    return [dict(item) for item in OVERLAY_EFFECTS]


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
    effect = str(annotation.get("effect") or "").strip().lower()
    size_key = str(annotation.get("size") or "").strip().lower()
    color_key = str(annotation.get("text_color") or "").strip().lower()

    use_box = 1
    border_w = 0
    border_color = "0x000000@0.85"
    shadow_x = 0
    shadow_y = 0
    shadow_color = "0x000000@0.65"
    alpha_expr: Optional[str] = None
    has_custom_box_or_effect = bool(effect or color_key or size_key in ("small", "medium", "large"))

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
    elif position in ("bottom_banner", "persistent_bottom", "bottom", "custom_xy") or style in ("persistent_bottom", "bottom_box", "phone_overlay"):
        font_color = "white"
        box_color = annotation.get("box_color", "black@0.78")
        boxborderw = int(annotation.get("boxborderw", 16 if is_large else 14))
        if is_large or size_key == "large":
            default_fs = max(48, min(64, int(video_height * 0.042)))
        elif size_key == "small":
            default_fs = max(28, min(38, int(video_height * 0.024)))
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

    # Explicit position preset override if not handled in theme
    if position == "top_banner":
        coord_x = "(w-text_w)/2"
        coord_y = "max(64,h*0.065)"
    elif position == "badge":
        coord_x = "(w-text_w)/2"
        coord_y = "max(68,h*0.07)"
    elif position == "center":
        coord_x = "(w-text_w)/2"
        coord_y = "(h-text_h)/2"

    # Visual & animation effect overrides (preserving legacy behavior when effect is unset)
    if effect == "solid_dark":
        font_color = "0xFFFFFF"
        box_color = "0x09090B@0.80"
        shadow_x, shadow_y = 0, 2
    elif effect == "luxury_gold":
        font_color = "0xFBBF24"
        box_color = "0x111827@0.88"
        border_w = 2
        border_color = "0x000000@0.85"
        shadow_x, shadow_y = 1, 2
    elif effect == "clean_outline":
        use_box = 0
        font_color = "0xFFFFFF"
        border_w = 3
        border_color = "0x000000@0.95"
        shadow_x, shadow_y = 2, 2
        shadow_color = "0x000000@0.80"
    elif effect == "neon_glow":
        use_box = 1
        font_color = "0xE0F2FE"
        box_color = "0x0F172A@0.58"
        border_w = 2
        border_color = "0x0284C7@0.90"
        shadow_x, shadow_y = 0, 0
        shadow_color = "0x38BDF8@0.90"
    elif effect == "fade_in":
        font_color = "0xFFFFFF"
        box_color = "0x09090B@0.78"
        shadow_x, shadow_y = 0, 2
        alpha_expr = f"'min(1\\,(t-{start_sec:.2f})/0.55)'"
    elif effect == "pulse_glow":
        font_color = "0xFFFFFF"
        box_color = "0x09090B@0.82"
        border_w = 2
        border_color = "0xFBBF24@0.85"
        alpha_expr = "'0.76+0.24*sin(2*PI*t/1.8)'"
    elif effect == "slide_up":
        font_color = "0xFFFFFF"
        box_color = "0x09090B@0.82"
        shadow_x, shadow_y = 0, 2
        alpha_expr = f"'min(1\\,(t-{start_sec:.2f})/0.35)'"
    elif effect == "urgent_red":
        font_color = "0xFFFFFF"
        box_color = "0xB91C1C@0.92"
        border_w = 1
        border_color = "0x7F1D1D@0.90"
        shadow_x, shadow_y = 1, 2

    if color_key in OVERLAY_COLOR_PRESETS and OVERLAY_COLOR_PRESETS[color_key]:
        font_color = OVERLAY_COLOR_PRESETS[color_key]
    elif re.fullmatch(r"#?[0-9a-f]{6}", color_key):
        font_color = f"0x{color_key.lstrip('#').upper()}"

    # Custom normalized drag placement (0.0..1.0) clamped safely inside frame boundaries
    raw_xp = annotation.get("x_pct")
    raw_yp = annotation.get("y_pct")
    if raw_xp is not None and raw_yp is not None:
        try:
            xp = max(0.05, min(0.95, float(raw_xp)))
            yp = max(0.05, min(0.95, float(raw_yp)))
            coord_x = f"max(16\\,min(w-text_w-16\\,w*{xp:.4f}-text_w/2))"
            if effect == "slide_up":
                coord_y = (
                    f"max(16\\,min(h-text_h-16\\,"
                    f"(h*{yp:.4f}-text_h/2)+max(0\\,1-(t-{start_sec:.2f})/0.50)*48))"
                )
            else:
                coord_y = f"max(16\\,min(h-text_h-16\\,h*{yp:.4f}-text_h/2))"
        except (TypeError, ValueError):
            pass
    elif effect == "slide_up":
        coord_y = f"({coord_y})+max(0\\,1-(t-{start_sec:.2f})/0.50)*48"

    filter_parts = [
        f"text='{escaped_text}'",
        f"fontsize={font_size}",
        f"fontcolor={font_color}",
        f"box={use_box}",
    ]
    if use_box:
        filter_parts.append(f"boxcolor={box_color}")
        filter_parts.append(f"boxborderw={boxborderw}")
    if border_w > 0:
        filter_parts.append(f"borderw={border_w}")
        filter_parts.append(f"bordercolor={border_color}")
    if shadow_x or shadow_y or effect == "neon_glow":
        filter_parts.append(f"shadowx={shadow_x}")
        filter_parts.append(f"shadowy={shadow_y}")
        filter_parts.append(f"shadowcolor={shadow_color}")
    if alpha_expr:
        filter_parts.append(f"alpha={alpha_expr}")
    if has_custom_box_or_effect or (raw_xp is not None and raw_yp is not None):
        filter_parts.append("fix_bounds=1")

    filter_parts.extend([
        f"x={coord_x}",
        f"y={coord_y}",
    ])

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

    # Optional animated caption track (.ass rendered by libass) burned on top of drawtext overlays
    ass_file = kwargs.get("ass_file") or kwargs.get("captions_ass")
    ass_path: Optional[Path] = Path(ass_file).resolve() if ass_file else None
    if ass_path is not None and not ass_path.is_file():
        ass_path = None

    valid_annotations = [a for a in (annotations or []) if isinstance(a, dict) and str(a.get("text", "")).strip()]
    if not valid_annotations and ass_path is None:
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

    default_font_file = find_system_font()
    filters = []
    for a in valid_annotations:
        ann_font_id = a.get("font_id") or a.get("font")
        ann_font_file = resolve_overlay_font(ann_font_id)["file"] if ann_font_id else default_font_file
        filters.append(_build_drawtext_filter(a, font_file=ann_font_file, video_width=vw, video_height=vh))
    run_cwd: Optional[str] = None
    if ass_path is not None:
        # Run FFmpeg from the subtitle directory so the filter argument needs no path escaping
        run_cwd = str(ass_path.parent)
        filters.append(f"ass=filename={ass_path.name}")
    filter_chain = ",".join(filters)

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
        res = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace", check=True, cwd=run_cwd,
        )
        return {
            "status": "ok",
            "annotations_applied": len(valid_annotations),
            "captions_applied": ass_path is not None,
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
