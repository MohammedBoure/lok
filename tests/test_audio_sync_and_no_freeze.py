#!/usr/bin/env python3
"""Tests for silence trimming, scene-locked TTS timing, atempo fit, and zero 10s end-freeze."""

import math
import shutil
import struct
import subprocess
import sys
import wave
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web.pipeline_bridge import (
    _build_atempo_chain,
    _fit_audio_tempo,
    _trim_wav_silence,
    get_media_duration,
    process_mobile_video,
    synthesize_scene_aligned_narration,
)


def _write_tone_wav(path: Path, lead_sil_s: float, tone_s: float, tail_sil_s: float, sr: int = 24000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        if lead_sil_s > 0:
            w.writeframes(b"\x00\x00" * int(sr * lead_sil_s))
        n_tone = int(sr * tone_s)
        frames = bytearray()
        for i in range(n_tone):
            val = int(12000 * math.sin(2.0 * math.pi * 440.0 * (i / sr)))
            frames.extend(struct.pack("<h", val))
        w.writeframes(bytes(frames))
        if tail_sil_s > 0:
            w.writeframes(b"\x00\x00" * int(sr * tail_sil_s))


def _ffmpeg_available() -> bool:
    return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def test_trim_wav_silence_removes_leading_and_trailing_dead_air(tmp_path: Path):
    wav_file = tmp_path / "noisy_edges.wav"
    _write_tone_wav(wav_file, lead_sil_s=0.9, tone_s=1.2, tail_sil_s=1.0)
    assert get_media_duration(wav_file) == pytest.approx(3.1, abs=0.1)

    new_dur = _trim_wav_silence(wav_file)
    assert 1.1 <= new_dur <= 1.45


def test_build_atempo_chain_and_fit_audio_tempo(tmp_path: Path):
    assert _build_atempo_chain(1.25) == "atempo=1.2500"
    assert "atempo=1.9500" in _build_atempo_chain(2.4)

    if not _ffmpeg_available():
        pytest.skip("ffmpeg not available")
    wav_file = tmp_path / "long_voice.wav"
    _write_tone_wav(wav_file, lead_sil_s=0.0, tone_s=6.0, tail_sil_s=0.0)
    new_dur = _fit_audio_tempo(wav_file, max_duration=4.2, max_tempo=1.55)
    assert 4.0 <= new_dur <= 4.45


@pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg/ffprobe not on PATH")
def test_synthesize_scene_aligned_narration_prevents_room_drift(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    out_wav = tmp_path / "scene_aligned.wav"

    def fake_synth(script_text, output_path, voice="ar-XA-Standard-A", style_prompt=None, emotional_tone=None):
        # Simulate Gemini speaking too long (4.2s for scene 1 inside 3.5s window, plus dead air)
        _write_tone_wav(Path(output_path), lead_sil_s=0.4, tone_s=3.8, tail_sil_s=0.4)
        return {
            "audio_path": str(output_path),
            "duration": 4.6,
            "synthesizer": "gemini_tts",
            "voice": voice,
            "gemini_voice": "Kore",
            "script": script_text,
        }

    scenes = [
        {"start_sec": 0.0, "end_sec": 4.5, "text": "شوفو معايا الدخلة والصالون."},
        {"start_sec": 5.0, "end_sec": 9.0, "text": "وهنا الحمام العصري المجهز."},
    ]
    with patch("web.pipeline_bridge.synthesize_narration", side_effect=fake_synth):
        res = synthesize_scene_aligned_narration(
            scene_segments=scenes,
            output_path=out_wav,
            visual_lead_in=1.0,
        )

    assert out_wav.is_file()
    timings = res.get("scene_timings", [])
    assert len(timings) == 2
    # Scene 1 must finish inside its 4.5s window and NEVER push Scene 2 ("bathroom") 3 seconds late
    assert timings[0]["end_sec"] <= 4.6
    assert 4.9 <= timings[1]["start_sec"] <= 5.2


@pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg/ffprobe not on PATH")
def test_process_mobile_video_eliminates_10s_end_freeze(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEYS", raising=False)

    src = tmp_path / "short_room.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc2=s=720x1280:r=24:d=8",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "26",
        str(src),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr

    def slow_long_tts(script_text, output_path, voice="ar-XA-Standard-A", style_prompt=None, emotional_tone=None):
        # Deliberately produce a 16-second narration for an 8-second video!
        _write_tone_wav(Path(output_path), lead_sil_s=1.0, tone_s=14.0, tail_sil_s=1.0)
        return {
            "audio_path": str(output_path),
            "duration": 16.0,
            "synthesizer": "synthetic_speech_engine",
            "voice": voice,
            "gemini_voice": "Charon",
            "script": script_text,
        }

    with patch("web.pipeline_bridge.synthesize_narration", side_effect=slow_long_tts):
        summary = process_mobile_video(
            video_path=src,
            script="نص طويل بزاف مقارنة بمدة الفيديو القصيرة باش نجربو منع التجميد.",
            voice="ar-XA-Standard-A",
            output_dir=tmp_path / "out",
            visual_lead_in=1.2,
            outro_buffer=1.2,
            job_id="test_no_freeze",
        )

    assert summary["status"] == "completed"
    # Before fix: this produced an ~18.4s video with 10.4s frozen last frame!
    # Now: end freeze is strictly capped <= 0.8s (total <= 8.85s)
    assert summary["end_freeze_seconds"] <= 0.8
    assert summary["duration"] <= 8.85

