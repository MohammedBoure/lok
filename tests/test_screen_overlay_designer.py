#!/usr/bin/env python3
"""
Tests for the interactive persistent screen note / phone overlay designer:
- Font & effect catalogs and TTF font resolution
- Custom (x_pct, y_pct) FFmpeg drawtext filter generation and animated effects
- Real FFmpeg burn-in verification on synthetic vertical video
- Pipeline bridge normalization & cuts re-render persistence
- API endpoints (/api/overlay-options, /api/overlay-fonts/{font_id}/file)
- UI DOM/JS/CSS contracts and zero U+0669 check
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from starlette.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from web.pipeline_bridge import (
    build_screen_overlay_annotation,
    normalize_screen_overlay_options,
    update_cuts_text_and_rerender,
)
from web.server import _parse_screen_overlay_options, app
from web.video_annotator import (
    OVERLAY_EFFECTS,
    OVERLAY_FONTS,
    _build_drawtext_filter,
    annotate_video,
    get_overlay_effects_list,
    get_overlay_fonts_list,
    resolve_overlay_font,
)


def test_overlay_fonts_and_effects_catalogs():
    fonts = get_overlay_fonts_list()
    effects = get_overlay_effects_list()

    assert len(fonts) >= 5
    font_ids = {f["id"] for f in fonts}
    assert {"tahoma_bold", "arial_bold", "segoe_bold"}.issubset(font_ids)

    for f in fonts:
        assert f["name_ar"]
        assert f["name_en"]
        assert "font_url" in f

    effect_ids = {e["id"] for e in effects}
    assert {e["id"] for e in OVERLAY_EFFECTS} == effect_ids
    assert {
        "solid_dark",
        "luxury_gold",
        "clean_outline",
        "neon_glow",
        "fade_in",
        "pulse_glow",
        "slide_up",
        "urgent_red",
    }.issubset(effect_ids)

    resolved = resolve_overlay_font("arial_bold")
    assert resolved["id"] == "arial_bold"
    assert resolve_overlay_font("nonexistent_font")["id"] in {f["id"] for f in OVERLAY_FONTS}


def test_build_drawtext_filter_custom_coords_and_effects():
    # Custom dragged coordinates (x_pct=0.25, y_pct=0.22) + clean_outline
    flt_outline = _build_drawtext_filter(
        {
            "text": "0550 12 34 56",
            "start_sec": 0.0,
            "end_sec": 8.0,
            "style": "persistent_bottom",
            "position": "custom_xy",
            "x_pct": 0.25,
            "y_pct": 0.22,
            "effect": "clean_outline",
            "size": "large",
            "text_color": "gold",
        },
        video_width=1080,
        video_height=1920,
    )
    assert "fix_bounds=1" in flt_outline
    assert "0.2500" in flt_outline
    assert "0.2200" in flt_outline
    assert "borderw=3" in flt_outline
    assert "fontcolor=0xFBBF24" in flt_outline
    assert "box=0" in flt_outline

    # Animated effects must escape internal commas for ffmpeg filtergraph
    for fx_id in ("fade_in", "pulse_glow", "slide_up"):
        flt_anim = _build_drawtext_filter(
            {
                "text": "0550 12 34 56",
                "start_sec": 0.0,
                "end_sec": 6.0,
                "style": "persistent_bottom",
                "position": "custom_xy",
                "x_pct": 0.5,
                "y_pct": 0.85,
                "effect": fx_id,
            },
            video_width=1080,
            video_height=1920,
        )
        assert "\\," in flt_anim or "alpha=" in flt_anim

    # Legacy call with no custom options keeps original persistent_bottom defaults
    flt_legacy = _build_drawtext_filter(
        {
            "text": "0550 12 34 56",
            "start_sec": 0.0,
            "end_sec": 6.0,
            "style": "persistent_bottom",
            "large_font": True,
        },
        video_width=1080,
        video_height=1920,
    )
    assert "fontsize=64" in flt_legacy
    assert "boxcolor=black@0.78" in flt_legacy
    assert "fontcolor=white" in flt_legacy


def test_real_ffmpeg_burns_dragged_arabic_overlay_with_font_and_effects(tmp_path: Path):
    src_mp4 = tmp_path / "src_vert.mp4"
    out_mp4 = tmp_path / "out_overlay.mp4"

    gen = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=#182436:s=540x960:d=1.5:r=24",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(src_mp4),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if gen.returncode != 0:
        pytest.skip(f"ffmpeg synthetic source skipped: {gen.stderr[:200]}")

    res = annotate_video(
        input_video=src_mp4,
        output_video=out_mp4,
        annotations=[
            {
                "text": "0550 12 34 56 - شقة فاخرة",
                "style": "persistent_bottom",
                "start_time": 0.0,
                "end_time": 1.5,
                "x_pct": 0.30,
                "y_pct": 0.24,
                "font_id": "tahoma_bold",
                "effect": "slide_up",
                "size": "medium",
                "text_color": "gold",
            }
        ],
    )
    assert res["status"] == "ok", res
    assert res["annotations_applied"] == 1
    assert out_mp4.exists() and out_mp4.stat().st_size > 5000


def test_pipeline_bridge_normalize_and_rerender_preserves_screen_overlay(tmp_path: Path, monkeypatch):
    import web.pipeline_bridge as pb

    monkeypatch.setattr(pb, "REPO_ROOT", tmp_path)

    norm = normalize_screen_overlay_options(
        {
            "text": "0555 99 88 77",
            "x_pct": 1.4,  # Should clamp to 0.95
            "y_pct": -0.2,  # Should clamp to 0.05
            "font": "arial_bold",
            "effect": "neon_glow",
            "size": "large",
            "text_color": "cyan",
        }
    )
    assert norm is not None
    assert norm["x_pct"] == 0.95
    assert norm["y_pct"] == 0.05
    assert norm["font"] == "arial_bold"
    assert norm["effect"] == "neon_glow"
    assert norm["size"] == "large"
    assert norm["text_color"] == "cyan"

    ann = build_screen_overlay_annotation(norm, total_duration=12.0, target_h=1920)
    assert ann["style"] == "persistent_bottom"
    assert ann["x_pct"] == 0.95
    assert ann["y_pct"] == 0.05
    assert ann["font_id"] == "arial_bold"
    assert ann["effect"] == "neon_glow"
    assert ann["is_screen_overlay"] is True

    job_id = "test_overlay_rerender"
    sandbox = tmp_path / "outputs" / "jobs" / job_id / "sandbox"
    sandbox.mkdir(parents=True, exist_ok=True)
    clean_vid = sandbox / f"clean_visual_{job_id}.mp4"
    clean_vid.write_bytes(b"video_bytes")

    summary_data = {
        "job_id": job_id,
        "duration": 10.0,
        "voice": "ar-XA-Standard-A",
        "music_muted": True,
        "clean_visual_source": str(clean_vid),
        "editable_cuts": [{"scene_index": 1, "start_sec": 0.0, "end_sec": 5.0, "text": "الصالون"}],
        "shot_timeline": [{"start_sec": 0.0, "end_sec": 5.0, "title": "الصالون", "description": "الصالون"}],
        "render_config": {"src_duration": 10.0, "mute_music": True},
        "metadata": {},
    }
    (sandbox / f"summary_{job_id}.json").write_text(json.dumps(summary_data), encoding="utf-8")

    wav_path = sandbox / f"narration_{job_id}.wav"
    wav_path.write_bytes(b"RIFF....")

    captured_annotations = []

    def fake_annotate(*, input_video_path, output_video_path, annotations, **kwargs):
        captured_annotations.extend(annotations)
        Path(output_video_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_video_path).write_bytes(b"mp4_annotated")
        return {"status": "ok", "annotations_applied": len(annotations)}

    def fake_ffmpeg(cmd, *args, **kwargs):
        if isinstance(cmd, list) and cmd:
            Path(cmd[-1]).parent.mkdir(parents=True, exist_ok=True)
            Path(cmd[-1]).write_bytes(b"mp4")
        return MagicMock(returncode=0, stdout="", stderr="")

    with (
        patch("frame_extractor.get_video_metadata", return_value={"width": 720, "height": 1280, "total_duration": 10.0}),
        patch("web.pipeline_bridge.subprocess.run", side_effect=fake_ffmpeg),
        patch("web.pipeline_bridge.synthesize_narration", return_value={"duration": 4.0, "synthesizer": "mock", "file": str(wav_path)}),
        patch("web.pipeline_bridge.annotate_video", side_effect=fake_annotate),
    ):
        updated = update_cuts_text_and_rerender(
            job_id=job_id,
            edited_cuts=[{"scene_index": 1, "start_sec": 0.0, "end_sec": 5.0, "text": "الصالون الواسع"}],
            output_dir=tmp_path / "outputs" / "mobile_cuts",
            screen_overlay={
                "text": "اتصل الآن: 0550112233",
                "x_pct": 0.28,
                "y_pct": 0.18,
                "font": "tahoma_bold",
                "effect": "pulse_glow",
                "size": "large",
                "text_color": "gold",
            },
        )

    assert updated["screen_overlay"]["x_pct"] == 0.28
    assert updated["screen_overlay"]["y_pct"] == 0.18
    assert updated["screen_overlay"]["effect"] == "pulse_glow"
    assert len(captured_annotations) == 1
    assert captured_annotations[0]["text"] == "اتصل الآن: 0550112233"
    assert captured_annotations[0]["effect"] == "pulse_glow"


def test_server_overlay_endpoints_and_form_parser():
    client = TestClient(app)

    resp = client.get("/api/overlay-options")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "ok"
    assert len(payload["fonts"]) >= 5
    assert len(payload["effects"]) >= 6

    available_fonts = [f for f in payload["fonts"] if f.get("available") and f.get("font_url")]
    if available_fonts:
        font_res = client.get(available_fonts[0]["font_url"])
        assert font_res.status_code == 200
        assert len(font_res.content) > 1000

    bad_font = client.get("/api/overlay-fonts/not_in_allowlist/file")
    assert bad_font.status_code == 404

    parsed = _parse_screen_overlay_options(
        {
            "overlay_text": "0550 00 11 22",
            "overlay_x_pct": "0.35",
            "overlay_y_pct": "0.22",
            "overlay_font": "tahoma_bold",
            "overlay_effect": "slide_up",
            "overlay_size": "large",
            "overlay_color": "gold",
        }
    )
    assert parsed is not None
    assert parsed["text"] == "0550 00 11 22"
    assert parsed["x_pct"] == 0.35
    assert parsed["y_pct"] == 0.22
    assert parsed["effect"] == "slide_up"


def test_screen_overlay_ui_dom_js_css_contract():
    html = (REPO_ROOT / "web" / "static" / "index.html").read_text(encoding="utf-8")
    js = (REPO_ROOT / "web" / "static" / "app.js").read_text(encoding="utf-8")
    css = (REPO_ROOT / "web" / "static" / "style.css").read_text(encoding="utf-8")

    # HTML hooks
    assert 'id="btnToggleScreenNoteOptIn"' in html
    assert 'id="screenOverlaySummaryBar"' in html
    assert 'id="screenOverlayModal"' in html
    assert 'id="overlayScreenStage"' in html
    assert 'id="draggableOverlayNode"' in html
    assert 'id="overlayFontList"' in html
    assert 'id="overlayEffectList"' in html
    assert '20261113_user_guide' in html

    # JS handlers & API integration
    assert "/api/overlay-options" in js
    assert "setupScreenOverlayDesigner" in js
    assert "pointerdown" in js
    assert 'formData.append("overlay_text"' in js
    assert 'formData.append("overlay_x_pct"' in js
    assert 'formData.append("overlay_effect"' in js

    # CSS styles & keyframe animations
    assert ".overlay-screen-stage" in css
    assert ".draggable-overlay-node" in css
    assert "@keyframes lokOverlaySlideUp" in css
    assert "@keyframes lokOverlayPulse" in css

    for content in (html, js, css):
        assert "\u0669" not in content


def test_top_right_user_guide_button_and_first_visit_highlight_contract():
    html = (REPO_ROOT / "web" / "static" / "index.html").read_text(encoding="utf-8")
    js = (REPO_ROOT / "web" / "static" / "app.js").read_text(encoding="utf-8")
    css = (REPO_ROOT / "web" / "static" / "style.css").read_text(encoding="utf-8")

    # Top-right header guide button & login guide button; modal hidden on load (no forced auto-open)
    assert 'id="btnOpenUserGuide"' in html
    assert 'id="btnLoginUserGuide"' in html
    assert 'id="userGuideHighlightTip"' in html
    assert 'id="userGuideModal"' in html
    assert 'id="userGuideModal" class="lok-settings-overlay user-guide-modal" style="display: none;"' in html
    assert html.index('class="header-brand-group"') < html.index('id="btnOpenUserGuide"') < html.index('class="lok-header-logo"')

    # First-visit highlight without auto-opening modal
    assert 'lok_user_guide_seen' in js
    assert 'setupUserGuide' in js
    assert 'is-first-visit-highlight' in js
    assert 'openUserGuideModal' in js
    assert 'clearUserGuideHighlight' in js

    # Highlight & modal styling
    assert '@keyframes lokGuidePulse' in css
    assert '.btn-user-guide.is-first-visit-highlight' in css
    assert '.user-guide-modal' in css

    for content in (html, js, css):
        assert "\u0669" not in content

