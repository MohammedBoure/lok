#!/usr/bin/env python3
"""
Privacy-preserving two-pass face blurring for uploaded marketing videos.

Pass 1 detects faces across frames, discards short isolated false-positive flashes,
cuts tracks cleanly at hard scene boundaries, bridges brief profile-turn dropouts,
and fades out cleanly when a person exits the frame (avoiding floating wall blobs).
Pass 2 applies a smooth feathered elliptical Gaussian blur inside each tracked region
and remuxes the original audio track into browser-ready H.264 MP4 via FFmpeg.
"""

from __future__ import annotations

import logging
import math
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

import cv2
import numpy as np

logger = logging.getLogger("lok.face_blur")

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_YUNET_MODEL = REPO_ROOT / "assets" / "models" / "face_detection_yunet_2023mar.onnx"

# Type aliases for clarity: (cx, cy, w, h, score)
BoxRecord = Tuple[float, float, float, float, float]
FrameBox = Tuple[float, float, float, float, float]  # (cx, cy, w, h, alpha)


def _find_yunet_model(model_path: Optional[Union[str, Path]] = None) -> Path:
    candidate = Path(model_path) if model_path else DEFAULT_YUNET_MODEL
    if not candidate.is_file():
        raise FileNotFoundError(
            f"Face detector model not found at '{candidate}'. Expected bundled YuNet ONNX asset."
        )
    return candidate


class _YuNetFaceDetector:
    """Thin wrapper around OpenCV FaceDetectorYN normalized to (cx, cy, w, h, score) in full-res coords."""

    def __init__(self, model_path: Path, score_threshold: float = 0.55, detect_max_side: int = 640):
        self.model_path = str(model_path)
        self.score_threshold = float(score_threshold)
        self.detect_max_side = max(160, int(detect_max_side))
        self._detector = None
        self._det_size: Tuple[int, int] = (0, 0)

    def detect(self, frame_bgr: np.ndarray) -> List[BoxRecord]:
        h, w = frame_bgr.shape[:2]
        if w <= 0 or h <= 0:
            return []

        scale = min(1.0, self.detect_max_side / float(max(w, h)))
        det_w = max(32, int(round(w * scale)))
        det_h = max(32, int(round(h * scale)))

        resized = frame_bgr if scale >= 0.999 else cv2.resize(frame_bgr, (det_w, det_h), interpolation=cv2.INTER_AREA)

        if self._detector is None:
            self._detector = cv2.FaceDetectorYN.create(
                self.model_path,
                "",
                (det_w, det_h),
                score_threshold=self.score_threshold,
                nms_threshold=0.35,
                top_k=50,
            )
            self._det_size = (det_w, det_h)
        elif self._det_size != (det_w, det_h):
            self._detector.setInputSize((det_w, det_h))
            self._det_size = (det_w, det_h)

        _, raw_faces = self._detector.detect(resized)
        if raw_faces is None or len(raw_faces) == 0:
            return []

        inv_scale_x = w / float(det_w)
        inv_scale_y = h / float(det_h)
        min_box_det = 14.0  # Reject tiny background texture noise

        boxes: List[BoxRecord] = []
        for row in raw_faces:
            bx, by, bw, bh = float(row[0]), float(row[1]), float(row[2]), float(row[3])
            score = float(row[14]) if len(row) > 14 else self.score_threshold
            if bw < min_box_det or bh < min_box_det or score < self.score_threshold:
                continue
            full_w = bw * inv_scale_x
            full_h = bh * inv_scale_y
            full_cx = (bx + bw * 0.5) * inv_scale_x
            full_cy = (by + bh * 0.5) * inv_scale_y
            boxes.append((full_cx, full_cy, full_w, full_h, score))
        return boxes


def _box_iou(a: BoxRecord, b: BoxRecord) -> float:
    acx, acy, aw, ah, _ = a
    bcx, bcy, bw, bh, _ = b
    ax1, ay1, ax2, ay2 = acx - aw * 0.5, acy - ah * 0.5, acx + aw * 0.5, acy + ah * 0.5
    bx1, by1, bx2, by2 = bcx - bw * 0.5, bcy - bh * 0.5, bcx + bw * 0.5, bcy + bh * 0.5

    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0.0:
        return 0.0
    union = aw * ah + bw * bh - inter
    return inter / union if union > 0.0 else 0.0


def _same_face_match(a: BoxRecord, b: BoxRecord) -> float:
    """Return association score (>0 if plausible match across consecutive frames)."""
    iou = _box_iou(a, b)
    if iou >= 0.15:
        return iou + 1.0
    dist = math.hypot(a[0] - b[0], a[1] - b[1])
    size = max(1.0, max(a[2], a[3], b[2], b[3]))
    if dist <= size * 1.15:
        return max(0.01, 1.0 - dist / (size * 1.15))
    return 0.0


def _is_near_border(box: BoxRecord, width: int, height: int, margin_ratio: float = 0.065) -> bool:
    cx, cy, bw, bh, _ = box
    mx = width * margin_ratio
    my = height * margin_ratio
    return (
        (cx - bw * 0.5) <= mx
        or (cx + bw * 0.5) >= (width - mx)
        or (cy - bh * 0.5) <= my
        or (cy + bh * 0.5) >= (height - my)
    )


def plan_blur_timeline(
    raw_detections: Sequence[Sequence[BoxRecord]],
    frame_width: int,
    frame_height: int,
    scene_cuts: Sequence[int] = (),
    min_track_frames: int = 3,
    max_bridge_gap: int = 8,
    smooth_radius: int = 2,
    pad_w: float = 0.24,
    pad_h: float = 0.30,
) -> List[List[FrameBox]]:
    """
    Build clean per-frame blur ovals from raw per-frame detections.

    Handles:
      - Short isolated false-positive rejection (< min_track_frames)
      - Hard scene-cut isolation (tracks never bleed across cuts)
      - Brief gap interpolation during side-profile turns
      - Edge-exit velocity fade-out vs mid-frame fade-out (no floating wall blobs)
      - Zero-lag centered smoothing + head/forehead oval expansion
    """
    total_frames = len(raw_detections)
    if total_frames == 0:
        return []

    effective_min_len = min(min_track_frames, total_frames)
    cut_set = {int(c) for c in scene_cuts if 0 < int(c) < total_frames}

    # Build contiguous scene intervals [start, end)
    sorted_cuts = sorted(cut_set)
    scenes: List[Tuple[int, int]] = []
    prev_start = 0
    for c in sorted_cuts:
        if c > prev_start:
            scenes.append((prev_start, c))
            prev_start = c
    if prev_start < total_frames:
        scenes.append((prev_start, total_frames))

    per_frame_output: List[List[FrameBox]] = [[] for _ in range(total_frames)]

    for scene_start, scene_end in scenes:
        # 1. Link detections inside this scene into tracklets allowing brief gaps
        active_tracks: List[Dict[str, Any]] = []
        finished_tracks: List[Dict[int, BoxRecord]] = []

        for f_idx in range(scene_start, scene_end):
            dets = list(raw_detections[f_idx])
            used_dets = set()

            # Match against currently active tracks (up to max_bridge_gap missing frames)
            candidates: List[Tuple[float, int, int]] = []
            for t_idx, tr in enumerate(active_tracks):
                gap = f_idx - tr["last_frame"]
                if gap <= 0 or gap > (max_bridge_gap + 1):
                    continue
                last_box = tr["frames"][tr["last_frame"]]
                for d_idx, d_box in enumerate(dets):
                    score = _same_face_match(last_box, d_box)
                    if score > 0.0:
                        candidates.append((score - 0.05 * (gap - 1), t_idx, d_idx))

            candidates.sort(reverse=True, key=lambda x: x[0])
            used_tracks = set()
            for _, t_idx, d_idx in candidates:
                if t_idx in used_tracks or d_idx in used_dets:
                    continue
                tr = active_tracks[t_idx]
                tr["frames"][f_idx] = dets[d_idx]
                tr["last_frame"] = f_idx
                used_tracks.add(t_idx)
                used_dets.add(d_idx)

            # Retire stale tracks
            still_active = []
            for tr in active_tracks:
                if (f_idx - tr["last_frame"]) > max_bridge_gap:
                    finished_tracks.append(tr["frames"])
                else:
                    still_active.append(tr)
            active_tracks = still_active

            # Start new tracks for unmatched detections
            for d_idx, d_box in enumerate(dets):
                if d_idx not in used_dets:
                    active_tracks.append({"last_frame": f_idx, "frames": {f_idx: d_box}})

        for tr in active_tracks:
            finished_tracks.append(tr["frames"])

        # 2. Filter noise & densify/smooth each track
        for track_map in finished_tracks:
            if len(track_map) < effective_min_len:
                continue

            keys = sorted(track_map.keys())
            first_k, last_k = keys[0], keys[-1]

            # Fill internal gaps via linear interpolation
            dense: Dict[int, Tuple[float, float, float, float, float]] = {}
            for i in range(len(keys) - 1):
                k0, k1 = keys[i], keys[i + 1]
                b0, b1 = track_map[k0], track_map[k1]
                span = k1 - k0
                for step in range(span):
                    t = step / float(span)
                    dense[k0 + step] = (
                        b0[0] + (b1[0] - b0[0]) * t,
                        b0[1] + (b1[1] - b0[1]) * t,
                        b0[2] + (b1[2] - b0[2]) * t,
                        b0[3] + (b1[3] - b0[3]) * t,
                        1.0,
                    )
            blast = track_map[last_k]
            dense[last_k] = (blast[0], blast[1], blast[2], blast[3], 1.0)

            # Centered zero-lag box smoothing on detected+interpolated frames
            smoothed: Dict[int, FrameBox] = {}
            for f in range(first_k, last_k + 1):
                lo = max(first_k, f - smooth_radius)
                hi = min(last_k, f + smooth_radius)
                samples = [dense[k] for k in range(lo, hi + 1)]
                n = float(len(samples))
                scx = sum(s[0] for s in samples) / n
                scy = sum(s[1] for s in samples) / n
                sw = sum(s[2] for s in samples) / n
                sh = sum(s[3] for s in samples) / n
                smoothed[f] = (scx, scy, sw, sh, 1.0)

            # Short smooth fade-out tail (follows exit velocity if near border)
            if last_k + 1 < scene_end:
                end_box = smoothed[last_k]
                prev_k = max(first_k, last_k - 3)
                dt = max(1, last_k - prev_k)
                vx = (end_box[0] - smoothed[prev_k][0]) / dt
                vy = (end_box[1] - smoothed[prev_k][1]) / dt
                raw_last_tuple = (end_box[0], end_box[1], end_box[2], end_box[3], 1.0)
                exiting_edge = _is_near_border(raw_last_tuple, frame_width, frame_height)
                tail_len = 3 if exiting_edge else 4
                for step in range(1, tail_len + 1):
                    tf = last_k + step
                    if tf >= scene_end:
                        break
                    # Extrapolate velocity on edge exit so blur slides out with person rather than floating
                    vel_scale = step if exiting_edge else min(step * 0.35, 1.2)
                    alpha = max(0.0, 1.0 - (step / float(tail_len + 1)))
                    if alpha > 0.05:
                        smoothed[tf] = (
                            end_box[0] + vx * vel_scale,
                            end_box[1] + vy * vel_scale,
                            end_box[2],
                            end_box[3],
                            alpha,
                        )

            # Expand slightly so forehead, jawline, and hairline stay safely covered
            for f, (cx, cy, bw, bh, alpha) in smoothed.items():
                exp_w = bw * (1.0 + pad_w)
                exp_h = bh * (1.0 + pad_h)
                shifted_cy = cy - bh * 0.04  # Shift slightly upward to cover forehead/hairline
                per_frame_output[f].append((cx, shifted_cy, exp_w, exp_h, alpha))

    return per_frame_output


def _apply_feathered_oval_blur(frame_bgr: np.ndarray, boxes: Sequence[FrameBox]) -> np.ndarray:
    """Apply soft elliptical Gaussian blur only within each planned face region."""
    if not boxes:
        return frame_bgr

    out = frame_bgr.copy()
    fh, fw = out.shape[:2]

    for cx, cy, bw, bh, alpha in boxes:
        if alpha <= 0.02 or bw <= 2 or bh <= 2:
            continue

        # Feather pad slightly outside ellipse so boundaries never show hard boxes
        pad_px = max(6, int(round(max(bw, bh) * 0.14)))
        x1 = max(0, int(math.floor(cx - bw * 0.5)) - pad_px)
        y1 = max(0, int(math.floor(cy - bh * 0.5)) - pad_px)
        x2 = min(fw, int(math.ceil(cx + bw * 0.5)) + pad_px)
        y2 = min(fh, int(math.ceil(cy + bh * 0.5)) + pad_px)

        roi_w = x2 - x1
        roi_h = y2 - y1
        if roi_w < 4 or roi_h < 4:
            continue

        roi = out[y1:y2, x1:x2]

        # Strong odd blur kernel proportional to face size
        k = max(21, int(round(min(max(bw, bh) * 0.55, 111))))
        if k % 2 == 0:
            k += 1
        blurred_roi = cv2.GaussianBlur(roi, (k, k), 0)

        mask = np.zeros((roi_h, roi_w), dtype=np.float32)
        local_cx = int(round(cx - x1))
        local_cy = int(round(cy - y1))
        ax_w = max(2, int(round(bw * 0.5)))
        ax_h = max(2, int(round(bh * 0.5)))
        cv2.ellipse(mask, (local_cx, local_cy), (ax_w, ax_h), 0, 0, 360, 1.0, -1)

        f_k = max(7, int(round(min(bw, bh) * 0.20)))
        if f_k % 2 == 0:
            f_k += 1
        mask = cv2.GaussianBlur(mask, (f_k, f_k), 0)
        if alpha < 0.999:
            mask = mask * float(alpha)

        mask_3 = mask[:, :, None]
        blended = (blurred_roi.astype(np.float32) * mask_3 + roi.astype(np.float32) * (1.0 - mask_3))
        out[y1:y2, x1:x2] = np.clip(blended, 0, 255).astype(np.uint8)

    return out


def blur_faces_in_video(
    input_video_path: Union[str, Path],
    output_video_path: Union[str, Path],
    model_path: Optional[Union[str, Path]] = None,
    score_threshold: float = 0.55,
    detector: Optional[Any] = None,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> Dict[str, Any]:
    """
    Detect and smoothly blur faces in a video file while preserving audio and browser H.264 compatibility.
    """
    src_path = Path(input_video_path).resolve()
    dst_path = Path(output_video_path).resolve()
    if not src_path.is_file():
        raise FileNotFoundError(f"Input video not found: {src_path}")
    dst_path.parent.mkdir(parents=True, exist_ok=True)

    active_detector = detector or _YuNetFaceDetector(
        _find_yunet_model(model_path),
        score_threshold=score_threshold,
    )

    cap = cv2.VideoCapture(str(src_path))
    if not cap.isOpened():
        raise RuntimeError(f"Unable to open video for face blurring: {src_path}")

    fps = float(cap.get(cv2.CAP_PROP_FPS) or 25.0)
    if fps <= 1.0 or fps > 120.0:
        fps = 25.0
    width = 0
    height = 0

    # Pass 1: Detect per-frame boxes + lightweight scene cut marks
    raw_detections: List[List[BoxRecord]] = []
    scene_cuts: List[int] = []
    prev_thumb: Optional[np.ndarray] = None

    try:
        frame_idx = 0
        while True:
            ok, frame = cap.read()
            if not ok or frame is None:
                break
            fh, fw = frame.shape[:2]
            if width <= 0 or height <= 0:
                width, height = fw, fh
            elif (fw, fh) != (width, height):
                frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)

            thumb = cv2.resize(frame, (64, 64), interpolation=cv2.INTER_AREA)
            if prev_thumb is not None:
                diff = float(np.mean(np.abs(thumb.astype(np.int16) - prev_thumb.astype(np.int16))))
                if diff > 30.0:
                    scene_cuts.append(frame_idx)
            prev_thumb = thumb

            boxes = active_detector.detect(frame)
            raw_detections.append(boxes)
            frame_idx += 1
    finally:
        cap.release()

    total_frames = len(raw_detections)
    if total_frames == 0:
        raise RuntimeError(f"Video contains zero readable frames: {src_path}")

    if progress_callback:
        progress_callback(45, f"تم فحص {total_frames} إطاراً للبحث عن الوجوه...")

    planned_boxes = plan_blur_timeline(
        raw_detections,
        frame_width=width,
        frame_height=height,
        scene_cuts=scene_cuts,
    )
    blurred_frames_count = sum(1 for b in planned_boxes if b)

    duration_sec = round(total_frames / fps, 2)
    if blurred_frames_count == 0:
        if str(src_path) != str(dst_path):
            shutil.copyfile(src_path, dst_path)
        return {
            "applied": False,
            "faces_detected": False,
            "total_frames": total_frames,
            "blurred_frames": 0,
            "duration": duration_sec,
            "resolution": f"{width}x{height}",
        }

    # Pass 2: Render blurred silent track then remux with original audio as H.264 MP4
    raw_silent_tmp = dst_path.parent / f"_faceblur_silent_{dst_path.stem}.mp4"
    rendered_tmp = dst_path.parent / f"_faceblur_final_{dst_path.stem}.mp4"

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(raw_silent_tmp), fourcc, fps, (width, height))
    if not writer.isOpened():
        raise RuntimeError("Failed to initialize VideoWriter for face blur output.")

    cap2 = cv2.VideoCapture(str(src_path))
    if not cap2.isOpened():
        writer.release()
        raise RuntimeError(f"Unable to reopen video for face blur pass 2: {src_path}")

    try:
        idx = 0
        while True:
            ok, frame = cap2.read()
            if not ok or frame is None:
                break
            if frame.shape[1] != width or frame.shape[0] != height:
                frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
            boxes = planned_boxes[idx] if idx < len(planned_boxes) else []
            out_frame = _apply_feathered_oval_blur(frame, boxes) if boxes else frame
            writer.write(out_frame)
            idx += 1
    finally:
        cap2.release()
        writer.release()

    if progress_callback:
        progress_callback(82, "جاري ضغط الفيديو المعتمد ودمج الصوت الأصلي عبر FFmpeg...")

    ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
    cmd = [
        ffmpeg_bin,
        "-y",
        "-i", str(raw_silent_tmp),
        "-i", str(src_path),
        "-map", "0:v:0",
        "-map", "1:a?",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        "-shortest",
        str(rendered_tmp),
    ]
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        rendered_tmp.replace(dst_path)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"FFmpeg audio/video remux after face blur failed: {exc.stderr.strip()}") from exc
    finally:
        for tmp_f in (raw_silent_tmp, rendered_tmp):
            try:
                if tmp_f.is_file():
                    tmp_f.unlink()
            except OSError:
                pass

    return {
        "applied": True,
        "faces_detected": True,
        "total_frames": total_frames,
        "blurred_frames": blurred_frames_count,
        "duration": duration_sec,
        "resolution": f"{width}x{height}",
    }
