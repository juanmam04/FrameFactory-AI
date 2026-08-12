"""Tests for Documentary 100-days MVP (offline-friendly)."""
from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from src.documentary.assemble_service import build_preview
from src.documentary.flow_pack import export_flow_pack, load_shot_list, update_shot_status
from src.documentary.import_images import import_images, replace_shot_image
from src.documentary.project import (
    create_project,
    load_project,
    project_dir,
)
from src.documentary.script_service import approve_script, generate_documentary_script, save_edited_script
from src.voice_generator import generar_voz


@pytest.fixture()
def tmp_projects(monkeypatch, tmp_path):
    root = tmp_path / "projects"
    root.mkdir()
    monkeypatch.setattr("src.documentary.project.PROJECTS_ROOT", root)
    return root


def test_create_persist_reload(tmp_projects):
    p = create_project("The Rise and Fall of WeWork", project_id="100-days-test", target_words=1200)
    assert p["id"] == "100-days-test"
    assert (tmp_projects / "100-days-test" / "project.json").exists()
    p2 = load_project("100-days-test")
    assert p2["topic"].startswith("The Rise")
    assert p2["checkpoints"]["script_ready"] is False


def test_script_approve_flow_import_replace(tmp_projects, tmp_path):
    p = create_project("WeWork story", project_id="doc-a", target_words=400, research_notes="SoftBank invested.")
    generate_documentary_script(p, use_llm=False)
    p = load_project("doc-a")
    assert p["checkpoints"]["script_ready"] is True
    assert p["script_approved"] is False

    save_edited_script(p, p["script"] + " SoftBank remained a major backer.")
    p = load_project("doc-a")
    approve_script(p)
    p = load_project("doc-a")
    assert p["script_approved"] is True

    export_flow_pack(p, use_llm=False, rebuild_visuals=True)
    p = load_project("doc-a")
    assert p["checkpoints"]["flow_pack_ready"] is True
    data = load_shot_list("doc-a")
    shots = data["shots"]
    assert 5 <= len(shots) <= 80
    assert (project_dir("doc-a") / "flow-pack" / "shots" / "001.txt").exists()

    update_shot_status("doc-a", 1, "generated")
    assert load_shot_list("doc-a")["shots"][0]["status"] == "generated"

    src = tmp_path / "flow_out"
    src.mkdir()
    for s in shots:
        n = int(s["number"])
        if n == 2:
            continue
        img = Image.new("RGB", (1280, 720), color=(n * 3 % 255, 40, 80))
        img.save(src / f"{n:03d}.png")

    report = import_images(p, src)
    assert "002" in report["missing"]
    assert report["ready"] == len(shots) - 1

    one = tmp_path / "002.png"
    Image.new("RGB", (1280, 720), color=(10, 200, 10)).save(one)
    replace_shot_image(p, 2, one)
    assert (project_dir("doc-a") / "images" / "002.png").exists()

    p_b = create_project("Other", project_id="doc-b", target_words=300)
    generate_documentary_script(p_b, use_llm=False)
    approve_script(p_b)
    export_flow_pack(load_project("doc-b"), use_llm=False, rebuild_visuals=True)
    assert (project_dir("doc-a") / "images" / "001.png").exists()
    assert not (project_dir("doc-b") / "images" / "001.png").exists()


def test_voice_fail_without_keys(monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="No se pudo generar voz"):
        generar_voz("Hello world test.", nombre_archivo="doc_test_empty")


def test_preview_warns_missing(tmp_projects):
    p = create_project("X", project_id="doc-prev", target_words=300)
    generate_documentary_script(p, use_llm=False)
    approve_script(p)
    export_flow_pack(load_project("doc-prev"), use_llm=False, rebuild_visuals=True)
    prev = build_preview(load_project("doc-prev"))
    assert prev["missing_images"]
    assert prev["voice_ok"] is False
