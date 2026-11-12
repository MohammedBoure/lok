#!/usr/bin/env python3
"""
Autonomous Video Montage & Editorial Decision Engine (web/video_editor.py)
Provides high-performance FFmpeg video trimming, shot slicing, multi-segment assembly,
and AI-directed montage generation.

Author: MouhammedBoure
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("video_editor")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s")


# ---------------------------------------------------------------------------
# Media Probing & Timing Helpers
# ---------------------------------------------------------------------------

def probe_video_stream(video_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Probe video container, stream dimensions, fps, duration, and audio presence.
    """
    path = Path(video_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Video file not found: {path}")

    ffprobe_bin = shutil.which("ffprobe") or "ffprobe"
    cmd = [
        ffprobe_bin,
        "-v", "error",
        "-show_entries", "stream=width,height,r_frame_rate,codec_name,codec_type,duration:format=duration,size",
        "-of", "json",
        str(path)
    ]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)
    except Exception as exc:
        raise RuntimeError(f"ffprobe failed to probe '{path}': {exc}") from exc

    streams = data.get("streams", [])
    v_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
    a_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

    fmt = data.get("format", {})
    raw_duration = v_stream.get("duration") or fmt.get("duration", 0.0)
    try:
        duration = round(float(raw_duration), 3)
    except (ValueError, TypeError):
        duration = 0.0

    width = int(v_stream.get("width", 1280))
    height = int(v_stream.get("height", 720))

    r_fps = v_stream.get("r_frame_rate", "24/1")
    try:
        num, den = map(float, r_fps.split("/"))
        fps = round(num / den, 2) if den != 0 else 24.0
    except (ValueError, ZeroDivisionError):
        fps = 24.0

    return {
        "path": str(path),
        "duration": duration,
        "width": width,
        "height": height,
        "fps": fps,
        "codec": v_stream.get("codec_name", "h264"),
        "has_audio": a_stream is not None,
        "size_bytes": path.stat().st_size,
    }


def parse_time_to_seconds(val: Union[str, float, int], total_duration: float = 3600.0) -> float:
    """
    Parse timestamp string or numeric value into seconds.
    Supports formats:
      - Raw seconds: "12", "12.5", 12.5
      - MM:SS: "01:23", "0:45"
      - HH:MM:SS: "00:01:23"
    """
    if isinstance(val, (int, float)):
        return max(0.0, min(float(val), total_duration))

    s = str(val).strip()
    if not s:
        return 0.0

    # Match MM:SS or HH:MM:SS
    if ":" in s:
        parts = s.split(":")
        try:
            if len(parts) == 2:
                sec = float(parts[0]) * 60 + float(parts[1])
            elif len(parts) == 3:
                sec = float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
            else:
                sec = float(parts[-1])
            return max(0.0, min(sec, total_duration))
        except ValueError:
            pass

    # Match numeric with optional 's' or 'sec'
    num_match = re.search(r"(\d+(?:\.\d+)?)", s)
    if num_match:
        try:
            return max(0.0, min(float(num_match.group(1)), total_duration))
        except ValueError:
            pass

    return 0.0


# ---------------------------------------------------------------------------
# Trimming & Slicing Primitives
# ---------------------------------------------------------------------------

def trim_video_clip(
    input_path: Union[str, Path],
    output_path: Union[str, Path],
    start_sec: float = 0.0,
    end_sec: Optional[float] = None,
    target_duration: Optional[float] = None,
    target_w: Optional[int] = None,
    target_h: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Frame-accurate trim of video clip between start_sec and end_sec.
    """
    in_file = Path(input_path).resolve()
    out_file = Path(output_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)

    meta = probe_video_stream(in_file)
    src_dur = meta["duration"]

    start = max(0.0, min(start_sec, max(0.0, src_dur - 0.2)))
    if end_sec is not None:
        end = max(start + 0.2, min(end_sec, src_dur))
    elif target_duration is not None:
        end = min(start + target_duration, src_dur)
    else:
        end = src_dur

    clip_dur = round(end - start, 3)
    if clip_dur <= 0.1:
        raise ValueError(f"Invalid trim bounds: start={start:.2f}s, end={end:.2f}s (source duration: {src_dur:.2f}s)")

    ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"

    # Fast input-level seek avoids decoding minutes of 1080p frames before start
    v_filters = ["setpts=PTS-STARTPTS"]
    if target_w and target_h:
        v_filters.extend([
            f"scale={target_w}:{target_h}:force_original_aspect_ratio=decrease",
            f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2",
            "setsar=1",
        ])
    v_filters.append("format=yuv420p")

    v_filter_chain = ",".join(v_filters)

    if meta["has_audio"]:
        filter_complex = f"[0:v]{v_filter_chain}[vout];[0:a]asetpts=PTS-STARTPTS[aout]"
        cmd = [
            ffmpeg_bin, "-y",
            "-ss", f"{start:.3f}",
            "-i", str(in_file),
            "-t", f"{clip_dur:.3f}",
            "-filter_complex", filter_complex,
            "-map", "[vout]",
            "-map", "[aout]",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "21",
            "-threads", "0",
            "-movflags", "+faststart",
            "-c:a", "aac",
            "-b:a", "192k",
            str(out_file),
        ]
    else:
        cmd = [
            ffmpeg_bin, "-y",
            "-ss", f"{start:.3f}",
            "-i", str(in_file),
            "-t", f"{clip_dur:.3f}",
            "-vf", v_filter_chain,
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "21",
            "-threads", "0",
            "-movflags", "+faststart",
            str(out_file),
        ]

    logger.info("Trimming video '%s' [%.2fs -> %.2fs] (dur: %.2fs) -> '%s'", in_file.name, start, end, clip_dur, out_file.name)
    subprocess.run(cmd, capture_output=True, text=True, check=True)

    if not out_file.is_file() or out_file.stat().st_size == 0:
        raise RuntimeError(f"Trimmed video was not created: {out_file}")

    out_meta = probe_video_stream(out_file)
    return {
        "status": "success",
        "output_path": str(out_file),
        "start_sec": start,
        "end_sec": end,
        "duration": out_meta["duration"],
        "original_duration": src_dur,
        "file_size": out_file.stat().st_size,
    }


def assemble_shot_segments(
    input_path: Union[str, Path],
    output_path: Union[str, Path],
    segments: List[Tuple[float, float]],
    transition: str = "cut",
    transition_dur: float = 0.5,
    target_w: Optional[int] = None,
    target_h: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Assemble multiple segments cut from a source video into a unified continuous cut.
    """
    in_file = Path(input_path).resolve()
    out_file = Path(output_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)

    if not segments:
        raise ValueError("At least one segment (start, end) must be provided.")

    meta = probe_video_stream(in_file)
    src_dur = meta["duration"]

    valid_segments: List[Tuple[float, float]] = []
    for s_start, s_end in segments:
        start_c = max(0.0, min(float(s_start), src_dur))
        end_c = max(start_c + 0.2, min(float(s_end), src_dur))
        if end_c - start_c >= 0.2:
            valid_segments.append((round(start_c, 3), round(end_c, 3)))

    if not valid_segments:
        raise ValueError("No valid segments could be formed within video duration bounds.")

    if len(valid_segments) == 1:
        return trim_video_clip(
            input_path=in_file,
            output_path=out_file,
            start_sec=valid_segments[0][0],
            end_sec=valid_segments[0][1],
            target_w=target_w,
            target_h=target_h,
        )

    ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
    w = target_w or meta["width"]
    h = target_h or meta["height"]
    num_seg = len(valid_segments)

    def _run_assemble(use_xfade: bool) -> None:
        eff_td = max(0.15, min(0.8, float(transition_dur or 0.35)))
        input_args: List[str] = []
        filter_parts: List[str] = []
        v_labels: List[str] = []
        a_labels: List[str] = []

        # Fast-seek per segment directly on input file so 4-minute sources skip unwanted decoding
        for idx, (st, en) in enumerate(valid_segments):
            seg_len = round(en - st, 3)
            input_args.extend(["-ss", f"{st:.3f}", "-t", f"{seg_len:.3f}", "-i", str(in_file)])
            v_label = f"v{idx}"
            a_label = f"a{idx}"
            fps_step = "fps=30," if use_xfade else ""
            v_filter = (
                f"[{idx}:v]{fps_step}setpts=PTS-STARTPTS,"
                f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
                f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p[{v_label}]"
            )
            filter_parts.append(v_filter)
            v_labels.append(f"[{v_label}]")

            if meta["has_audio"]:
                a_filter = f"[{idx}:a]asetpts=PTS-STARTPTS[{a_label}]"
                filter_parts.append(a_filter)
                a_labels.append(f"[{a_label}]")

        if use_xfade and num_seg >= 2:
            # Chain xfade progressively across segments
            cur_v = v_labels[0]
            acc_dur = valid_segments[0][1] - valid_segments[0][0]
            for i in range(1, num_seg):
                next_v = v_labels[i]
                out_v = "vout" if i == num_seg - 1 else f"vx{i}"
                offset = max(0.05, round(acc_dur - eff_td, 3))
                filter_parts.append(f"{cur_v}{next_v}xfade=transition=fade:duration={eff_td:.3f}:offset={offset:.3f}[{out_v}]")
                cur_v = f"[{out_v}]"
                seg_d = valid_segments[i][1] - valid_segments[i][0]
                acc_dur = offset + seg_d

            if meta["has_audio"]:
                cur_a = a_labels[0]
                for i in range(1, num_seg):
                    next_a = a_labels[i]
                    out_a = "aout" if i == num_seg - 1 else f"ax{i}"
                    filter_parts.append(f"{cur_a}{next_a}acrossfade=d={eff_td:.3f}:c1=tri:c2=tri[{out_a}]")
                    cur_a = f"[{out_a}]"
        else:
            filter_parts.append("".join(v_labels) + f"concat=n={num_seg}:v=1:a=0[vout]")
            if meta["has_audio"]:
                filter_parts.append("".join(a_labels) + f"concat=n={num_seg}:v=0:a=1[aout]")

        cmd = [
            ffmpeg_bin, "-y",
            *input_args,
            "-filter_complex", ";".join(filter_parts),
            "-map", "[vout]",
        ]
        if meta["has_audio"]:
            cmd.extend(["-map", "[aout]", "-c:a", "aac", "-b:a", "192k"])
        cmd.extend([
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "21",
            "-threads", "0",
            "-movflags", "+faststart",
            str(out_file),
        ])
        subprocess.run(cmd, capture_output=True, text=True, check=True)

    wants_smooth = str(transition or "cut").strip().lower() in ("dissolve", "fade", "smooth")
    can_xfade = wants_smooth and num_seg >= 2 and all((en - st) >= max(0.8, float(transition_dur or 0.35) * 2.4) for st, en in valid_segments)

    logger.info("Assembling %d shot segments from '%s' -> '%s' (xfade=%s)", num_seg, in_file.name, out_file.name, can_xfade)
    if can_xfade:
        try:
            _run_assemble(use_xfade=True)
        except subprocess.CalledProcessError as xf_err:
            logger.warning("Smooth xfade failed (%s); falling back to clean concat.", xf_err.stderr[-180:] if xf_err.stderr else xf_err)
            _run_assemble(use_xfade=False)
    else:
        _run_assemble(use_xfade=False)

    out_meta = probe_video_stream(out_file)
    return {
        "status": "success",
        "output_path": str(out_file),
        "segments": valid_segments,
        "segment_count": len(valid_segments),
        "duration": out_meta["duration"],
        "original_duration": src_dur,
        "file_size": out_file.stat().st_size,
    }


# ---------------------------------------------------------------------------
# Smart AI Montage & Highlight Extraction
# ---------------------------------------------------------------------------

def calculate_smart_montage_segments(
    total_duration: float,
    target_duration: float = 15.0,
    min_shot_duration: float = 3.0,
    max_shot_duration: float = 5.0,
    scene_cuts: Optional[List[float]] = None,
    quality_segments: Optional[List[Dict[str, Any]]] = None,
) -> List[Tuple[float, float]]:
    """
    Compute optimal montage segment bounds to cover key visual highlights
    while respecting target duration.
    """
    target = max(5.0, min(target_duration, total_duration))
    if total_duration <= target:
        return [(0.0, total_duration)]

    # 1. Prioritize local visual quality segments (picks sharp/bright spans across single-take walkthroughs)
    if quality_segments:
        valid_q = []
        for q in quality_segments:
            try:
                st = max(0.0, min(total_duration, float(q["start_sec"])))
                en = max(0.0, min(total_duration, float(q["end_sec"])))
                score = float(q.get("quality_score", 0.5))
            except (KeyError, TypeError, ValueError):
                continue
            if en - st >= 1.2:
                valid_q.append((st, en, score))

        if len(valid_q) >= 2:
            # Bucket timeline into early / middle / late zones so highlights span the whole property tour
            ranked = sorted(valid_q, key=lambda x: x[2], reverse=True)
            chosen_spans: List[Tuple[float, float]] = []
            acc = 0.0
            for st, en, _ in ranked:
                if any(min(en, c_en) - max(st, c_st) > 0.3 for c_st, c_en in chosen_spans):
                    continue
                take = min(en - st, max_shot_duration, max(min_shot_duration * 0.7, target - acc))
                if take < 1.2:
                    continue
                chosen_spans.append((round(st, 2), round(st + take, 2)))
                acc += take
                if acc >= target * 0.92:
                    break
            if chosen_spans:
                return sorted(chosen_spans, key=lambda s: s[0])

    # 2. If scene cuts provided, pick segments centered around diverse scenes
    if scene_cuts and len(scene_cuts) >= 2:
        valid_cuts = [c for c in sorted(scene_cuts) if 0.0 < c < total_duration]
        if valid_cuts:
            points = [0.0] + valid_cuts + [total_duration]
            shots: List[Tuple[float, float]] = []
            for i in range(len(points) - 1):
                p_start = points[i]
                p_end = points[i + 1]
                if p_end - p_start >= 1.5:
                    shots.append((p_start, p_end))

            if shots:
                num_shots_needed = max(2, min(5, int(target / min_shot_duration)))
                step = max(1, len(shots) // num_shots_needed)
                chosen = [shots[i] for i in range(0, len(shots), step)][:num_shots_needed]

                allocated_per_shot = round(target / len(chosen), 2)
                final_segments: List[Tuple[float, float]] = []
                for s_st, s_en in chosen:
                    s_dur = s_en - s_st
                    take = min(allocated_per_shot, s_dur)
                    final_segments.append((round(s_st, 2), round(s_st + take, 2)))
                return final_segments

    # 3. Dynamic uniform highlight distribution across early, middle, and peak frames
    num_segments = 3 if target >= 9.0 else 2
    per_seg = round(target / num_segments, 2)

    seg1 = (0.5, round(0.5 + per_seg, 2))
    mid_start = max(seg1[1] + 1.0, round(total_duration * 0.45, 2))
    seg2 = (mid_start, round(min(total_duration - 1.0, mid_start + per_seg), 2))

    if num_segments == 2:
        return [seg1, seg2]

    last_start = max(seg2[1] + 1.0, round(total_duration - per_seg - 0.5, 2))
    seg3 = (last_start, round(min(total_duration, last_start + per_seg), 2))

    return [seg1, seg2, seg3]


def _select_preferred_segments(
    preferred_scenes: List[Dict[str, Any]],
    src_dur: float,
    target_duration: float,
) -> List[Tuple[float, float]]:
    """
    Resolve AI-recommended highlight windows into non-overlapping chronological cuts
    that honor ``target_duration`` without exceeding it disproportionately.
    """
    scored: List[Tuple[float, float, float]] = []
    for idx, sc in enumerate(preferred_scenes):
        if "start_sec" not in sc or "end_sec" not in sc:
            continue
        st = parse_time_to_seconds(sc["start_sec"], src_dur)
        en = parse_time_to_seconds(sc["end_sec"], src_dur)
        if en - st < 1.0:
            continue
        try:
            score = float(sc.get("score")) if sc.get("score") is not None else max(0.5, 0.95 - idx * 0.05)
        except (TypeError, ValueError):
            score = 0.8
        scored.append((round(st, 2), round(en, 2), score))

    if not scored:
        return []

    total_raw = sum(en - st for st, en, _ in scored)
    budget = max(5.0, min(float(target_duration), src_dur))

    # If preferred cuts already fit reasonably near budget, keep all chronological cuts
    if total_raw <= budget * 1.35:
        return sorted([(st, en) for st, en, _ in scored], key=lambda s: s[0])

    # Otherwise keep highest-scored non-overlapping cuts up to budget
    ranked = sorted(scored, key=lambda x: x[2], reverse=True)
    picked: List[Tuple[float, float]] = []
    acc = 0.0
    for st, en, _ in ranked:
        if any(min(en, k_en) - max(st, k_st) > 0.35 for k_st, k_en in picked):
            continue
        remaining = budget - acc
        if remaining < 1.0:
            break
        dur = en - st
        if dur > remaining * 1.2 and remaining >= 2.0:
            en = round(st + remaining, 2)
            dur = en - st
        picked.append((st, en))
        acc += dur
    return sorted(picked, key=lambda s: s[0])


def auto_smart_montage(
    input_path: Union[str, Path],
    output_path: Union[str, Path],
    target_duration: float = 15.0,
    preferred_scenes: Optional[List[Dict[str, Any]]] = None,
    target_w: Optional[int] = None,
    target_h: Optional[int] = None,
    scene_cuts: Optional[List[float]] = None,
    quality_segments: Optional[List[Dict[str, Any]]] = None,
    proxy_path: Optional[Union[str, Path]] = None,
    transition: str = "cut",
    transition_dur: float = 0.35,
) -> Dict[str, Any]:
    """
    Intelligently select the best highlights (from Vision ``preferred_scenes`` and/or
    proxy scene/quality analysis) and assemble a fast 1080p marketing cut.
    """
    in_file = Path(input_path).resolve()
    meta = probe_video_stream(in_file)
    src_dur = meta["duration"]

    segments: List[Tuple[float, float]] = []
    if preferred_scenes:
        segments = _select_preferred_segments(preferred_scenes, src_dur=src_dur, target_duration=target_duration)

    analysis_target = Path(proxy_path).resolve() if (proxy_path and Path(proxy_path).is_file()) else in_file

    if not segments:
        if scene_cuts is None:
            try:
                import frame_extractor
                scene_cuts = frame_extractor.detect_scene_cut_timestamps(analysis_target)
            except Exception:
                scene_cuts = None

        if quality_segments is None:
            try:
                import frame_extractor
                quality_segments = frame_extractor.score_video_segments(analysis_target, scene_cuts=scene_cuts)
            except Exception:
                quality_segments = None

        segments = calculate_smart_montage_segments(
            total_duration=src_dur,
            target_duration=target_duration,
            scene_cuts=scene_cuts,
            quality_segments=quality_segments,
        )

    return assemble_shot_segments(
        input_path=in_file,
        output_path=output_path,
        segments=segments,
        transition=transition,
        transition_dur=transition_dur,
        target_w=target_w,
        target_h=target_h,
    )
