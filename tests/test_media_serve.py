"""Range serving + render resume helpers."""
from __future__ import annotations

import pytest

from src.documentary.media_serve import content_disposition, parse_byte_range
from src.video_assembler import _still_clip_name


@pytest.fixture()
def tmp_projects(monkeypatch, tmp_path):
    root = tmp_path / "projects"
    root.mkdir()
    monkeypatch.setenv("FRAMEFACTORY_PROJECTS_DIR", str(root))
    monkeypatch.setattr("src.documentary.project.PROJECTS_ROOT", root)
    return root


def test_parse_byte_range_full_and_suffix():
    assert parse_byte_range(None, 1000) == (0, 999, 200)
    assert parse_byte_range("bytes=0-499", 1000) == (0, 499, 206)
    assert parse_byte_range("bytes=500-", 1000) == (500, 999, 206)
    start, end, status = parse_byte_range("bytes=-100", 1000)
    assert (start, end, status) == (900, 999, 206)
    assert parse_byte_range("bytes=0-999", 1000) == (0, 999, 200)


def test_parse_byte_range_clamps():
    start, end, status = parse_byte_range("bytes=980-5000", 1000)
    assert start == 980
    assert end == 999
    assert status == 206


def test_content_disposition_download_vs_inline():
    att = content_disposition("ep.mp4", download=True)
    assert att.startswith("attachment;")
    assert "ep.mp4" in att
    inline = content_disposition("ep.mp4", download=False)
    assert inline.startswith("inline;")


def test_still_clip_name_is_stable(tmp_path):
    img = tmp_path / "001.png"
    img.write_bytes(b"hello-still")
    a = _still_clip_name(img, style="push", seg=6.0, width=1920, height=1080, fps=24, crf=20, look="soft", fade=0.28)
    b = _still_clip_name(img, style="push", seg=6.0, width=1920, height=1080, fps=24, crf=20, look="soft", fade=0.28)
    c = _still_clip_name(img, style="pull", seg=6.0, width=1920, height=1080, fps=24, crf=20, look="soft", fade=0.28)
    assert a == b
    assert a.endswith(".mp4")
    assert a != c


def test_set_render_state_resume_keeps_percent(tmp_projects):
    from src.documentary.assemble_service import set_render_state
    from src.documentary.project import create_project, load_project

    p = create_project("Resume render", project_id="resume-dl", target_words=800)
    set_render_state(p, "running", message="start")
    rec = p["render"]
    rec["percent"] = 42
    rec["kb_done"] = 9
    rec["kb_total"] = 20
    rec["started_at"] = "2026-08-14T12:00:00Z"
    p["render"] = rec
    set_render_state(p, "running", message="reanudando", reset_progress=False)
    p2 = load_project("resume-dl")
    rec2 = p2["render"]
    assert rec2["percent"] == 42
    assert rec2["kb_done"] == 9
    assert rec2["started_at"] == "2026-08-14T12:00:00Z"
    assert rec2["message"] == "reanudando"
