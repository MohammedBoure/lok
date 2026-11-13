#!/usr/bin/env python3
"""
Tests for background music opt-in toggle activation fix, dynamic assets/music/ discovery,
and audio streaming endpoint.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from starlette.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from web.pipeline_bridge import (
    get_music_tracks_list,
    parse_music_directives,
    process_mobile_video,
    resolve_music_track,
    update_cuts_text_and_rerender,
)
from web.server import app


def test_parse_music_directives_distinguishes_default_from_explicit_mute():
    neutral = parse_music_directives("أريد فيديو تسويقي لشقة جميلة في وهران")
    assert neutral["mute_music"] is True
    assert neutral["explicit_mute"] is False
    assert neutral["music_requested"] is False

    explicit = parse_music_directives("شقة جميلة بدون موسيقى نهائيا")
    assert explicit["mute_music"] is True
    assert explicit["explicit_mute"] is True
    assert explicit["music_requested"] is False


@patch("web.pipeline_bridge.annotate_video")
@patch("web.pipeline_bridge.synthesize_narration")
@patch("web.pipeline_bridge.subprocess.run")
@patch("frame_extractor.extract_keyframes")
@patch("frame_extractor.get_video_metadata")
def test_enable_music_flag_activates_music_even_without_prompt_keywords(
    mock_meta,
    mock_kf,
    mock_subp,
    mock_synth,
    mock_annot,
    tmp_path: Path,
):
    video = tmp_path / "src.mp4"
    video.write_bytes(b"\x00" * 2048)

    mock_meta.return_value = {"width": 1080, "height": 1920, "total_duration": 12.0}
    mock_kf.return_value = {"frames": []}
    wav_path = tmp_path / "voice.wav"
    wav_path.write_bytes(b"RIFF....WAVEfmt ")
    mock_synth.return_value = {
        "duration": 6.0,
        "synthesizer": "mock_tts",
        "file": str(wav_path),
    }

    captured_cmds = []

    def fake_ffmpeg(cmd, *args, **kwargs):
        if isinstance(cmd, list) and cmd:
            captured_cmds.append(cmd)
            out_p = Path(cmd[-1])
            out_p.parent.mkdir(parents=True, exist_ok=True)
            out_p.write_bytes(b"mock_mp4_bytes")
        return MagicMock(returncode=0, stdout="", stderr="")

    mock_subp.side_effect = fake_ffmpeg
    mock_annot.return_value = {"status": "ok", "annotations_applied": 0}

    summary = process_mobile_video(
        video_path=video,
        script="مرحبا بكم في هذا المنزل العصري الأنيق.",
        output_dir=tmp_path / "out",
        voice="ar-XA-Standard-A",
        enable_music=True,
        music_track="acoustic_guitar",
    )

    assert summary["music_muted"] is False
    assert summary["music_track"]["muted"] is False
    assert summary["music_track"]["id"] == "acoustic_guitar"

    render_cmds = [c for c in captured_cmds if "-filter_complex" in c]
    assert len(render_cmds) > 0
    inputs = [render_cmds[0][i + 1] for i, a in enumerate(render_cmds[0]) if a == "-i"]
    assert len(inputs) == 3, f"Expected 3 inputs (video, music, narration), got {inputs}"
    assert any("acoustic_guitar.mp3" in inp for inp in inputs)


@patch("web.pipeline_bridge.annotate_video")
@patch("web.pipeline_bridge.synthesize_narration")
@patch("web.pipeline_bridge.subprocess.run")
@patch("frame_extractor.extract_keyframes")
@patch("frame_extractor.get_video_metadata")
def test_explicit_mute_in_prompt_still_overrides_enable_music(
    mock_meta,
    mock_kf,
    mock_subp,
    mock_synth,
    mock_annot,
    tmp_path: Path,
):
    video = tmp_path / "src_mute.mp4"
    video.write_bytes(b"\x00" * 2048)

    mock_meta.return_value = {"width": 1080, "height": 1920, "total_duration": 10.0}
    mock_kf.return_value = {"frames": []}
    mock_synth.return_value = {"duration": 5.0, "synthesizer": "mock_tts", "file": str(tmp_path / "v.wav")}

    def fake_ffmpeg(cmd, *args, **kwargs):
        if isinstance(cmd, list) and cmd:
            out_p = Path(cmd[-1])
            out_p.parent.mkdir(parents=True, exist_ok=True)
            out_p.write_bytes(b"mock_mp4_bytes")
        return MagicMock(returncode=0, stdout="", stderr="")

    mock_subp.side_effect = fake_ffmpeg
    mock_annot.return_value = {"status": "ok", "annotations_applied": 0}

    summary = process_mobile_video(
        video_path=video,
        speech_description="شقة جميلة بدون موسيقى",
        output_dir=tmp_path / "out_mute",
        voice="ar-XA-Standard-A",
        enable_music=True,
        music_track="luxury_piano",
    )

    assert summary["music_muted"] is True
    assert summary["music_track"]["muted"] is True


def test_dynamic_assets_music_discovery_and_audio_endpoint(tmp_path: Path, monkeypatch):
    import web.pipeline_bridge as pb

    fake_root = tmp_path
    music_dir = fake_root / "assets" / "music"
    music_dir.mkdir(parents=True, exist_ok=True)
    for name in ("luxury_piano.mp3", "acoustic_guitar.mp3", "ambient_meditation.mp3", "custom_oud_lounge.mp3"):
        (music_dir / name).write_bytes(b"ID3" + b"\x00" * 128)

    monkeypatch.setattr(pb, "REPO_ROOT", fake_root)
    monkeypatch.setitem(pb.MUSIC_LIBRARY["luxury_piano"], "file", music_dir / "luxury_piano.mp3")
    monkeypatch.setitem(pb.MUSIC_LIBRARY["acoustic_guitar"], "file", music_dir / "acoustic_guitar.mp3")
    monkeypatch.setitem(pb.MUSIC_LIBRARY["ambient_meditation"], "file", music_dir / "ambient_meditation.mp3")

    tracks = get_music_tracks_list()
    ids = [t["id"] for t in tracks]
    assert "custom_oud_lounge" in ids
    custom = next(t for t in tracks if t["id"] == "custom_oud_lounge")
    assert custom["audio_url"] == "/api/music-tracks/custom_oud_lounge/audio"
    assert resolve_music_track("custom_oud_lounge", strict=True) is not None

    client = TestClient(app)
    res_list = client.get("/api/music-tracks")
    assert res_list.status_code == 200
    assert any(t["id"] == "custom_oud_lounge" for t in res_list.json())

    res_audio = client.get("/api/music-tracks/custom_oud_lounge/audio")
    assert res_audio.status_code == 200
    assert res_audio.headers["content-type"].startswith("audio/mpeg")

    res_missing = client.get("/api/music-tracks/does_not_exist/audio")
    assert res_missing.status_code == 404


@patch("web.pipeline_bridge.annotate_video")
@patch("web.pipeline_bridge.synthesize_narration")
@patch("web.pipeline_bridge.subprocess.run")
@patch("frame_extractor.get_video_metadata")
def test_update_cuts_text_updates_music_selection(
    mock_meta,
    mock_subp,
    mock_synth,
    mock_annot,
    tmp_path: Path,
    monkeypatch,
):
    import web.pipeline_bridge as pb

    monkeypatch.setattr(pb, "REPO_ROOT", tmp_path)
    job_id = "test_music_rerender"
    sandbox = tmp_path / "outputs" / "jobs" / job_id / "sandbox"
    sandbox.mkdir(parents=True, exist_ok=True)
    clean_vid = sandbox / f"clean_visual_{job_id}.mp4"
    clean_vid.write_bytes(b"video_bytes")

    summary_data = {
        "job_id": job_id,
        "duration": 10.0,
        "voice": "ar-XA-Standard-A",
        "music_muted": True,
        "music_track": {"id": "luxury_piano", "title": "Piano", "license": "CC0", "muted": True, "volume": 0.16},
        "clean_visual_source": str(clean_vid),
        "editable_cuts": [{"scene_index": 1, "start_sec": 0.0, "end_sec": 5.0, "title": "Intro", "text": "مرحبا"}],
        "shot_timeline": [{"start_sec": 0.0, "end_sec": 5.0, "title": "Intro", "description": "مرحبا"}],
        "render_config": {"src_duration": 10.0, "mute_music": True, "music_track_id": "luxury_piano"},
        "metadata": {},
    }
    (sandbox / f"summary_{job_id}.json").write_text(json.dumps(summary_data), encoding="utf-8")

    mock_meta.return_value = {"width": 720, "height": 1280, "total_duration": 10.0}
    wav_path = sandbox / f"narration_{job_id}.wav"
    wav_path.write_bytes(b"RIFF....")
    mock_synth.return_value = {"duration": 4.0, "synthesizer": "mock_tts", "file": str(wav_path)}

    def fake_ffmpeg(cmd, *args, **kwargs):
        if isinstance(cmd, list) and cmd:
            Path(cmd[-1]).parent.mkdir(parents=True, exist_ok=True)
            Path(cmd[-1]).write_bytes(b"mp4")
        return MagicMock(returncode=0, stdout="", stderr="")

    mock_subp.side_effect = fake_ffmpeg
    mock_annot.return_value = {"status": "ok", "annotations_applied": 0}

    updated = update_cuts_text_and_rerender(
        job_id=job_id,
        edited_cuts=[{"scene_index": 1, "start_sec": 0.0, "end_sec": 5.0, "text": "نص محدث"}],
        output_dir=tmp_path / "outputs" / "mobile_cuts",
        music_track="ambient_meditation",
        enable_music=True,
    )

    assert updated["music_muted"] is False
    assert updated["music_track"]["id"] == "ambient_meditation"
    assert updated["music_track"]["muted"] is False
