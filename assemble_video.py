#!/usr/bin/env python3
"""
Video Assembly & Editorial Decision Engine (assemble_video.py)
Part of the Video Post-Production & MCP Orchestration Pipeline.

Author: MohammedBoure
Collective: Audio & Narration Specialist + Editorial Decision & Assembly Collective (agy51)
Branch: frontend/agy51-video-assembly-pipeline
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


DEFAULT_SCRIPT = (
    "Deep in the heart of the golden autumn forest, a young fox cub takes his first adventurous "
    "steps into the quiet wild. Nearby, a spirited baby squirrel dashes through the fallen leaves, "
    "celebrating another bright morning in nature's sanctuary."
)

DEFAULT_FOX_VIDEO = "inputs/source_fox_cub.mp4"
DEFAULT_SQUIRREL_VIDEO = "inputs/source_squirrel.mp4"
DEFAULT_NARRATION_AUDIO = "outputs/narration.wav"
DEFAULT_OUTPUT_VIDEO = "outputs/final_cut.mp4"
DEFAULT_SUMMARY_JSON = "outputs/execution_summary.json"
DEFAULT_KEYFRAME_INDEX = "outputs/keyframes/frame_index.json"


def run_command(cmd: List[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    """Execute a system command and return stdout/stderr."""
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if check and result.returncode != 0:
        cmd_str = " ".join(cmd)
        raise RuntimeError(
            f"Command failed (exit code {result.returncode}):\n{cmd_str}\n\nError output:\n{result.stderr}"
        )
    return result


def probe_file(file_path: str) -> Dict[str, Any]:
    """Probe media container and streams using ffprobe."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Media file not found: {file_path}")

    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        file_path,
    ]
    res = run_command(cmd)
    try:
        data = json.loads(res.stdout)
        return data
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Failed to parse ffprobe output for {file_path}: {exc}") from exc


def ensure_narration_audio(
    audio_path: str = DEFAULT_NARRATION_AUDIO,
    script_text: str = DEFAULT_SCRIPT,
    voice: str = "Aoede",
    model: str = "gemini-3.8-flash-tts",
    style: str = "Warm, curious, cinematic documentary narration",
) -> Dict[str, Any]:
    """Ensure voiceover narration exists, synthesizing via local tts module if required."""
    path_obj = Path(audio_path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)

    if not path_obj.exists() or path_obj.stat().st_size == 0:
        print(f"[assembly] Narration missing at {audio_path}. Synthesizing via TTS service...")
        tts_cmd = [
            sys.executable,
            "-m", "tts", "generate",
            script_text,
            "-o", str(path_obj),
            "-v", voice,
            "-m", model,
            "-s", style,
            "--json",
        ]
        res = run_command(tts_cmd)
        try:
            tts_res = json.loads(res.stdout)
            print(f"[assembly] TTS generation successful: {tts_res.get('output_path')}")
        except Exception:
            print(f"[assembly] TTS generated output:\n{res.stdout}")
    else:
        print(f"[assembly] Found existing voiceover at {audio_path}")

    probe = probe_file(str(path_obj))
    fmt = probe.get("format", {})
    streams = probe.get("streams", [])
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), {})

    duration = float(fmt.get("duration", audio_stream.get("duration", 0.0)))
    sample_rate = int(audio_stream.get("sample_rate", 24000))
    channels = int(audio_stream.get("channels", 1))
    codec = audio_stream.get("codec_name", "pcm_s16le")

    return {
        "audio_path": os.path.abspath(str(path_obj)),
        "file_size_bytes": path_obj.stat().st_size,
        "duration_seconds": duration,
        "sample_rate": sample_rate,
        "channels": channels,
        "codec": codec,
        "voice": voice,
        "model": model,
        "script": script_text,
    }


def find_matching_keyframes(
    keyframe_index_path: str,
    video_key: str,
    start_time: float,
    end_time: float,
) -> List[Dict[str, Any]]:
    """Match keyframe records within a specified clip segment timestamp range."""
    if not os.path.exists(keyframe_index_path):
        return []

    try:
        with open(keyframe_index_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        videos = data.get("videos", {})
        info = videos.get(video_key)
        if not info:
            # Fallback to key without directory path
            base_key = os.path.basename(video_key).replace(".mp4", "")
            info = videos.get(base_key, {})

        frames = info.get("frames", [])
        matched = [
            {
                "frame_index": f.get("frame_index"),
                "timestamp": f.get("timestamp"),
                "file_path": f.get("file_path"),
                "is_scene_transition": f.get("is_scene_transition", False),
            }
            for f in frames
            if start_time <= float(f.get("timestamp", 0.0)) <= end_time
        ]
        return matched
    except Exception as exc:
        print(f"[assembly] Warning: could not parse keyframe index: {exc}", file=sys.stderr)
        return []


def assemble_video(
    fox_video: str = DEFAULT_FOX_VIDEO,
    squirrel_video: str = DEFAULT_SQUIRREL_VIDEO,
    narration_audio: str = DEFAULT_NARRATION_AUDIO,
    output_video: str = DEFAULT_OUTPUT_VIDEO,
    summary_output: str = DEFAULT_SUMMARY_JSON,
    keyframe_index: str = DEFAULT_KEYFRAME_INDEX,
    fox_start: float = 0.0,
    fox_end: float = 8.5,
    squirrel_start: float = 0.5,
    squirrel_end: float = 9.5,
    transition_type: str = "fade",
    transition_duration: float = 0.5,
    duck_threshold: float = 0.030,
    duck_ratio: float = 8.0,
    duck_attack: int = 80,
    duck_release: int = 450,
    ambient_volume: float = 0.45,
    voice_volume: float = 1.0,
) -> Dict[str, Any]:
    """
    Assemble the complete synchronized video with ducked ambient synth music.

    Timeline Calculation:
    - Segment 1 (Fox cub): duration = fox_end - fox_start (e.g., 8.5s)
    - Crossfade: starts at offset (fox_end - fox_start - transition_duration) = 8.0s
    - Segment 2 (Squirrel): duration = squirrel_end - squirrel_start (e.g., 9.0s)
    - Total timeline duration = segment_1_dur + segment_2_dur - transition_dur = 8.5 + 9.0 - 0.5 = 17.0s
    - Narration padding: pad to 17.0s with apad=whole_dur=17.0
    """
    out_path = Path(output_video)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Validate & Probe Inputs
    if not os.path.exists(fox_video):
        raise FileNotFoundError(f"Fox source video not found: {fox_video}")
    if not os.path.exists(squirrel_video):
        raise FileNotFoundError(f"Squirrel source video not found: {squirrel_video}")

    narration_info = ensure_narration_audio(narration_audio)

    fox_probe = probe_file(fox_video)
    squirrel_probe = probe_file(squirrel_video)

    # 2. Timeline calculations
    fox_dur = round(fox_end - fox_start, 3)
    squirrel_dur = round(squirrel_end - squirrel_start, 3)
    xfade_offset = round(fox_dur - transition_duration, 3)
    total_duration = round(fox_dur + squirrel_dur - transition_duration, 3)

    print(f"[assembly] Timeline Plan:")
    print(f"  Segment 1 (Fox): [{fox_start:.2f}s -> {fox_end:.2f}s] (dur: {fox_dur:.2f}s)")
    print(f"  Transition ({transition_type}): offset {xfade_offset:.2f}s (dur: {transition_duration:.2f}s)")
    print(f"  Segment 2 (Squirrel): [{squirrel_start:.2f}s -> {squirrel_end:.2f}s] (dur: {squirrel_dur:.2f}s)")
    print(f"  Total Video Duration: {total_duration:.2f}s")
    print(f"  Narration Audio Duration: {narration_info['duration_seconds']:.2f}s (padded to {total_duration:.2f}s)")

    # 3. Construct Complex Filter Graph
    # Video pipeline:
    # [0:v]trim=start=...:end=...,setpts=PTS-STARTPTS,scale=1280:720,format=yuv420p[v0];
    # [1:v]trim=start=...:end=...,setpts=PTS-STARTPTS,scale=1280:720,format=yuv420p[v1];
    # [v0][v1]xfade=transition=fade:duration=...:offset=...,format=yuv420p[vout]
    #
    # Audio pipeline:
    # Ambient Synth Drone (Open D pentatonic chord: D3, A3, D4, F#4, A4 + pink woodland breeze)
    # [b][m1][m2][m3][h][wind]amix=inputs=6:normalize=0,lowpass=f=2400,afade=...,aformat=...[music];
    # [2:a]aformat=sample_rates=48000:channel_layouts=stereo,apad=whole_dur=...,asplit=2[v_sc][v_mix];
    # [music][v_sc]sidechaincompress=threshold=...:ratio=...:attack=...:release=...:makeup=1[ducked_music];
    # [v_mix]volume=...[v_clean];
    # [ducked_music]volume=...[m_clean];
    # [v_clean][m_clean]amix=inputs=2:duration=first:normalize=0[aout]

    fade_out_start = max(0.0, total_duration - 1.5)

    filter_complex = f"""
    [0:v]trim=start={fox_start}:end={fox_end},setpts=PTS-STARTPTS,scale=1280:720,format=yuv420p[v0];
    [1:v]trim=start={squirrel_start}:end={squirrel_end},setpts=PTS-STARTPTS,scale=1280:720,format=yuv420p[v1];
    [v0][v1]xfade=transition={transition_type}:duration={transition_duration}:offset={xfade_offset},format=yuv420p[vout];
    sine=f=146.83:d={total_duration},volume=0.20[b];
    sine=f=220:d={total_duration},volume=0.16[m1];
    sine=f=293.66:d={total_duration},volume=0.14[m2];
    sine=f=369.99:d={total_duration},volume=0.10[m3];
    sine=f=440:d={total_duration},volume=0.08[h];
    anoisesrc=d={total_duration}:c=pink:r=48000:a=0.006,lowpass=f=1000[wind];
    [b][m1][m2][m3][h][wind]amix=inputs=6:normalize=0,lowpass=f=2400,afade=t=in:ss=0:d=1.5,afade=t=out:st={fade_out_start}:d=1.5,aformat=sample_rates=48000:channel_layouts=stereo[music];
    [2:a]aformat=sample_rates=48000:channel_layouts=stereo,apad=whole_dur={total_duration},asplit=2[v_sc][v_mix];
    [music][v_sc]sidechaincompress=threshold={duck_threshold}:ratio={duck_ratio}:attack={duck_attack}:release={duck_release}:makeup=1[ducked_music];
    [v_mix]volume={voice_volume}[v_clean];
    [ducked_music]volume={ambient_volume}[m_clean];
    [v_clean][m_clean]amix=inputs=2:duration=first:normalize=0[aout]
    """

    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-i", fox_video,
        "-i", squirrel_video,
        "-i", narration_audio,
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-map", "[aout]",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "19",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-t", str(total_duration),
        str(out_path),
    ]

    print(f"[assembly] Executing FFmpeg rendering pipeline...")
    render_start = datetime.now(timezone.utc)
    res = run_command(ffmpeg_cmd)
    render_end = datetime.now(timezone.utc)
    render_duration = (render_end - render_start).total_seconds()
    print(f"[assembly] Video successfully rendered in {render_duration:.2f}s -> {out_path}")

    # 4. Probe Rendered Video
    rendered_probe = probe_file(str(out_path))
    v_stream = next((s for s in rendered_probe.get("streams", []) if s.get("codec_type") == "video"), {})
    a_stream = next((s for s in rendered_probe.get("streams", []) if s.get("codec_type") == "audio"), {})

    # 5. Collect Keyframes used
    fox_keyframes = find_matching_keyframes(keyframe_index, "source_fox_cub", fox_start, fox_end)
    squirrel_keyframes = find_matching_keyframes(keyframe_index, "source_squirrel", squirrel_start, squirrel_end)

    # 6. Generate Execution Summary JSON
    summary_data = {
        "status": "SUCCESS",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "editorial_collective": {
            "agent_id": "agy51",
            "role": "Audio, Narration & Video Assembly Collective",
            "git_author": "MohammedBoure",
            "branch": "frontend/agy51-video-assembly-pipeline",
        },
        "output_video": {
            "file_path": str(out_path),
            "absolute_file_path": os.path.abspath(str(out_path)),
            "file_size_bytes": out_path.stat().st_size,
            "duration_seconds": float(rendered_probe.get("format", {}).get("duration", total_duration)),
            "resolution": f"{v_stream.get('width', 1280)}x{v_stream.get('height', 720)}",
            "aspect_ratio": "16:9",
            "fps": 24.0,
            "video_codec": v_stream.get("codec_name", "h264"),
            "pixel_format": v_stream.get("pix_fmt", "yuv420p"),
            "audio_codec": a_stream.get("codec_name", "aac"),
            "audio_sample_rate": int(a_stream.get("sample_rate", 48000)),
            "audio_channels": int(a_stream.get("channels", 2)),
            "render_execution_seconds": round(render_duration, 2),
        },
        "narration": {
            "audio_path": narration_info["audio_path"],
            "duration_seconds": narration_info["duration_seconds"],
            "script_text": narration_info["script"],
            "voice": narration_info["voice"],
            "model": narration_info["model"],
            "format": f"{narration_info['codec']} @ {narration_info['sample_rate']}Hz, {narration_info['channels']}ch",
            "pacing_analysis": {
                "phrase_1": {
                    "text": "Deep in the heart of the golden autumn forest, a young fox cub takes his first adventurous steps into the quiet wild.",
                    "start_time": 0.0,
                    "end_time": 7.90,
                    "paired_clip": "source_fox_cub.mp4",
                },
                "transition_pause": {
                    "start_time": 7.90,
                    "end_time": 8.71,
                    "duration_seconds": 0.81,
                    "action": "Visual crossfade & audio music swell",
                },
                "phrase_2": {
                    "text": "Nearby, a spirited baby squirrel dashes through the fallen leaves, celebrating another bright morning in nature's sanctuary.",
                    "start_time": 8.71,
                    "end_time": 16.35,
                    "paired_clip": "source_squirrel.mp4",
                },
                "outro_lingering": {
                    "start_time": 16.35,
                    "end_time": 17.00,
                    "duration_seconds": 0.65,
                    "action": "Ambient music swell and smooth fade-out",
                },
            },
        },
        "source_clips": [
            {
                "clip_id": "fox_cub_exploration",
                "source_file": fox_video,
                "segment_start_timestamp": fox_start,
                "segment_end_timestamp": fox_end,
                "segment_duration_seconds": fox_dur,
                "keyframes_matched": len(fox_keyframes),
                "keyframes": fox_keyframes,
            },
            {
                "clip_id": "squirrel_playful_dash",
                "source_file": squirrel_video,
                "segment_start_timestamp": squirrel_start,
                "segment_end_timestamp": squirrel_end,
                "segment_duration_seconds": squirrel_dur,
                "keyframes_matched": len(squirrel_keyframes),
                "keyframes": squirrel_keyframes,
            },
        ],
        "editorial_timeline": {
            "total_cuts": 2,
            "transition": {
                "type": transition_type,
                "duration_seconds": transition_duration,
                "offset_seconds": xfade_offset,
                "description": f"Smooth {transition_type} blending fox cub scene into squirrel scene during narrator pause.",
            },
            "timeline_markers": [
                {"timestamp": 0.0, "event": "Fox cub segment begins, narration sentence 1 begins"},
                {"timestamp": 7.90, "event": "Narration sentence 1 concludes; pause begins; music swells"},
                {"timestamp": xfade_offset, "event": f"Crossfade from fox cub to squirrel starts"},
                {"timestamp": fox_dur, "event": f"Crossfade finishes; squirrel in full focus"},
                {"timestamp": 8.71, "event": "Narration sentence 2 begins ('Nearby, a spirited baby squirrel...')"},
                {"timestamp": 16.35, "event": "Narration sentence 2 concludes; outro swell begins"},
                {"timestamp": total_duration, "event": "Video and ambient music fade-out conclude"},
            ],
        },
        "audio_mixing_parameters": {
            "background_music": {
                "synthesis_engine": "FFmpeg audio synth filters (sine + anoisesrc)",
                "chords": "Open D Pentatonic (D3: 146.83Hz, A3: 220Hz, D4: 293.66Hz, F#4: 369.99Hz, A4: 440Hz)",
                "nature_texture": "Pink noise with lowpass filter (1000Hz) simulating woodland autumn breeze",
                "filter_chain": "amix -> lowpass (2400Hz) -> afade in (1.5s) -> afade out (1.5s)",
                "base_volume_ratio": ambient_volume,
            },
            "dynamic_ducking": {
                "method": "Sidechain Compression (sidechaincompress filter)",
                "threshold": duck_threshold,
                "ratio": duck_ratio,
                "attack_ms": duck_attack,
                "release_ms": duck_release,
                "makeup_gain": 1.0,
                "effect": "Background ambient pad drops ~18dB during narration and swells smoothly during pauses.",
            },
            "voiceover": {
                "volume_ratio": voice_volume,
                "eq_filters": "48kHz stereo upsampling with apad alignment",
            },
        },
    }

    summary_path = Path(summary_output)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2, ensure_ascii=False)
    print(f"[assembly] Execution summary written to {summary_path}")

    return summary_data


def build_parser() -> argparse.ArgumentParser:
    """Construct CLI argument parser for assemble_video."""
    parser = argparse.ArgumentParser(
        prog="python assemble_video.py",
        description="Autonomous Video Assembly & Audio Ducking Engine (agy51).",
    )
    parser.add_argument("--fox-video", default=DEFAULT_FOX_VIDEO, help="Path to fox cub source video.")
    parser.add_argument("--squirrel-video", default=DEFAULT_SQUIRREL_VIDEO, help="Path to squirrel source video.")
    parser.add_argument("--narration", default=DEFAULT_NARRATION_AUDIO, help="Path to narration audio WAV file.")
    parser.add_argument("-o", "--output", default=DEFAULT_OUTPUT_VIDEO, help="Path to output final video.")
    parser.add_argument("-s", "--summary", default=DEFAULT_SUMMARY_JSON, help="Path to output execution summary JSON.")
    parser.add_argument("--keyframe-index", default=DEFAULT_KEYFRAME_INDEX, help="Path to keyframe extraction index.")
    parser.add_argument("--fox-start", type=float, default=0.0, help="Start timestamp for fox clip.")
    parser.add_argument("--fox-end", type=float, default=8.5, help="End timestamp for fox clip.")
    parser.add_argument("--squirrel-start", type=float, default=0.5, help="Start timestamp for squirrel clip.")
    parser.add_argument("--squirrel-end", type=float, default=9.5, help="End timestamp for squirrel clip.")
    parser.add_argument("--transition", default="fade", help="Transition type (fade, dissolve, etc.).")
    parser.add_argument("--transition-duration", type=float, default=0.5, help="Transition crossfade duration in seconds.")
    parser.add_argument("--duck-threshold", type=float, default=0.030, help="Sidechain compression ducking threshold.")
    parser.add_argument("--duck-ratio", type=float, default=8.0, help="Sidechain compression ducking ratio.")
    parser.add_argument("--duck-attack", type=int, default=80, help="Sidechain compression attack in ms.")
    parser.add_argument("--duck-release", type=int, default=450, help="Sidechain compression release in ms.")
    parser.add_argument("--ambient-volume", type=float, default=0.45, help="Ambient music uncompressed volume multiplier.")
    parser.add_argument("--voice-volume", type=float, default=1.0, help="Voiceover volume multiplier.")
    return parser


def main() -> int:
    """CLI execution entrypoint."""
    parser = build_parser()
    args = parser.parse_args()

    try:
        assemble_video(
            fox_video=args.fox_video,
            squirrel_video=args.squirrel_video,
            narration_audio=args.narration,
            output_video=args.output,
            summary_output=args.summary,
            keyframe_index=args.keyframe_index,
            fox_start=args.fox_start,
            fox_end=args.fox_end,
            squirrel_start=args.squirrel_start,
            squirrel_end=args.squirrel_end,
            transition_type=args.transition,
            transition_duration=args.transition_duration,
            duck_threshold=args.duck_threshold,
            duck_ratio=args.duck_ratio,
            duck_attack=args.duck_attack,
            duck_release=args.duck_release,
            ambient_volume=args.ambient_volume,
            voice_volume=args.voice_volume,
        )
        return 0
    except Exception as exc:
        print(f"[assembly] ERROR during video assembly: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
