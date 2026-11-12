#!/usr/bin/env python3
"""
Visual Frame Extraction Tool & MCP Server (mcp_get_image_from_video)
Part of the Video Post-Production & MCP Orchestration Pipeline.

Author: MouhammedBoure
Squad: Tool Development & Visual Extraction Squad (agy11)
Branch: backend/agy11-frame-extraction-mcp
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
from typing import Any, Dict, List, Optional, Union

# Attempt MCP Server import (supports mcp 2.x MCPServer or fallback to FastMCP)
try:
    from mcp.server.mcpserver import MCPServer
except ImportError:
    try:
        from mcp.server.fastmcp import FastMCP as MCPServer
    except ImportError:
        MCPServer = None  # type: ignore


# ---------------------------------------------------------------------------
# Video Metadata & Scene Analysis Utilities
# ---------------------------------------------------------------------------

def get_video_metadata(video_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Extract comprehensive technical metadata from a video file using ffprobe.

    Args:
        video_path: Path to the target video file.

    Returns:
        Dict containing total_duration, duration, frame_rate, resolution, codec,
        width, height, bit_rate, and size_bytes.

    Raises:
        FileNotFoundError: If the specified video file does not exist.
        RuntimeError: If ffprobe fails to parse video stream properties.
    """
    path = Path(video_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Video file not found at: {path}")

    ffprobe_bin = shutil.which("ffprobe") or "ffprobe"
    cmd = [
        ffprobe_bin,
        "-v", "error",
        "-show_entries", "stream=width,height,r_frame_rate,codec_name,duration:format=duration,size,bit_rate",
        "-of", "json",
        str(path)
    ]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffprobe failed to analyze '{path}': {e.stderr.strip()}") from e
    except json.JSONDecodeError as e:
        raise RuntimeError(f"ffprobe returned invalid JSON for '{path}': {e}") from e

    streams = data.get("streams", [])
    video_stream = next((s for s in streams if s.get("codec_name")), None)
    if not video_stream:
        raise RuntimeError(f"No valid video stream identified in: {path}")

    # Parse frame rate (e.g., '24/1' or '30000/1001')
    r_fps = video_stream.get("r_frame_rate", "24/1")
    try:
        num, den = map(float, r_fps.split("/"))
        frame_rate = round(num / den, 2) if den != 0 else 24.0
    except (ValueError, ZeroDivisionError):
        frame_rate = 24.0

    # Parse total duration (priority: video stream duration, fallback: format duration)
    fmt_data = data.get("format", {})
    raw_duration = video_stream.get("duration") or fmt_data.get("duration", 0.0)
    try:
        duration = round(float(raw_duration), 3)
    except (ValueError, TypeError):
        duration = 0.0

    width = int(video_stream.get("width", 0))
    height = int(video_stream.get("height", 0))
    resolution = f"{width}x{height}"
    codec = str(video_stream.get("codec_name", "unknown"))

    try:
        size_bytes = int(fmt_data.get("size", path.stat().st_size))
    except (ValueError, TypeError, OSError):
        size_bytes = path.stat().st_size if path.exists() else 0

    try:
        bit_rate = int(fmt_data.get("bit_rate", 0))
    except (ValueError, TypeError):
        bit_rate = 0

    try:
        rel_path = str(path.relative_to(Path.cwd()))
    except ValueError:
        rel_path = str(path)

    return {
        "total_duration": duration,
        "duration": duration,
        "frame_rate": frame_rate,
        "resolution": resolution,
        "codec": codec,
        "width": width,
        "height": height,
        "bit_rate": bit_rate,
        "size_bytes": size_bytes,
        "video_path": rel_path,
        "absolute_video_path": str(path),
    }


def detect_keyframe_timestamps(video_path: Union[str, Path]) -> List[float]:
    """
    Detect packet presentation timestamps of native I-frames (keyframes).

    Args:
        video_path: Path to the target video file.

    Returns:
        List of keyframe timestamps in seconds, sorted ascending.
    """
    path = Path(video_path).resolve()
    ffprobe_bin = shutil.which("ffprobe") or "ffprobe"
    cmd = [
        ffprobe_bin,
        "-v", "error",
        "-select_streams", "v:0",
        "-show_frames",
        "-show_entries", "frame=best_effort_timestamp_time,key_frame,pict_type",
        "-of", "json",
        str(path)
    ]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)
        frames = data.get("frames", [])
        timestamps: List[float] = []
        for f in frames:
            if f.get("key_frame") == 1 or f.get("pict_type") == "I":
                ts = f.get("best_effort_timestamp_time")
                if ts is not None:
                    try:
                        timestamps.append(round(float(ts), 3))
                    except (ValueError, TypeError):
                        pass
        return sorted(list(set(timestamps)))
    except Exception:
        return [0.0]


def detect_scene_cut_timestamps(video_path: Union[str, Path], threshold: float = 0.25) -> List[float]:
    """
    Detect scene cut timestamps using FFmpeg's scene change detection filter.

    Args:
        video_path: Path to target video file.
        threshold: Scene score threshold (0.0 to 1.0). Default 0.25.

    Returns:
        List of scene change timestamps in seconds.
    """
    path = Path(video_path).resolve()
    ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
    cmd = [
        ffmpeg_bin,
        "-i", str(path),
        "-filter:v", f"select='gt(scene,{threshold})',metadata=print:file=-",
        "-f", "null",
        "-"
    ]

    scene_timestamps: List[float] = [0.0]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        for line in res.stdout.splitlines() + res.stderr.splitlines():
            line_str = line.strip()
            if "pts_time:" in line_str:
                parts = line_str.split("pts_time:")
                if len(parts) > 1:
                    raw_val = parts[1].split()[0]
                    try:
                        ts = round(float(raw_val), 3)
                        scene_timestamps.append(ts)
                    except ValueError:
                        pass
        return sorted(list(set(scene_timestamps)))
    except Exception:
        return [0.0]


def _compute_even_proxy_dimensions(width: int, height: int, max_short_side: int = 480) -> tuple[int, int]:
    """Compute even width and height capping the shorter side to ``max_short_side``."""
    w = max(2, int(width or 0))
    h = max(2, int(height or 0))
    short_side = min(w, h)
    if short_side <= max_short_side:
        return (w - (w % 2), h - (h % 2))
    scale = max_short_side / float(short_side)
    new_w = max(2, int(round((w * scale) / 2.0)) * 2)
    new_h = max(2, int(round((h * scale) / 2.0)) * 2)
    return (new_w, new_h)


def create_analysis_proxy(
    video_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
    max_short_side: int = 480,
    fps: float = 2.0,
    crf: int = 28,
    include_audio: bool = True,
    timeout: int = 120,
) -> Dict[str, Any]:
    """
    Create a lightweight compressed analysis proxy (e.g. 480p @ 2 fps) from a
    high-resolution upload so vision/scene analysis stays fast and small while the
    final render cuts from the original 1080p source.
    """
    src = Path(video_path).resolve()
    if not src.is_file():
        raise FileNotFoundError(f"Video file not found at: {src}")

    meta = get_video_metadata(src)
    src_w = int(meta.get("width") or 0)
    src_h = int(meta.get("height") or 0)
    src_dur = float(meta.get("duration") or 0.0)
    target_w, target_h = _compute_even_proxy_dimensions(src_w, src_h, max_short_side=max_short_side)

    if output_path is None:
        out = src.parent / f"{src.stem}_analysis_proxy_{max_short_side}p.mp4"
    else:
        out = Path(output_path).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
    eff_fps = max(0.5, float(fps))
    scale_filter = (
        f"scale={target_w}:{target_h}:flags=fast_bilinear,fps={eff_fps:.3f}"
        if target_w > 0 and target_h > 0
        else f"scale='if(gt(iw,ih),-2,min({max_short_side},iw))':'if(gt(iw,ih),min({max_short_side},ih),-2)',fps={eff_fps:.3f}"
    )

    cmd: List[str] = [
        ffmpeg_bin,
        "-y",
        "-i", str(src),
        "-map", "0:v:0",
    ]
    if include_audio:
        cmd.extend(["-map", "0:a?"])
    cmd.extend([
        "-vf", scale_filter,
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", str(int(crf)),
        "-pix_fmt", "yuv420p",
        "-threads", "0",
        "-movflags", "+faststart",
    ])
    if include_audio:
        cmd.extend(["-c:a", "aac", "-b:a", "48k", "-ac", "1", "-ar", "16000"])
    else:
        cmd.append("-an")
    cmd.append(str(out))

    res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if res.returncode != 0 or not out.exists() or out.stat().st_size == 0:
        raise RuntimeError(f"FFmpeg proxy generation failed: {res.stderr[-300:] if res.stderr else res.returncode}")

    return {
        "proxy_path": str(out),
        "source_path": str(src),
        "source_width": src_w,
        "source_height": src_h,
        "width": target_w,
        "height": target_h,
        "fps": eff_fps,
        "duration": src_dur,
        "size_bytes": out.stat().st_size,
        "created": True,
    }


def _score_gray_frame(
    buf: bytes,
    prev_buf: Optional[bytes],
    width: int,
    height: int,
) -> Dict[str, float]:
    """Compute brightness, contrast, sharpness, and frame-to-frame motion."""
    try:
        import numpy as np  # type: ignore

        arr = np.frombuffer(buf, dtype=np.uint8).reshape((height, width)).astype(np.float32)
        mean_luma = float(arr.mean())
        std_luma = float(arr.std())
        dx = np.abs(arr[:, 1:] - arr[:, :-1]).mean() if width > 1 else 0.0
        dy = np.abs(arr[1:, :] - arr[:-1, :]).mean() if height > 1 else 0.0
        sharpness = float(dx + dy)
        motion = float(np.abs(arr - np.frombuffer(prev_buf, dtype=np.uint8).reshape((height, width)).astype(np.float32)).mean()) if prev_buf else 0.0
        return {
            "luma": round(mean_luma, 2),
            "contrast": round(std_luma, 2),
            "sharpness": round(sharpness, 2),
            "motion": round(motion, 2),
        }
    except Exception:
        total = max(1, len(buf))
        step = max(1, total // 2000)
        samples = buf[::step]
        n = max(1, len(samples))
        mean_luma = sum(samples) / n
        var_luma = sum((v - mean_luma) ** 2 for v in samples) / n
        sharp_acc = sum(abs(samples[i] - samples[i - 1]) for i in range(1, n)) / max(1, n - 1)
        if prev_buf and len(prev_buf) == len(buf):
            prev_samples = prev_buf[::step]
            motion = sum(abs(a - b) for a, b in zip(samples, prev_samples)) / n
        else:
            motion = 0.0
        return {
            "luma": round(mean_luma, 2),
            "contrast": round(var_luma ** 0.5, 2),
            "sharpness": round(sharp_acc * 1.5, 2),
            "motion": round(motion, 2),
        }


def score_video_segments(
    video_path: Union[str, Path],
    segment_duration: float = 2.5,
    sample_fps: float = 2.0,
    scene_cuts: Optional[List[float]] = None,
    top_k: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Score candidate windows in a video (ideally the lightweight 480p proxy)
    for brightness, exposure contrast, edge sharpness, and camera stability.
    """
    path = Path(video_path).resolve()
    if not path.is_file():
        return []

    try:
        meta = get_video_metadata(path)
        duration = max(0.5, float(meta.get("duration") or 0.0))
    except Exception:
        return []

    grid_w, grid_h = 160, 90
    ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
    eff_fps = max(0.5, min(6.0, float(sample_fps)))
    cmd = [
        ffmpeg_bin,
        "-i", str(path),
        "-vf", f"fps={eff_fps:.3f},scale={grid_w}:{grid_h}:flags=fast_bilinear",
        "-f", "rawvideo",
        "-pix_fmt", "gray",
        "-",
    ]

    frame_bytes = grid_w * grid_h
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=60)
        raw = proc.stdout or b""
    except Exception:
        return []

    num_frames = len(raw) // frame_bytes
    if num_frames <= 0:
        return []

    frame_metrics: List[Dict[str, float]] = []
    prev_slice: Optional[bytes] = None
    for idx in range(num_frames):
        chunk = raw[idx * frame_bytes : (idx + 1) * frame_bytes]
        m = _score_gray_frame(chunk, prev_slice, grid_w, grid_h)
        m["time"] = round(idx / eff_fps, 3)
        # Quality formula: favor clear exposure (luma 40..220), contrast, sharpness, moderate smooth motion
        luma = m["luma"]
        expo_score = 1.0 if 35.0 <= luma <= 220.0 else max(0.1, 1.0 - abs(luma - 125.0) / 140.0)
        sharp_score = min(1.0, m["sharpness"] / 18.0)
        contrast_score = min(1.0, m["contrast"] / 45.0)
        # Excess whip-pan / camera shake (>28 avg delta) reduces score; slight smooth motion (1..14) is good
        motion_val = m["motion"]
        if motion_val > 28.0:
            stability_score = max(0.2, 1.0 - (motion_val - 28.0) / 35.0)
        elif motion_val < 0.6:
            stability_score = 0.72
        else:
            stability_score = 1.0
        m["quality"] = round(
            0.35 * sharp_score + 0.25 * expo_score + 0.20 * contrast_score + 0.20 * stability_score,
            4,
        )
        frame_metrics.append(m)
        prev_slice = chunk

    # Build contiguous windows aligned with scene_cuts when available, otherwise uniform buckets
    win_len = max(1.5, float(segment_duration))
    boundaries: List[float] = [0.0]
    if scene_cuts:
        for cut in sorted(scene_cuts):
            c = float(cut)
            if 0.6 < c < duration - 0.6 and (c - boundaries[-1]) >= 1.5:
                boundaries.append(round(c, 3))
    while duration - boundaries[-1] > win_len * 1.35:
        boundaries.append(round(boundaries[-1] + win_len, 3))
    boundaries.append(round(duration, 3))

    segments: List[Dict[str, Any]] = []
    for i in range(len(boundaries) - 1):
        st = boundaries[i]
        en = boundaries[i + 1]
        if (en - st) < 0.8:
            continue
        bucket = [fm for fm in frame_metrics if st <= fm["time"] < en]
        if not bucket:
            nearest = min(frame_metrics, key=lambda fm: abs(fm["time"] - (st + en) / 2.0))
            bucket = [nearest]
        avg_q = sum(b["quality"] for b in bucket) / len(bucket)
        avg_sharp = sum(b["sharpness"] for b in bucket) / len(bucket)
        avg_motion = sum(b["motion"] for b in bucket) / len(bucket)
        avg_luma = sum(b["luma"] for b in bucket) / len(bucket)
        segments.append({
            "start_sec": round(st, 2),
            "end_sec": round(en, 2),
            "duration_sec": round(en - st, 2),
            "quality_score": round(avg_q, 4),
            "sharpness": round(avg_sharp, 2),
            "motion": round(avg_motion, 2),
            "luma": round(avg_luma, 2),
        })

    if top_k is not None and top_k > 0:
        ranked = sorted(segments, key=lambda s: s["quality_score"], reverse=True)[:top_k]
        return sorted(ranked, key=lambda s: s["start_sec"])
    return segments


# ---------------------------------------------------------------------------
# Core Frame Extraction Engine
# ---------------------------------------------------------------------------

def extract_frames(
    video_path: Union[str, Path],
    timestamps: Optional[List[float]] = None,
    fps_sample: Optional[float] = None,
    output_dir: Union[str, Path] = "outputs/keyframes",
    image_format: str = "jpg",
    quality: int = 2,
    include_scene_analysis: bool = True,
    include_scenes_in_sampling: bool = True,
) -> Dict[str, Any]:
    """
    Extract high-fidelity visual frames from a video at designated timestamps or sample rates.

    Args:
        video_path: Path to the input video file.
        timestamps: Optional explicit list of target timestamps in seconds.
        fps_sample: Optional frame sampling rate (e.g. 1.0 for 1 frame every second,
                    0.5 for 1 frame every 2 seconds).
        output_dir: Destination directory for extracted image assets. Default 'outputs/keyframes'.
        image_format: Image file extension ('jpg' or 'png'). Default 'jpg'.
        quality: JPEG compression quality parameter for FFmpeg -q:v (1=highest, 31=lowest). Default 2.
        include_scene_analysis: Whether to compute native keyframes and scene cuts into metadata.
        include_scenes_in_sampling: If timestamps is not provided, whether to include detected
                                   scene cuts alongside sampled intervals. Default True.

    Returns:
        Structured JSON dictionary containing:
          - frames: List of extracted frame objects {"frame_index", "timestamp", "file_path", "resolution"}
          - metadata: Video technical metadata (total_duration, frame_rate, resolution, codec, scene_timestamps)
          - Top-level mirrors for convenience (total_duration, frame_rate, resolution, codec, video_path)

    Raises:
        FileNotFoundError: If the video file is missing.
        ValueError: If parameters are invalid.
        RuntimeError: If frame extraction encounters an error.
    """
    path = Path(video_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Input video file does not exist: {path}")

    # Gather video metadata first
    meta = get_video_metadata(path)
    duration = meta["total_duration"]
    resolution = meta["resolution"]
    stem = path.stem

    # Detect scene cuts and native I-frames (skip full-stream decode when explicit timestamps are given on long videos)
    scene_cuts: List[float] = [0.0]
    i_frames: List[float] = [0.0]
    explicit_ts_provided = bool(timestamps is not None and len(timestamps) > 0)
    if include_scene_analysis and not (explicit_ts_provided and duration > 20.0):
        try:
            scene_cuts = detect_scene_cut_timestamps(path)
        except Exception:
            scene_cuts = [0.0]
        try:
            i_frames = detect_keyframe_timestamps(path)
        except Exception:
            i_frames = [0.0]

    # Determine timestamps to extract
    target_timestamps: List[float] = []

    if timestamps is not None and len(timestamps) > 0:
        for t in timestamps:
            try:
                ft = float(t)
                if ft < 0.0:
                    continue
                if duration > 0 and ft > duration:
                    ft = duration
                target_timestamps.append(round(ft, 3))
            except (ValueError, TypeError) as err:
                raise ValueError(f"Invalid timestamp value in list: {t}") from err
        target_timestamps = sorted(list(set(target_timestamps)))
    else:
        # Sample rate determination
        rate = fps_sample if fps_sample is not None else 1.0
        if rate <= 0.0:
            raise ValueError(f"fps_sample must be strictly positive, got: {rate}")
        interval = 1.0 / rate

        current_t = 0.0
        while current_t < duration:
            target_timestamps.append(round(current_t, 3))
            current_t += interval

        if include_scenes_in_sampling:
            for sc in scene_cuts:
                if 0.0 <= sc <= duration:
                    target_timestamps.append(round(sc, 3))

        target_timestamps = sorted(list(set(target_timestamps)))
        if not target_timestamps:
            target_timestamps.append(0.0)

    # Prepare destination directory
    out_dir_path = Path(output_dir).resolve()
    out_dir_path.mkdir(parents=True, exist_ok=True)

    ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
    clean_format = image_format.lower().lstrip(".")
    if clean_format not in ("jpg", "jpeg", "png"):
        clean_format = "jpg"

    extracted_frames: List[Dict[str, Any]] = []

    for index, ts in enumerate(target_timestamps):
        filename = f"{stem}_frame_{index:04d}_{ts:06.2f}s.{clean_format}"
        frame_dest = out_dir_path / filename

        # FFmpeg frame extraction command
        cmd = [
            ffmpeg_bin,
            "-y",
            "-ss", str(ts),
            "-i", str(path),
            "-frames:v", "1",
        ]

        if clean_format in ("jpg", "jpeg"):
            cmd.extend(["-q:v", str(quality)])

        cmd.append(str(frame_dest))

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"FFmpeg failed extracting frame at {ts}s to '{frame_dest}': {e.stderr.strip()}"
            ) from e

        if not frame_dest.is_file() or frame_dest.stat().st_size == 0:
            raise RuntimeError(f"Extracted frame file is empty or missing: {frame_dest}")

        # Check if timestamp aligns closely with a scene cut
        is_scene_transition = any(abs(ts - sc) < 0.1 for sc in scene_cuts)

        try:
            rel_file_path = str(frame_dest.relative_to(Path.cwd()))
        except ValueError:
            rel_file_path = str(frame_dest)

        frame_info: Dict[str, Any] = {
            "frame_index": index,
            "timestamp": ts,
            "file_path": rel_file_path,
            "absolute_file_path": str(frame_dest),
            "resolution": resolution,
            "is_scene_transition": is_scene_transition,
            "file_size_bytes": frame_dest.stat().st_size,
        }
        extracted_frames.append(frame_info)

    # Attach scene analytics to metadata
    meta["scene_timestamps"] = scene_cuts
    meta["keyframe_timestamps"] = i_frames

    # Construct the final structured payload
    payload: Dict[str, Any] = {
        "frames": extracted_frames,
        "metadata": meta,
        "total_duration": meta["total_duration"],
        "duration": meta["duration"],
        "frame_rate": meta["frame_rate"],
        "resolution": meta["resolution"],
        "codec": meta["codec"],
        "video_path": meta["video_path"],
        "total_frames_extracted": len(extracted_frames),
    }

    return payload


# Programmatic keyframe extraction alias
extract_keyframes = extract_frames


# ---------------------------------------------------------------------------
# MCP Tool Interface
# ---------------------------------------------------------------------------

def mcp_get_image_from_video(
    video_path: str,
    timestamps: Optional[List[float]] = None,
    fps_sample: Optional[float] = None,
    output_dir: str = "outputs/keyframes",
) -> Dict[str, Any]:
    """
    Model Context Protocol (MCP) tool: Extracts visual frames and metadata from a video file.

    Args:
        video_path: Path to the target video file (e.g. 'inputs/source_fox_cub.mp4').
        timestamps: Optional explicit list of timestamps in seconds to extract.
        fps_sample: Optional sampling frequency in frames per second (e.g., 1.0 for 1 frame/sec,
                    0.5 for 1 frame every 2 seconds).
        output_dir: Destination directory for extracted keyframes. Default 'outputs/keyframes'.

    Returns:
        Structured JSON dictionary containing:
          - frames: [{"frame_index": int, "timestamp": float, "file_path": str, "resolution": str}, ...]
          - metadata: {"total_duration": float, "frame_rate": float, "resolution": str, "codec": str, ...}
          - Top-level mirrors: total_duration, frame_rate, resolution, codec
    """
    return extract_frames(
        video_path=video_path,
        timestamps=timestamps,
        fps_sample=fps_sample,
        output_dir=output_dir,
    )


# ---------------------------------------------------------------------------
# Batch Processing Utility
# ---------------------------------------------------------------------------

def process_videos_batch(
    video_paths: List[Union[str, Path]],
    output_dir: Union[str, Path] = "outputs/keyframes",
    fps_sample: Optional[float] = 1.0,
    timestamps: Optional[List[float]] = None,
    index_file: Optional[Union[str, Path]] = "outputs/keyframes/frame_index.json",
) -> Dict[str, Any]:
    """
    Process multiple video files, extract keyframes, and generate a unified frame index JSON.

    Args:
        video_paths: List of video file paths to process.
        output_dir: Output directory for keyframe images.
        fps_sample: Sampling rate in fps.
        timestamps: Optional specific timestamps for extraction.
        index_file: Path to save the combined index JSON.

    Returns:
        Master dictionary indexing all processed videos and frames.
    """
    out_dir_path = Path(output_dir).resolve()
    out_dir_path.mkdir(parents=True, exist_ok=True)

    try:
        rel_output_dir = str(out_dir_path.relative_to(Path.cwd()))
    except ValueError:
        rel_output_dir = str(out_dir_path)

    master_index: Dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "output_dir": rel_output_dir,
        "videos": {},
        "all_frames": [],
    }

    for vp in video_paths:
        path = Path(vp)
        if not path.exists():
            continue

        result = extract_frames(
            video_path=path,
            timestamps=timestamps,
            fps_sample=fps_sample,
            output_dir=out_dir_path,
        )

        stem = path.stem
        # Rel path key
        try:
            rel_vp = str(path.relative_to(Path.cwd()))
        except ValueError:
            rel_vp = str(path)

        master_index["videos"][stem] = result
        master_index["videos"][rel_vp] = result
        # Direct top-level access alias
        master_index[stem] = result
        master_index["all_frames"].extend(result["frames"])

    master_index["total_videos"] = len([vp for vp in video_paths if Path(vp).exists()])
    master_index["total_frames"] = len(master_index["all_frames"])

    if index_file:
        index_path = Path(index_file).resolve()
        index_path.parent.mkdir(parents=True, exist_ok=True)
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(master_index, f, indent=2)

    return master_index


# ---------------------------------------------------------------------------
# MCP Server Registration
# ---------------------------------------------------------------------------

def create_mcp_server(name: str = "video-extractor") -> Optional[Any]:
    """
    Initialize and configure the MCP server instance with the frame extraction tool.
    """
    if MCPServer is None:
        return None

    server = MCPServer(name)
    server.tool(name="mcp_get_image_from_video")(mcp_get_image_from_video)
    return server


# Global server instance for direct import or fast execution
mcp_server = create_mcp_server("video-extractor")


def run_mcp_server(transport: str = "stdio") -> None:
    """
    Run the visual frame extraction MCP server.
    """
    if mcp_server is None:
        raise RuntimeError("mcp library is not installed or MCPServer could not be initialized.")
    mcp_server.run(transport=transport)


# ---------------------------------------------------------------------------
# Command Line Interface (CLI)
# ---------------------------------------------------------------------------

def build_cli_parser() -> argparse.ArgumentParser:
    """Construct command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="python -m frame_extractor",
        description="High-fidelity visual keyframe extraction tool and MCP server."
    )
    parser.add_argument(
        "video_path",
        nargs="?",
        default=None,
        help="Path to video file to extract frames from."
    )
    parser.add_argument(
        "--timestamps",
        type=str,
        default=None,
        help="Comma-separated list of timestamps in seconds (e.g. '0.0,1.5,4.5')."
    )
    parser.add_argument(
        "--fps-sample",
        type=float,
        default=None,
        help="Sample rate in frames per second (e.g. 1.0 for 1 frame/sec, 0.5 for 1 frame every 2 sec)."
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="outputs/keyframes",
        help="Output directory for extracted frames (default: 'outputs/keyframes')."
    )
    parser.add_argument(
        "--format",
        choices=["jpg", "png", "jpeg"],
        default="jpg",
        help="Image format (default: 'jpg')."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output structured JSON response to stdout."
    )
    parser.add_argument(
        "--mcp",
        action="store_true",
        help="Launch as Model Context Protocol (MCP) server over stdio."
    )
    parser.add_argument(
        "--batch",
        nargs="+",
        default=None,
        help="Batch process multiple video paths."
    )
    parser.add_argument(
        "--index-file",
        type=str,
        default="outputs/keyframes/frame_index.json",
        help="Path to save aggregate frame index JSON in batch mode."
    )
    parser.add_argument(
        "--metadata-only",
        action="store_true",
        help="Only display video metadata without extracting frames."
    )

    return parser


def main() -> int:
    """Main CLI entrypoint."""
    parser = build_cli_parser()
    args = parser.parse_args()

    # MCP server mode
    if args.mcp:
        run_mcp_server("stdio")
        return 0

    # Batch processing mode
    if args.batch:
        timestamps_list: Optional[List[float]] = None
        if args.timestamps:
            timestamps_list = [float(t.strip()) for t in args.timestamps.split(",") if t.strip()]

        result = process_videos_batch(
            video_paths=args.batch,
            output_dir=args.output_dir,
            fps_sample=args.fps_sample or 1.0,
            timestamps=timestamps_list,
            index_file=args.index_file,
        )

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"[OK] Batch processed {result['total_videos']} videos.")
            print(f"     Extracted {result['total_frames']} frames to: {args.output_dir}")
            print(f"     Aggregate index saved to: {args.index_file}")
        return 0

    # Single video mode
    if not args.video_path:
        parser.print_help()
        return 1

    # Metadata inspection only
    if args.metadata_only:
        meta = get_video_metadata(args.video_path)
        print(json.dumps(meta, indent=2))
        return 0

    # Parse timestamps
    timestamps_list = None
    if args.timestamps:
        timestamps_list = [float(t.strip()) for t in args.timestamps.split(",") if t.strip()]

    result = extract_frames(
        video_path=args.video_path,
        timestamps=timestamps_list,
        fps_sample=args.fps_sample,
        output_dir=args.output_dir,
        image_format=args.format,
    )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"[OK] Extracted {result['total_frames_extracted']} frames from: {args.video_path}")
        print(f"     Resolution: {result['resolution']}, Frame Rate: {result['frame_rate']} fps, Duration: {result['total_duration']}s")
        print(f"     Destination: {args.output_dir}")
        for f in result["frames"]:
            print(f"     - Frame #{f['frame_index']:02d} @ {f['timestamp']:05.2f}s -> {f['file_path']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
