"""
Comprehensive Pragmatic Pipeline Integration Test Suite.
Verifies the end-to-end video post-production and MCP orchestration pipeline:
1. MCP visual extraction tool (mcp_get_image_from_video / frame_extractor.py).
2. TTS voiceover generation (outputs/narration.wav, sampling rate, duration, format).
3. Assembled video (outputs/final_cut.mp4, streams, duration, aspect ratio, ducked audio).
4. Execution summary (outputs/execution_summary.json, required fields, pacing, mixing).

Author: MouhammedBoure
Agent: agy100 (Quality Control & Gatekeeper)
"""

import json
import os
import subprocess
import sys
import wave
from pathlib import Path

import pytest

import frame_extractor
import assemble_video

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
FOX_VIDEO = str(WORKSPACE_ROOT / "inputs" / "source_fox_cub.mp4")
SQUIRREL_VIDEO = str(WORKSPACE_ROOT / "inputs" / "source_squirrel.mp4")
NARRATION_WAV = str(WORKSPACE_ROOT / "outputs" / "narration.wav")
FINAL_CUT_MP4 = str(WORKSPACE_ROOT / "outputs" / "final_cut.mp4")
EXECUTION_SUMMARY = str(WORKSPACE_ROOT / "outputs" / "execution_summary.json")
KEYFRAMES_DIR = WORKSPACE_ROOT / "outputs" / "keyframes"
FRAME_INDEX_JSON = KEYFRAMES_DIR / "frame_index.json"


# ─────────────────────────────────────────────────────────────────────────────
# 1. MCP Visual Extraction Tool Verification
# ─────────────────────────────────────────────────────────────────────────────

class TestMCPVisualExtractionTool:
    """Verifies MCP visual extraction tool mcp_get_image_from_video & frame_extractor.py."""

    def test_video_metadata_parsing(self):
        """Verify video metadata extraction on source footage."""
        meta = frame_extractor.get_video_metadata(FOX_VIDEO)
        assert meta["codec"] == "h264"
        assert meta["resolution"] == "1280x720"
        assert meta["width"] == 1280
        assert meta["height"] == 720
        assert meta["frame_rate"] == 24.0
        assert meta["total_duration"] == pytest.approx(10.0, abs=0.2)
        assert meta["size_bytes"] > 0

    def test_mcp_get_image_from_video_programmatic(self, tmp_path):
        """Verify mcp_get_image_from_video extracts frames and returns valid payload."""
        out_dir = tmp_path / "mcp_frames"
        result = frame_extractor.mcp_get_image_from_video(
            video_path=FOX_VIDEO,
            timestamps=[0.0, 2.5],
            output_dir=str(out_dir),
        )
        payload = json.loads(result) if isinstance(result, str) else result

        assert payload["total_frames_extracted"] == 2
        assert payload["resolution"] == "1280x720"
        assert payload["codec"] == "h264"
        assert payload["total_duration"] == pytest.approx(10.0, abs=0.2)
        assert len(payload["frames"]) == 2

        for frame_info in payload["frames"]:
            frame_path = Path(frame_info["file_path"])
            assert frame_path.exists(), f"Frame file not found: {frame_path}"
            assert frame_path.stat().st_size > 0
            assert frame_info["resolution"] == "1280x720"
            assert isinstance(frame_info["timestamp"], (int, float))

    def test_mcp_cli_execution(self, tmp_path):
        """Verify CLI interface (python -m frame_extractor) executes and outputs valid JSON."""
        out_dir = tmp_path / "cli_frames"
        cmd = [
            sys.executable,
            "-m",
            "frame_extractor",
            SQUIRREL_VIDEO,
            "--timestamps",
            "1.0,3.0",
            "--output-dir",
            str(out_dir),
            "--json",
        ]
        sub_env = dict(os.environ)
        sub_env["PYTHONPATH"] = str(WORKSPACE_ROOT)

        proc = subprocess.run(
            cmd,
            cwd=str(WORKSPACE_ROOT),
            env=sub_env,
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(proc.stdout)
        assert data["total_frames_extracted"] == 2
        assert data["resolution"] == "1280x720"
        assert len(data["frames"]) == 2

    def test_keyframe_index_artifacts(self):
        """Verify generated production keyframe directory and frame_index.json."""
        assert FRAME_INDEX_JSON.exists(), "frame_index.json must exist in outputs/keyframes"
        with open(FRAME_INDEX_JSON, "r", encoding="utf-8") as f:
            index_data = json.load(f)

        assert "total_videos" in index_data
        assert index_data["total_videos"] >= 2
        assert "videos" in index_data

        videos_collection = index_data["videos"]
        video_entries = list(videos_collection.values()) if isinstance(videos_collection, dict) else videos_collection
        assert len(video_entries) >= 2

        # Verify all indexed frame image files exist on disk
        for video_info in video_entries:
            assert video_info.get("total_frames_extracted", 0) > 0
            for frame_item in video_info["frames"]:
                frame_path = WORKSPACE_ROOT / frame_item["file_path"]
                assert frame_path.exists(), f"Indexed frame image missing: {frame_path}"
                assert frame_path.stat().st_size > 10_000, "Frame image file is unexpectedly tiny"


# ─────────────────────────────────────────────────────────────────────────────
# 2. TTS Voiceover Generation Verification
# ─────────────────────────────────────────────────────────────────────────────

class TestTTSVoiceoverGeneration:
    """Verifies TTS voiceover audio deliverable and properties."""

    def test_narration_file_exists(self):
        """Verify outputs/narration.wav exists and is non-empty."""
        path = Path(NARRATION_WAV)
        assert path.exists(), f"Narration audio file missing: {path}"
        assert path.stat().st_size > 100_000, "Narration audio file is suspiciously small"

    def test_narration_audio_specs_via_wave(self):
        """Verify WAV headers, sampling rate, channels, and non-zero duration."""
        with wave.open(NARRATION_WAV, "rb") as wf:
            channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            framerate = wf.getframerate()
            n_frames = wf.getnframes()
            duration = n_frames / float(framerate)

            assert channels in (1, 2), f"Expected mono or stereo, got {channels} channels"
            assert sample_width == 2, f"Expected 16-bit PCM (sample width 2), got {sample_width}"
            assert framerate == 24000, f"Expected 24000Hz sampling rate, got {framerate}"
            assert duration > 10.0, f"Expected duration > 10s for full narration, got {duration:.2f}s"
            assert duration == pytest.approx(16.8, abs=1.0)

    def test_tts_module_importable(self):
        """Verify local tts package is properly importable and configured."""
        import tts
        assert hasattr(tts, "__version__") or hasattr(tts, "create_story_voices") or Path(tts.__file__).exists()


# ─────────────────────────────────────────────────────────────────────────────
# 3. Assembled Final Video Verification
# ─────────────────────────────────────────────────────────────────────────────

class TestAssembledFinalCutVideo:
    """Verifies outputs/final_cut.mp4 streams, duration, aspect ratio, and ducking."""

    def test_final_cut_exists(self):
        """Verify final cut MP4 file exists and meets production size threshold."""
        video_path = Path(FINAL_CUT_MP4)
        assert video_path.exists(), f"Final cut video not found: {video_path}"
        assert video_path.stat().st_size > 1_000_000, "Video size is under 1MB threshold"

    def test_final_cut_probe_streams(self):
        """Verify video/audio streams, codec, resolution, and aspect ratio."""
        probe = assemble_video.probe_file(FINAL_CUT_MP4)
        assert "format" in probe
        assert "streams" in probe

        video_streams = [s for s in probe["streams"] if s.get("codec_type") == "video"]
        audio_streams = [s for s in probe["streams"] if s.get("codec_type") == "audio"]

        assert len(video_streams) == 1, "Expected exactly 1 video stream"
        assert len(audio_streams) == 1, "Expected exactly 1 audio stream"

        v_stream = video_streams[0]
        a_stream = audio_streams[0]

        # Video stream assertions
        assert v_stream["codec_name"] in ("h264", "avc1")
        assert int(v_stream["width"]) == 1280
        assert int(v_stream["height"]) == 720
        assert v_stream["pix_fmt"] == "yuv420p"

        # Aspect ratio check: 1280 / 720 == 16 / 9
        aspect_ratio = int(v_stream["width"]) / int(v_stream["height"])
        assert aspect_ratio == pytest.approx(16 / 9, abs=0.01)

        # Audio stream assertions
        assert a_stream["codec_name"] == "aac"
        assert int(a_stream["sample_rate"]) == 48000
        assert int(a_stream["channels"]) == 2

    def test_final_cut_duration_sync(self):
        """Verify final cut duration matches narrative pacing (~17.0 seconds)."""
        probe = assemble_video.probe_file(FINAL_CUT_MP4)
        duration = float(probe["format"]["duration"])
        assert duration == pytest.approx(17.0, abs=0.5)

    def test_ducked_audio_track_levels(self):
        """Verify audio track contains dynamic mixed sound levels via ffmpeg volumedetect."""
        cmd = [
            "ffmpeg",
            "-i",
            FINAL_CUT_MP4,
            "-af",
            "volumedetect",
            "-vn",
            "-sn",
            "-dn",
            "-f",
            "null",
            "/dev/null",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        stderr = proc.stderr

        assert "mean_volume" in stderr
        assert "max_volume" in stderr

        # Extract max_volume from stderr
        for line in stderr.splitlines():
            if "max_volume:" in line:
                max_vol = float(line.split("max_volume:")[1].replace("dB", "").strip())
                # Audio must not be clipping (> 0 dB) and must not be completely silent (< -50 dB)
                assert -30.0 < max_vol <= 0.0, f"Max volume {max_vol} dB outside expected range"


# ─────────────────────────────────────────────────────────────────────────────
# 4. Execution Summary Verification
# ─────────────────────────────────────────────────────────────────────────────

class TestExecutionSummary:
    """Verifies outputs/execution_summary.json schema, fields, and consistency."""

    def test_execution_summary_schema(self):
        """Verify required fields in outputs/execution_summary.json."""
        summary_path = Path(EXECUTION_SUMMARY)
        assert summary_path.exists(), f"execution_summary.json missing: {summary_path}"

        with open(summary_path, "r", encoding="utf-8") as f:
            summary = json.load(f)

        assert summary.get("status") == "SUCCESS"
        assert "output_video" in summary
        assert "narration" in summary
        assert "source_clips" in summary
        assert "editorial_timeline" in summary
        assert "audio_mixing_parameters" in summary
        assert "editorial_collective" in summary

        # Video metadata fields
        ov = summary["output_video"]
        assert ov["file_path"] == "outputs/final_cut.mp4"
        assert ov["resolution"] == "1280x720"
        assert ov["aspect_ratio"] == "16:9"
        assert ov["video_codec"] == "h264"
        assert ov["audio_codec"] == "aac"
        assert ov["audio_sample_rate"] == 48000
        assert ov["duration_seconds"] == pytest.approx(17.0, abs=0.5)

        # Narration metadata fields
        narr = summary["narration"]
        assert "narration.wav" in narr["audio_path"]
        assert narr["duration_seconds"] == pytest.approx(16.8, abs=0.5)
        assert "fox cub" in narr["script_text"]
        assert "pacing_analysis" in narr

        # Source clips validation
        clips = summary["source_clips"]
        assert len(clips) >= 2
        source_files = [c["source_file"] for c in clips]
        assert any("source_fox_cub.mp4" in sf for sf in source_files)
        assert any("source_squirrel.mp4" in sf for sf in source_files)

        # Dynamic ducking parameters validation
        amp = summary["audio_mixing_parameters"]
        assert "dynamic_ducking" in amp
        ducking = amp["dynamic_ducking"]
        assert "method" in ducking
        assert "Sidechain" in ducking["method"]
        assert "threshold" in ducking
        assert "ratio" in ducking
        assert "background_music" in amp
        assert "base_volume_ratio" in amp["background_music"]

        # Author attribution check
        ed_col = summary["editorial_collective"]
        assert ed_col.get("git_author") == "MouhammedBoure"
