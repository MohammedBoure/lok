"""Unit and integration tests for privacy face blurring and UI/API integration."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import List

import cv2
import numpy as np
from starlette.testclient import TestClient

from web.auth_db import init_db
from web.face_blur import (
    DEFAULT_YUNET_MODEL,
    _YuNetFaceDetector,
    _find_yunet_model,
    blur_faces_in_video,
    plan_blur_timeline,
)
from web.pipeline_bridge import _maybe_apply_face_blur, extract_directives
from web.server import app
from web.video_editor import probe_video_stream

REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = REPO_ROOT / "web" / "static"


def _make_sample_video_with_audio(dest: Path, frames: int = 18, width: int = 320, height: int = 240) -> None:
    """Create a synthetic checkerboard+audio MP4 for real FFmpeg/OpenCV face blur testing."""
    ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
    raw_mp4 = dest.with_name(f"_raw_{dest.name}")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(raw_mp4), fourcc, 15.0, (width, height))
    assert writer.isOpened()
    try:
        for i in range(frames):
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            # High-contrast pattern in the middle ("face" zone) so blur measurably softens it
            for y in range(60, 140, 8):
                for x in range(120, 200, 8):
                    if ((x + y) // 8) % 2 == 0:
                        frame[y : y + 8, x : x + 8] = (230, 200, 180)
                    else:
                        frame[y : y + 8, x : x + 8] = (20, 30, 40)
            # Sharp bright square near bottom-left ("product" zone) outside face region
            frame[190:225, 15:55] = (40, 240, 80)
            writer.write(frame)
    finally:
        writer.release()

    cmd = [
        ffmpeg_bin,
        "-y",
        "-i", str(raw_mp4),
        "-f", "lavfi",
        "-i", f"sine=frequency=440:duration={frames / 15.0:.2f}",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-shortest",
        str(dest),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    raw_mp4.unlink(missing_ok=True)


def test_plan_blur_timeline_anti_glitch_guarantees():
    # Frames 0..19:
    # - Frame 2 has a 1-frame isolated false positive (must be dropped)
    # - Track runs frames 6..9 and 12..14 (short 2-frame profile dropout bridged cleanly)
    # - Hard scene cut at frame 17 must stop blur before frame 17 (no bleed into new clip)
    detections: List[List[tuple]] = [[] for _ in range(20)]
    detections[2] = [(50.0, 50.0, 30.0, 30.0, 0.7)]
    for f in (6, 7, 8, 9, 12, 13, 14):
        detections[f] = [(160.0 + (f - 6) * 2.0, 100.0, 40.0, 50.0, 0.9)]

    planned = plan_blur_timeline(
        detections,
        frame_width=320,
        frame_height=240,
        scene_cuts=[17],
        min_track_frames=3,
        max_bridge_gap=6,
    )

    # Isolated frame-2 spike discarded completely (0..4 stay empty)
    assert all(len(planned[i]) == 0 for i in range(6))
    # Internal dropout frames 10 and 11 bridged cleanly at full opacity
    assert len(planned[10]) == 1 and planned[10][0][4] == 1.0
    assert len(planned[11]) == 1 and planned[11][0][4] == 1.0
    # Smooth fade-out tail (frames 15..16) stops cleanly before scene cut at frame 17
    assert len(planned[15]) == 1 and planned[15][0][4] < 1.0
    assert all(len(planned[i]) == 0 for i in range(17, 20))


def test_plan_blur_timeline_edge_exit_does_not_linger():
    # Face moving rightward out of frame border (320px wide)
    detections: List[List[tuple]] = [[] for _ in range(15)]
    for idx, f in enumerate((2, 3, 4, 5)):
        detections[f] = [(270.0 + idx * 12.0, 120.0, 40.0, 50.0, 0.92)]  # exits near right edge at 306

    planned = plan_blur_timeline(detections, frame_width=320, frame_height=240)
    # Edge tail fades cleanly within <= 3 frames and stops completely
    assert len(planned[6]) == 1
    assert planned[6][0][0] > planned[5][0][0]  # velocity slides outward instead of freezing on wall
    assert all(len(planned[i]) == 0 for i in range(9, 15))


def test_yunet_model_loads_cleanly():
    model_path = _find_yunet_model()
    assert model_path == DEFAULT_YUNET_MODEL
    detector = _YuNetFaceDetector(model_path)
    blank = np.zeros((240, 320, 3), dtype=np.uint8)
    assert detector.detect(blank) == []


def test_blur_faces_in_video_blurs_face_preserves_product_and_audio(tmp_path: Path):
    src = tmp_path / "src.mp4"
    dst = tmp_path / "blurred.mp4"
    _make_sample_video_with_audio(src, frames=16)

    class _StubDetector:
        def detect(self, frame_bgr):
            return [(160.0, 100.0, 60.0, 65.0, 0.95)]

    stats = blur_faces_in_video(src, dst, detector=_StubDetector())
    assert stats["applied"] is True
    assert stats["faces_detected"] is True
    assert stats["blurred_frames"] == 16

    info = probe_video_stream(dst)
    assert info["codec"] == "h264"
    assert info["has_audio"] is True

    # Verify center "face" region was blurred (variance dropped sharply) while bottom-left "product" stayed sharp
    cap_src = cv2.VideoCapture(str(src))
    cap_dst = cv2.VideoCapture(str(dst))
    ok1, f_src = cap_src.read()
    ok2, f_dst = cap_dst.read()
    cap_src.release()
    cap_dst.release()
    assert ok1 and ok2

    face_std_before = float(np.std(f_src[75:125, 135:185]))
    face_std_after = float(np.std(f_dst[75:125, 135:185]))
    assert face_std_after < face_std_before * 0.45

    # Untouched green product box stays intact and high green channel
    product_patch = f_dst[195:220, 20:50]
    assert float(np.mean(product_patch[:, :, 1])) > 200.0


def test_blur_faces_in_video_no_faces_keeps_clean(tmp_path: Path):
    src = tmp_path / "src.mp4"
    dst = tmp_path / "out.mp4"
    _make_sample_video_with_audio(src, frames=6)

    class _EmptyDetector:
        def detect(self, frame_bgr):
            return []

    stats = blur_faces_in_video(src, dst, detector=_EmptyDetector())
    assert stats["applied"] is False
    assert stats["faces_detected"] is False
    assert dst.is_file() and dst.stat().st_size > 0


def test_prompt_directive_and_api_endpoints(monkeypatch, tmp_path: Path):
    dirs = extract_directives("أريد فيديو مع تعتيم الوجه وإظهار رقم الهاتف 0558815453")
    assert dirs["blur_faces_requested"] is True
    assert dirs["phone_number"] == "0558815453"

    init_db()
    client = TestClient(app)

    # Unauthenticated request rejected cleanly
    unauth = client.post("/api/blur-faces", files={"video": ("clip.mp4", b"fake", "video/mp4")})
    assert unauth.status_code == 401

    # Authenticate via monkeypatched user + isolated temp dirs + mock face blur function
    tmp_uploads = tmp_path / "uploads"
    tmp_outputs = tmp_path / "outputs"
    tmp_uploads.mkdir()
    tmp_outputs.mkdir()
    monkeypatch.setattr("web.server.UPLOADS_DIR", tmp_uploads)
    monkeypatch.setattr("web.server.OUTPUTS_DIR", tmp_outputs)

    fake_user = {
        "id": 1,
        "username": "tester",
        "business_name": "TestBiz",
        "business_category": "real_estate",
        "role": "user",
    }
    monkeypatch.setattr("web.server._get_authenticated_user_from_form_or_header", lambda req, form: fake_user)
    monkeypatch.setattr("web.server.check_quota", lambda uid: (True, "ok", {"remaining": 10}))
    monkeypatch.setattr("web.server.record_generation", lambda **kwargs: None)

    def _fake_blur(input_video_path, output_video_path, **kwargs):
        Path(output_video_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_video_path).write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 64)
        return {
            "applied": True,
            "faces_detected": True,
            "total_frames": 30,
            "blurred_frames": 24,
            "duration": 2.0,
            "resolution": "720x1280",
        }

    monkeypatch.setattr("web.face_blur.blur_faces_in_video", _fake_blur)

    resp = client.post(
        "/api/blur-faces",
        files={"video": ("clip.mp4", b"fake-video-bytes", "video/mp4")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["standalone_mode"] == "face_blur_only"
    assert body["blur_faces_enabled"] is True
    assert body["blur_faces_applied"] is True
    assert body["faces_blurred_frames"] == 24
    assert body["video_url"].startswith("/outputs/mobile_cuts/cut_")
    mirrored = tmp_outputs / "mobile_cuts" / Path(body["video_url"]).name
    assert mirrored.is_file()

    # Also verify /api/upload-and-process forwards blur_faces=true to process_mobile_video
    captured = {}

    def _fake_process(**kwargs):
        captured.update(kwargs)
        return {
            "job_id": kwargs["job_id"],
            "status": "completed",
            "video_url": f"/outputs/mobile_cuts/cut_{kwargs['job_id']}.mp4",
            "blur_faces_enabled": bool(kwargs.get("blur_faces")),
            "blur_faces_applied": bool(kwargs.get("blur_faces")),
        }

    monkeypatch.setattr("web.server.process_mobile_video", _fake_process)
    resp2 = client.post(
        "/api/upload-and-process",
        data={"blur_faces": "true"},
        files={"video": ("clip.mp4", b"fake-video-bytes", "video/mp4")},
    )
    assert resp2.status_code == 200
    assert captured.get("blur_faces") is True
    assert resp2.json()["blur_faces_applied"] is True


def test_pipeline_bridge_maybe_apply_face_blur_replaces_cut_before_overlays(monkeypatch, tmp_path: Path):
    cut_path = tmp_path / "cut_abc.mp4"
    cut_path.write_bytes(b"original-video")
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()

    # When disabled: untouched
    off_meta = _maybe_apply_face_blur(
        final_cut_path=cut_path,
        job_id="abc",
        job_sandbox_dir=sandbox,
        blur_enabled=False,
    )
    assert off_meta == {"enabled": False, "applied": False, "faces_detected": False, "blurred_frames": 0}
    assert cut_path.read_bytes() == b"original-video"

    # When enabled & faces detected: replaces final_cut_path atomically
    def _fake_blur(input_video_path, output_video_path, **kwargs):
        Path(output_video_path).write_bytes(b"blurred-video")
        return {"applied": True, "faces_detected": True, "blurred_frames": 12, "total_frames": 20}

    monkeypatch.setattr("web.face_blur.blur_faces_in_video", _fake_blur)
    on_meta = _maybe_apply_face_blur(
        final_cut_path=cut_path,
        job_id="abc",
        job_sandbox_dir=sandbox,
        blur_enabled=True,
    )
    assert on_meta["enabled"] is True
    assert on_meta["applied"] is True
    assert on_meta["blurred_frames"] == 12
    assert cut_path.read_bytes() == b"blurred-video"


def test_frontend_face_blur_controls_and_notice_present():
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    css = (STATIC_DIR / "style.css").read_text(encoding="utf-8")

    assert 'id="btnToggleFaceBlurOptIn"' in html
    assert 'id="faceBlurTipNotice"' in html
    assert 'id="settingToggleFaceBlur"' in html
    assert 'id="btnBlurFacesOnly"' not in html
    assert 'id="resultFaceBlurPill"' in html
    assert "أمام الوجه" in html

    assert "blurFaces: false" in js
    assert 'formData.append("blur_faces"' in js
    assert "resultFaceBlurPill" in js

    assert ".face-blur-tip-notice" in css
    assert ".result-faceblur-pill" in css
