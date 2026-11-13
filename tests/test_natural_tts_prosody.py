#!/usr/bin/env python3
"""Tests for Gemini 3.8 TTS speechMetadata, automatic natural prosody, and clean caption stripping."""

import json
import shutil
import sys
import wave
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tts.gemini_speech.client import DEFAULT_TTS_MODEL, GeminiSpeechClient, strip_tts_vocal_tags
from web.pipeline_bridge import (
    build_scene_delivery_style,
    format_natural_speech_text,
    synthesize_narration,
    synthesize_scene_aligned_narration,
)
from web.vision_analyzer import generate_synchronized_subtitles


def _write_pcm_wav(path: Path, dur_s: float = 1.6, sr: int = 24000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(b"\x10\x00" * int(sr * dur_s))


def test_gemini_38_uses_speech_metadata_and_no_deprecated_25_models(tmp_path: Path):
    assert DEFAULT_TTS_MODEL.startswith("gemini-3.8-")
    client = GeminiSpeechClient(api_keys=["fake-test-key"])

    # Mock HTTP transport cleanly: 3.8 payload receives verbatim text + speechMetadata
    captured_requests = []

    class _FakeResp:
        def __init__(self, status_code: int, payload: dict):
            self.status_code = status_code
            self.text = json.dumps(payload)

        def json(self):
            return json.loads(self.text)

    fake_audio_b64 = "UklGRiQAAABXQVZFZm10IBAAAAABAAEAgD4AAAB9AAACABAAZGF0YQAAAAA="

    def fake_exec(method, path, params=None, json_body=None):
        captured_requests.append((path, json_body))
        return _FakeResp(
            200,
            {"candidates": [{"content": {"parts": [{"inlineData": {"mimeType": "audio/wav", "data": fake_audio_b64}}]}}]},
        )

    client._execute_with_failover = fake_exec  # type: ignore[method-assign]
    out_wav = tmp_path / "out_38.wav"
    res = client.generate_speech(
        text="أهلاً بيكم <short pause> شوفوا الصالون!",
        style_prompt="صوت دافئ وطبيعي",
        emotional_tone="دافئ وأنيق",
        output_path=str(out_wav),
    )

    assert len(captured_requests) == 1
    req_path, req_body = captured_requests[0]
    assert "gemini-3.8-flash-tts:generateContent" in req_path
    part = req_body["contents"][0]["parts"][0]
    assert part["text"] == "أهلاً بيكم <short pause> شوفوا الصالون!"
    assert "speechMetadata" in part
    assert "صوت دافئ وطبيعي" in part["speechMetadata"]["style"]
    assert "دافئ وأنيق" in part["speechMetadata"]["style"]
    assert res.model_used == "gemini-3.8-flash-tts"

    # Legacy 3.1 fallback strips tags and places directives inline cleanly
    legacy_payload = client._build_speech_request_body(
        candidate_model="gemini-3.1-flash-tts-preview",
        transcript_text="أهلاً <breath> بيكم",
        voice_name="Aoede",
        style_direction="Style: warm",
    )
    legacy_part = legacy_payload["contents"][0]["parts"][0]
    assert "speechMetadata" not in legacy_part
    assert "<breath>" not in legacy_part["text"]
    assert "(Style: warm)" in legacy_part["text"]


def test_format_natural_speech_text_and_clean_subtitles():
    # Normalizes bracket cues and stays idempotent
    casual = "أهلاً بيكم [pause] شوفوا المنظر الرائع"
    enriched = format_natural_speech_text(casual)
    assert "<short pause>" in enriched
    assert format_natural_speech_text(enriched) == enriched

    # Multi-sentence input receives a subtle breath/pause between thoughts
    multi = "مرحباً بكم في هذا المنزل الفخم جداً اليوم. شوفوا المساحة الواسعة والإضاءة الطبيعية هنا!"
    enriched_multi = format_natural_speech_text(multi)
    assert "<breath>" in enriched_multi or "<short pause>" in enriched_multi

    # Captions strip inline vocal tags cleanly so viewers never see <breath> or <short pause>
    stripped = strip_tts_vocal_tags(enriched_multi)
    assert "<breath>" not in stripped
    assert "<short pause>" not in stripped
    subs = generate_synchronized_subtitles(enriched_multi, narration_duration=5.0, visual_lead_in=0.2)
    assert subs
    joined_caps = " ".join(s["text"] for s in subs)
    assert "<breath>" not in joined_caps
    assert "<short pause>" not in joined_caps


def test_build_scene_delivery_style_adapts_to_scene_arc_and_budget():
    hook_style = build_scene_delivery_style(
        "نبرة تسويقية",
        scene_index=0,
        total_scenes=3,
        slot_text="شوفوا هذا المنزل الفخم في قلب المدينة!",
        slot_budget_sec=3.5,
    )
    mid_style = build_scene_delivery_style(
        "نبرة تسويقية",
        scene_index=1,
        total_scenes=3,
        slot_text="المطبخ مجهز بالكامل وواسع بزاف مع إطلالة جميلة على الحديقة كل صباح",
        slot_budget_sec=3.0,  # ~4.3 words/sec -> brisk pacing hint
    )
    cta_style = build_scene_delivery_style(
        "نبرة تسويقية",
        scene_index=2,
        total_scenes=3,
        slot_text="اتصلوا بنا اليوم لحجز المعاينة.",
        slot_budget_sec=4.0,
    )

    assert "افتتاحية جاذبة" in hook_style
    assert "إيقاع سريع" in mid_style
    assert "خاتمة واثقة" in cta_style


@pytest.mark.skipif(not (shutil.which("ffmpeg") and shutil.which("ffprobe")), reason="ffmpeg/ffprobe required")
def test_scene_aligned_narration_enriches_audio_but_keeps_clean_captions(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    seen_calls = []

    def fake_synth(script_text, output_path, voice="ar-XA-Standard-A", style_prompt=None, emotional_tone=None):
        seen_calls.append({"text": script_text, "style": style_prompt})
        _write_pcm_wav(Path(output_path), dur_s=2.0)
        return {
            "audio_path": str(output_path),
            "duration": 2.0,
            "synthesizer": "gemini_tts",
            "voice": voice,
            "gemini_voice": "Aoede",
            "script": script_text,
        }

    scenes = [
        {
            "start_sec": 0.0,
            "end_sec": 3.0,
            "text": "أهلاً بكم اليوم في جولة سريعة وممتعة، شوفوا الصالون الواسع والجميل بزاف.",
        },
        {
            "start_sec": 3.2,
            "end_sec": 6.5,
            "text": "تواصلوا معنا الآن لحجز الموعد!",
        },
    ]
    out_wav = tmp_path / "aligned_natural.wav"
    with patch("web.pipeline_bridge.synthesize_narration", side_effect=fake_synth):
        info = synthesize_scene_aligned_narration(
            scene_segments=scenes,
            output_path=out_wav,
            style_prompt="صوت دافئ",
        )

    assert len(seen_calls) == 2
    assert "<breath>" in seen_calls[0]["text"] or "<short pause>" in seen_calls[0]["text"]
    assert "افتتاحية جاذبة" in (seen_calls[0]["style"] or "")
    assert "خاتمة واثقة" in (seen_calls[1]["style"] or "")
    for st in info.get("scene_timings", []):
        assert "<breath>" not in st["text"]
        assert "<short pause>" not in st["text"]

