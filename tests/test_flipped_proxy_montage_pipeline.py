#!/usr/bin/env python3
"""End-to-end tests for flipped Analyze-First -> Cut-Original-1080p-Second pipeline & TTS chunking."""

import shutil
import subprocess
import sys
import wave
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web.pipeline_bridge import (
    _concatenate_wav_files,
    _split_tts_chunks,
    process_mobile_video,
    synthesize_narration,
)


def _ffmpeg_available() -> bool:
    return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def test_split_tts_chunks_respects_sentence_boundaries():
    long_text = ". ".join([f"جملة اختبار عقارية رقم {i} فيها وصف الشقة والإطلالة" for i in range(25)])
    chunks = _split_tts_chunks(long_text, max_words_per_chunk=60)
    assert len(chunks) >= 3
    assert all(len(c.split()) <= 60 for c in chunks)
    joined_words = " ".join(chunks).split()
    assert len(joined_words) == len(long_text.split())


def test_synthesize_narration_chunks_and_concatenates_wav(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    long_script = " ".join([f"كلمة{i}" for i in range(130)])
    out_wav = tmp_path / "out_long.wav"
    chunk_calls = []

    def fake_generate(self, text, voice_name, output_path, style_prompt=None, emotional_tone=None):
        chunk_calls.append(len(text.split()))
        with wave.open(output_path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(24000)
            w.writeframes(b"\x01\x00" * 12000)

    with patch("tts.gemini_speech.client.GeminiSpeechClient.generate_speech", fake_generate):
        info = synthesize_narration(long_script, out_wav, voice="Charon")

    assert len(chunk_calls) == 2
    assert info["synthesizer"] == "gemini_tts"
    assert out_wav.is_file()
    assert info["duration"] > 1.0


@pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg/ffprobe not on PATH")
def test_flipped_pipeline_analyzes_proxy_before_cutting_1080p(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEYS", raising=False)

    src = tmp_path / "walkthrough_1080p.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc2=s=1080x1920:r=24:d=12",
        "-f", "lavfi", "-i", "sine=frequency=330:duration=12",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "26",
        "-c:a", "aac", "-shortest",
        str(src),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr

    call_order = []

    def fake_vision(
        keyframe_paths,
        video_duration=10.0,
        preset_hint=None,
        speech_description=None,
        visual_description=None,
        visual_lead_in=1.2,
        outro_buffer=1.2,
        keyframes_metadata=None,
        videographer_speech=None,
        proxy_video_path=None,
        quality_segments=None,
        target_montage_duration=None,
    ):
        call_order.append(("vision", float(video_duration), bool(proxy_video_path), bool(quality_segments), target_montage_duration))
        return {
            "script": "شوفو معايا هاد الشقة المميزة بإطلالة رائعة وتصميم عصري.",
            "subtitles": [],
            "shot_timeline": [],
            "emotional_tone": "فاخر وهادئ",
            "emotional_prompt": "Warm luxury",
            "recommended_music": "luxury_piano",
            "highlights": ["صالون واسع"],
            "recommended_cuts": [
                {"start_sec": 1.0, "end_sec": 4.0, "score": 0.95, "title": "مدخل"},
                {"start_sec": 7.0, "end_sec": 10.5, "score": 0.92, "title": "صالون"},
            ],
            "engine": "gemini_multimodal_vision",
            "analysis_mode": "proxy_video_file",
        }

    from web import video_editor as real_editor
    orig_auto = real_editor.auto_smart_montage

    def spy_auto_montage(*args, **kwargs):
        call_order.append(("montage", bool(kwargs.get("preferred_scenes")), bool(kwargs.get("proxy_path"))))
        return orig_auto(*args, **kwargs)

    out_dir = tmp_path / "mobile_out"
    with patch("web.vision_analyzer.infer_video_script_and_mood", side_effect=fake_vision), \
         patch("web.video_editor.auto_smart_montage", side_effect=spy_auto_montage):
        res = process_mobile_video(
            video_path=src,
            speech_description="مونتاج ذكي لأفضل اللقطات بمدة 7 ثواني",
            voice="ar-XA-Standard-A",
            output_dir=out_dir,
            auto_mode=True,
            job_id="test_flipped_1080p",
        )

    assert res["status"] == "completed"
    assert res["resolution"] == "1080x1920"
    assert res["proxy_used"] is True
    assert res["montage_applied"] is True
    assert res["montage_details"]["used_ai_cuts"] is True
    assert call_order[0][0] == "vision"
    assert call_order[0][1] == pytest.approx(12.0, abs=0.5)
    assert call_order[0][2] is True  # proxy passed to Vision
    assert call_order[0][3] is True  # quality segments passed to Vision
    assert call_order[1] == ("montage", True, True)
    # Temporary proxy must be deleted after completion
    assert not (Path(res["sandbox_dir"]) / "analysis_proxy_test_flipped_1080p.mp4").exists()
