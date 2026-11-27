"""Unit and integration tests for Video-Voice Auto-Captions (original audio preserved)."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

from starlette.testclient import TestClient

from web.auth_db import init_db
from web.caption_templates import (
    build_ass_document,
    group_words_into_chunks,
    segments_to_timed_chunks,
)
from web.server import app
from web.video_captions import (
    _transcribe_with_groq,
    burn_video_voice_captions,
    extract_audio_for_stt,
    transcribe_video_speech,
)
from web.video_editor import probe_video_stream

REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = REPO_ROOT / "web" / "static"


def _make_test_video(dest: Path, with_audio: bool = True, duration: float = 2.0) -> None:
    ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
    if with_audio:
        cmd = [
            ffmpeg_bin, "-y",
            "-f", "lavfi", "-i", f"color=c=0x15616d:s=360x640:d={duration}",
            "-f", "lavfi", "-i", f"sine=frequency=440:duration={duration}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest",
            str(dest),
        ]
    else:
        cmd = [
            ffmpeg_bin, "-y",
            "-f", "lavfi", "-i", f"color=c=0x15616d:s=360x640:d={duration}",
            "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            str(dest),
        ]
    subprocess.run(cmd, check=True, capture_output=True)


def test_group_words_preserves_acoustic_timings_and_splits_on_pauses():
    words = [
        {"word": "شوفو", "start_sec": 0.20, "end_sec": 0.55},
        {"word": "هاد", "start_sec": 0.58, "end_sec": 0.80},
        # 0.70s pause -> must flush a new chunk even below max_words
        {"word": "المنتج", "start_sec": 1.50, "end_sec": 2.00},
        {"word": "الجديد", "start_sec": 2.02, "end_sec": 2.50},
    ]
    chunks = group_words_into_chunks(words, template="karaoke_highlight", total_duration=3.0)
    assert len(chunks) == 2
    assert chunks[0]["text"] == "شوفو هاد"
    assert chunks[0]["words"][0]["start_sec"] == 0.2
    assert chunks[1]["text"] == "المنتج الجديد"
    assert chunks[1]["start_sec"] == 1.5

    # Preserves acoustic per-word times when text untouched; falls back cleanly if user edits word count
    timed_exact = segments_to_timed_chunks(chunks, total_duration=3.0)
    assert timed_exact[0]["words"][1]["start_sec"] == 0.58

    edited = [{"text": "شوفو هاد العرض الخاص", "start_sec": 0.20, "end_sec": 0.80, "words": chunks[0]["words"]}]
    timed_edited = segments_to_timed_chunks(edited, total_duration=3.0)
    assert len(timed_edited[0]["words"]) == 4

    # single_word clamps overlapping words so two lines never collide
    overlap_chunks = [{
        "text": "كلمة واحدة",
        "start_sec": 0.0,
        "end_sec": 1.0,
        "words": [
            {"word": "كلمة", "start_sec": 0.0, "end_sec": 0.65},
            {"word": "واحدة", "start_sec": 0.50, "end_sec": 1.0},
        ],
    }]
    ass_doc = build_ass_document(overlap_chunks, template="single_word")
    assert "0:00:00.00,0:00:00.50" in ass_doc


def test_groq_stt_rotates_on_429_and_filters_silence_hallucinations(monkeypatch, tmp_path: Path):
    mp3 = tmp_path / "speech.mp3"
    mp3.write_bytes(b"ID3" + b"\x00" * 200)
    monkeypatch.setenv("GROQ_API_KEYS", "key-rate-limited,key-good")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    calls = []

    def _fake_post(url, headers, files, data, timeout):
        calls.append((headers["Authorization"], data))
        if headers["Authorization"] == "Bearer key-rate-limited":
            return SimpleNamespace(status_code=429, text="rate limit")
        return SimpleNamespace(
            status_code=200,
            json=lambda: {
                "language": "ar",
                "segments": [
                    {"start": 0.1, "end": 1.2, "text": "أهلاً بكم اليوم", "no_speech_prob": 0.05},
                    {"start": 1.8, "end": 2.6, "text": "اشتركوا في القناة", "no_speech_prob": 0.92},
                ],
                "words": [
                    {"word": "أهلاً", "start": 0.1, "end": 0.45},
                    {"word": "بكم", "start": 0.48, "end": 0.80},
                    {"word": "اليوم", "start": 0.85, "end": 1.20},
                    {"word": "اشتركوا", "start": 1.90, "end": 2.20},
                ],
            },
        )

    monkeypatch.setattr("web.video_captions.requests.post", _fake_post)
    res = _transcribe_with_groq(mp3, total_duration=3.0)
    assert res is not None
    assert len(calls) == 2
    assert res["engine"].startswith("groq:")
    assert [w["word"] for w in res["words"]] == ["أهلاً", "بكم", "اليوم"]


def test_silent_or_no_audio_video_skips_stt_cleanly(tmp_path: Path):
    silent_vid = tmp_path / "no_audio.mp4"
    _make_test_video(silent_vid, with_audio=False, duration=1.5)
    mp3, dur = extract_audio_for_stt(silent_vid, tmp_path / "out.mp3")
    assert mp3 is None
    assert dur >= 1.0

    stt = transcribe_video_speech(silent_vid)
    assert stt["speech_detected"] is False
    assert stt["chunks"] == []


def test_burn_video_voice_captions_preserves_original_audio(monkeypatch, tmp_path: Path):
    src = tmp_path / "speaker.mp4"
    dst = tmp_path / "captioned.mp4"
    sandbox = tmp_path / "sandbox"
    _make_test_video(src, with_audio=True, duration=2.0)

    def _fake_transcribe(video_path, template=None, language=None):
        return {
            "speech_detected": True,
            "engine": "groq:whisper-large-v3-turbo",
            "language": "ar",
            "duration": 2.0,
            "full_text": "عرض خاص اليوم",
            "words": [
                {"word": "عرض", "start_sec": 0.1, "end_sec": 0.6},
                {"word": "خاص", "start_sec": 0.65, "end_sec": 1.2},
                {"word": "اليوم", "start_sec": 1.25, "end_sec": 1.8},
            ],
            "chunks": group_words_into_chunks(
                [
                    {"word": "عرض", "start_sec": 0.1, "end_sec": 0.6},
                    {"word": "خاص", "start_sec": 0.65, "end_sec": 1.2},
                    {"word": "اليوم", "start_sec": 1.25, "end_sec": 1.8},
                ],
                template=template or "karaoke_highlight",
                total_duration=2.0,
            ),
        }

    monkeypatch.setattr("web.video_captions.transcribe_video_speech", _fake_transcribe)

    res = burn_video_voice_captions(
        input_video_path=src,
        output_video_path=dst,
        work_dir=sandbox,
        job_id="vc1",
        template="karaoke_highlight",
        font_id="almarai_bold",
        color_theme="gold_luxury",
    )
    assert res["speech_detected"] is True
    assert res["stt_engine"] == "groq:whisper-large-v3-turbo"
    assert res["animated_captions"]["source"] == "video_voice"
    assert dst.is_file() and dst.stat().st_size > 0

    info = probe_video_stream(dst)
    assert info["codec"] == "h264"
    assert info["has_audio"] is True

    # Edited segments path skips STT completely
    called = []
    monkeypatch.setattr("web.video_captions.transcribe_video_speech", lambda *a, **k: called.append(1))
    dst2 = tmp_path / "captioned_edited.mp4"
    res2 = burn_video_voice_captions(
        input_video_path=src,
        output_video_path=dst2,
        work_dir=sandbox,
        job_id="vc2",
        template="pop_bounce",
        edited_segments=[{"start_sec": 0.1, "end_sec": 1.8, "text": "سعر ممتاز 2500 دج"}],
    )
    assert called == []
    assert res2["stt_engine"] == "user_edited_video_voice"
    assert dst2.is_file()


def test_video_captions_api_endpoints_and_ui_contracts(monkeypatch, tmp_path: Path):
    init_db()
    client = TestClient(app)

    assert client.post("/api/captions/transcribe", files={"video": ("a.mp4", b"x", "video/mp4")}).status_code == 401
    assert client.post("/api/video-captions", files={"video": ("a.mp4", b"x", "video/mp4")}).status_code == 401

    tmp_up = tmp_path / "uploads"
    tmp_out = tmp_path / "outputs"
    tmp_up.mkdir()
    tmp_out.mkdir()
    monkeypatch.setattr("web.server.UPLOADS_DIR", tmp_up)
    monkeypatch.setattr("web.server.OUTPUTS_DIR", tmp_out)
    monkeypatch.setattr(
        "web.server._get_authenticated_user_from_form_or_header",
        lambda req, form: {"id": 1, "username": "tester", "role": "user"},
    )
    monkeypatch.setattr("web.server.check_quota", lambda uid: (True, "ok", {"remaining": 10}))
    monkeypatch.setattr("web.server.record_generation", lambda **kwargs: None)

    monkeypatch.setattr(
        "web.video_captions.transcribe_video_speech",
        lambda **kwargs: {
            "speech_detected": True,
            "engine": "groq:whisper-large-v3-turbo",
            "language": "ar",
            "duration": 4.2,
            "full_text": "شوفو معايا",
            "words": [{"word": "شوفو", "start_sec": 0.2, "end_sec": 0.7}],
            "chunks": [{"text": "شوفو معايا", "start_sec": 0.2, "end_sec": 1.2}],
            "message": "ok",
        },
    )
    tr = client.post("/api/captions/transcribe", files={"video": ("talk.mp4", b"video-bytes", "video/mp4")})
    assert tr.status_code == 200
    assert tr.json()["speech_detected"] is True
    assert tr.json()["engine"] == "groq:whisper-large-v3-turbo"
    assert list(tmp_up.glob("_stt_probe_*")) == []

    captured = {}

    def _fake_burn(**kwargs):
        captured.update(kwargs)
        Path(kwargs["output_video_path"]).write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 64)
        return {
            "speech_detected": True,
            "stt_engine": "groq:whisper-large-v3-turbo",
            "transcript": "شوفو معايا",
            "duration": 4.2,
            "resolution": "720x1280",
            "animated_captions": {"template": "pop_bounce", "template_name_ar": "نطّة مرحة", "chunks_count": 2},
            "captions_count": 2,
            "blur_faces_enabled": bool(kwargs.get("blur_faces")),
            "blur_faces_applied": bool(kwargs.get("blur_faces")),
            "faces_blurred_frames": 10 if kwargs.get("blur_faces") else 0,
            "screen_overlay": kwargs.get("screen_overlay"),
        }

    monkeypatch.setattr("web.video_captions.burn_video_voice_captions", _fake_burn)
    vc = client.post(
        "/api/video-captions",
        data={
            "caption_template": "pop_bounce",
            "caption_font": "almarai_bold",
            "caption_color": "gold_luxury",
            "blur_faces": "true",
            "caption_segments": json.dumps([{"start_sec": 0.2, "end_sec": 1.2, "text": "شوفو معايا"}]),
        },
        files={"video": ("talk.mp4", b"video-bytes", "video/mp4")},
    )
    assert vc.status_code == 200
    body = vc.json()
    assert body["standalone_mode"] == "video_captions_only"
    assert body["original_audio_preserved"] is True
    assert body["captions_applied"] is True
    assert captured["template"] == "pop_bounce"
    assert captured["font_id"] == "almarai_bold"
    assert captured["color_theme"] == "gold_luxury"
    assert captured["blur_faces"] is True
    assert len(captured["edited_segments"]) == 1

    # UI wiring assertions
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    css = (STATIC_DIR / "style.css").read_text(encoding="utf-8")
    assert 'id="btnExtractVideoCaptions"' in html
    assert 'id="videoCaptionEditorWrap"' in html
    assert 'id="btnAutoVideoCaptions"' in html
    assert 'fetch("/api/captions/transcribe"' in js
    assert 'fetch("/api/video-captions"' in js
    assert "extractedVideoCaptions" in js
    assert ".btn-video-captions-only" in css
    assert ".video-caption-editor-wrap" in css
