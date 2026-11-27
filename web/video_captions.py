#!/usr/bin/env python3
"""
Video-Voice Auto-Captions Engine (web/video_captions.py).

Transcribes the real speaker's voice directly from an uploaded video and burns
CapCut-style animated subtitles onto the video while keeping the original voice
100% untouched (no AI TTS overwrite, no unintended cuts).

Engine priority:
  1. Groq Whisper API (GROQ_API_KEY / GROQ_API_KEYS) -> millisecond word timestamps,
     ~200x real-time, zero local RAM overhead.
  2. Local faster-whisper (if installed) -> offline word timestamps with Silero VAD.
  3. FFmpeg acoustic pause detection + Gemini API (GEMINI_API_KEY) -> zero-setup fallback
     aligned to real spoken bursts.
"""

from __future__ import annotations

import base64
import importlib.util
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import requests

from web.caption_templates import (
    DEFAULT_TEMPLATE,
    group_words_into_chunks,
    normalize_template,
    prepare_caption_track,
    segments_to_timed_chunks,
)
from web.video_annotator import annotate_video, find_system_font

logger = logging.getLogger("lok.video_captions")

REPO_ROOT = Path(__file__).resolve().parent.parent
GROQ_TRANSCRIPTION_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
DEFAULT_GROQ_MODEL = "whisper-large-v3-turbo"
GEMINI_AUDIO_MODEL = "gemini-3.6-flash"

# Common Whisper hallucinations on pure silence / music intros
_WHISPER_HALLUCINATION_EXACT = {
    "اشتركوا في القناة",
    "اشترك في القناة",
    "شكرا للمشاهدة",
    "شكراً للمشاهدة",
    "ترجمة نانسي قنقر",
    "thank you for watching",
    "thanks for watching",
    "sous-titres réalisés par la communauté d'amara.org",
    "merci d'avoir regardé",
    "...",
}

_LOCAL_WHISPER_LOCK = threading.Lock()
_LOCAL_WHISPER_MODEL: Any = None
_LOCAL_WHISPER_NAME: Optional[str] = None


def _ensure_stt_env_loaded() -> None:
    """Load GROQ_API_KEY / GROQ_API_KEYS / GEMINI_API_KEY from .env if missing from os.environ."""
    candidates = [REPO_ROOT / ".env", REPO_ROOT / "tts" / ".env", Path.cwd() / ".env"]
    wanted = ("GROQ_API_KEY", "GROQ_API_KEYS", "GROQ_WHISPER_MODEL", "GEMINI_API_KEY", "GEMINI_API_KEYS", "LOK_WHISPER_MODEL")
    if all(os.getenv(k) for k in ("GROQ_API_KEY", "GEMINI_API_KEY")):
        return
    for env_path in candidates:
        if not env_path.is_file():
            continue
        try:
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip("\"'")
                if k in wanted and k not in os.environ and v:
                    os.environ[k] = v
        except OSError:
            pass


def _get_api_keys(*env_names: str) -> List[str]:
    _ensure_stt_env_loaded()
    keys: List[str] = []
    for name in env_names:
        raw = os.getenv(name) or ""
        for part in raw.split(","):
            k = part.strip().strip("\"'")
            if k and k not in keys:
                keys.append(k)
    return keys


def _probe_video_geometry_and_audio(video_path: Path) -> Dict[str, Any]:
    """Return upright (rotation-aware) dimensions, duration, and audio presence."""
    ffprobe_bin = shutil.which("ffprobe") or "ffprobe"
    cmd = [
        ffprobe_bin,
        "-v", "error",
        "-show_entries", "stream=width,height,codec_type,duration:stream_tags=rotate:stream_side_data=rotation:format=duration",
        "-of", "json",
        str(video_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(res.stdout or "{}")
    streams = data.get("streams", [])
    v_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
    a_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
    fmt = data.get("format", {})

    width = int(v_stream.get("width") or 1080)
    height = int(v_stream.get("height") or 1920)
    rotation = 0
    tags = v_stream.get("tags") or {}
    if "rotate" in tags:
        try:
            rotation = int(float(tags["rotate"]))
        except (ValueError, TypeError):
            rotation = 0
    for sd in v_stream.get("side_data_list") or []:
        if isinstance(sd, dict) and sd.get("rotation") is not None:
            try:
                rotation = int(float(sd["rotation"]))
            except (ValueError, TypeError):
                pass
    if abs(rotation) % 180 == 90:
        width, height = height, width

    raw_dur = v_stream.get("duration") or fmt.get("duration") or 0.0
    try:
        duration = round(float(raw_dur), 3)
    except (ValueError, TypeError):
        duration = 0.0

    return {
        "width": width,
        "height": height,
        "duration": duration,
        "has_audio": a_stream is not None,
    }


def extract_audio_for_stt(video_path: Union[str, Path], out_mp3: Union[str, Path]) -> Tuple[Optional[Path], float]:
    """
    Extract lightweight 16kHz mono MP3 (~0.36 MB/min, fits 60+ min under Groq's 25MB limit).
    Returns (mp3_path, duration) or (None, duration) if video has no audible audio.
    """
    src = Path(video_path).resolve()
    dst = Path(out_mp3).resolve()
    if not src.is_file():
        raise FileNotFoundError(f"Video file not found: {src}")

    meta = _probe_video_geometry_and_audio(src)
    duration = float(meta["duration"])
    if not meta["has_audio"]:
        return None, duration

    dst.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
    subprocess.run(
        [
            ffmpeg_bin, "-y",
            "-i", str(src),
            "-vn",
            "-ar", "16000",
            "-ac", "1",
            "-c:a", "libmp3lame",
            "-b:a", "48k",
            str(dst),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    if not dst.is_file() or dst.stat().st_size < 500:
        return None, duration

    # Reject completely silent tracks so STT never hallucinates
    vol = subprocess.run(
        [ffmpeg_bin, "-i", str(dst), "-filter:a", "volumedetect", "-f", "null", os.devnull],
        capture_output=True,
        text=True,
    )
    vol_err = (vol.stderr or "").lower()
    if "max_volume: -inf" in vol_err or "mean_volume: -inf" in vol_err:
        return None, duration

    return dst, duration


def _detect_speech_intervals_ffmpeg(audio_path: Path, total_duration: float) -> List[Tuple[float, float]]:
    """Measure non-silent acoustic bursts with FFmpeg silencedetect."""
    ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
    res = subprocess.run(
        [
            ffmpeg_bin,
            "-i", str(audio_path),
            "-af", "silencedetect=noise=-35dB:d=0.35",
            "-f", "null", os.devnull,
        ],
        capture_output=True,
        text=True,
    )
    stderr = res.stderr or ""
    silences: List[Tuple[float, float]] = []
    cur_start: Optional[float] = None
    for line in stderr.splitlines():
        m_s = re.search(r"silence_start:\s*([0-9.]+)", line)
        if m_s:
            cur_start = float(m_s.group(1))
            continue
        m_e = re.search(r"silence_end:\s*([0-9.]+)", line)
        if m_e and cur_start is not None:
            silences.append((cur_start, float(m_e.group(1))))
            cur_start = None
    if cur_start is not None and total_duration > cur_start:
        silences.append((cur_start, total_duration))

    speech: List[Tuple[float, float]] = []
    cursor = 0.0
    for s_start, s_end in silences:
        if s_start - cursor >= 0.25:
            speech.append((round(cursor, 2), round(s_start, 2)))
        cursor = max(cursor, s_end)
    if total_duration - cursor >= 0.25:
        speech.append((round(cursor, 2), round(total_duration, 2)))
    return speech


def _is_hallucination(text: str, no_speech_prob: float = 0.0) -> bool:
    clean = re.sub(r"[\s\.,!؟?]+", " ", (text or "").strip().lower()).strip()
    if not clean:
        return True
    if no_speech_prob >= 0.85:
        return True
    return clean in _WHISPER_HALLUCINATION_EXACT


def _transcribe_with_groq(
    audio_mp3: Path,
    total_duration: float,
    language: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Transcribe audio via Groq Whisper API with exact word-level timestamps."""
    keys = _get_api_keys("GROQ_API_KEY", "GROQ_API_KEYS")
    if not keys:
        return None

    model = (os.getenv("GROQ_WHISPER_MODEL") or DEFAULT_GROQ_MODEL).strip()
    audio_bytes = audio_mp3.read_bytes()

    data: List[Tuple[str, str]] = [
        ("model", model),
        ("response_format", "verbose_json"),
        ("temperature", "0"),
        ("timestamp_granularities[]", "word"),
        ("timestamp_granularities[]", "segment"),
    ]
    if language and language.strip() and language.strip().lower() != "auto":
        data.append(("language", language.strip().lower()[:5]))

    last_err = ""
    for key in keys:
        try:
            resp = requests.post(
                GROQ_TRANSCRIPTION_URL,
                headers={"Authorization": f"Bearer {key}"},
                files={"file": (audio_mp3.name, audio_bytes, "audio/mpeg")},
                data=data,
                timeout=(10.0, 60.0),
            )
            if resp.status_code == 429:
                last_err = "Groq rate limit (429)"
                continue
            if resp.status_code != 200:
                last_err = f"Groq HTTP {resp.status_code}: {resp.text[:200]}"
                logger.warning("Groq transcription error: %s", last_err)
                continue

            payload = resp.json()
            raw_segments = payload.get("segments") or []
            raw_words = payload.get("words") or []

            # Filter out segments marked as silence / known hallucinations
            blocked_ranges: List[Tuple[float, float]] = []
            valid_segments: List[Dict[str, Any]] = []
            for seg in raw_segments:
                txt = str(seg.get("text") or "").strip()
                nsp = float(seg.get("no_speech_prob") or 0.0)
                st = max(0.0, float(seg.get("start") or 0.0))
                et = min(total_duration or 36000.0, float(seg.get("end") or st))
                if _is_hallucination(txt, nsp):
                    blocked_ranges.append((st - 0.05, et + 0.05))
                    continue
                if et > st:
                    valid_segments.append({"text": txt, "start_sec": round(st, 3), "end_sec": round(et, 3)})

            words: List[Dict[str, Any]] = []
            for w in raw_words:
                wt = str(w.get("word") or "").strip()
                if not wt:
                    continue
                ws = max(0.0, float(w.get("start") or 0.0))
                we = min(total_duration or 36000.0, float(w.get("end") or ws + 0.12))
                mid = (ws + we) * 0.5
                if any(bs <= mid <= be for bs, be in blocked_ranges):
                    continue
                words.append({"word": wt, "start_sec": round(ws, 3), "end_sec": round(max(we, ws + 0.05), 3)})

            full_text = " ".join(w["word"] for w in words) if words else " ".join(s["text"] for s in valid_segments)
            return {
                "engine": f"groq:{model}",
                "language": payload.get("language") or language or "auto",
                "full_text": full_text.strip(),
                "words": words,
                "segments": valid_segments,
            }
        except Exception as exc:
            last_err = str(exc)
            logger.warning("Groq request failed: %s", exc)

    if last_err:
        logger.warning("All Groq keys failed (%s); trying fallback STT.", last_err)
    return None


def _transcribe_with_local_faster_whisper(
    audio_mp3: Path,
    total_duration: float,
    language: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Optional offline fallback when faster-whisper is installed locally."""
    if importlib.util.find_spec("faster_whisper") is None:
        return None

    global _LOCAL_WHISPER_MODEL, _LOCAL_WHISPER_NAME
    model_name = (os.getenv("LOK_WHISPER_MODEL") or "small").strip()

    try:
        from faster_whisper import WhisperModel

        with _LOCAL_WHISPER_LOCK:
            if _LOCAL_WHISPER_MODEL is None or _LOCAL_WHISPER_NAME != model_name:
                _LOCAL_WHISPER_MODEL = WhisperModel(model_name, device="auto", compute_type="int8")
                _LOCAL_WHISPER_NAME = model_name

            lang_arg = language.strip().lower()[:5] if (language and language.strip().lower() != "auto") else None
            seg_iter, info = _LOCAL_WHISPER_MODEL.transcribe(
                str(audio_mp3),
                language=lang_arg,
                vad_filter=True,
                word_timestamps=True,
            )
            words: List[Dict[str, Any]] = []
            segments: List[Dict[str, Any]] = []
            for seg in seg_iter:
                txt = str(seg.text or "").strip()
                nsp = float(getattr(seg, "no_speech_prob", 0.0) or 0.0)
                if _is_hallucination(txt, nsp):
                    continue
                st = max(0.0, float(seg.start))
                et = min(total_duration or 36000.0, float(seg.end))
                if et > st:
                    segments.append({"text": txt, "start_sec": round(st, 3), "end_sec": round(et, 3)})
                for w in getattr(seg, "words", None) or []:
                    wt = str(w.word or "").strip()
                    if not wt:
                        continue
                    ws = max(0.0, float(w.start))
                    we = min(total_duration or 36000.0, float(w.end))
                    words.append({"word": wt, "start_sec": round(ws, 3), "end_sec": round(max(we, ws + 0.05), 3)})

        full_text = " ".join(w["word"] for w in words) if words else " ".join(s["text"] for s in segments)
        return {
            "engine": f"faster-whisper:{model_name}",
            "language": getattr(info, "language", None) or language or "auto",
            "full_text": full_text.strip(),
            "words": words,
            "segments": segments,
        }
    except Exception as exc:
        logger.warning("Local faster-whisper transcription failed: %s", exc)
        return None


def _transcribe_with_gemini_acoustic(
    audio_mp3: Path,
    total_duration: float,
    language: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Fallback STT using FFmpeg acoustic speech boundaries + existing GEMINI_API_KEY."""
    keys = _get_api_keys("GEMINI_API_KEY", "GEMINI_API_KEYS")
    if not keys:
        return None

    intervals = _detect_speech_intervals_ffmpeg(audio_mp3, total_duration)
    interval_hint = (
        ", ".join(f"[{a:.2f}s-{b:.2f}s]" for a, b in intervals[:40])
        if intervals
        else f"[0.00s-{total_duration:.2f}s]"
    )
    lang_hint = f"Primary spoken language hint: {language}." if (language and language != "auto") else (
        "Transcribe verbatim in the exact spoken language (Algerian Darja, Arabic, French, or English)."
    )
    prompt = (
        "Transcribe every spoken word in this audio verbatim into short CapCut caption chunks (2-4 words per chunk). "
        f"{lang_hint} "
        f"Acoustic speech activity was measured at these timestamps: {interval_hint}. "
        f"Total audio duration is {total_duration:.2f}s. "
        "Align every chunk's start_sec and end_sec tightly to when those exact words are spoken. "
        "Do NOT invent text during silence or music. If there is no clear human speech, return {\"segments\": []}. "
        "Return ONLY valid JSON: {\"language\": \"ar\", \"segments\": [{\"start_sec\": 0.5, \"end_sec\": 1.8, \"text\": \"...\"}]}"
    )

    audio_b64 = base64.b64encode(audio_mp3.read_bytes()).decode("utf-8")
    body = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {"inlineData": {"mimeType": "audio/mpeg", "data": audio_b64}},
            ]
        }],
        "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
    }

    for key in keys:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_AUDIO_MODEL}:generateContent?key={key}"
            resp = requests.post(url, json=body, timeout=(10.0, 45.0))
            if resp.status_code != 200:
                continue
            cands = resp.json().get("candidates") or []
            if not cands:
                continue
            raw_txt = cands[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
            raw_txt = re.sub(r"^```(?:json)?|```$", "", raw_txt, flags=re.MULTILINE).strip()
            parsed = json.loads(raw_txt)
            raw_segs = parsed.get("segments") if isinstance(parsed, dict) else (parsed if isinstance(parsed, list) else [])
            segments: List[Dict[str, Any]] = []
            for s in raw_segs or []:
                if not isinstance(s, dict):
                    continue
                txt = str(s.get("text") or "").strip()
                if _is_hallucination(txt):
                    continue
                try:
                    st = max(0.0, float(s.get("start_sec", s.get("start", 0.0))))
                    et = min(total_duration or 36000.0, float(s.get("end_sec", s.get("end", st + 1.2))))
                except (TypeError, ValueError):
                    continue
                if et > st:
                    segments.append({"text": txt, "start_sec": round(st, 3), "end_sec": round(et, 3)})

            full_text = " ".join(s["text"] for s in segments).strip()
            return {
                "engine": f"gemini-acoustic:{GEMINI_AUDIO_MODEL}",
                "language": (parsed.get("language") if isinstance(parsed, dict) else None) or language or "auto",
                "full_text": full_text,
                "words": [],
                "segments": segments,
            }
        except Exception as exc:
            logger.warning("Gemini acoustic transcription failed: %s", exc)
    return None


def transcribe_video_speech(
    video_path: Union[str, Path],
    template: Optional[str] = None,
    language: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Transcribe speech directly from a video's audio track into CapCut-ready timed chunks.
    Returns {speech_detected, engine, language, duration, full_text, words, chunks}.
    """
    src = Path(video_path).resolve()
    tpl = normalize_template(template or DEFAULT_TEMPLATE)

    with tempfile.TemporaryDirectory(prefix="lok_stt_") as tmp_dir:
        mp3_path, duration = extract_audio_for_stt(src, Path(tmp_dir) / "speech.mp3")
        if mp3_path is None:
            return {
                "speech_detected": False,
                "engine": "none",
                "language": language or "auto",
                "duration": duration,
                "full_text": "",
                "words": [],
                "chunks": [],
                "message": "لم يتم العثور على صوت كلام واضح في هذا الفيديو.",
            }

        raw = (
            _transcribe_with_groq(mp3_path, duration, language=language)
            or _transcribe_with_local_faster_whisper(mp3_path, duration, language=language)
            or _transcribe_with_gemini_acoustic(mp3_path, duration, language=language)
        )

    if not raw:
        raise RuntimeError(
            "تعذر استخراج الكلام من الفيديو. تأكد من إضافة GROQ_API_KEY (مجاني) أو GEMINI_API_KEY في ملف .env."
        )

    words = raw.get("words") or []
    segments = raw.get("segments") or []
    if words:
        chunks = group_words_into_chunks(words, template=tpl, total_duration=duration)
    else:
        chunks = segments_to_timed_chunks(segments, total_duration=max(duration, 1.0))

    speech_detected = bool(chunks)
    return {
        "speech_detected": speech_detected,
        "engine": raw["engine"],
        "language": raw.get("language") or language or "auto",
        "duration": duration,
        "full_text": raw.get("full_text") or " ".join(c["text"] for c in chunks),
        "words": words,
        "chunks": chunks,
        "message": (
            f"تم استخراج {len(chunks)} مقاطع كلام متزامنة بنجاح."
            if speech_detected
            else "لم يُرصد كلام واضح في الفيديو (صمت أو ضوضاء فقط)."
        ),
    }


def burn_video_voice_captions(
    input_video_path: Union[str, Path],
    output_video_path: Union[str, Path],
    work_dir: Union[str, Path],
    job_id: str,
    template: Optional[str] = None,
    position: Optional[str] = None,
    size: Optional[str] = None,
    font_id: Optional[str] = None,
    color_theme: Optional[str] = None,
    language: Optional[str] = None,
    edited_segments: Optional[List[Dict[str, Any]]] = None,
    blur_faces: bool = False,
    screen_overlay: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Burn animated CapCut captions synced to the video's own voice without replacing audio.
    Optionally applies face blur first and persistent phone/screen note on top.
    """
    src_path = Path(input_video_path).resolve()
    dst_path = Path(output_video_path).resolve()
    sandbox = Path(work_dir).resolve()
    sandbox.mkdir(parents=True, exist_ok=True)
    dst_path.parent.mkdir(parents=True, exist_ok=True)

    meta = _probe_video_geometry_and_audio(src_path)
    vw, vh, duration = int(meta["width"]), int(meta["height"]), float(meta["duration"])
    tpl = normalize_template(template or DEFAULT_TEMPLATE)

    # 1. Resolve timed caption chunks (reuse user-edited transcript if supplied, else transcribe)
    if edited_segments:
        chunks = segments_to_timed_chunks(edited_segments, total_duration=max(duration, 1.0))
        stt_engine = "user_edited_video_voice"
        full_text = " ".join(c["text"] for c in chunks)
        speech_detected = bool(chunks)
    else:
        stt = transcribe_video_speech(src_path, template=tpl, language=language)
        chunks = stt["chunks"]
        stt_engine = stt["engine"]
        full_text = stt["full_text"]
        speech_detected = bool(stt["speech_detected"])

    # 2. Optional face blur runs BEFORE captions & phone overlay so text stays razor sharp
    working_video = src_path
    face_blur_meta: Dict[str, Any] = {"enabled": bool(blur_faces), "applied": False, "faces_detected": False, "blurred_frames": 0}
    if blur_faces:
        from web import face_blur as face_blur_mod

        blurred_tmp = sandbox / f"blurred_{job_id}.mp4"
        res = face_blur_mod.blur_faces_in_video(input_video_path=working_video, output_video_path=blurred_tmp)
        face_blur_meta = {
            "enabled": True,
            "applied": bool(res.get("applied")),
            "faces_detected": bool(res.get("faces_detected")),
            "blurred_frames": int(res.get("blurred_frames", 0)),
            "total_frames": int(res.get("total_frames", 0)),
        }
        if res.get("applied") and blurred_tmp.is_file() and blurred_tmp.stat().st_size > 0:
            working_video = blurred_tmp

    # 3. Optional persistent screen note / phone number overlay
    annotations: List[Dict[str, Any]] = []
    normalized_overlay = None
    if screen_overlay:
        from web.pipeline_bridge import build_screen_overlay_annotation, normalize_screen_overlay_options

        normalized_overlay = normalize_screen_overlay_options(screen_overlay)
        if normalized_overlay:
            annotations.append(
                build_screen_overlay_annotation(
                    normalized_overlay,
                    total_duration=max(duration, 1.0),
                    target_h=vh,
                )
            )

    # 4. Build .ass caption file from timed video speech chunks
    caption_track_meta: Optional[Dict[str, Any]] = None
    if chunks:
        caption_track_meta = prepare_caption_track(
            sandbox / f"video_captions_{job_id}.ass",
            total_duration=max(duration, 1.0),
            video_width=vw,
            video_height=vh,
            template=tpl,
            segments=chunks,
            position=position,
            size=size,
            font_path=find_system_font(),
            font_id=font_id,
            color_theme=color_theme,
            engine_name=stt_engine,
            source_label="video_voice",
        )

    # 5. Burn captions & overlays while preserving original audio untouched (-c:a copy)
    if caption_track_meta or annotations:
        annot_kwargs: Dict[str, Any] = {}
        if caption_track_meta:
            annot_kwargs["ass_file"] = caption_track_meta["ass_path"]
        annotate_video(
            input_video_path=working_video,
            output_video_path=dst_path,
            annotations=annotations,
            video_width=vw,
            video_height=vh,
            **annot_kwargs,
        )
    elif str(working_video) != str(dst_path):
        shutil.copyfile(working_video, dst_path)

    return {
        "speech_detected": speech_detected,
        "stt_engine": stt_engine,
        "transcript": full_text,
        "duration": duration,
        "resolution": f"{vw}x{vh}",
        "animated_captions": caption_track_meta,
        "captions_count": len(chunks),
        "chunks": chunks,
        "blur_faces_enabled": bool(blur_faces),
        "blur_faces_applied": bool(face_blur_meta["applied"]),
        "faces_blurred_frames": int(face_blur_meta["blurred_frames"]),
        "blur_faces_details": face_blur_meta,
        "screen_overlay": normalized_overlay,
    }
