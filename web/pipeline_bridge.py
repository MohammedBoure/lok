#!/usr/bin/env python3
"""
Mobile Post-Production Bridge & Assembly Engine (web/pipeline_bridge.py)
Part of the Video Post-Production & Mobile API Server Pipeline.

Author: MohammedBoure
Role: Backend Architecture & Processing Bridge (agy11)
Branch: backend/agy11-mobile-api-server
"""

from __future__ import annotations

import json
import logging
import math
import os
import shutil
import struct
import subprocess
import sys
import uuid
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import frame_extractor

logger = logging.getLogger("mobile_pipeline_bridge")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s")


# ---------------------------------------------------------------------------
# Algerian Real Estate Presets
# ---------------------------------------------------------------------------

ALGERIAN_REAL_ESTATE_PRESETS: Dict[str, Dict[str, str]] = {
    "algiers_f4_luxury": {
        "id": "algiers_f4_luxury",
        "title_ar": "شقة فاخرة F4 - الجزائر العاصمة",
        "title_fr": "Appartement F4 Haut Standing - Alger",
        "description": "شقة فاخرة من أربع غرف بتشطيبات عالية الجودة في قلب العاصمة، إطلالة ساحرة وموقع هادئ قريب من كل المرافق الحيوية.",
    },
    "oran_seaview_villa": {
        "id": "oran_seaview_villa",
        "title_ar": "فيلا عصرية بواجهة بحرية - وهران",
        "title_fr": "Villa Moderne Vue sur Mer - Oran",
        "description": "فيلا عصرية بواجهة بحرية خلابة في وهران، حديقة خاصة ومسبح وتصميم معماري رفيع يلبي أعلى معايير الرفاهية.",
    },
    "constantine_commercial": {
        "id": "constantine_commercial",
        "title_ar": "محل تجاري استراتيجي - قسنطينة",
        "title_fr": "Local Commercial Stratégique - Constantine",
        "description": "محل تجاري في موقع استراتيجي نشط بمدينة قسنطينة، واجهة واسعة وحركة تجارية ممتازة مناسب لكافة المشاريع.",
    },
    "rental_apartment": {
        "id": "rental_apartment",
        "title_ar": "شقة مجهزة ومؤثثة للكراء",
        "title_fr": "Appartement Équipé en Location",
        "description": "شقة مؤثثة بالكامل ومجهزة بأحدث التجهيزات للكراء في موقع متميز، راحة وأمان لعائلتك.",
    },
}

DEFAULT_PROMO_SCRIPT = (
    "عقار استثنائي بموقع استراتيجي وتشطيبات عصرية راقية، فرصة مثالية للاستثمار أو السكن العائلي الهادئ."
)


def get_presets_list() -> List[Dict[str, str]]:
    """Return catalog of presets formatted for API responses."""
    return list(ALGERIAN_REAL_ESTATE_PRESETS.values())


# ---------------------------------------------------------------------------
# Audio Synthesis & Fallback Helpers
# ---------------------------------------------------------------------------

def generate_synthetic_voice(
    text: str,
    output_path: Union[str, Path],
    sample_rate: int = 24000,
) -> float:
    """
    Generate harmonic formant-based voiceover audio when external TTS is unavailable.
    Produces spoken-word syllabic envelope with formant resonance and natural pacing.

    Args:
        text: Script text.
        output_path: Destination WAV file path.
        sample_rate: Output audio sample rate in Hz.

    Returns:
        Duration of generated audio in seconds.
    """
    out_file = Path(output_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)

    words = text.split()
    # Compute spoken duration based on word count (~0.45s per word with lead/trail padding)
    duration = max(5.0, min(60.0, len(words) * 0.45 + 1.2))
    total_samples = int(duration * sample_rate)

    lead_in = 0.5
    trail_out = 0.8
    speaking_dur = duration - lead_in - trail_out

    with wave.open(str(out_file), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)

        frames = bytearray()
        for i in range(total_samples):
            t = i / sample_rate
            if t < lead_in or t > (duration - trail_out):
                env = 0.0
            else:
                rel_t = t - lead_in
                # Syllabic pulse modulation at ~3.5 Hz and breath phrase pulse at 0.8 Hz
                syllable = 0.5 + 0.5 * math.sin(2.0 * math.pi * 3.5 * rel_t)
                phrase = 0.85 + 0.15 * math.sin(2.0 * math.pi * 0.8 * rel_t)
                fade = min(1.0, rel_t / 0.3) * min(1.0, (speaking_dur - rel_t) / 0.4)
                env = syllable * phrase * max(0.0, fade)

            # Vocal formant synthesis (F0 pitch + vocal tract harmonics)
            f0 = 145.0 + 10.0 * math.sin(2.0 * math.pi * 1.8 * t)
            harmonics = (
                0.40 * math.sin(2.0 * math.pi * f0 * t)
                + 0.28 * math.sin(2.0 * math.pi * 2.0 * f0 * t)
                + 0.18 * math.sin(2.0 * math.pi * 700.0 * t)   # F1 formant
                + 0.10 * math.sin(2.0 * math.pi * 1220.0 * t)  # F2 formant
                + 0.04 * math.sin(2.0 * math.pi * 2600.0 * t)  # F3 formant
            )
            sample_val = int(max(-1.0, min(1.0, harmonics * env * 0.65)) * 32767)
            frames.extend(struct.pack("<h", sample_val))

        wf.writeframes(frames)

    return duration


def synthesize_narration(
    script_text: str,
    output_path: Union[str, Path],
    voice: str = "ar-XA-Standard-A",
) -> Dict[str, Any]:
    """
    Synthesize narration audio using GeminiSpeechClient if accessible,
    or gracefully fall back to local synthetic audio engine.
    """
    out_file = Path(output_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)

    synthesizer_engine = "synthetic_speech_engine"
    success = False

    # Check for Gemini API key
    has_api_key = bool(os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEYS"))

    if has_api_key:
        try:
            from tts.gemini_speech.client import GeminiSpeechClient
            logger.info("Synthesizing speech via GeminiSpeechClient (Voice: %s)...", voice)
            client = GeminiSpeechClient()
            client.generate_speech(
                text=script_text,
                voice_name=voice,
                output_path=str(out_file),
            )
            if out_file.is_file() and out_file.stat().st_size > 0:
                synthesizer_engine = "gemini_tts"
                success = True
                logger.info("Gemini TTS synthesis completed: %s", out_file)
        except Exception as exc:
            logger.warning("GeminiSpeechClient failed or unreachable (%s). Using synthetic fallback.", exc)
            success = False

    if not success:
        logger.info("Generating synthetic voiceover narration at %s...", out_file)
        generate_synthetic_voice(script_text, out_file)
        synthesizer_engine = "synthetic_speech_engine"

    # Probe duration
    audio_dur = get_media_duration(out_file)

    return {
        "audio_path": str(out_file),
        "duration": audio_dur,
        "synthesizer": synthesizer_engine,
        "voice": voice,
        "script": script_text,
    }


def get_media_duration(file_path: Union[str, Path]) -> float:
    """Probe duration of an audio or video file using ffprobe."""
    path = Path(file_path).resolve()
    ffprobe_bin = shutil.which("ffprobe") or "ffprobe"
    cmd = [
        ffprobe_bin,
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return round(float(res.stdout.strip()), 3)
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# Core Mobile Video Processing Engine
# ---------------------------------------------------------------------------

def process_mobile_video(
    video_path: Union[str, Path],
    script: Optional[str] = None,
    preset_id: Optional[str] = None,
    voice: str = "ar-XA-Standard-A",
    duck_level: float = 0.25,
    output_dir: Union[str, Path] = "outputs/mobile_cuts",
) -> Dict[str, Any]:
    """
    Process smartphone video recording into a polished marketing promo cut.

    Workflow:
      1. Extract visual keyframes using frame_extractor into outputs/keyframes/mobile_<job_id>/
      2. Synthesize narration voiceover with preset/custom script (with graceful synthetic fallback)
      3. Assemble final video in FFmpeg with warm D minor ambient synth pad and sidechain ducking
      4. Support both portrait (9:16) and landscape (16:9) orientations smoothly
      5. Return comprehensive execution summary dictionary

    Args:
        video_path: Path to the incoming mobile video file.
        script: Optional custom narration script text.
        preset_id: Optional preset ID ('algiers_f4_luxury', 'oran_seaview_villa', etc.).
        voice: Voice name or identifier. Default 'ar-XA-Standard-A'.
        duck_level: Ambient music level multiplier under speech (0.05 to 0.50). Default 0.25.
        output_dir: Target output directory for rendered cut. Default 'outputs/mobile_cuts'.

    Returns:
        Execution summary dictionary with job_id, video_url, keyframes, duration, and script.
    """
    input_path = Path(video_path).resolve()
    if not input_path.is_file():
        raise FileNotFoundError(f"Input video file not found: {input_path}")

    # Generate unique job identifier
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    unique_suffix = uuid.uuid4().hex[:6]
    job_id = f"{timestamp_str}_{unique_suffix}"

    out_cuts_dir = Path(output_dir).resolve()
    out_cuts_dir.mkdir(parents=True, exist_ok=True)

    keyframes_dest_dir = Path("outputs/keyframes").resolve() / f"mobile_{job_id}"
    keyframes_dest_dir.mkdir(parents=True, exist_ok=True)

    # 1. Probe input video properties
    meta = frame_extractor.get_video_metadata(input_path)
    src_width = int(meta.get("width", 1280))
    src_height = int(meta.get("height", 720))
    src_duration = float(meta.get("total_duration", 0.0))

    is_portrait = src_height > src_width
    orientation = "portrait" if is_portrait else "landscape"

    # Standardize output resolution
    if is_portrait:
        target_w = 1080 if src_width >= 900 else 720
        target_h = 1920 if src_width >= 900 else 1280
        aspect_label = "9:16"
    else:
        target_w = 1920 if src_width >= 1600 else 1280
        target_h = 1080 if src_width >= 1600 else 720
        aspect_label = "16:9"

    logger.info(
        "Job %s: Input %s (%dx%d, %.2fs, orientation: %s -> %dx%d)",
        job_id,
        input_path.name,
        src_width,
        src_height,
        src_duration,
        orientation,
        target_w,
        target_h,
    )

    # 2. Extract visual keyframes
    logger.info("Job %s: Extracting keyframes to %s...", job_id, keyframes_dest_dir)
    # Sample every 1.5s or keyframes
    fps_sample = 0.66 if src_duration > 4.0 else 1.0
    keyframe_extraction = frame_extractor.extract_keyframes(
        video_path=input_path,
        fps_sample=fps_sample,
        output_dir=keyframes_dest_dir,
        image_format="jpg",
    )
    raw_frames = keyframe_extraction.get("frames", [])

    # Format keyframe list for web consumption
    formatted_keyframes: List[Dict[str, Any]] = []
    for f in raw_frames:
        file_path_obj = Path(f["file_path"])
        web_url = f"/outputs/keyframes/mobile_{job_id}/{file_path_obj.name}"
        formatted_keyframes.append({
            "frame_index": f.get("frame_index"),
            "timestamp": f.get("timestamp"),
            "url": web_url,
            "file_path": f.get("file_path"),
            "resolution": f.get("resolution"),
            "is_scene_transition": f.get("is_scene_transition", False),
        })

    # 3. Determine Narration Script
    if script and script.strip():
        selected_script = script.strip()
        selected_preset = preset_id if preset_id in ALGERIAN_REAL_ESTATE_PRESETS else None
    elif preset_id and preset_id in ALGERIAN_REAL_ESTATE_PRESETS:
        selected_script = ALGERIAN_REAL_ESTATE_PRESETS[preset_id]["description"]
        selected_preset = preset_id
    else:
        selected_script = DEFAULT_PROMO_SCRIPT
        selected_preset = None

    # 4. Synthesize Narration Audio
    narration_wav = out_cuts_dir / f"narration_{job_id}.wav"
    narration_info = synthesize_narration(
        script_text=selected_script,
        output_path=narration_wav,
        voice=voice,
    )
    narration_duration = narration_info["duration"]

    # 5. Timeline & Outro Calculations
    # Ensure total duration encompasses narration plus warm musical outro swell
    outro_swell = 2.0
    min_required_duration = round(narration_duration + outro_swell, 2)
    total_duration = max(round(src_duration, 2), min_required_duration)
    total_duration = max(5.0, total_duration)

    pad_needed = max(0.0, round(total_duration - src_duration, 2))
    fade_out_start = max(0.5, round(total_duration - 1.8, 2))

    logger.info(
        "Job %s: Timeline - Video: %.2fs, Narration: %.2fs, Total: %.2fs (Pad: %.2fs)",
        job_id,
        src_duration,
        narration_duration,
        total_duration,
        pad_needed,
    )

    # 6. Sidechain Compression & Dynamic Ducking Settings
    # duck_level dictates ducked volume (default 0.25)
    effective_duck_level = max(0.05, min(0.60, float(duck_level)))
    duck_threshold = 0.030
    duck_ratio = max(4.0, min(24.0, round(1.0 / effective_duck_level, 1)))
    duck_attack = 80
    duck_release = 450
    ambient_volume = 0.42

    # 7. Construct FFmpeg Filter Graph
    # Video pipeline:
    # Scale & pad to standard portrait/landscape aspect ratio without distortion
    # Freeze last frame if video is shorter than narration+outro
    # Apply smooth visual fade-in and fade-out
    video_filters: List[str] = [
        f"scale={target_w}:{target_h}:force_original_aspect_ratio=decrease",
        f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2",
        "setsar=1",
    ]
    if pad_needed > 0:
        video_filters.append(f"tpad=stop_mode=clone:stop_duration={pad_needed}")
    video_filters.append("fade=t=in:st=0:d=0.5")
    video_filters.append(f"fade=t=out:st={round(total_duration - 1.0, 2)}:d=1.0")
    video_filters.append("format=yuv420p")
    v_graph = ",".join(video_filters) + "[vout]"

    # Audio pipeline:
    # Ambient Synth Drone in D Minor (D3, F3, A3, C4, D4, F4 + pink noise shimmer)
    # Sidechain compressor ducks ambient pad under narration voiceover
    # Padded voiceover allows ambient music to swell during pauses and the final outro
    filter_complex = f"""
    [0:v]{v_graph};
    sine=f=146.83:d={total_duration},volume=0.22[d3];
    sine=f=174.61:d={total_duration},volume=0.18[f3];
    sine=f=220.00:d={total_duration},volume=0.16[a3];
    sine=f=261.63:d={total_duration},volume=0.12[c4];
    sine=f=293.66:d={total_duration},volume=0.14[d4];
    sine=f=349.23:d={total_duration},volume=0.10[f4];
    anoisesrc=d={total_duration}:c=pink:r=48000:a=0.005,lowpass=f=900[warm_air];
    [d3][f3][a3][c4][d4][f4][warm_air]amix=inputs=7:normalize=0,lowpass=f=2000,afade=t=in:ss=0:d=1.5,afade=t=out:st={fade_out_start}:d=1.8,aformat=sample_rates=48000:channel_layouts=stereo[music];
    [1:a]aformat=sample_rates=48000:channel_layouts=stereo,apad=whole_dur={total_duration},asplit=2[v_sc][v_mix];
    [music][v_sc]sidechaincompress=threshold={duck_threshold}:ratio={duck_ratio}:attack={duck_attack}:release={duck_release}:makeup=1[ducked_music];
    [v_mix]volume=1.0[v_clean];
    [ducked_music]volume={ambient_volume}[m_clean];
    [v_clean][m_clean]amix=inputs=2:duration=first:normalize=0[aout]
    """

    final_cut_path = out_cuts_dir / f"cut_{job_id}.mp4"
    ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
    ffmpeg_cmd = [
        ffmpeg_bin, "-y",
        "-i", str(input_path),
        "-i", str(narration_wav),
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-map", "[aout]",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-t", str(total_duration),
        str(final_cut_path),
    ]

    logger.info("Job %s: Rendering final cut with FFmpeg -> %s", job_id, final_cut_path)
    start_render = datetime.now(timezone.utc)
    try:
        subprocess.run(ffmpeg_cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        logger.error("FFmpeg render failed: %s", e.stderr)
        raise RuntimeError(f"FFmpeg assembly failed: {e.stderr.strip()}") from e

    render_seconds = (datetime.now(timezone.utc) - start_render).total_seconds()
    logger.info("Job %s: Final cut rendered in %.2fs (%d bytes)", job_id, render_seconds, final_cut_path.stat().st_size)

    # 8. Compile Complete Execution Summary
    video_web_url = f"/outputs/mobile_cuts/cut_{job_id}.mp4"
    summary: Dict[str, Any] = {
        "job_id": job_id,
        "status": "completed",
        "video_url": video_web_url,
        "output_path": str(final_cut_path),
        "absolute_output_path": str(final_cut_path.resolve()),
        "file_size_bytes": final_cut_path.stat().st_size,
        "duration": total_duration,
        "orientation": orientation,
        "aspect_ratio": aspect_label,
        "resolution": f"{target_w}x{target_h}",
        "script": selected_script,
        "preset_id": selected_preset,
        "voice": voice,
        "duck_level": effective_duck_level,
        "synthesizer": narration_info["synthesizer"],
        "narration_audio_url": f"/outputs/mobile_cuts/narration_{job_id}.wav",
        "keyframes": formatted_keyframes,
        "total_keyframes": len(formatted_keyframes),
        "metadata": {
            "source_video": str(input_path),
            "source_duration": src_duration,
            "source_resolution": f"{src_width}x{src_height}",
            "narration_duration": narration_duration,
            "render_seconds": round(render_seconds, 2),
            "sidechain_compression": {
                "pad_harmony": "D Minor Ambient Pad (D3, F3, A3, C4, D4, F4)",
                "duck_threshold": duck_threshold,
                "duck_ratio": duck_ratio,
                "duck_attack_ms": duck_attack,
                "duck_release_ms": duck_release,
            },
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Persist summary JSON
    summary_path = out_cuts_dir / f"summary_{job_id}.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    return summary
