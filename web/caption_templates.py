#!/usr/bin/env python3
"""
Animated Caption Templates Engine (CapCut-style custom text).

The customer types free text; this module:
  1. Splits it smartly into short on-screen caption chunks (Gemini when an API key
     is configured, otherwise a punctuation/connector-aware heuristic splitter).
  2. Assigns reading-speed based timings across the video (snapped to shot cuts),
     plus per-word timings inside every chunk (no speech recognition involved).
  3. Renders the chunks into an Advanced SubStation Alpha (.ass) document using one
     of the animated templates below, which FFmpeg burns in through libass
     (proper Arabic shaping + RTL, outlines, boxes, karaoke, scale/fade/move).
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

logger = logging.getLogger("lok.captions")

# ---------------------------------------------------------------------------
# Template catalogue
# ---------------------------------------------------------------------------

CAPTION_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "karaoke_highlight": {
        "name_ar": "كاريوكي مُبرز",
        "name_en": "Karaoke Highlight",
        "description_ar": "الكلمة الحالية تُضاء باللون الأصفر بينما تبقى البقية بيضاء",
        "max_words": 4,
        "default_position": "bottom",
        "size_factor": 1.0,
        "accent": "FFD700",
    },
    "pop_bounce": {
        "name_ar": "نطّة مرحة",
        "name_en": "Pop / Bounce",
        "description_ar": "كل جملة تقفز بحركة تكبير مرنة مع إبراز الكلمة المهمة",
        "max_words": 3,
        "default_position": "center",
        "size_factor": 1.15,
        "accent": "FFE135",
    },
    "typewriter": {
        "name_ar": "آلة كاتبة",
        "name_en": "Typewriter",
        "description_ar": "النص يظهر تدريجياً كأنه يُكتب أمامك",
        "max_words": 6,
        "default_position": "bottom",
        "size_factor": 0.85,
        "accent": "7DF9FF",
    },
    "fade_slide_up": {
        "name_ar": "ظهور منزلق",
        "name_en": "Fade + Slide Up",
        "description_ar": "النص يظهر بتلاشٍ ناعم مع انزلاق خفيف للأعلى",
        "max_words": 6,
        "default_position": "bottom",
        "size_factor": 0.9,
        "accent": "FFFFFF",
    },
    "box_caption": {
        "name_ar": "صندوق تيك توك",
        "name_en": "Box Caption",
        "description_ar": "نص أبيض عريض داخل صندوق داكن مع إبراز الكلمة الحالية",
        "max_words": 5,
        "default_position": "bottom",
        "size_factor": 0.85,
        "accent": "3DFF8B",
    },
    "bold_outline": {
        "name_ar": "خط عريض بإطار",
        "name_en": "Bold Outline",
        "description_ar": "خط أبيض كبير بإطار أسود سميك وظل، مثالي للعناوين",
        "max_words": 3,
        "default_position": "center",
        "size_factor": 1.2,
        "accent": "FFD700",
    },
    "single_word": {
        "name_ar": "كلمة بكلمة",
        "name_en": "Single Word",
        "description_ar": "كلمة واحدة كبيرة في كل مرة بأسلوب الريلز",
        "max_words": 3,
        "default_position": "center",
        "size_factor": 1.55,
        "accent": "FFD700",
    },
}

DEFAULT_TEMPLATE = "karaoke_highlight"
VALID_POSITIONS = ("top", "center", "bottom")
SIZE_FACTORS = {"small": 0.8, "medium": 1.0, "large": 1.25}

_ARABIC_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]")
_DIGIT_RE = re.compile(r"\d")  # unicode-aware: Latin + Arabic-Indic digits
_SENTENCE_END_RE = re.compile(r"(?<=[.!?\u061F\u2026])\s+")
_CLAUSE_PUNCT = ("\u060C", ",", "\u061B", ";", ":")

# Words that naturally start a new phrase (break *before* them)
_CONNECTORS = {
    "\u062B\u0645", "\u0644\u0643\u0646", "\u0645\u0639", "\u0641\u064A", "\u0639\u0644\u0649",
    "\u0645\u0646", "\u0625\u0644\u0649", "\u0627\u0644\u0649", "\u0623\u0648", "\u0627\u0648",
    "\u062D\u062A\u0649", "\u0644\u0623\u0646", "\u0644\u0627\u0646", "\u0628\u0627\u0634",
    "\u0628\u0635\u062D", "\u0648\u0644\u0643\u0646", "\u0639\u0646\u062F", "\u0628\u0644",
    "\u0627\u0644\u0644\u064A", "\u0627\u0644\u0630\u064A", "\u0627\u0644\u062A\u064A",
    "and", "but", "with", "for", "to", "or", "because", "so", "then", "et", "mais", "avec", "pour",
}


def normalize_template(template: Optional[str]) -> str:
    key = str(template or "").strip().lower().replace("-", "_").replace(" ", "_")
    return key if key in CAPTION_TEMPLATES else DEFAULT_TEMPLATE


def normalize_position(position: Optional[str], template: str) -> str:
    pos = str(position or "").strip().lower()
    aliases = {"middle": "center", "centre": "center", "auto": "", "default": ""}
    pos = aliases.get(pos, pos)
    if pos in VALID_POSITIONS:
        return pos
    return CAPTION_TEMPLATES[normalize_template(template)]["default_position"]


def normalize_size(size: Optional[str]) -> str:
    s = str(size or "").strip().lower()
    return s if s in SIZE_FACTORS else "medium"


def list_caption_templates() -> List[Dict[str, Any]]:
    return [
        {
            "id": key,
            "name_ar": meta["name_ar"],
            "name_en": meta["name_en"],
            "description_ar": meta["description_ar"],
            "default_position": meta["default_position"],
            "max_words": meta["max_words"],
        }
        for key, meta in CAPTION_TEMPLATES.items()
    ]


# ---------------------------------------------------------------------------
# Smart splitting
# ---------------------------------------------------------------------------

def _clean_text(text: str) -> str:
    raw = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    raw = raw.replace("{", "(").replace("}", ")").replace("\\", "/")
    lines = [re.sub(r"[ \t\u00A0]+", " ", ln).strip() for ln in raw.split("\n")]
    return "\n".join(ln for ln in lines if ln)


def _is_numberish(word: str) -> bool:
    return bool(_DIGIT_RE.search(word))


def _bare(word: str) -> str:
    return re.sub(r"[^\w\u0600-\u06FF]", "", word).lower()


def _pick_emphasis(words: Sequence[str]) -> Optional[str]:
    if not words:
        return None
    for w in words:
        if _is_numberish(w):
            return w
    candidates = [w for w in words if len(_bare(w)) >= 4 and _bare(w) not in _CONNECTORS]
    if not candidates:
        return None
    return max(candidates, key=lambda w: len(_bare(w)))


def _balanced_split(words: List[str], max_words: int) -> List[List[str]]:
    """Split a long clause into balanced chunks, preferring breaks before connectors."""
    if len(words) <= max_words:
        return [words]
    n_chunks = math.ceil(len(words) / max_words)
    chunks: List[List[str]] = []
    start = 0
    remaining_chunks = n_chunks
    while start < len(words):
        remaining_words = len(words) - start
        if remaining_chunks <= 1 or remaining_words <= max_words:
            chunks.append(words[start:])
            break
        target = start + math.ceil(remaining_words / remaining_chunks)
        best = target
        best_score = None
        for cut in range(max(start + 1, target - 1), min(len(words), start + max_words) + 1):
            if cut >= len(words):
                continue
            score = abs(cut - target)
            nxt_raw = words[cut]
            nxt = _bare(nxt_raw)
            prev = words[cut - 1]
            if nxt in _CONNECTORS:
                score -= 1.5
            elif nxt_raw.startswith("\u0648") and len(nxt) >= 5:
                score -= 0.75  # likely a "wa-" conjunction starting a new phrase
            if _is_numberish(prev) and not _is_numberish(nxt_raw):
                score -= 0.75  # a number usually closes its phrase
            if _is_numberish(prev) and _is_numberish(nxt_raw):
                score += 5  # keep number groups together
            if best_score is None or score < best_score:
                best, best_score = cut, score
        chunks.append(words[start:best])
        start = best
        remaining_chunks -= 1
    return [c for c in chunks if c]


def heuristic_split(text: str, max_words: int = 4) -> List[Dict[str, Any]]:
    """Punctuation + connector aware splitting used when AI is unavailable."""
    cleaned = _clean_text(text)
    if not cleaned:
        return []
    chunks: List[Dict[str, Any]] = []
    for line in cleaned.split("\n"):
        for sentence in _SENTENCE_END_RE.split(line):
            sentence = sentence.strip()
            if not sentence:
                continue
            clauses: List[List[str]] = []
            current: List[str] = []
            for word in sentence.split():
                current.append(word)
                if word.endswith(_CLAUSE_PUNCT):
                    clauses.append(current)
                    current = []
            if current:
                clauses.append(current)
            # merge tiny clauses with the next one when they fit
            merged: List[List[str]] = []
            for cl in clauses:
                if merged and len(merged[-1]) == 1 and len(merged[-1]) + len(cl) <= max_words:
                    merged[-1] = merged[-1] + cl
                else:
                    merged.append(cl)
            for cl in merged:
                for part in _balanced_split(cl, max_words):
                    chunks.append({"text": " ".join(part), "emphasis": _pick_emphasis(part)})
    return chunks


def _gemini_api_key() -> Optional[str]:
    for var in ("GEMINI_API_KEY", "GEMINI_API_KEYS"):
        raw = os.getenv(var) or ""
        for item in raw.split(","):
            val = item.strip().strip("\"'")
            if val:
                return val
    return None


def ai_split(text: str, max_words: int, template: str, duration: float) -> Optional[List[Dict[str, Any]]]:
    """Ask Gemini to split the text into caption chunks. Returns None on any failure."""
    api_key = _gemini_api_key()
    cleaned = _clean_text(text)
    if not api_key or not cleaned:
        return None
    try:
        import requests
    except Exception:
        return None

    prompt = (
        "You are a professional short-form video caption editor (CapCut / TikTok / Reels style).\n"
        "Split the on-screen TEXT below into caption chunks that will appear one after another on a phone screen.\n"
        "Strict rules:\n"
        "- Do NOT change, translate, correct, add, remove or reorder any word. Copy the exact original words and punctuation.\n"
        f"- Each chunk has 1 to {max_words} words and is a natural meaning unit that reads well on its own.\n"
        "- Never split a number, phone number, price, date, brand or person name across two chunks.\n"
        "- Prefer breaking at punctuation and before connectors (and, with, but, \u0648\u0644\u0643\u0646, \u0645\u0639, \u062B\u0645 ...).\n"
        "- For every chunk choose at most ONE emphasis word (the most impactful word, copied exactly) or null.\n"
        f"Video duration: {duration:.1f} seconds. Visual template: {template}.\n"
        'Return ONLY JSON: {"chunks": [{"text": "...", "emphasis": "..." }]}\n'
        "TEXT:\n<<<\n" + cleaned + "\n>>>"
    )
    env_models = os.getenv("GEMINI_CAPTION_MODELS")
    models = [m.strip() for m in env_models.split(",") if m.strip()] if env_models else ["gemini-3.6-flash", "gemini-3-flash-preview"]
    original_tokens = cleaned.split()

    for model in models[:2]:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            body = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
            }
            resp = requests.post(url, json=body, timeout=(5.0, 15.0))
            if resp.status_code != 200:
                logger.info("Caption AI split: model %s returned HTTP %s", model, resp.status_code)
                continue
            data = resp.json()
            raw = data["candidates"][0]["content"]["parts"][0].get("text", "").strip()
            raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
            raw = re.sub(r"\s*```$", "", raw)
            parsed = json.loads(raw)
            items = parsed.get("chunks") if isinstance(parsed, dict) else parsed
            if not isinstance(items, list) or not items:
                continue
            chunks: List[Dict[str, Any]] = []
            for it in items:
                if isinstance(it, str):
                    it = {"text": it}
                txt = re.sub(r"\s+", " ", str(it.get("text", ""))).strip()
                if not txt:
                    continue
                emph = it.get("emphasis")
                emph = str(emph).strip() if emph else None
                if emph and emph not in txt.split():
                    emph = None
                chunks.append({"text": txt, "emphasis": emph})
            produced_tokens = " ".join(c["text"] for c in chunks).split()
            if produced_tokens != original_tokens:
                logger.info("Caption AI split rejected (words were altered); using heuristic splitter.")
                return None
            # Enforce a hard ceiling on chunk length even if the model ignored it
            final: List[Dict[str, Any]] = []
            for c in chunks:
                words = c["text"].split()
                if len(words) <= max_words + 1:
                    final.append(c)
                else:
                    for part in _balanced_split(words, max_words):
                        emph = c["emphasis"] if c["emphasis"] in part else _pick_emphasis(part)
                        final.append({"text": " ".join(part), "emphasis": emph})
            return final
        except Exception as exc:
            logger.info("Caption AI split failed on %s: %s", model, exc)
            continue
    return None


def smart_split_text(
    text: str,
    template: str = DEFAULT_TEMPLATE,
    duration: float = 15.0,
    use_ai: bool = True,
) -> Dict[str, Any]:
    """Split customer text into caption chunks (AI first, heuristic fallback)."""
    tpl = normalize_template(template)
    max_words = int(CAPTION_TEMPLATES[tpl]["max_words"])
    chunks = ai_split(text, max_words, tpl, duration) if use_ai else None
    engine = "gemini"
    if not chunks:
        chunks = heuristic_split(text, max_words)
        engine = "heuristic"
    return {"chunks": chunks, "engine": engine, "template": tpl}


# ---------------------------------------------------------------------------
# Timing
# ---------------------------------------------------------------------------

def _reading_seconds(text: str) -> float:
    chars = len(text.replace(" ", ""))
    words = len(text.split())
    return max(0.9, min(4.0, 0.45 + chars * 0.065 + words * 0.08))


def _word_timings(words: List[str], start: float, end: float) -> List[Dict[str, Any]]:
    weights = [len(_bare(w)) + 2 for w in words]
    total_w = float(sum(weights)) or 1.0
    span = max(0.1, end - start)
    out: List[Dict[str, Any]] = []
    cursor = start
    for w, wt in zip(words, weights):
        dur = span * (wt / total_w)
        out.append({"word": w, "start_sec": round(cursor, 3), "end_sec": round(cursor + dur, 3)})
        cursor += dur
    if out:
        out[-1]["end_sec"] = round(end, 3)
    return out


def _snap_to_shots(t: float, cuts: Sequence[float], tolerance: float = 0.45) -> float:
    best = t
    best_d = tolerance
    for c in cuts:
        d = abs(c - t)
        if d < best_d:
            best, best_d = c, d
    return best


def assign_timings(
    chunks: List[Dict[str, Any]],
    total_duration: float,
    start_offset: float = 0.3,
    end_padding: float = 0.3,
    shot_timeline: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Distribute chunks across the video using reading speed, snapping starts to shot cuts."""
    if not chunks:
        return []
    window_start = max(0.0, start_offset)
    window_end = max(window_start + 1.0, total_duration - end_padding)
    window = window_end - window_start

    natural = [_reading_seconds(c["text"]) for c in chunks]
    total_natural = sum(natural)

    if total_natural >= window:
        scale = window / total_natural
        durations = [d * scale for d in natural]
        gap = 0.0
    else:
        stretch = min(1.6, window / total_natural)
        durations = [d * stretch for d in natural]
        leftover = window - sum(durations)
        gap = leftover / max(1, len(chunks))

    cuts: List[float] = []
    for shot in shot_timeline or []:
        try:
            cuts.append(float(shot.get("start_sec", 0.0)))
        except Exception:
            continue

    timed: List[Dict[str, Any]] = []
    cursor = window_start
    for i, (c, dur) in enumerate(zip(chunks, durations)):
        st = cursor
        if gap > 0.2 and cuts:
            snapped = _snap_to_shots(st, cuts)
            if timed and snapped < timed[-1]["end_sec"]:
                snapped = st
            st = snapped
        et = min(window_end, st + dur)
        if et - st < 0.4:
            et = min(total_duration, st + 0.4)
        words = c["text"].split()
        timed.append({
            "text": c["text"],
            "emphasis": c.get("emphasis"),
            "start_sec": round(st, 3),
            "end_sec": round(et, 3),
            "words": _word_timings(words, st, et),
        })
        cursor = et + gap
    return timed


def segments_to_timed_chunks(segments: List[Dict[str, Any]], total_duration: float) -> List[Dict[str, Any]]:
    """Convert already-timed subtitle segments (e.g. narration captions) into timed chunks."""
    out: List[Dict[str, Any]] = []
    for seg in segments or []:
        txt = _clean_text(str(seg.get("text", ""))).replace("\n", " ").strip()
        if not txt:
            continue
        try:
            st = max(0.0, float(seg.get("start_sec", 0.0)))
            et = min(total_duration, float(seg.get("end_sec", st + 2.0)))
        except Exception:
            continue
        if et <= st:
            continue
        words = txt.split()
        out.append({
            "text": txt,
            "emphasis": _pick_emphasis(words),
            "start_sec": round(st, 3),
            "end_sec": round(et, 3),
            "words": _word_timings(words, st, et),
        })
    return out


# ---------------------------------------------------------------------------
# ASS rendering
# ---------------------------------------------------------------------------

def _ass_color(hex_rgb: str, alpha: int = 0) -> str:
    h = hex_rgb.lstrip("#")
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H{alpha:02X}{b}{g}{r}".upper()


def _inline_color(hex_rgb: str) -> str:
    h = hex_rgb.lstrip("#")
    return f"&H{h[4:6]}{h[2:4]}{h[0:2]}&".upper()


def _ass_time(t: float) -> str:
    t = max(0.0, t)
    cs = int(round(t * 100))
    h, rem = divmod(cs, 360000)
    m, rem = divmod(rem, 6000)
    s, cs = divmod(rem, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _ass_escape(text: str) -> str:
    return text.replace("\\", "/").replace("{", "(").replace("}", ")").replace("\n", " ")


def font_family_for_ass(font_path: Optional[str] = None) -> str:
    name = Path(font_path).stem.lower() if font_path else ""
    if "tahoma" in name:
        return "Tahoma"
    if "segoe" in name:
        return "Segoe UI"
    if "dejavu" in name:
        return "DejaVu Sans"
    if "noto" in name:
        return "Noto Sans Arabic"
    if "liberation" in name:
        return "Liberation Sans"
    if "freesans" in name:
        return "FreeSans"
    return "Arial"


def _anchor(position: str) -> int:
    return {"top": 8, "center": 5, "bottom": 2}.get(position, 2)


def _anchor_xy(position: str, w: int, h: int, margin_v: int) -> tuple:
    if position == "top":
        return w // 2, margin_v
    if position == "center":
        return w // 2, h // 2
    return w // 2, h - margin_v


def build_ass_document(
    timed_chunks: List[Dict[str, Any]],
    template: str = DEFAULT_TEMPLATE,
    video_width: int = 1080,
    video_height: int = 1920,
    position: Optional[str] = None,
    size: Optional[str] = None,
    font_name: Optional[str] = None,
) -> str:
    """Render timed chunks into a complete .ass document for the chosen animated template."""
    tpl = normalize_template(template)
    meta = CAPTION_TEMPLATES[tpl]
    pos = normalize_position(position, tpl)
    size_key = normalize_size(size)
    w, h = int(video_width or 1080), int(video_height or 1920)
    font = font_name or "Arial"

    base = min(w, h) * 0.074
    font_size = max(24, int(round(base * meta["size_factor"] * SIZE_FACTORS[size_key])))
    margin_lr = int(w * 0.07)
    # Bottom captions stay above the persistent phone/bottom banner area
    margin_v = int(h * (0.20 if pos == "bottom" else 0.11))
    align = _anchor(pos)
    accent = meta["accent"]
    accent_inline = _inline_color(accent)
    white_inline = "&HFFFFFF&"

    primary = _ass_color("FFFFFF")
    outline_col = _ass_color("000000")
    back_col = _ass_color("000000", 0x80)
    border_style = 1
    outline = max(2, int(font_size * 0.07))
    shadow = max(1, int(font_size * 0.03))

    if tpl == "box_caption":
        border_style = 3
        outline_col = _ass_color("101014", 0x30)
        back_col = _ass_color("101014", 0x30)
        outline = max(8, int(font_size * 0.22))
        shadow = 0
    elif tpl == "bold_outline":
        outline = max(4, int(font_size * 0.11))
        shadow = max(2, int(font_size * 0.06))
        back_col = _ass_color("000000", 0x60)
    elif tpl == "pop_bounce":
        outline = max(4, int(font_size * 0.10))
        shadow = 0
    elif tpl == "single_word":
        outline = max(4, int(font_size * 0.09))
        shadow = max(2, int(font_size * 0.04))
    elif tpl == "fade_slide_up":
        outline = max(2, int(font_size * 0.05))
        shadow = max(2, int(font_size * 0.05))
        outline_col = _ass_color("000000", 0x40)
    elif tpl == "typewriter":
        outline = max(2, int(font_size * 0.06))
        shadow = max(1, int(font_size * 0.03))

    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        f"PlayResX: {w}\n"
        f"PlayResY: {h}\n"
        "WrapStyle: 0\n"
        "ScaledBorderAndShadow: yes\n"
        "YCbCr Matrix: TV.709\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Caption,{font},{font_size},{primary},{_ass_color(accent)},{outline_col},{back_col},"
        f"-1,0,0,0,100,100,0,0,{border_style},{outline},{shadow},{align},{margin_lr},{margin_lr},{margin_v},-1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )

    events: List[str] = []

    def add_event(start: float, end: float, text: str, layer: int = 0) -> None:
        if end - start < 0.05:
            end = start + 0.05
        events.append(f"Dialogue: {layer},{_ass_time(start)},{_ass_time(end)},Caption,,0,0,0,,{text}")

    for chunk in timed_chunks:
        st, et = float(chunk["start_sec"]), float(chunk["end_sec"])
        words = chunk.get("words") or _word_timings(chunk["text"].split(), st, et)
        emphasis = chunk.get("emphasis")

        def rel_ms(t: float) -> int:
            return max(0, int(round((t - st) * 1000)))

        def emph_wrap(word: str) -> str:
            esc = _ass_escape(word)
            if emphasis and word == emphasis:
                return "{\\1c" + accent_inline + "}" + esc + "{\\1c" + white_inline + "}"
            return esc

        if tpl == "karaoke_highlight":
            parts = ["{\\fad(90,90)}"]
            for wd in words:
                a, b = rel_ms(wd["start_sec"]), rel_ms(wd["end_sec"])
                parts.append(
                    "{\\1c" + white_inline + "\\t(" + f"{a},{a + 70}" + ",\\1c" + accent_inline + ")"
                    + "\\t(" + f"{max(a + 71, b - 40)},{b}" + ",\\1c" + white_inline + ")}"
                    + _ass_escape(wd["word"]) + " "
                )
            add_event(st, et, "".join(parts).rstrip())

        elif tpl == "box_caption":
            parts = ["{\\fad(120,100)}"]
            for wd in words:
                a, b = rel_ms(wd["start_sec"]), rel_ms(wd["end_sec"])
                parts.append(
                    "{\\1c" + white_inline + "\\t(" + f"{a},{a + 60}" + ",\\1c" + accent_inline + ")"
                    + "\\t(" + f"{max(a + 61, b - 40)},{b}" + ",\\1c" + white_inline + ")}"
                    + _ass_escape(wd["word"]) + " "
                )
            add_event(st, et, "".join(parts).rstrip())

        elif tpl == "pop_bounce":
            prefix = (
                "{\\fad(0,120)\\fscx35\\fscy35"
                "\\t(0,150,\\fscx118\\fscy118)\\t(150,260,\\fscx94\\fscy94)\\t(260,340,\\fscx100\\fscy100)}"
            )
            body = " ".join(emph_wrap(wd["word"]) for wd in words)
            add_event(st, et, prefix + body)

        elif tpl == "typewriter":
            parts = ["{\\fad(0,120)}"]
            is_arabic = bool(_ARABIC_RE.search(chunk["text"]))
            if is_arabic:
                # Word-level reveal keeps Arabic letter joining intact
                for wd in words:
                    a = rel_ms(wd["start_sec"])
                    parts.append("{\\alpha&HFF&\\t(" + f"{a},{a + 40}" + ",\\alpha&H00&)}" + _ass_escape(wd["word"]) + " ")
            else:
                text_chars = list(" ".join(wd["word"] for wd in words))
                span_ms = max(1, rel_ms(et) - 250)
                reveal_ms = min(span_ms, max(300, len(text_chars) * 55))
                step = reveal_ms / max(1, len(text_chars))
                for idx, ch in enumerate(text_chars):
                    a = int(idx * step)
                    parts.append("{\\alpha&HFF&\\t(" + f"{a},{a + 1}" + ",\\alpha&H00&)}" + _ass_escape(ch))
            add_event(st, et, "".join(parts).rstrip())

        elif tpl == "fade_slide_up":
            x, y = _anchor_xy(pos, w, h, margin_v)
            dy = int(h * 0.025)
            prefix = "{\\fad(240,200)\\move(" + f"{x},{y + dy},{x},{y},0,320" + ")}"
            body = " ".join(emph_wrap(wd["word"]) for wd in words)
            add_event(st, et, prefix + body)

        elif tpl == "bold_outline":
            prefix = "{\\fad(70,70)\\fscx92\\fscy92\\t(0,140,\\fscx100\\fscy100)}"
            body = " ".join(emph_wrap(wd["word"]) for wd in words)
            add_event(st, et, prefix + body)

        elif tpl == "single_word":
            for idx, wd in enumerate(words):
                ws, we = float(wd["start_sec"]), float(wd["end_sec"])
                color = accent_inline if (emphasis and wd["word"] == emphasis) else white_inline
                txt = (
                    "{\\1c" + color + "\\fscx65\\fscy65\\t(0,90,\\fscx114\\fscy114)\\t(90,170,\\fscx100\\fscy100)}"
                    + _ass_escape(wd["word"])
                )
                add_event(ws, we, txt)

    return header + "\n".join(events) + "\n"


def write_ass_file(
    output_path: str | Path,
    timed_chunks: List[Dict[str, Any]],
    template: str = DEFAULT_TEMPLATE,
    video_width: int = 1080,
    video_height: int = 1920,
    position: Optional[str] = None,
    size: Optional[str] = None,
    font_name: Optional[str] = None,
) -> Path:
    doc = build_ass_document(
        timed_chunks,
        template=template,
        video_width=video_width,
        video_height=video_height,
        position=position,
        size=size,
        font_name=font_name,
    )
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    # UTF-8 with BOM is the most compatible encoding for libass across platforms
    out.write_text(doc, encoding="utf-8-sig")
    return out


def prepare_caption_track(
    output_path: str | Path,
    total_duration: float,
    video_width: int,
    video_height: int,
    template: Optional[str] = None,
    custom_text: Optional[str] = None,
    segments: Optional[List[Dict[str, Any]]] = None,
    position: Optional[str] = None,
    size: Optional[str] = None,
    shot_timeline: Optional[List[Dict[str, Any]]] = None,
    font_path: Optional[str] = None,
    use_ai: bool = True,
) -> Optional[Dict[str, Any]]:
    """
    High level helper used by the pipeline.
    - custom_text: customer typed text -> smart split + calculated timings.
    - segments: already-timed narration captions -> styled with the template.
    Returns metadata dict (ass_path, chunks, engine, template...) or None if nothing to render.
    """
    tpl = normalize_template(template)
    engine = "segments"
    if custom_text and _clean_text(custom_text):
        split = smart_split_text(custom_text, tpl, total_duration, use_ai=use_ai)
        engine = split["engine"]
        timed = assign_timings(split["chunks"], total_duration, shot_timeline=shot_timeline)
    elif segments:
        timed = segments_to_timed_chunks(segments, total_duration)
    else:
        return None
    if not timed:
        return None
    ass_path = write_ass_file(
        output_path,
        timed,
        template=tpl,
        video_width=video_width,
        video_height=video_height,
        position=position,
        size=size,
        font_name=font_family_for_ass(font_path),
    )
    return {
        "ass_path": str(ass_path),
        "template": tpl,
        "template_name_ar": CAPTION_TEMPLATES[tpl]["name_ar"],
        "position": normalize_position(position, tpl),
        "size": normalize_size(size),
        "engine": engine,
        "chunks": [{k: v for k, v in c.items() if k != "words"} for c in timed],
        "chunks_count": len(timed),
        "source": "custom_text" if engine != "segments" else "narration_subtitles",
    }
