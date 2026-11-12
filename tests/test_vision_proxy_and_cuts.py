#!/usr/bin/env python3
"""Tests for Gemini Files API proxy analysis, cleanup, and recommended_cuts normalization."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web.vision_analyzer import (
    _normalize_recommended_cuts,
    _upload_video_to_gemini_files,
    infer_video_script_and_mood,
)


def test_normalize_recommended_cuts_clamps_dedupes_and_falls_back_to_quality():
    raw = [
        {"start_sec": -2.0, "end_sec": 4.0, "score": 0.9, "title": "مدخل"},
        {"start_sec": 1.0, "end_sec": 4.2, "score": 0.4, "title": "مكرر"},
        {"start_sec": 8.0, "end_sec": 8.4, "score": 0.95, "title": "قصير جدا"},
        {"start_sec": 10.0, "end_sec": 25.0, "score": 0.85, "title": "صالون"},
    ]
    norm = _normalize_recommended_cuts(raw, video_duration=18.0)
    assert norm is not None
    assert len(norm) == 2
    assert norm[0]["start_sec"] == 0.0 and norm[0]["end_sec"] == 4.0
    assert norm[1]["start_sec"] == 10.0 and norm[1]["end_sec"] == 18.0

    q_segs = [
        {"start_sec": 0.0, "end_sec": 3.0, "quality_score": 0.2},
        {"start_sec": 5.0, "end_sec": 9.0, "quality_score": 0.92},
        {"start_sec": 12.0, "end_sec": 16.0, "quality_score": 0.88},
    ]
    q_norm = _normalize_recommended_cuts(None, video_duration=20.0, quality_segments=q_segs)
    assert q_norm is not None
    assert q_norm[0]["start_sec"] == 0.0 or any(c["start_sec"] == 5.0 for c in q_norm)
    assert any(c["reason"] == "local_quality_score" for c in q_norm)


def test_infer_video_uses_gemini_files_api_and_cleans_up(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-test-key")
    monkeypatch.setenv("GEMINI_VISION_MODELS", "gemini-3.6-flash")
    monkeypatch.setenv("GEMINI_VISION_USE_VIDEO_FILE", "1")

    proxy_file = tmp_path / "proxy_480p.mp4"
    proxy_file.write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"0" * 1024)

    calls = {"delete": []}

    def fake_post(url, headers=None, json=None, data=None, timeout=None):
        resp = MagicMock()
        if "/upload/v1beta/files" in url:
            resp.status_code = 200
            resp.headers = {"X-Goog-Upload-URL": "https://upload.example.invalid/session-1"}
            return resp
        if "upload.example.invalid" in url:
            resp.status_code = 200
            resp.json.return_value = {
                "file": {
                    "name": "files/proxy123",
                    "uri": "https://generativelanguage.googleapis.com/v1beta/files/proxy123",
                    "state": "PROCESSING",
                }
            }
            return resp
        if ":generateContent" in url:
            parts = json["contents"][0]["parts"]
            assert any("fileData" in p and p["fileData"]["fileUri"].endswith("files/proxy123") for p in parts)
            resp.status_code = 200
            resp.json.return_value = {
                "candidates": [{
                    "content": {
                        "parts": [{
                            "text": '{"script": "شوفو معايا هاد الشقة الرائعة بإطلالة مفتوحة ومساحات واسعة.", "subtitles": [], "emotional_tone": "فاخر وهادئ", "emotional_prompt": "Warm luxury", "recommended_music": "luxury_piano", "highlights": ["صالون واسع"], "recommended_cuts": [{"start_sec": 2.0, "end_sec": 7.0, "score": 0.94, "title": "صالون"}], "phone_number": null, "bottom_text": null}'
                        }]
                    }
                }]
            }
            return resp
        resp.status_code = 404
        return resp

    def fake_get(url, timeout=None):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "name": "files/proxy123",
            "uri": "https://generativelanguage.googleapis.com/v1beta/files/proxy123",
            "state": "ACTIVE",
        }
        return resp

    def fake_delete(url, timeout=None):
        calls["delete"].append(url)
        resp = MagicMock()
        resp.status_code = 200
        return resp

    with patch("web.vision_analyzer.requests.post", side_effect=fake_post), \
         patch("web.vision_analyzer.requests.get", side_effect=fake_get), \
         patch("web.vision_analyzer.requests.delete", side_effect=fake_delete):
        res = infer_video_script_and_mood(
            keyframe_paths=[],
            video_duration=60.0,
            proxy_video_path=proxy_file,
            quality_segments=[{"start_sec": 2.0, "end_sec": 7.0, "quality_score": 0.9, "sharpness": 12.0, "motion": 4.0, "luma": 130.0}],
            target_montage_duration=15.0,
        )

    assert res["engine"] == "gemini_multimodal_vision"
    assert res["analysis_mode"] == "proxy_video_file"
    assert res["recommended_cuts"][0]["start_sec"] == 2.0
    assert res["recommended_cuts"][0]["end_sec"] == 7.0
    assert len(calls["delete"]) == 1 and "files/proxy123" in calls["delete"][0]


def test_infer_video_falls_back_to_keyframes_when_file_upload_fails(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-test-key")
    monkeypatch.setenv("GEMINI_VISION_MODELS", "gemini-3.6-flash")

    proxy_file = tmp_path / "proxy_480p.mp4"
    proxy_file.write_bytes(b"123456")
    kf = tmp_path / "kf_001.jpg"
    kf.write_bytes(b"\xff\xd8\xff\xe0" + b"0" * 64)

    def fake_post(url, headers=None, json=None, data=None, timeout=None):
        resp = MagicMock()
        if "/upload/v1beta/files" in url:
            resp.status_code = 500
            resp.text = "upload error"
            return resp
        if ":generateContent" in url:
            parts = json["contents"][0]["parts"]
            assert any("inlineData" in p for p in parts)
            resp.status_code = 200
            resp.json.return_value = {
                "candidates": [{
                    "content": {
                        "parts": [{
                            "text": '{"script": "جولة سريعة داخل الشقة.", "subtitles": [], "emotional_tone": "دافئ", "emotional_prompt": "Warm", "recommended_music": "luxury_piano", "highlights": [], "recommended_cuts": null, "phone_number": null, "bottom_text": null}'
                        }]
                    }
                }]
            }
            return resp
        resp.status_code = 404
        return resp

    with patch("web.vision_analyzer.requests.post", side_effect=fake_post):
        res = infer_video_script_and_mood(
            keyframe_paths=[kf],
            video_duration=12.0,
            proxy_video_path=proxy_file,
        )

    assert res["engine"] == "gemini_multimodal_vision"
    assert res["analysis_mode"] == "keyframes"
