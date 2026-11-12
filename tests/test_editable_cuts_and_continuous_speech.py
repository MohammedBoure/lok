#!/usr/bin/env python3
"""Tests for continuous non-stopping narration, editable_cuts metadata, and cut-text re-render endpoint."""

import math
import shutil
import struct
import subprocess
import sys
import wave
from pathlib import Path
from unittest.mock import patch

import pytest
from starlette.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web.pipeline_bridge import process_mobile_video, update_cuts_text_and_rerender
from web.server import JOBS_STORE, app


def _write_tone_wav(path: Path, tone_s: float = 2.5, sr: int = 24000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        n_tone = int(sr * tone_s)
        frames = bytearray()
        for i in range(n_tone):
            val = int(12000 * math.sin(2.0 * math.pi * 440.0 * (i / sr)))
            frames.extend(struct.pack("<h", val))
        w.writeframes(bytes(frames))


def _ffmpeg_available() -> bool:
    return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def _fake_auth_header(client: TestClient) -> dict:
    from web.auth_db import create_session, list_users
    users = list_users()
    user = users[0] if users else {"id": 1, "username": "pluto", "role": "admin"}
    sess = create_session(user["id"])
    return {"Authorization": f"Bearer {sess['session_token']}"}


def test_editable_cuts_ui_and_endpoint_contracts():
    root = Path(__file__).resolve().parent.parent
    html = (root / "web/static/index.html").read_text(encoding="utf-8")
    js = (root / "web/static/app.js").read_text(encoding="utf-8")
    css = (root / "web/static/style.css").read_text(encoding="utf-8")

    assert 'id="btnApplyCutsEdit"' in html
    assert 'id="cutsEditActions"' in html
    assert "cut-text-editor" in js
    assert "update-cuts-text" in js
    assert ".cut-text-editor" in css
    assert ".btn-apply-cuts-edit" in css


@pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg/ffprobe not on PATH")
def test_editable_cuts_emitted_and_rerendered_via_api(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    src = tmp_path / "sample_tour.mp4"
    proc = subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "testsrc2=s=720x1280:r=24:d=8",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "26",
            str(src),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr

    spoken_calls = []

    def fake_synth(script_text, output_path, voice="ar-XA-Standard-A", style_prompt=None, emotional_tone=None):
        spoken_calls.append(script_text)
        _write_tone_wav(Path(output_path), tone_s=2.8)
        return {
            "audio_path": str(output_path),
            "duration": 2.8,
            "synthesizer": "synthetic_speech_engine",
            "voice": voice,
            "gemini_voice": "Kore",
            "script": script_text,
        }

    fake_vision_res = {
        "script": "شوفو معايا الدخلة والصالون. وهنا المطبخ العصري المجهز.",
        "subtitles": [],
        "shot_timeline": [
            {"scene_index": 1, "start_sec": 0.0, "end_sec": 4.0, "title": "الصالون"},
            {"scene_index": 2, "start_sec": 4.0, "end_sec": 8.0, "title": "المطبخ"},
        ],
        "scene_scripts": [
            {"start_sec": 0.0, "end_sec": 4.0, "room_or_subject": "الصالون", "text": "شوفو معايا الدخلة والصالون."},
            {"start_sec": 4.0, "end_sec": 8.0, "room_or_subject": "المطبخ", "text": "وهنا المطبخ العصري المجهز."},
        ],
        "emotional_tone": "فاخر وهادئ",
        "emotional_prompt": "Warm luxury",
        "recommended_music": "luxury_piano",
        "highlights": [],
    }

    job_id = "test_edit_cuts_01"
    with patch("web.vision_analyzer.infer_video_script_and_mood", return_value=fake_vision_res), \
         patch("web.pipeline_bridge.synthesize_narration", side_effect=fake_synth):
        summary = process_mobile_video(
            video_path=src,
            voice="ar-XA-Standard-A",
            output_dir=Path("outputs/mobile_cuts"),
            auto_mode=True,
            job_id=job_id,
        )

    assert len(summary["editable_cuts"]) == 2
    assert summary["editable_cuts"][0]["text"] == "شوفو معايا الدخلة والصالون."
    assert summary["editable_cuts"][1]["text"] == "وهنا المطبخ العصري المجهز."
    assert summary["visual_lead_in_seconds"] <= 0.35

    JOBS_STORE[job_id] = summary
    client = TestClient(app)
    headers = _fake_auth_header(client)
    assert headers, "Expected preseeded demo auth token"

    edited_payload = {
        "cuts": [
            {"scene_index": 1, "start_sec": 0.0, "end_sec": 4.0, "title": "الصالون", "text": "مرحبا بكم في الصالون الواسع."},
            {"scene_index": 2, "start_sec": 4.0, "end_sec": 8.0, "title": "المطبخ", "text": "والآن ندخلو للمطبخ الفاخر."},
        ]
    }
    spoken_calls.clear()
    with patch("web.pipeline_bridge.synthesize_narration", side_effect=fake_synth):
        resp = client.post(f"/api/jobs/{job_id}/update-cuts-text", json=edited_payload, headers=headers)

    assert resp.status_code == 200, resp.text
    updated = resp.json()
    assert updated["editable_cuts"][0]["text"] == "مرحبا بكم في الصالون الواسع."
    assert updated["editable_cuts"][1]["text"] == "والآن ندخلو للمطبخ الفاخر."
    assert "مرحبا بكم في الصالون الواسع." in updated["script"]
    assert "والآن ندخلو للمطبخ الفاخر." in updated["script"]
    assert "video_url_versioned" in updated
    assert set(spoken_calls) == {"مرحبا بكم في الصالون الواسع.", "والآن ندخلو للمطبخ الفاخر."}

    # Cleanup generated test job artifacts cleanly
    sandbox_dir = Path("outputs/jobs") / job_id
    if sandbox_dir.exists():
        shutil.rmtree(sandbox_dir, ignore_errors=True)
    for p in [
        Path("outputs/mobile_cuts") / f"cut_{job_id}.mp4",
        Path("outputs/mobile_cuts") / f"narration_{job_id}.wav",
        Path("outputs/mobile_cuts") / f"summary_{job_id}.json",
    ]:
        p.unlink(missing_ok=True)
