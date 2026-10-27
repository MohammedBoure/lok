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
from typing import Any, Callable, Dict, List, Optional, Union

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Load environment configuration (.env)
def _ensure_env_loaded():
    """Load GEMINI_API_KEY from .env if not currently present in os.environ."""
    if os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEYS"):
        return
    candidates = [
        REPO_ROOT / ".env",
        REPO_ROOT / "tts" / ".env",
        Path.cwd() / ".env",
    ]
    for env_path in candidates:
        if env_path.is_file():
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k, v = k.strip(), v.strip().strip("\"'")
                            if k not in os.environ:
                                os.environ[k] = v
            except OSError:
                pass

_ensure_env_loaded()

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
        "recommended_music": "luxury_piano",
    },
    "oran_seaview_villa": {
        "id": "oran_seaview_villa",
        "title_ar": "فيلا عصرية بواجهة بحرية - وهران",
        "title_fr": "Villa Moderne Vue sur Mer - Oran",
        "description": "فيلا عصرية بواجهة بحرية خلابة في وهران، حديقة خاصة ومسبح وتصميم معماري رفيع يلبي أعلى معايير الرفاهية.",
        "recommended_music": "ambient_meditation",
    },
    "constantine_commercial": {
        "id": "constantine_commercial",
        "title_ar": "محل تجاري استراتيجي - قسنطينة",
        "title_fr": "Local Commercial Stratégique - Constantine",
        "description": "محل تجاري في موقع استراتيجي نشط بمدينة قسنطينة، واجهة واسعة وحركة تجارية ممتازة مناسب لكافة المشاريع.",
        "recommended_music": "acoustic_guitar",
    },
    "rental_apartment": {
        "id": "rental_apartment",
        "title_ar": "شقة مجهزة ومؤثثة للكراء",
        "title_fr": "Appartement Équipé en Location",
        "description": "شقة مؤثثة بالكامل ومجهزة بأحدث التجهيزات للكراء في موقع متميز، راحة وأمان لعائلتك.",
        "recommended_music": "acoustic_guitar",
    },
}

DEFAULT_PROMO_SCRIPT = (
    "عقار استثنائي بموقع استراتيجي وتشطيبات عصرية راقية، فرصة مثالية للاستثمار أو السكن العائلي الهادئ."
)


def get_presets_list() -> List[Dict[str, str]]:
    """Return catalog of presets formatted for API responses."""
    return list(ALGERIAN_REAL_ESTATE_PRESETS.values())


# ---------------------------------------------------------------------------
# Open-Source Background Music Library
# ---------------------------------------------------------------------------

MUSIC_LIBRARY: Dict[str, Dict[str, Any]] = {
    "luxury_piano": {
        "id": "luxury_piano",
        "title": "Gymnopédie No. 1 (Erik Satie)",
        "title_ar": "بيانو كلاسيكي راقي (Gymnopédie) - للعقارات الفاخرة",
        "style": "Classical warm acoustic piano",
        "license": "Public Domain / CC0",
        "file": REPO_ROOT / "assets" / "music" / "luxury_piano.mp3",
    },
    "acoustic_guitar": {
        "id": "acoustic_guitar",
        "title": "Solo Acoustic Guitar (Jason Shaw)",
        "title_ar": "غيتار أكوستيك مشرق وهادئ - للمنازل والشقق العائلية",
        "style": "Uplifting melodic acoustic guitar",
        "license": "Creative Commons Attribution 3.0 (CC-BY 3.0)",
        "file": REPO_ROOT / "assets" / "music" / "acoustic_guitar.mp3",
    },
    "ambient_meditation": {
        "id": "ambient_meditation",
        "title": "Acoustic Meditation (Jason Shaw)",
        "title_ar": "موسيقى تأملية مهدئة بإطلالة بحرية - للفلل والشاليهات",
        "style": "Relaxed Mediterranean ambient guitar",
        "license": "Creative Commons Attribution 3.0 (CC-BY 3.0)",
        "file": REPO_ROOT / "assets" / "music" / "ambient_meditation.mp3",
    },
}


def get_music_tracks_list() -> List[Dict[str, str]]:
    """Return catalog of available open-source background music tracks."""
    tracks = []
    for m in MUSIC_LIBRARY.values():
        tracks.append({
            "id": m["id"],
            "title": m["title"],
            "title_ar": m["title_ar"],
            "style": m["style"],
            "license": m["license"],
        })
    return tracks


# Voice mapping from standard web identifiers to supported Gemini TTS voice personas
VOICE_MAPPING: Dict[str, str] = {
    "ar-xa-standard-a": "Aoede",
    "ar-xa-standard-b": "Charon",
    "aoede": "Aoede",
    "charon": "Charon",
    "kore": "Kore",
    "fenrir": "Fenrir",
    "puck": "Puck",
    "leda": "Leda",
    "orus": "Orus",
    "zephyr": "Zephyr",
    "female": "Aoede",
    "male": "Charon",
}


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

    words = [w for w in text.strip().split() if w]
    word_count = max(1, len(words))

    # Syllabic acoustic timing: ~2.4 Arabic words per second
    duration = max(3.5, round(word_count / 2.3, 2))
    num_samples = int(duration * sample_rate)

    f0_base = 140.0
    formants = [(650.0, 0.45), (1700.0, 0.35), (2600.0, 0.20)]

    audio_samples = []
    for i in range(num_samples):
        t = i / sample_rate
        syllable_env = 0.55 + 0.45 * math.sin(2.0 * math.pi * 3.8 * t)
        breath_pause = 0.2 + 0.8 * abs(math.sin(2.0 * math.pi * 0.45 * t))
        mod_env = syllable_env * breath_pause

        sample_val = 0.0
        pitch_drift = 1.0 + 0.04 * math.sin(2.0 * math.pi * 0.6 * t)
        current_f0 = f0_base * pitch_drift

        sample_val += 0.40 * math.sin(2.0 * math.pi * current_f0 * t)
        for f_freq, f_amp in formants:
            sample_val += f_amp * math.sin(2.0 * math.pi * (f_freq + current_f0 * 0.1) * t)

        val = sample_val * mod_env * 0.38
        if t < 0.1:
            val *= (t / 0.1)
        elif t > (duration - 0.2):
            val *= ((duration - t) / 0.2)

        val = max(-0.95, min(0.95, val))
        audio_samples.append(int(val * 32767.0))

    with wave.open(str(out_file), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        packed_data = struct.pack(f"<{len(audio_samples)}h", *audio_samples)
        wf.writeframes(packed_data)

    return duration


def synthesize_narration(
    script_text: str,
    output_path: Union[str, Path],
    voice: str = "ar-XA-Standard-A",
    style_prompt: Optional[str] = None,
    emotional_tone: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Synthesize narration audio using GeminiSpeechClient via official Google Gemini API,
    or gracefully fall back to local synthetic audio engine if API is unreachable.
    Supports emotional tone steering and acoustic style prompt modulation.
    """
    _ensure_env_loaded()
    out_file = Path(output_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)

    synthesizer_engine = "synthetic_speech_engine"
    success = False

    # Resolve voice name to supported Gemini persona
    clean_voice_key = voice.strip().lower()
    gemini_voice = VOICE_MAPPING.get(clean_voice_key, "Aoede")

    # Check for Gemini API key
    has_api_key = bool(os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEYS"))

    if has_api_key:
        try:
            from tts.gemini_speech.client import GeminiSpeechClient
            logger.info(
                "Synthesizing speech via GeminiSpeechClient (Voice: %s, tone: %s, style: %s)...",
                gemini_voice,
                emotional_tone,
                style_prompt,
            )
            client = GeminiSpeechClient()
            client.generate_speech(
                text=script_text,
                voice_name=gemini_voice,
                output_path=str(out_file),
                style_prompt=style_prompt,
                emotional_tone=emotional_tone,
            )
            if out_file.is_file() and out_file.stat().st_size > 0:
                synthesizer_engine = "gemini_tts"
                success = True
                logger.info("Gemini TTS synthesis completed: %s (%d bytes)", out_file, out_file.stat().st_size)
        except Exception as exc:
            logger.warning("GeminiSpeechClient failed or unreachable (%s). Using synthetic fallback.", exc)
            success = False

    if not success:
        logger.info("Generating synthetic voiceover narration fallback at %s...", out_file)
        generate_synthetic_voice(script_text, out_file)
        synthesizer_engine = "synthetic_speech_engine"

    # Probe duration
    audio_dur = get_media_duration(out_file)

    return {
        "audio_path": str(out_file),
        "duration": audio_dur,
        "synthesizer": synthesizer_engine,
        "voice": gemini_voice,
        "requested_voice": voice,
        "script": script_text,
        "emotional_tone": emotional_tone,
        "style_prompt": style_prompt,
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
    music_track: Optional[str] = None,
    output_dir: Union[str, Path] = "outputs/mobile_cuts",
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    auto_mode: bool = False,
    emotional_tone: Optional[str] = None,
    style_prompt: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Process smartphone video recording into a polished marketing promo cut.

    Workflow:
      1. Probe input video properties and resolve target aspect ratio (9:16 or 16:9).
      2. Extract visual keyframes using frame_extractor into outputs/keyframes/mobile_<job_id>/
      3. Perform Autonomous Multimodal Vision Analysis (if auto_mode or no script/preset provided)
         to infer engaging Arabic real estate voiceover, emotional tone, and recommended music.
      4. Synthesize expressive neural narration voiceover with Gemini TTS API modulated by emotional tone.
      5. Assemble final video in FFmpeg with selected open-source royalty-free music and sidechain ducking.
      6. Return comprehensive execution summary dictionary.
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

    # Load customizable production principles
    from config.production_principles_manager import load_principles
    from web.video_annotator import annotate_video

    active_principles = load_principles()
    principles_voice = active_principles.get("voice_principles", {})
    principles_visual = active_principles.get("visual_principles", {})
    principles_annotation = active_principles.get("annotation_principles", {})

    # Telemetry helper
    def _notify(step: int, percent: int, message: str, log: str, extra: Optional[Dict[str, Any]] = None):
        if progress_callback:
            try:
                payload = {
                    "job_id": job_id,
                    "status": "processing",
                    "step": step,
                    "progress_percent": percent,
                    "message": message,
                    "log": log,
                }
                if extra:
                    payload.update(extra)
                progress_callback(payload)
            except Exception as e:
                logger.warning("Progress callback error: %s", e)

    # 1. Probe input video properties
    _notify(
        step=1,
        percent=15,
        message="وكيل الذكاء الاصطناعي يقوم بفحص أبعاد الفيديو واتجاهه...",
        log=f"[فحص الوسائط] تم استلام الفيديو '{input_path.name}'. جاري تحليل الأبعاد والمواصفات الفنية...",
    )

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
    _notify(
        step=2,
        percent=30,
        message="وكيل الذكاء الاصطناعي يستخرج اللقطات المفتاحية والمشاهد بدقة...",
        log="[رؤية حاسوبية] 🖼️ استخراج لقطات المعاينة البصرية من الفيديو...",
    )

    logger.info("Job %s: Extracting keyframes to %s...", job_id, keyframes_dest_dir)
    fps_sample = 0.66 if src_duration > 4.0 else 1.0
    keyframe_extraction = frame_extractor.extract_keyframes(
        video_path=input_path,
        fps_sample=fps_sample,
        output_dir=keyframes_dest_dir,
        image_format="jpg",
    )
    raw_frames = keyframe_extraction.get("frames", [])

    formatted_keyframes: List[Dict[str, Any]] = []
    keyframe_files: List[Path] = []
    for f in raw_frames:
        file_path_obj = Path(f["file_path"])
        abs_path = Path(f.get("absolute_file_path", file_path_obj)).resolve()
        if abs_path.is_file():
            keyframe_files.append(abs_path)
        web_url = f"/outputs/keyframes/mobile_{job_id}/{file_path_obj.name}"
        formatted_keyframes.append({
            "frame_index": f.get("frame_index"),
            "timestamp": f.get("timestamp"),
            "url": web_url,
            "file_path": f.get("file_path"),
            "resolution": f.get("resolution"),
            "is_scene_transition": f.get("is_scene_transition", False),
        })

    # 3. Autonomous Vision Analysis & Script Determination
    is_auto_mode = bool(auto_mode or (not script and not preset_id))
    inferred_script: Optional[str] = None
    vision_engine: Optional[str] = None
    inferred_music: Optional[str] = None

    if is_auto_mode:
        _notify(
            step=2,
            percent=45,
            message="تحليل المشاهد المعمارية عبر Gemini Multimodal Vision...",
            log="[رؤية حاسوبية] 🧠 تحليل المشاهد المعمارية عبر Gemini Multimodal Vision...",
        )
        try:
            from web.vision_analyzer import infer_video_script_and_mood
            vision_result = infer_video_script_and_mood(
                keyframe_paths=keyframe_files,
                video_duration=src_duration,
                preset_hint=preset_id,
            )
            inferred_script = vision_result.get("script")
            selected_script = inferred_script or DEFAULT_PROMO_SCRIPT
            resolved_tone = emotional_tone or vision_result.get("emotional_tone") or principles_voice.get("active_tone_bias", "فاخر وهادئ")
            resolved_style_prompt = style_prompt or vision_result.get("emotional_prompt")
            inferred_music = vision_result.get("recommended_music")
            vision_engine = vision_result.get("engine")
        except Exception as exc:
            logger.warning("Vision analysis error: %s. Using fallback.", exc)
            selected_script = DEFAULT_PROMO_SCRIPT
            inferred_script = selected_script
            resolved_tone = emotional_tone or principles_voice.get("active_tone_bias", "فاخر وهادئ")
            resolved_style_prompt = style_prompt or "Warm, luxurious and prestigious real estate tone"
            inferred_music = "luxury_piano"
            vision_engine = "fallback_on_error"

        _notify(
            step=3,
            percent=60,
            message=f"تم استنتاج الوصف التسويقي بنجاح. الحالة الشعورية: {resolved_tone}",
            log=f"[تحليل شعوري] ✨ تم استنتاج الوصف التسويقي والحالة الشعورية: [{resolved_tone}]",
            extra={"emotional_tone": resolved_tone, "inferred_script": inferred_script},
        )
        selected_preset = preset_id if preset_id in ALGERIAN_REAL_ESTATE_PRESETS else None
    else:
        inferred_script = None
        inferred_music = None
        if script and script.strip():
            selected_script = script.strip()
            selected_preset = preset_id if preset_id in ALGERIAN_REAL_ESTATE_PRESETS else None
        elif preset_id and preset_id in ALGERIAN_REAL_ESTATE_PRESETS:
            selected_script = ALGERIAN_REAL_ESTATE_PRESETS[preset_id]["description"]
            selected_preset = preset_id
        else:
            selected_script = DEFAULT_PROMO_SCRIPT
            selected_preset = None

        preset_tones = {
            "algiers_f4_luxury": "فاخر وهادئ",
            "oran_seaview_villa": "دافئ ومشرق بإطلالة بحرية",
            "constantine_commercial": "متحمس وحيوي",
            "rental_apartment": "دافئ ومريح للعائلات",
        }
        resolved_tone = emotional_tone or preset_tones.get(selected_preset or "", principles_voice.get("active_tone_bias", "فاخر وهادئ"))
        resolved_style_prompt = style_prompt or f"Warm and prestigious real estate presentation in {resolved_tone}"

    # Resolve background music track
    resolved_music_key = principles_visual.get("selected_music_theme", "luxury_piano")
    if music_track and music_track in MUSIC_LIBRARY:
        resolved_music_key = music_track
    elif is_auto_mode and inferred_music and inferred_music in MUSIC_LIBRARY:
        resolved_music_key = inferred_music
    elif selected_preset and "recommended_music" in ALGERIAN_REAL_ESTATE_PRESETS.get(selected_preset, {}):
        resolved_music_key = ALGERIAN_REAL_ESTATE_PRESETS[selected_preset]["recommended_music"]
    music_meta = MUSIC_LIBRARY.get(resolved_music_key, MUSIC_LIBRARY["luxury_piano"])
    music_audio_file = music_meta["file"]

    # 4. Synthesize Narration Audio with Emotional Tone Steering
    clean_voice_key = voice.strip().lower()
    resolved_voice_name = VOICE_MAPPING.get(clean_voice_key, "Aoede")
    _notify(
        step=3,
        percent=70,
        message=f"توليد التعليق الصوتي العصبي عبر Gemini TTS ({resolved_voice_name}) بالحالة الشعورية ({resolved_tone})...",
        log="[توليد صوت] 🎙️ توليد التعليق الصوتي العصبي بالحالة الشعورية المحددة...",
        extra={"emotional_tone": resolved_tone, "inferred_script": inferred_script},
    )

    from config.production_principles_manager import build_tts_style_principles
    tts_principles_style = build_tts_style_principles(emotional_tone=resolved_tone)
    final_style_prompt = f"{resolved_style_prompt}. {tts_principles_style}" if resolved_style_prompt else tts_principles_style

    narration_wav = out_cuts_dir / f"narration_{job_id}.wav"
    narration_info = synthesize_narration(
        script_text=selected_script,
        output_path=narration_wav,
        voice=voice,
        style_prompt=final_style_prompt,
        emotional_tone=resolved_tone,
    )
    narration_duration = narration_info["duration"]

    # 5. Timeline & Outro Calculations
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
    target_duck = principles_visual.get("smart_ducking_volume", duck_level) if duck_level == 0.25 else duck_level
    effective_duck_level = max(0.05, min(0.60, float(target_duck)))
    duck_threshold = 0.030
    duck_ratio = max(4.0, min(24.0, round(1.0 / effective_duck_level, 1)))
    duck_attack = 80
    duck_release = 450
    ambient_volume = 0.38

    _notify(
        step=4,
        percent=85,
        message=f"دمج الموسيقى التصويرية ({music_meta['title']}) وتطبيق خفض الصوت التلقائي (Sidechain Ducking)...",
        log=f"[مكساج صوتي] تم إنتاج الصوت ({narration_duration:.1f}s - {narration_info['synthesizer']}). دمج الموسيقى وتطبيق الخفض الذكي ({effective_duck_level:.2f}).",
    )

    # 7. Construct FFmpeg Filter Graph
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

    # Audio pipeline: Use real open-source music file if available, with mathematical fallback
    use_real_music = music_audio_file.is_file()
    ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
    final_cut_path = out_cuts_dir / f"cut_{job_id}.mp4"

    if use_real_music:
        filter_complex = f"""
        [0:v]{v_graph};
        [2:a]aloop=loop=-1:size=2e+09,atrim=0:{total_duration},afade=t=in:ss=0:d=1.0,afade=t=out:st={fade_out_start}:d=1.8,aformat=sample_rates=48000:channel_layouts=stereo[music];
        [1:a]aformat=sample_rates=48000:channel_layouts=stereo,apad=whole_dur={total_duration},asplit=2[v_sc][v_mix];
        [music][v_sc]sidechaincompress=threshold={duck_threshold}:ratio={duck_ratio}:attack={duck_attack}:release={duck_release}:makeup=1[ducked_music];
        [v_mix]volume=1.0[v_clean];
        [ducked_music]volume={ambient_volume}[m_clean];
        [v_clean][m_clean]amix=inputs=2:duration=first:normalize=0[aout]
        """
        ffmpeg_cmd = [
            ffmpeg_bin, "-y",
            "-i", str(input_path),
            "-i", str(narration_wav),
            "-i", str(music_audio_file),
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
    else:
        # Fallback harmonic synth pad
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

    # 8. Apply Smart Video Annotations & Lower-Third Banners if enabled
    applied_annotations_count = 0
    if principles_annotation.get("enable_auto_annotations", True):
        annotations_list: List[Dict[str, Any]] = []
        banner_title = ""
        if selected_preset and selected_preset in ALGERIAN_REAL_ESTATE_PRESETS:
            banner_title = ALGERIAN_REAL_ESTATE_PRESETS[selected_preset]["title_ar"]
        elif is_auto_mode and inferred_script:
            banner_title = f"عقار استثنائي • {resolved_tone}"
        else:
            banner_title = "فرصة عقارية راقية"

        annotations_list.append({
            "text": banner_title,
            "start_sec": 0.5,
            "end_sec": min(4.5, total_duration),
            "position": principles_annotation.get("position", "lower_third"),
            "style": principles_annotation.get("font_style", "luxury_gold"),
        })

        if is_auto_mode and "vision_result" in locals() and isinstance(vision_result, dict):
            hl_items = vision_result.get("highlights", [])
            for idx, hl in enumerate(hl_items[:3]):
                hl_text = hl if isinstance(hl, str) else hl.get("title", str(hl))
                start_t = 4.5 + (idx * 3.0)
                if start_t < total_duration - 1.0:
                    annotations_list.append({
                        "text": hl_text,
                        "start_sec": round(start_t, 1),
                        "end_sec": round(min(start_t + 2.5, total_duration - 0.5), 1),
                        "position": "lower_third",
                        "style": "emerald_badge",
                    })

        if annotations_list:
            annotated_tmp = out_cuts_dir / f"annotated_{job_id}.mp4"
            try:
                annot_res = annotate_video(
                    input_video_path=final_cut_path,
                    output_video_path=annotated_tmp,
                    annotations=annotations_list,
                )
                ok = isinstance(annot_res, dict) and annot_res.get("status") in ("ok", "completed")
                if ok and annotated_tmp.is_file() and annotated_tmp.stat().st_size > 1000:
                    annotated_tmp.replace(final_cut_path)
                    applied_annotations_count = len(annotations_list)
                    logger.info("Job %s: Video annotations applied successfully (%d overlays)", job_id, applied_annotations_count)
                    _notify(
                        step=5,
                        percent=95,
                        message="تمت إضافة الملصقات والنصوص التوضيحية على الفيديو بنجاح.",
                        log=f"[ملصقات الفيديو] تم تطبيق {applied_annotations_count} نصوص وشارات توضيحية ذكية على المشاهد.",
                    )
            except Exception as annot_err:
                logger.warning("Job %s: Annotation pass encountered non-fatal error: %s", job_id, annot_err)

    # 9. Compile Complete Execution Summary
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
        "auto_mode": is_auto_mode,
        "emotional_tone": resolved_tone,
        "inferred_script": inferred_script,
        "vision_engine": vision_engine,
        "style_prompt": resolved_style_prompt,
        "script": selected_script,
        "preset_id": selected_preset,
        "voice": narration_info["voice"],
        "duck_level": effective_duck_level,
        "synthesizer": narration_info["synthesizer"],
        "narration_audio_url": f"/outputs/mobile_cuts/narration_{job_id}.wav",
        "annotations_applied": applied_annotations_count,
        "music_track": {
            "id": music_meta["id"],
            "title": music_meta["title"],
            "license": music_meta["license"],
        },
        "keyframes": formatted_keyframes,
        "total_keyframes": len(formatted_keyframes),
        "metadata": {
            "source_video": str(input_path),
            "source_duration": src_duration,
            "source_resolution": f"{src_width}x{src_height}",
            "narration_duration": narration_duration,
            "render_seconds": round(render_seconds, 2),
            "annotations_count": applied_annotations_count,
            "sidechain_compression": {
                "music_track": music_meta["title"],
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

    _notify(
        step=5,
        percent=100,
        message="اكتمل إنتاج الفيديو التسويقي بنجاح! جاهز للمعاينة والتحميل.",
        log=f"[إخراج نهائي] تم تصدير الفيديو النهائي ({summary['resolution']}, {total_duration:.1f}s) بنجاح. جاهز للمعاينة والتحميل.",
    )

    return summary
